from __future__ import annotations

import csv
import json
import math
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from PIL import Image, ImageDraw

from ...config import load_yaml
from ..downloads import inspect_video


class SubjectLockError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SubjectLockThresholds:
    max_center_drift_px: float
    max_scale_change_pct: float
    min_tracking_success_rate: float
    sample_count: int = 11
    analysis_width: int = 320
    min_component_pixels: int = 20

    def __post_init__(self) -> None:
        if self.max_center_drift_px <= 0 or self.max_scale_change_pct <= 0:
            raise SubjectLockError("subject-lock drift and scale thresholds must be positive")
        if not 0 < self.min_tracking_success_rate <= 1:
            raise SubjectLockError("subject-lock tracking success rate must be within (0, 1]")
        if self.sample_count < 2 or self.analysis_width < 32 or self.min_component_pixels < 1:
            raise SubjectLockError("subject-lock sampling configuration is invalid")

    def evidence(self) -> dict[str, float]:
        return {
            "max_center_drift_px": self.max_center_drift_px,
            "max_scale_change_pct": self.max_scale_change_pct,
            "min_tracking_success_rate": self.min_tracking_success_rate,
        }


@dataclass(frozen=True, slots=True)
class SubjectBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0 or self.width <= 0 or self.height <= 0:
            raise SubjectLockError("subject box coordinates are invalid")

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(frozen=True, slots=True)
class TrackedSubject:
    box: SubjectBox
    confidence: float


@dataclass(frozen=True, slots=True)
class SubjectObservation:
    frame_index: int
    timestamp_seconds: float
    box: SubjectBox | None
    tracking_confidence: float
    dx: float | None = None
    dy: float | None = None
    distance: float | None = None
    width_change_pct: float | None = None
    height_change_pct: float | None = None
    area_change_pct: float | None = None


@dataclass(frozen=True, slots=True)
class SubjectLockResult:
    measurement_scope: str
    frames_sampled: int
    frames_tracked: int
    tracking_success_rate: float
    first_to_last_dx_px: float | None
    first_to_last_dy_px: float | None
    max_abs_dx_px: float | None
    max_abs_dy_px: float | None
    max_center_distance_px: float | None
    first_to_last_width_change_pct: float | None
    first_to_last_height_change_pct: float | None
    max_scale_change_pct: float | None
    diagnostic_status: str
    thresholds: SubjectLockThresholds
    observations: tuple[SubjectObservation, ...]

    def evidence(self, *, run_id: str | None = None) -> dict[str, Any]:
        result = {
            "schema_version": "subject-lock-v1",
            "measurement_scope": self.measurement_scope,
            "frames_sampled": self.frames_sampled,
            "frames_tracked": self.frames_tracked,
            "tracking_success_rate": _rounded(self.tracking_success_rate),
            "first_to_last_dx_px": _rounded(self.first_to_last_dx_px),
            "first_to_last_dy_px": _rounded(self.first_to_last_dy_px),
            "max_abs_dx_px": _rounded(self.max_abs_dx_px),
            "max_abs_dy_px": _rounded(self.max_abs_dy_px),
            "max_center_distance_px": _rounded(self.max_center_distance_px),
            "first_to_last_width_change_pct": _rounded(self.first_to_last_width_change_pct),
            "first_to_last_height_change_pct": _rounded(self.first_to_last_height_change_pct),
            "max_scale_change_pct": _rounded(self.max_scale_change_pct),
            "diagnostic_status": self.diagnostic_status,
            "thresholds": self.thresholds.evidence(),
            "human_qa_authority": "not_automatic",
        }
        if run_id:
            result["run_id"] = run_id
        return result


class SubjectTracker(Protocol):
    measurement_scope: str

    def track(self, frame: Image.Image, previous: SubjectBox | None = None) -> TrackedSubject | None:
        ...


class ColorRegionSubjectTracker:
    """Track the dominant connected red region as a limited Lady LaLa subject proxy."""

    measurement_scope = "color_region_proxy"

    def __init__(self, *, analysis_width: int = 320, min_component_pixels: int = 20) -> None:
        self.analysis_width = analysis_width
        self.min_component_pixels = min_component_pixels

    def track(self, frame: Image.Image, previous: SubjectBox | None = None) -> TrackedSubject | None:
        source = frame.convert("RGB")
        scale = min(1.0, self.analysis_width / source.width)
        size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
        reduced = source.resize(size, Image.Resampling.NEAREST)
        pixels = reduced.load()
        mask = {
            (x, y)
            for y in range(reduced.height)
            for x in range(reduced.width)
            if _is_red_proxy(*pixels[x, y])
        }
        components: list[tuple[int, tuple[int, int, int, int]]] = []
        while mask:
            seed = mask.pop()
            stack = [seed]
            min_x = max_x = seed[0]
            min_y = max_y = seed[1]
            count = 1
            while stack:
                x, y = stack.pop()
                for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if point in mask:
                        mask.remove(point)
                        stack.append(point)
                        count += 1
                        min_x = min(min_x, point[0])
                        max_x = max(max_x, point[0])
                        min_y = min(min_y, point[1])
                        max_y = max(max_y, point[1])
            if count >= self.min_component_pixels:
                components.append((count, (min_x, min_y, max_x + 1, max_y + 1)))
        if not components:
            return None
        inverse = 1.0 / scale
        candidates = [
            (
                count,
                SubjectBox(x1 * inverse, y1 * inverse, (x2 - x1) * inverse, (y2 - y1) * inverse),
            )
            for count, (x1, y1, x2, y2) in components
        ]
        if previous is None:
            count, box = max(candidates, key=lambda item: item[0])
        else:
            count, box = min(
                candidates,
                key=lambda item: (
                    math.hypot(item[1].center_x - previous.center_x, item[1].center_y - previous.center_y)
                    - min(item[0], 1000) / 1000
                ),
            )
        density = count / max(1.0, (box.width * scale) * (box.height * scale))
        confidence = max(0.0, min(1.0, density))
        return TrackedSubject(box, confidence)


def load_subject_lock_thresholds(project_root: Path) -> SubjectLockThresholds:
    data = load_yaml(project_root.resolve() / "configs/video-qa.yaml")
    raw = data.get("subject_lock")
    if not isinstance(raw, dict):
        raise SubjectLockError("video QA configuration requires subject_lock")
    try:
        return SubjectLockThresholds(
            max_center_drift_px=float(raw["max_center_drift_px"]),
            max_scale_change_pct=float(raw["max_scale_change_pct"]),
            min_tracking_success_rate=float(raw["min_tracking_success_rate"]),
            sample_count=int(raw.get("sample_count", 11)),
            analysis_width=int(raw.get("analysis_width", 320)),
            min_component_pixels=int(raw.get("min_component_pixels", 20)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SubjectLockError("video QA subject_lock configuration is invalid") from exc


def analyze_subject_frames(
    frames: Sequence[tuple[int, float, Image.Image]],
    tracker: SubjectTracker,
    thresholds: SubjectLockThresholds,
) -> SubjectLockResult:
    raw: list[SubjectObservation] = []
    previous: SubjectBox | None = None
    for frame_index, timestamp, frame in frames:
        tracked = tracker.track(frame, previous)
        box = tracked.box if tracked else None
        if box is not None:
            previous = box
        raw.append(SubjectObservation(frame_index, timestamp, box, tracked.confidence if tracked else 0.0))
    first = next((item.box for item in raw if item.box is not None), None)
    observations: list[SubjectObservation] = []
    for item in raw:
        if item.box is None or first is None:
            observations.append(item)
            continue
        dx = item.box.center_x - first.center_x
        dy = item.box.center_y - first.center_y
        observations.append(
            SubjectObservation(
                item.frame_index,
                item.timestamp_seconds,
                item.box,
                item.tracking_confidence,
                dx,
                dy,
                math.hypot(dx, dy),
                _pct(item.box.width, first.width),
                _pct(item.box.height, first.height),
                _pct(item.box.area, first.area),
            )
        )
    tracked = [item for item in observations if item.box is not None]
    success = len(tracked) / len(observations) if observations else 0.0
    sufficient = bool(
        observations
        and observations[0].box is not None
        and observations[-1].box is not None
        and success >= thresholds.min_tracking_success_rate
    )
    if not sufficient:
        metrics: tuple[float | None, ...] = (None,) * 8
        status = "INSUFFICIENT_EVIDENCE"
    else:
        last = observations[-1]
        dxs = [item.dx for item in tracked if item.dx is not None]
        dys = [item.dy for item in tracked if item.dy is not None]
        distances = [item.distance for item in tracked if item.distance is not None]
        scale = [
            abs(value)
            for item in tracked
            for value in (item.width_change_pct, item.height_change_pct)
            if value is not None
        ]
        metrics = (
            last.dx,
            last.dy,
            max(abs(value) for value in dxs),
            max(abs(value) for value in dys),
            max(distances),
            last.width_change_pct,
            last.height_change_pct,
            max(scale),
        )
        outside = metrics[4] > thresholds.max_center_drift_px or metrics[7] > thresholds.max_scale_change_pct
        status = "OUTSIDE_THRESHOLD" if outside else "WITHIN_THRESHOLD"
    return SubjectLockResult(
        tracker.measurement_scope,
        len(observations),
        len(tracked),
        success,
        *metrics,
        status,
        thresholds,
        tuple(observations),
    )


def analyze_video_to_artifacts(
    video_path: Path,
    output_dir: Path,
    *,
    thresholds: SubjectLockThresholds,
    run_id: str | None = None,
    tracker: SubjectTracker | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> SubjectLockResult:
    info = inspect_video(video_path, runner=runner)
    tracker = tracker or ColorRegionSubjectTracker(
        analysis_width=thresholds.analysis_width,
        min_component_pixels=thresholds.min_component_pixels,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lala-subject-lock-") as temporary:
        sample_root = Path(temporary)
        frames: list[tuple[int, float, Image.Image]] = []
        for index in range(thresholds.sample_count):
            timestamp = (info.duration_seconds * index / (thresholds.sample_count - 1))
            if index == thresholds.sample_count - 1:
                timestamp = max(0.0, info.duration_seconds - min(0.1, info.duration_seconds / 10))
            target = sample_root / f"frame-{index:03d}.png"
            runner(
                ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.6f}", "-i", str(video_path), "-frames:v", "1", "-y", str(target)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            with Image.open(target) as image:
                frames.append((index, timestamp, image.convert("RGB")))
        result = analyze_subject_frames(frames, tracker, thresholds)
        _write_subject_artifacts(output_dir, result, frames[0][2], run_id=run_id)
    return result


def _write_subject_artifacts(output_dir: Path, result: SubjectLockResult, first_frame: Image.Image, *, run_id: str | None) -> None:
    (output_dir / "subject-lock.json").write_text(
        json.dumps(result.evidence(run_id=run_id), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fields = (
        "frame_index", "timestamp_seconds", "x", "y", "width", "height", "center_x", "center_y", "dx", "dy", "distance", "width_change_pct", "height_change_pct", "area_change_pct", "tracking_confidence"
    )
    with (output_dir / "subject-trajectory.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for item in result.observations:
            box = item.box
            writer.writerow(
                {
                    "frame_index": item.frame_index,
                    "timestamp_seconds": f"{item.timestamp_seconds:.6f}",
                    "x": _csv_value(box.x if box else None),
                    "y": _csv_value(box.y if box else None),
                    "width": _csv_value(box.width if box else None),
                    "height": _csv_value(box.height if box else None),
                    "center_x": _csv_value(box.center_x if box else None),
                    "center_y": _csv_value(box.center_y if box else None),
                    "dx": _csv_value(item.dx),
                    "dy": _csv_value(item.dy),
                    "distance": _csv_value(item.distance),
                    "width_change_pct": _csv_value(item.width_change_pct),
                    "height_change_pct": _csv_value(item.height_change_pct),
                    "area_change_pct": _csv_value(item.area_change_pct),
                    "tracking_confidence": _csv_value(item.tracking_confidence),
                }
            )
    overlay = first_frame.convert("RGB")
    draw = ImageDraw.Draw(overlay)
    tracked = [item for item in result.observations if item.box is not None]
    points = [(round(item.box.center_x), round(item.box.center_y)) for item in tracked if item.box]
    if len(points) > 1:
        draw.line(points, fill="yellow", width=3)
    for item, color in ((tracked[0] if tracked else None, "lime"), (tracked[-1] if tracked else None, "cyan")):
        if item and item.box:
            box = item.box
            draw.rectangle((box.x, box.y, box.x + box.width, box.y + box.height), outline=color, width=4)
            draw.ellipse((box.center_x - 4, box.center_y - 4, box.center_x + 4, box.center_y + 4), fill=color)
    draw.rectangle((0, 0, min(620, overlay.width), 44), fill="black")
    draw.text((8, 5), f"Scope: {result.measurement_scope}", fill="white")
    draw.text((8, 23), f"Diagnostic: {result.diagnostic_status} (not human QA)", fill="white")
    overlay.save(output_dir / "subject-overlay.png", format="PNG", optimize=False)
    overlay.close()


def _is_red_proxy(r: int, g: int, b: int) -> bool:
    return r >= 100 and r >= g * 1.35 and r >= b * 1.2


def _pct(value: float, baseline: float) -> float:
    return (value - baseline) / baseline * 100


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _csv_value(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"
