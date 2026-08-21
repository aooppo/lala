from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lala_workflow.cli import build_parser
from lala_workflow.hashing import sha256_file
from lala_workflow.video.coffee_table_recovery_live import (
    APPROVED_SOURCE_AGGREGATE_SHA256,
    RECOVERY_V2_MANIFEST,
    RECOVERY_V2_MANIFEST_SHA256,
    READY_FOR_OWNER_REVIEW,
    CoffeeTableRecoveryLiveStopped,
    assemble_recovery_delivery,
    execute_coffee_table_recovery_live,
)
from lala_workflow.video.domain import MediaArtifact, VideoTaskResult, VideoTaskStatus
from lala_workflow.video.downloads import inspect_video
from lala_workflow.video.validation import ExternalInputBlocked


REPOSITORY = Path(__file__).resolve().parents[1]
FIXED_NOW = datetime(2026, 8, 21, 14, 0, 0, tzinfo=timezone.utc)


def _copy(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


def _copy_tree_files(source: Path, target: Path) -> None:
    for path in source.rglob("*"):
        if path.is_file():
            _copy(path, target / path.relative_to(source))


def _live_fixture(root: Path) -> Path:
    paths = (
        RECOVERY_V2_MANIFEST,
        Path("outputs/campaign-recovery-manifests/COFFEE-TABLE-RECOVERY-20260821-164849-001/coffee-table-recovery-manifest.json"),
        Path("outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json"),
        Path("runs/LALA-VIDEO-20260821-082100-COFFEE-TABLE-LIVE-001/provider-results.json"),
        Path("outputs/broll/LALA-VIDEO-20260821-082100-COFFEE-TABLE-LIVE-001/TASK-01.mp4"),
        Path("outputs/broll/LALA-VIDEO-20260821-082100-COFFEE-TABLE-LIVE-001/TASK-02.mp4"),
        Path("outputs/broll/COFFEE-TABLE-RECOVERY-20260821-164849-001/LOCAL-TASK-03.mp4"),
        Path("outputs/reviews/coffee-table-task04-source-frame-review/TASK-02-frame-000092.png"),
        Path("outputs/reviews/coffee-table-task04-source-frame-review/manifest.json"),
        Path("outputs/reviews/coffee-table-task04-source-frame-review/review.csv"),
        Path("prompts/coffee-table-task-04-sit-hero-v3.txt"),
    )
    for relative in paths:
        _copy(REPOSITORY / relative, root / relative)
    for relative in (
        Path("assets/approved_anchors"),
        Path("assets/approved_keyframes"),
        Path("assets/voice/source"),
        Path("assets/voice/approved"),
        Path("assets/scripts"),
    ):
        _copy_tree_files(REPOSITORY / relative, root / relative)
    return root


def _make_video(path: Path, *, duration: float = 5.0, color: str = "purple") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:r=24:d={duration}",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(path),
        ],
        check=True,
    )


class _FakeProvider:
    def __init__(
        self,
        source_video: Path,
        sink,
        *,
        status: VideoTaskStatus = VideoTaskStatus.SUCCEEDED,
        ambiguous_without_id: bool = False,
        durable_then_raise: bool = False,
    ) -> None:
        self.source_video = source_video
        self.sink = sink
        self.status = status
        self.ambiguous_without_id = ambiguous_without_id
        self.durable_then_raise = durable_then_raise
        self.submissions = []
        self.waited = []
        self.downloads = 0

    def validate_request(self, request) -> None:
        assert request.request_id == request.shot_id == "TASK-04"
        assert request.model == "gen4_turbo"
        assert request.duration_seconds == 5
        assert request.ratio == "1280:720"
        assert request.max_retries == 0
        assert sha256_file(request.image_path) == request.image_sha256
        assert sha256_file(request.prompt_path) == request.prompt_sha256

    def submit(self, request) -> str:
        self.submissions.append(request)
        if self.ambiguous_without_id:
            raise RuntimeError("synthetic transport ambiguity fixture-only")
        task_id = "fake-task-04"
        self.sink(task_id, None, 25)
        if self.durable_then_raise:
            raise RuntimeError("synthetic post-ID interruption")
        return task_id

    def wait(self, task_id: str, _timeout: float) -> VideoTaskResult:
        self.waited.append(task_id)
        return VideoTaskResult(
            task_id,
            self.status,
            ("https://fixture.invalid/TASK-04.mp4",) if self.status is VideoTaskStatus.SUCCEEDED else (),
            estimated_credits=25,
            actual_credits=25 if self.status is VideoTaskStatus.SUCCEEDED else 0,
            error_code=None if self.status is VideoTaskStatus.SUCCEEDED else "SYNTHETIC.FAILURE",
            error_message=None if self.status is VideoTaskStatus.SUCCEEDED else "synthetic failure",
        )

    def download_results(self, result, output_dir: Path, output_stem: str, _timeout: float, max_retries: int):
        assert max_retries == 0
        self.downloads += 1
        target = output_dir / f"{output_stem}.mp4"
        _copy(self.source_video, target)
        info = inspect_video(target)
        return (
            MediaArtifact(
                artifact_id=output_stem,
                kind="motion",
                path=target,
                sha256=sha256_file(target),
                size_bytes=target.stat().st_size,
                mime_type="video/mp4",
                duration_seconds=info.duration_seconds,
                width=info.width,
                height=info.height,
                provider_task_id=result.provider_task_id,
                container=info.container,
                video_codec=info.video_codec,
                pixel_format=info.pixel_format,
                average_frame_rate=info.average_frame_rate,
                audio_stream_present=info.audio_stream_present,
            ),
        )


def _execute(root: Path, provider: _FakeProvider):
    return execute_coffee_table_recovery_live(
        root,
        manifest_path=RECOVERY_V2_MANIFEST,
        manifest_sha256=RECOVERY_V2_MANIFEST_SHA256,
        confirm_owner_authorized_live=True,
        max_runway_credits=25,
        max_provider_cost_usd=0.25,
        environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
        provider_factory=lambda _sink: provider,
        now=FIXED_NOW,
    )


def test_cli_requires_explicit_live_recovery_modifier() -> None:
    args = build_parser().parse_args(
        [
            "video", "campaign", "coffee-table", "--live", "--recovery-live",
            "--execution-manifest", RECOVERY_V2_MANIFEST.as_posix(),
            "--execution-manifest-sha256", RECOVERY_V2_MANIFEST_SHA256,
            "--confirm-owner-authorized-live", "--max-runway-credits", "25",
            "--max-provider-cost-usd", "0.25",
        ]
    )
    assert args.live is True
    assert args.recovery_live is True


@pytest.mark.parametrize(
    "override",
    [
        {"manifest_sha256": "0" * 64},
        {"confirm_owner_authorized_live": False},
        {"max_runway_credits": 24},
        {"max_provider_cost_usd": 0.26},
        {"environ": {"RUNWAYML_API_SECRET": "fixture-only"}},
        {"environ": {"VIDEO_ALLOW_LIVE_CALLS": "true"}},
    ],
)
def test_preflight_failure_allocates_no_run_or_provider(tmp_path: Path, override: dict) -> None:
    root = _live_fixture(tmp_path)
    calls = 0

    def factory(_sink):
        nonlocal calls
        calls += 1
        raise AssertionError("provider must not be constructed")

    values = {
        "manifest_path": RECOVERY_V2_MANIFEST,
        "manifest_sha256": RECOVERY_V2_MANIFEST_SHA256,
        "confirm_owner_authorized_live": True,
        "max_runway_credits": 25,
        "max_provider_cost_usd": 0.25,
        "environ": {"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
    }
    values.update(override)
    with pytest.raises(ExternalInputBlocked):
        execute_coffee_table_recovery_live(root, **values, provider_factory=factory, now=FIXED_NOW)
    assert calls == 0
    assert not (root / "runs").exists() or not list((root / "runs").glob("*RECOVERY-LIVE*"))


def test_success_submits_only_task04_and_builds_blank_review_package(tmp_path: Path) -> None:
    root = _live_fixture(tmp_path)
    provider_video = tmp_path / "provider-task04.mp4"
    _make_video(provider_video, color="yellow")
    holder = {}

    def factory(sink):
        provider = _FakeProvider(provider_video, sink)
        holder["provider"] = provider
        return provider

    outcome = execute_coffee_table_recovery_live(
        root,
        manifest_path=RECOVERY_V2_MANIFEST,
        manifest_sha256=RECOVERY_V2_MANIFEST_SHA256,
        confirm_owner_authorized_live=True,
        max_runway_credits=25,
        max_provider_cost_usd=0.25,
        environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
        provider_factory=factory,
        now=FIXED_NOW,
    )
    provider = holder["provider"]
    assert outcome.status == READY_FOR_OWNER_REVIEW
    assert outcome.provider_task_id == "fake-task-04"
    assert len(provider.submissions) == 1
    request = provider.submissions[0]
    assert request.image_sha256 == "95f68fa1f9bd3dcf6db94c2298511a224484c85c1fc5f278c3c67aa72e765e2e"
    assert request.prompt_sha256 == "e73cc7844806f8a25249c22da261e57df67ba7c3762172746b33a3b45b24f669"
    assert outcome.provider_submissions == 1
    assert outcome.automatic_paid_retries == outcome.automatic_replacement_tasks == 0
    assert outcome.actual_credits == 25
    assert outcome.actual_cost_usd == pytest.approx(0.25)

    events = [json.loads(line) for line in (outcome.run_dir / "task-events.jsonl").read_text().splitlines()]
    names = [event["event"] for event in events]
    assert names.index("recovery_live_prepared") < names.index("task_submitting")
    assert names.index("task_submitting") < names.index("provider_task_id_durable")
    assert names.index("provider_task_id_durable") < names.index("task_submitted")
    assert names.index("task_submitted") < names.index("provider_task_terminal")
    assert names[-1] == "ready_for_owner_review"

    master = Path(outcome.delivery["master"]["path"])
    info = inspect_video(master)
    assert (info.width, info.height, info.average_frame_rate) == (1280, 720, "24/1")
    assert info.duration_seconds == pytest.approx(20.0, abs=0.01)
    assert outcome.delivery["master"]["frame_count"] == 480
    assert outcome.delivery["local_1_1"]["status"] == "BLOCKED_SAFE_AREA"
    assert outcome.delivery["local_9_16"]["status"] == "BLOCKED_SAFE_AREA"
    assert "path" not in outcome.delivery["local_1_1"]
    assert "path" not in outcome.delivery["local_9_16"]

    package = Path(outcome.review_package["path"])
    copied_names = {path.name for path in package.iterdir() if path.suffix == ".mp4"}
    assert copied_names == {
        "TASK-01.mp4", "TASK-02.mp4", "LOCAL-TASK-03.mp4", "TASK-04.mp4",
        "coffee-table-master-16x9.mp4",
    }
    with (package / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) >= 25
    assert all(not row[field] for row in rows for field in ("decision", "notes", "reviewer", "reviewed_at"))
    assert sha256_file(root / RECOVERY_V2_MANIFEST) == RECOVERY_V2_MANIFEST_SHA256
    assert outcome.integrity["approved_source_aggregate_sha256"] == APPROVED_SOURCE_AGGREGATE_SHA256

    with pytest.raises(ExternalInputBlocked, match="already has Live execution evidence"):
        execute_coffee_table_recovery_live(
            root,
            manifest_path=RECOVERY_V2_MANIFEST,
            manifest_sha256=RECOVERY_V2_MANIFEST_SHA256,
            confirm_owner_authorized_live=True,
            max_runway_credits=25,
            max_provider_cost_usd=0.25,
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
            provider_factory=lambda _sink: (_ for _ in ()).throw(
                AssertionError("provider must not be reconstructed")
            ),
            now=FIXED_NOW,
        )


def test_unknown_submission_stops_without_retry_or_assembly(tmp_path: Path) -> None:
    root = _live_fixture(tmp_path)
    source = tmp_path / "provider.mp4"
    _make_video(source)
    holder = {}

    def factory(sink):
        provider = _FakeProvider(source, sink, ambiguous_without_id=True)
        holder["provider"] = provider
        return provider

    with pytest.raises(CoffeeTableRecoveryLiveStopped) as caught:
        execute_coffee_table_recovery_live(
            root,
            manifest_path=RECOVERY_V2_MANIFEST,
            manifest_sha256=RECOVERY_V2_MANIFEST_SHA256,
            confirm_owner_authorized_live=True,
            max_runway_credits=25,
            max_provider_cost_usd=0.25,
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
            provider_factory=factory,
            now=FIXED_NOW,
        )
    assert caught.value.status == "BLOCKED_SUBMISSION_UNKNOWN"
    assert len(holder["provider"].submissions) == 1
    assert holder["provider"].waited == []
    run_dir = root / "runs" / caught.value.run_id
    results = json.loads((run_dir / "provider-results.json").read_text())
    assert results["submission_count"] == 1
    assert results["provider_task_id"] is None
    for path in run_dir.iterdir():
        if path.is_file():
            assert "fixture-only" not in path.read_text(encoding="utf-8")
    assert not (root / "outputs/final" / caught.value.run_id).exists()


def test_durable_id_then_submit_exception_continues_same_task(tmp_path: Path) -> None:
    root = _live_fixture(tmp_path)
    source = tmp_path / "provider.mp4"
    _make_video(source)
    holder = {}

    def factory(sink):
        provider = _FakeProvider(source, sink, durable_then_raise=True)
        holder["provider"] = provider
        return provider

    outcome = execute_coffee_table_recovery_live(
        root,
        manifest_path=RECOVERY_V2_MANIFEST,
        manifest_sha256=RECOVERY_V2_MANIFEST_SHA256,
        confirm_owner_authorized_live=True,
        max_runway_credits=25,
        max_provider_cost_usd=0.25,
        environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
        provider_factory=factory,
        now=FIXED_NOW,
    )
    assert len(holder["provider"].submissions) == 1
    assert holder["provider"].waited == ["fake-task-04"]
    assert outcome.provider_task_id == "fake-task-04"


def test_provider_failure_stops_without_download_assembly_or_replacement(tmp_path: Path) -> None:
    root = _live_fixture(tmp_path)
    source = tmp_path / "provider.mp4"
    _make_video(source)
    holder = {}

    def factory(sink):
        provider = _FakeProvider(source, sink, status=VideoTaskStatus.FAILED)
        holder["provider"] = provider
        return provider

    with pytest.raises(CoffeeTableRecoveryLiveStopped) as caught:
        execute_coffee_table_recovery_live(
            root,
            manifest_path=RECOVERY_V2_MANIFEST,
            manifest_sha256=RECOVERY_V2_MANIFEST_SHA256,
            confirm_owner_authorized_live=True,
            max_runway_credits=25,
            max_provider_cost_usd=0.25,
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
            provider_factory=factory,
            now=FIXED_NOW,
        )
    assert caught.value.status == "BLOCKED_TASK04_PROVIDER"
    assert len(holder["provider"].submissions) == 1
    assert holder["provider"].downloads == 0
    assert not (root / "outputs/final" / caught.value.run_id).exists()


def test_invalid_short_task04_output_stops_without_assembly(tmp_path: Path) -> None:
    root = _live_fixture(tmp_path)
    source = tmp_path / "short-provider.mp4"
    _make_video(source, duration=1)
    holder = {}

    def factory(sink):
        provider = _FakeProvider(source, sink)
        holder["provider"] = provider
        return provider

    with pytest.raises(CoffeeTableRecoveryLiveStopped) as caught:
        execute_coffee_table_recovery_live(
            root,
            manifest_path=RECOVERY_V2_MANIFEST,
            manifest_sha256=RECOVERY_V2_MANIFEST_SHA256,
            confirm_owner_authorized_live=True,
            max_runway_credits=25,
            max_provider_cost_usd=0.25,
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
            provider_factory=factory,
            now=FIXED_NOW,
        )
    assert caught.value.status == "BLOCKED_TASK04_PROVIDER"
    assert len(holder["provider"].submissions) == 1
    assert holder["provider"].downloads == 1
    assert not (root / "outputs/final" / caught.value.run_id).exists()


def test_local_assembly_uses_explicit_last_decoded_frame_and_exact_timeline(tmp_path: Path) -> None:
    paths = []
    for name, duration, color in (
        ("TASK-01", 5, "red"),
        ("TASK-02", 5, "green"),
        ("LOCAL-TASK-03", 3, "blue"),
        ("TASK-04", 5, "yellow"),
    ):
        path = tmp_path / f"{name}.mp4"
        _make_video(path, duration=duration, color=color)
        paths.append(path)
    delivery = assemble_recovery_delivery(*paths, tmp_path / "delivery")
    assert delivery["master"]["duration_seconds"] == pytest.approx(20.0, abs=0.01)
    assert delivery["master"]["frame_count"] == 480
    assert delivery["terminal_hold"]["selected_zero_based_frame_index"] == (
        delivery["terminal_hold"]["frame_count"] - 1
    )
    assert sha256_file(Path(delivery["terminal_hold"]["extracted_png_path"])) == delivery["terminal_hold"]["extracted_png_sha256"]
    command = delivery["assembly_ffmpeg_argv"]
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "concat=n=8" in filter_graph
    assert all(token in filter_graph for token in ("end=3", "start=3:end=5", "start=2:end=5", "start=4:end=5"))
    assert delivery["local_1_1"]["status"] == delivery["local_9_16"]["status"] == "BLOCKED_SAFE_AREA"
