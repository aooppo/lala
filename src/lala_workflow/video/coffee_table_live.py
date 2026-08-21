from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image

from ..hashing import sha256_file
from ..providers.base import ProviderSubmissionError, ProviderTaskError
from ..providers.motion_base import MotionVideoProvider
from ..providers.runway_video import RunwayMotionProvider
from ..redaction import redact_text
from .campaigns import load_validated_coffee_table_execution_manifest
from .config import load_video_config
from .domain import MediaArtifact, MotionVideoRequest, VideoTaskStatus
from .downloads import inspect_video, validate_media_artifact
from .reporting import blank_review_rows
from .storage import VideoRunContext, VideoRunStorage
from .validation import ExternalInputBlocked


APPROVED_COFFEE_TABLE_MANIFEST = Path(
    "outputs/campaign-execution-manifests/"
    "COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json"
)
APPROVED_COFFEE_TABLE_MANIFEST_SHA256 = (
    "ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea"
)
READY_FOR_OWNER_REVIEW = "READY_FOR_OWNER_REVIEW"


class CoffeeTableLiveStopped(ProviderTaskError):
    code = "coffee_table_live_stopped"

    def __init__(self, message: str, *, run_id: str) -> None:
        super().__init__(f"{message}; run_id={run_id}")
        self.run_id = run_id


@dataclass(frozen=True, slots=True)
class CoffeeTableLiveOutcome:
    run_id: str
    run_dir: Path
    status: str
    manifest_sha256: str
    task_ids: tuple[str, ...]
    raw_artifacts: tuple[Mapping[str, Any], ...]
    delivery: Mapping[str, Any]
    provider_submissions: int
    automatic_paid_retries: int
    automatic_replacement_tasks: int
    actual_credits: float | None
    projected_cost_usd: float


ProviderFactory = Callable[[Callable[[str, str | None, float | None], None]], MotionVideoProvider]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def execute_coffee_table_live(
    project_root: Path,
    *,
    manifest_path: Path,
    manifest_sha256: str,
    confirm_owner_authorized_live: bool,
    max_runway_credits: float,
    max_provider_cost_usd: float,
    environ: Mapping[str, str] | None = None,
    provider_factory: ProviderFactory | None = None,
    manifest_loader: Callable[..., dict[str, Any]] = load_validated_coffee_table_execution_manifest,
    command_runner: CommandRunner = subprocess.run,
    now: datetime | None = None,
) -> CoffeeTableLiveOutcome:
    root = project_root.resolve()
    environment = os.environ if environ is None else environ
    if manifest_path != APPROVED_COFFEE_TABLE_MANIFEST:
        raise ExternalInputBlocked("Coffee Table Live requires the exact Owner-approved manifest path")
    if manifest_sha256 != APPROVED_COFFEE_TABLE_MANIFEST_SHA256:
        raise ExternalInputBlocked("Coffee Table Live requires the exact Owner-approved manifest SHA-256")
    if not confirm_owner_authorized_live:
        raise ExternalInputBlocked("Coffee Table Live requires explicit Owner Live authorization")
    if max_runway_credits != 100 or max_provider_cost_usd != 1.0:
        raise ExternalInputBlocked("Coffee Table Live caps must be exactly 100 credits and USD 1.00")
    if environment.get("VIDEO_ALLOW_LIVE_CALLS") != "true":
        raise ExternalInputBlocked("live video calls require exact VIDEO_ALLOW_LIVE_CALLS=true")
    credential = str(environment.get("RUNWAYML_API_SECRET") or "").strip()
    if not credential:
        raise ExternalInputBlocked("live provider credential is missing: RUNWAYML_API_SECRET")
    manifest = manifest_loader(
        root, manifest_path=manifest_path, manifest_sha256=manifest_sha256
    )
    _block_prior_execution(root, manifest_sha256)

    storage = VideoRunStorage(root, secrets=(credential,))
    run = storage.create_run("coffee-table-live", now=now)
    raw_dir = root / "outputs/broll" / run.run_id
    delivery_dir = root / "outputs/final" / run.run_id
    raw_dir.mkdir(parents=True, exist_ok=False)
    storage.write_json_new(
        run,
        "coffee-table-live-authorization.json",
        {
            "manifest_path": manifest_path.as_posix(),
            "manifest_sha256": manifest_sha256,
            "parent_plan_sha256": manifest["parent_plan"]["sha256"],
            "owner_authorized_live": True,
            "max_runway_credits": 100,
            "max_provider_cost_usd": 1.0,
            "concurrency": 1,
            "automatic_paid_retries": 0,
            "automatic_replacement_tasks": 0,
        },
    )
    storage.append_event(run, "live_preflight_passed", {"manifest_sha256": manifest_sha256})

    current_task = {"task_id": "", "provider_task_id": None}

    def task_created_sink(task_id: str, _request_id: str | None, credits: float | None) -> None:
        current_task["provider_task_id"] = task_id
        storage.append_event(
            run,
            "provider_task_id_durable",
            {"task_id": current_task["task_id"], "provider_task_id": task_id, "estimated_credits": credits},
        )

    if provider_factory is None:
        config = load_video_config(root, require_inputs=False)
        definition = config.providers["runway"]

        def provider_factory(sink: Callable[[str, str | None, float | None], None]) -> MotionVideoProvider:
            return RunwayMotionProvider(
                definition,
                api_key=credential,
                max_poll_retries=2,
                task_created_sink=sink,
            )

    provider = provider_factory(task_created_sink)
    records: list[dict[str, Any]] = []
    task_ids: list[str] = []
    raw_artifacts: list[MediaArtifact] = []
    actual_credits: float | None = 0.0
    lineage: dict[str, Any] | None = None
    try:
        for index, task in enumerate(manifest["tasks"], start=1):
            if index > 4 or len(task_ids) >= 4:
                raise RuntimeError("fifth provider task is prohibited")
            if sum(float(item["projected_runway_credits"]) for item in manifest["tasks"][:index]) > 100:
                raise RuntimeError("Coffee Table planned credit cap would be exceeded")
            task_id = str(task["task_id"])
            current_task["task_id"] = task_id
            current_task["provider_task_id"] = None
            request = _motion_request(root, run, task, lineage)
            provider.validate_request(request)
            storage.append_event(
                run,
                "task_submitting",
                {"task_id": task_id, "submission_attempt": 1, "planned_credits": 25},
            )
            try:
                durable_id = provider.submit(request)
            except Exception as exc:
                known = current_task.get("provider_task_id")
                status = "STOPPED_AFTER_DURABLE_TASK_ID" if known else "STOPPED_SUBMISSION_AMBIGUOUS"
                records.append(
                    {"task_id": task_id, "status": status, "provider_task_id": known, "error": redact_text(str(exc), secrets=(credential,))}
                )
                raise RuntimeError(status) from exc
            if current_task.get("provider_task_id") is None:
                current_task["provider_task_id"] = durable_id
                storage.append_event(
                    run,
                    "provider_task_id_durable",
                    {"task_id": task_id, "provider_task_id": durable_id, "estimated_credits": None},
                )
            elif current_task["provider_task_id"] != durable_id:
                raise RuntimeError("provider task ID changed after durable persistence")
            task_ids.append(durable_id)
            record = {
                "task_id": task_id,
                "status": "SUBMITTED",
                "provider_task_id": durable_id,
                "submission_attempts": 1,
            }
            records.append(record)
            result = provider.wait(durable_id, request.timeout_seconds)
            storage.append_event(
                run,
                "provider_task_terminal",
                {"task_id": task_id, "provider_task_id": durable_id, "status": result.status.value,
                 "error_code": result.error_code, "error_message": result.error_message,
                 "estimated_credits": result.estimated_credits, "actual_credits": result.actual_credits},
            )
            record.update(
                {
                    "status": result.status.value,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                    "estimated_credits": result.estimated_credits,
                    "actual_credits": result.actual_credits,
                }
            )
            if result.actual_credits is None:
                actual_credits = None
            elif actual_credits is not None:
                actual_credits += float(result.actual_credits)
                if actual_credits > index * 25 or actual_credits > 100:
                    raise RuntimeError("reported Runway credit cap exceeded")
            if result.status is not VideoTaskStatus.SUCCEEDED:
                raise RuntimeError(f"STOPPED_TASK_{result.status.value}")
            artifacts = provider.download_results(
                result, raw_dir, task_id, request.timeout_seconds, 0
            )
            if len(artifacts) != 1:
                raise RuntimeError("each Coffee Table task must yield exactly one MP4")
            artifact = validate_media_artifact(artifacts[0])
            if artifact.width != 1280 or artifact.height != 720 or (artifact.duration_seconds or 0) < 5:
                raise RuntimeError(f"{task_id} output fails frozen media bounds")
            raw_artifacts.append(artifact)
            record["artifact"] = _artifact_evidence(artifact, root)
            if task_id == "TASK-02":
                extracted = raw_dir / "TASK-02-last-valid-frame.png"
                lineage = extract_last_valid_frame(
                    artifact.path, extracted, runner=command_runner
                )
                lineage.update({"source_task_id": "TASK-02", "provider_calls": 0})
                storage.write_json_new(run, "task-04-source-lineage.json", lineage)
        delivery = assemble_coffee_table_delivery(
            tuple(item.path for item in raw_artifacts), delivery_dir, runner=command_runner
        )
        _write_success_evidence(storage, run, manifest, records, raw_artifacts, delivery, lineage, actual_credits)
    except Exception as exc:
        _write_stopped_evidence(storage, run, manifest, records, actual_credits, str(exc))
        raise CoffeeTableLiveStopped(str(exc), run_id=run.run_id) from exc
    return CoffeeTableLiveOutcome(
        run.run_id,
        run.path,
        READY_FOR_OWNER_REVIEW,
        manifest_sha256,
        tuple(task_ids),
        tuple(_artifact_evidence(item, root) for item in raw_artifacts),
        delivery,
        len(task_ids),
        0,
        0,
        actual_credits,
        1.0,
    )


def extract_last_valid_frame(
    source_mp4: Path,
    output_png: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    if output_png.exists():
        raise RuntimeError("last-frame output already exists")
    probe = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=nb_read_frames", "-of",
        "default=nokey=1:noprint_wrappers=1", str(source_mp4),
    ]
    counted = runner(probe, check=True, capture_output=True, text=True, timeout=60)
    try:
        frame_count = int(counted.stdout.strip())
    except (TypeError, ValueError) as exc:
        raise RuntimeError("FFprobe returned an invalid decoded frame count") from exc
    if frame_count <= 0:
        raise RuntimeError("source MP4 has no decodable frame")
    selected = frame_count - 1
    output_png.parent.mkdir(parents=True, exist_ok=True)
    extract = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i",
        str(source_mp4), "-vf", f"select=eq(n\\,{selected})", "-frames:v", "1",
        "-c:v", "png", "-n", str(output_png),
    ]
    runner(extract, check=True, capture_output=True, text=True, timeout=120)
    with Image.open(output_png) as image:
        image.verify()
    return {
        "frame_selector": "LAST_VALID_FRAME",
        "frame_count": frame_count,
        "selected_zero_based_frame_index": selected,
        "source_mp4_path": str(source_mp4),
        "source_mp4_sha256": sha256_file(source_mp4),
        "extracted_png_path": str(output_png),
        "extracted_png_sha256": sha256_file(output_png),
        "ffprobe_argv": probe,
        "ffmpeg_argv": extract,
    }


def assemble_coffee_table_delivery(
    raw_paths: tuple[Path, ...],
    output_dir: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    if len(raw_paths) != 4:
        raise RuntimeError("Coffee Table assembly requires exactly four raw MP4s")
    output_dir.mkdir(parents=True, exist_ok=False)
    master = output_dir / "coffee-table-master-16x9.mp4"
    inputs = [part for path in raw_paths for part in ("-i", str(path))]
    filters = (
        "[0:v]trim=start=0:end=5,fps=24,scale=1280:720,setsar=1,setpts=PTS-STARTPTS[v0];"
        "[1:v]trim=start=0:end=5,fps=24,scale=1280:720,setsar=1,setpts=PTS-STARTPTS[v1];"
        "[2:v]trim=start=0:end=3,fps=24,scale=1280:720,setsar=1,setpts=PTS-STARTPTS[v2];"
        "[3:v]trim=start=0:end=5,fps=24,scale=1280:720,setsar=1,setpts=PTS-STARTPTS,"
        "tpad=stop_mode=clone:stop_duration=2[v3];"
        "[v0][v1][v2][v3]concat=n=4:v=1:a=0,format=yuv420p[v]"
    )
    master_cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", *inputs,
        "-filter_complex", filters, "-map", "[v]", "-an", "-c:v", "libx264",
        "-preset", "medium", "-crf", "18", "-movflags", "+faststart", "-n", str(master),
    ]
    runner(master_cmd, check=True, capture_output=True, text=True, timeout=1800)
    master_evidence = _local_media_evidence(master)
    if abs(float(master_evidence["duration_seconds"]) - 20.0) > 0.12:
        raise RuntimeError("assembled master duration is not twenty seconds")
    variants: dict[str, Any] = {}
    commands: list[list[str]] = [master_cmd]
    for name, target, vf in (
        ("local_1_1", output_dir / "coffee-table-local-1x1.mp4", "crop=720:720:(iw-720)/2:0,scale=1080:1080"),
        ("local_9_16", output_dir / "coffee-table-local-9x16.mp4", "crop=405:720:(iw-405)/2:0,scale=720:1280"),
    ):
        command = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(master),
            "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-n", str(target),
        ]
        commands.append(command)
        try:
            runner(command, check=True, capture_output=True, text=True, timeout=1800)
            variants[name] = _local_media_evidence(target)
            variants[name]["status"] = "READY_FOR_OWNER_SAFE_AREA_REVIEW"
        except Exception as exc:
            variants[name] = {
                "status": "LOCAL_GUARDED_OUTPUT_UNAVAILABLE",
                "error": redact_text(str(exc)),
                "native_provider_regeneration": "NOT_AUTHORIZED",
            }
    return {
        "status": READY_FOR_OWNER_REVIEW,
        "master": master_evidence,
        **variants,
        "commands": commands,
        "provider_calls": 0,
        "native_provider_regeneration": "NOT_AUTHORIZED",
    }


def _motion_request(
    root: Path, run: VideoRunContext, task: Mapping[str, Any], lineage: Mapping[str, Any] | None
) -> MotionVideoRequest:
    request = task["request"]
    prompt = task["prompt"]
    if task["task_id"] == "TASK-04":
        if lineage is None:
            raise RuntimeError("TASK-04 lineage is missing")
        image_path = Path(str(lineage["extracted_png_path"]))
        image_sha = str(lineage["extracted_png_sha256"])
        if sha256_file(Path(str(lineage["source_mp4_path"]))) != lineage["source_mp4_sha256"]:
            raise RuntimeError("TASK-04 upstream MP4 hash drift")
        if sha256_file(image_path) != image_sha:
            raise RuntimeError("TASK-04 extracted PNG hash drift")
    else:
        image_path = root / str(request["input_image_path"])
        image_sha = str(request["input_image_sha256"])
    prompt_path = root / str(prompt["path"])
    return MotionVideoRequest(
        request_id=str(task["task_id"]), run_id=run.run_id, preset="coffee-table-live",
        shot_id=str(task["task_id"]), variation=1, provider="runway", model=str(request["model"]),
        image_path=image_path, image_sha256=image_sha, prompt_path=prompt_path,
        prompt_text=str(prompt["text"]), prompt_sha256=str(prompt["sha256"]),
        ratio=str(request["ratio"]), duration_seconds=int(request["duration_seconds"]),
        seed=request.get("seed"), output_format="mp4", timeout_seconds=1800, max_retries=0,
    )


def _block_prior_execution(root: Path, manifest_sha256: str) -> None:
    for evidence in (root / "runs").glob("*/coffee-table-live-authorization.json"):
        try:
            value = json.loads(evidence.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("manifest_sha256") == manifest_sha256:
            raise ExternalInputBlocked(
                f"Coffee Table manifest already has Live execution evidence: {evidence.parent.name}"
            )


def _artifact_evidence(artifact: MediaArtifact, root: Path) -> dict[str, Any]:
    value = asdict(artifact)
    value["path"] = str(artifact.path.relative_to(root))
    value.pop("source_url_redacted", None)
    return value


def _local_media_evidence(path: Path) -> dict[str, Any]:
    info = inspect_video(path)
    return {
        "path": str(path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size,
        "duration_seconds": info.duration_seconds, "width": info.width, "height": info.height,
        "container": info.container, "video_codec": info.video_codec,
        "pixel_format": info.pixel_format, "audio_stream_present": info.audio_stream_present,
    }


def _write_success_evidence(
    storage: VideoRunStorage,
    run: VideoRunContext,
    manifest: Mapping[str, Any],
    records: list[dict[str, Any]],
    raw: list[MediaArtifact],
    delivery: Mapping[str, Any],
    lineage: Mapping[str, Any] | None,
    actual_credits: float | None,
) -> None:
    storage.write_json_new(run, "request.json", {"mode": "LIVE", "action": "coffee-table-live", "preset": "coffee-table-live", "manifest_sha256": APPROVED_COFFEE_TABLE_MANIFEST_SHA256, "provider_call_count": 4, "requests": manifest["tasks"]})
    storage.write_json_new(run, "provider-results.json", {"status": READY_FOR_OWNER_REVIEW, "submission_count": 4, "successful_outputs": 4, "failed_outputs": 0, "results": records})
    storage.write_json_new(run, "delivery.json", delivery)
    storage.write_json_new(run, "cost.json", {"projected_runway_credits": 100, "actual_runway_credits": actual_credits, "projected_provider_cost_usd": 1.0, "actual_provider_cost_usd": None if actual_credits is None else actual_credits * 0.01, "currency": "USD", "automatic_paid_retries": 0, "automatic_replacement_tasks": 0})
    review_path = storage.write_review_new(run, blank_review_rows(run.run_id, "coffee-table-live", [{"video_id": "coffee-table-master-16x9", "candidate": "coffee-table-master-16x9.mp4"}]))
    review_package = _build_review_package(storage.root, run, raw, delivery, review_path)
    storage.write_json_new(run, "review-package.json", review_package)
    storage.write_text_new(run, "summary.md", f"# Coffee Table Live {run.run_id}\n\n- Status: `{READY_FOR_OWNER_REVIEW}`\n- Manifest SHA-256: `{APPROVED_COFFEE_TABLE_MANIFEST_SHA256}`\n- Provider submissions: 4\n- Automatic retries/replacements: 0 / 0\n- Human review: blank\n")
    storage.append_event(run, "ready_for_owner_review", {"status": READY_FOR_OWNER_REVIEW})


def _build_review_package(
    root: Path,
    run: VideoRunContext,
    raw: list[MediaArtifact],
    delivery: Mapping[str, Any],
    review_path: Path,
) -> dict[str, Any]:
    package = root / "outputs/reviews/coffee-table-live" / run.run_id
    package.mkdir(parents=True, exist_ok=False)
    items: list[dict[str, Any]] = []
    sources = [item.path for item in raw]
    for key in ("master", "local_1_1", "local_9_16"):
        value = delivery.get(key)
        if isinstance(value, Mapping) and value.get("path"):
            sources.append(Path(str(value["path"])))
    for source in sources:
        target = package / source.name
        shutil.copyfile(source, target)
        if sha256_file(target) != sha256_file(source):
            raise RuntimeError(f"review package copy hash mismatch: {source.name}")
        items.append(
            {"path": str(target.relative_to(root)), "sha256": sha256_file(target), "size_bytes": target.stat().st_size}
        )
    review_target = package / "review.csv"
    shutil.copyfile(review_path, review_target)
    manifest = {
        "run_id": run.run_id,
        "status": READY_FOR_OWNER_REVIEW,
        "human_review_fields": "BLANK",
        "items": items,
        "review_csv": {
            "path": str(review_target.relative_to(root)),
            "sha256": sha256_file(review_target),
        },
        "native_provider_regeneration": "NOT_AUTHORIZED",
    }
    manifest_path = package / "manifest.json"
    with manifest_path.open("x", encoding="utf-8") as output:
        json.dump(manifest, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    manifest["manifest_path"] = str(manifest_path.relative_to(root))
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest


def _write_stopped_evidence(
    storage: VideoRunStorage,
    run: VideoRunContext,
    manifest: Mapping[str, Any],
    records: list[dict[str, Any]],
    actual_credits: float | None,
    reason: str,
) -> None:
    safe_reason = redact_text(reason)
    if not (run.path / "request.json").exists():
        storage.write_json_new(run, "request.json", {"mode": "LIVE", "action": "coffee-table-live", "preset": "coffee-table-live", "manifest_sha256": APPROVED_COFFEE_TABLE_MANIFEST_SHA256, "provider_call_count": 4, "requests": manifest["tasks"]})
    storage.write_json_new(run, "provider-results.json", {"status": "STOPPED", "submission_count": len([item for item in records if item.get("provider_task_id")]), "successful_outputs": len([item for item in records if item.get("status") == "SUCCEEDED"]), "failed_outputs": 1, "stop_reason": safe_reason, "results": records})
    storage.write_json_new(run, "cost.json", {"projected_runway_credits": 100, "actual_runway_credits": actual_credits, "projected_provider_cost_usd": 1.0, "actual_provider_cost_usd": None if actual_credits is None else actual_credits * 0.01, "currency": "USD", "automatic_paid_retries": 0, "automatic_replacement_tasks": 0})
    storage.write_review_new(run, [])
    storage.write_text_new(run, "summary.md", f"# Coffee Table Live {run.run_id}\n\n- Status: `STOPPED`\n- Reason: `{safe_reason}`\n- Automatic retries/replacements: 0 / 0\n")
    storage.append_event(run, "live_stopped", {"reason": safe_reason})
