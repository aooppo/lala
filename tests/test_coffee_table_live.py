from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lala_workflow.cli import build_parser
from lala_workflow.hashing import sha256_file
from lala_workflow.video.coffee_table_live import (
    APPROVED_COFFEE_TABLE_MANIFEST,
    APPROVED_COFFEE_TABLE_MANIFEST_SHA256,
    assemble_coffee_table_delivery,
    CoffeeTableLiveStopped,
    execute_coffee_table_live,
    extract_last_valid_frame,
)
from lala_workflow.video.domain import MediaArtifact, VideoTaskResult, VideoTaskStatus
from lala_workflow.video.downloads import inspect_video
from lala_workflow.video.validation import ExternalInputBlocked


def test_live_cli_freezes_exact_owner_authorization() -> None:
    args = build_parser().parse_args(
        [
            "video", "campaign", "coffee-table", "--live",
            "--execution-manifest", APPROVED_COFFEE_TABLE_MANIFEST.as_posix(),
            "--execution-manifest-sha256", APPROVED_COFFEE_TABLE_MANIFEST_SHA256,
            "--confirm-owner-authorized-live", "--max-runway-credits", "100",
            "--max-provider-cost-usd", "1.00",
        ]
    )
    assert args.live is True
    assert args.execution_manifest_sha256 == APPROVED_COFFEE_TABLE_MANIFEST_SHA256
    assert args.max_runway_credits == 100
    assert args.max_provider_cost_usd == 1.0


def _make_video(path: Path, *, duration: float, color: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
            "-i", f"color=c={color}:s=1280x720:r=24:d={duration}", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-y", str(path),
        ],
        check=True,
    )


def test_last_frame_and_exact_local_delivery_are_deterministic(tmp_path: Path) -> None:
    raw = []
    for index, color in enumerate(("red", "green", "blue", "yellow"), start=1):
        path = tmp_path / f"TASK-{index:02d}.mp4"
        _make_video(path, duration=5, color=color)
        raw.append(path)
    frame = tmp_path / "task-02-last.png"
    lineage = extract_last_valid_frame(raw[1], frame)
    assert lineage["selected_zero_based_frame_index"] == lineage["frame_count"] - 1
    assert lineage["source_mp4_sha256"] == sha256_file(raw[1])
    assert lineage["extracted_png_sha256"] == sha256_file(frame)

    output_dir = tmp_path / "delivery"
    result = assemble_coffee_table_delivery(tuple(raw), output_dir)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["master"]["width"] == 1280
    assert result["master"]["height"] == 720
    assert result["master"]["duration_seconds"] == pytest.approx(20, abs=0.12)
    assert result["local_1_1"]["width"] == result["local_1_1"]["height"]
    assert result["local_9_16"]["width"] * 16 == result["local_9_16"]["height"] * 9
    assert result["provider_calls"] == 0


def test_final_manifest_is_still_the_authorized_identity() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / APPROVED_COFFEE_TABLE_MANIFEST
    assert sha256_file(path) == APPROVED_COFFEE_TABLE_MANIFEST_SHA256
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["execution"]["task_count"] == 4
    assert manifest["execution"]["live_authorized"] is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"manifest_sha256": "0" * 64},
        {"confirm_owner_authorized_live": False},
        {"max_runway_credits": 99},
        {"max_provider_cost_usd": 1.01},
        {"environ": {"RUNWAYML_API_SECRET": "fixture-only"}},
        {"environ": {"VIDEO_ALLOW_LIVE_CALLS": "true"}},
    ],
)
def test_live_authorization_fails_before_manifest_or_provider(
    tmp_path: Path, overrides: dict
) -> None:
    calls = {"manifest": 0, "provider": 0}

    def loader(*_args, **_kwargs):
        calls["manifest"] += 1
        return {}

    def factory(_sink):
        calls["provider"] += 1
        raise AssertionError("provider must not be constructed")

    values = {
        "manifest_path": APPROVED_COFFEE_TABLE_MANIFEST,
        "manifest_sha256": APPROVED_COFFEE_TABLE_MANIFEST_SHA256,
        "confirm_owner_authorized_live": True,
        "max_runway_credits": 100,
        "max_provider_cost_usd": 1.0,
        "environ": {"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
    }
    values.update(overrides)
    with pytest.raises(ExternalInputBlocked):
        execute_coffee_table_live(
            tmp_path, **values, provider_factory=factory, manifest_loader=loader
        )
    assert calls == {"manifest": 0, "provider": 0}
    assert not (tmp_path / "runs").exists()


class _FakeProvider:
    def __init__(self, source_video: Path, sink, *, fail_on: int | None = None, ambiguous_on: int | None = None):
        self.source_video = source_video
        self.sink = sink
        self.fail_on = fail_on
        self.ambiguous_on = ambiguous_on
        self.submissions = []

    def validate_request(self, request) -> None:
        assert sha256_file(request.image_path) == request.image_sha256
        assert sha256_file(request.prompt_path) == request.prompt_sha256
        assert request.max_retries == 0

    def submit(self, request) -> str:
        number = len(self.submissions) + 1
        self.submissions.append(request)
        if self.ambiguous_on == number:
            raise RuntimeError("synthetic ambiguous submit")
        task_id = f"fake-task-{number}"
        self.sink(task_id, None, 25)
        return task_id

    def wait(self, task_id: str, _timeout: float) -> VideoTaskResult:
        number = int(task_id.rsplit("-", 1)[1])
        if self.fail_on == number:
            return VideoTaskResult(task_id, VideoTaskStatus.FAILED, error_code="synthetic")
        return VideoTaskResult(
            task_id, VideoTaskStatus.SUCCEEDED, ("https://fixture.invalid/video.mp4",),
            estimated_credits=25, actual_credits=25,
        )

    def download_results(self, result, output_dir: Path, output_stem: str, _timeout: float, max_retries: int):
        assert max_retries == 0
        target = output_dir / f"{output_stem}.mp4"
        shutil.copyfile(self.source_video, target)
        info = inspect_video(target)
        return (
            MediaArtifact(
                artifact_id=output_stem, kind="motion", path=target,
                sha256=sha256_file(target), size_bytes=target.stat().st_size,
                mime_type="video/mp4", duration_seconds=info.duration_seconds,
                width=info.width, height=info.height, provider_task_id=result.provider_task_id,
                container=info.container, video_codec=info.video_codec,
                pixel_format=info.pixel_format, average_frame_rate=info.average_frame_rate,
                audio_stream_present=info.audio_stream_present,
            ),
        )


def _live_fixture(tmp_path: Path) -> tuple[dict, Path]:
    repository = Path(__file__).resolve().parents[1]
    manifest = json.loads((repository / APPROVED_COFFEE_TABLE_MANIFEST).read_text(encoding="utf-8"))
    for task in manifest["tasks"]:
        prompt = tmp_path / task["prompt"]["path"]
        prompt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repository / task["prompt"]["path"], prompt)
        source = task["source"].get("path")
        if source:
            target = tmp_path / source
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repository / source, target)
    source_video = tmp_path / "provider-source.mp4"
    _make_video(source_video, duration=5.05, color="purple")
    return manifest, source_video


def _run_fake_live(tmp_path: Path, manifest: dict, provider: _FakeProvider):
    return execute_coffee_table_live(
        tmp_path,
        manifest_path=APPROVED_COFFEE_TABLE_MANIFEST,
        manifest_sha256=APPROVED_COFFEE_TABLE_MANIFEST_SHA256,
        confirm_owner_authorized_live=True,
        max_runway_credits=100,
        max_provider_cost_usd=1.0,
        environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
        provider_factory=lambda sink: provider,
        manifest_loader=lambda *_args, **_kwargs: manifest,
    )


def test_fake_live_runs_four_serial_tasks_and_stops_at_blank_owner_review(tmp_path: Path) -> None:
    manifest, source_video = _live_fixture(tmp_path)
    holder = {}

    def factory(sink):
        provider = _FakeProvider(source_video, sink)
        holder["provider"] = provider
        return provider

    outcome = execute_coffee_table_live(
        tmp_path, manifest_path=APPROVED_COFFEE_TABLE_MANIFEST,
        manifest_sha256=APPROVED_COFFEE_TABLE_MANIFEST_SHA256,
        confirm_owner_authorized_live=True, max_runway_credits=100,
        max_provider_cost_usd=1.0,
        environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
        provider_factory=factory, manifest_loader=lambda *_args, **_kwargs: manifest,
    )
    assert outcome.status == "READY_FOR_OWNER_REVIEW"
    assert outcome.task_ids == tuple(f"fake-task-{index}" for index in range(1, 5))
    assert [request.request_id for request in holder["provider"].submissions] == [
        "TASK-01", "TASK-02", "TASK-03", "TASK-04"
    ]
    assert holder["provider"].submissions[-1].image_sha256 == sha256_file(
        tmp_path / "outputs/broll" / outcome.run_id / "TASK-02-last-valid-frame.png"
    )
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 1
    assert all(not value for key, value in rows[0].items() if key not in {"run_id", "video_id", "preset", "candidate"})
    assert json.loads((outcome.run_dir / "provider-results.json").read_text())["status"] == "READY_FOR_OWNER_REVIEW"


@pytest.mark.parametrize(("fail_on", "ambiguous_on", "expected_submissions"), [(2, None, 2), (None, 2, 2)])
def test_fake_live_stops_without_later_or_replacement_task(
    tmp_path: Path, fail_on: int | None, ambiguous_on: int | None, expected_submissions: int
) -> None:
    manifest, source_video = _live_fixture(tmp_path)
    holder = {}

    def factory(sink):
        provider = _FakeProvider(source_video, sink, fail_on=fail_on, ambiguous_on=ambiguous_on)
        holder["provider"] = provider
        return provider

    with pytest.raises(CoffeeTableLiveStopped) as caught:
        execute_coffee_table_live(
            tmp_path, manifest_path=APPROVED_COFFEE_TABLE_MANIFEST,
            manifest_sha256=APPROVED_COFFEE_TABLE_MANIFEST_SHA256,
            confirm_owner_authorized_live=True, max_runway_credits=100,
            max_provider_cost_usd=1.0,
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
            provider_factory=factory, manifest_loader=lambda *_args, **_kwargs: manifest,
        )
    assert len(holder["provider"].submissions) == expected_submissions
    run_dir = tmp_path / "runs" / caught.value.run_id
    results = json.loads((run_dir / "provider-results.json").read_text())
    assert results["status"] == "STOPPED"
    assert json.loads((run_dir / "cost.json").read_text())["automatic_replacement_tasks"] == 0
