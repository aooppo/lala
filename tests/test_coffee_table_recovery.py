from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lala_workflow.cli import build_parser
from lala_workflow.hashing import sha256_file
from lala_workflow.video import coffee_table_recovery as recovery_module
from lala_workflow.video.coffee_table_recovery import (
    FAILED_LIVE_RUN_ID,
    LOCAL_CUTAWAY_FILTER,
    ORIGINAL_PROVIDER_RESULTS_SHA256,
    PARENT_EXECUTION_MANIFEST,
    PARENT_EXECUTION_MANIFEST_SHA256,
    PRODUCT_SOURCE,
    READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW,
    TASK_02_SHA256,
    TASK_04_FRAME_INDEX,
    TASK_04_PROMPT,
    TASK_04_PROMPT_SHA256,
    extract_fixed_task_04_frame,
    generate_local_product_cutaway,
    prepare_coffee_table_recovery,
)
from lala_workflow.video.downloads import inspect_video
from lala_workflow.video.validation import ExternalInputBlocked


REPOSITORY = Path(__file__).resolve().parents[1]
FIXED_NOW = datetime(2026, 8, 21, 12, 0, 0, tzinfo=timezone.utc)


def _copy(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


def _recovery_fixture(root: Path) -> Path:
    relative_paths = (
        PARENT_EXECUTION_MANIFEST,
        Path("runs") / FAILED_LIVE_RUN_ID / "provider-results.json",
        Path("outputs/broll") / FAILED_LIVE_RUN_ID / "TASK-01.mp4",
        Path("outputs/broll") / FAILED_LIVE_RUN_ID / "TASK-02.mp4",
        PRODUCT_SOURCE,
        TASK_04_PROMPT,
    )
    for relative in relative_paths:
        _copy(REPOSITORY / relative, root / relative)
    return root


def test_recovery_cli_is_offline_and_mutually_exclusive() -> None:
    args = build_parser().parse_args(
        [
            "video", "campaign", "coffee-table", "--prepare-recovery",
            "--execution-manifest", PARENT_EXECUTION_MANIFEST.as_posix(),
            "--execution-manifest-sha256", PARENT_EXECUTION_MANIFEST_SHA256,
            "--failed-live-run", FAILED_LIVE_RUN_ID,
        ]
    )
    assert args.prepare_recovery is True
    assert args.live is False
    assert args.failed_live_run == FAILED_LIVE_RUN_ID
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "video", "campaign", "coffee-table", "--prepare-recovery", "--live",
                "--failed-live-run", FAILED_LIVE_RUN_ID,
            ]
        )


def test_wrong_recovery_binding_fails_before_output_allocation(tmp_path: Path) -> None:
    _recovery_fixture(tmp_path)
    with pytest.raises(ExternalInputBlocked, match="parent manifest SHA"):
        prepare_coffee_table_recovery(
            tmp_path,
            manifest_path=PARENT_EXECUTION_MANIFEST,
            manifest_sha256="0" * 64,
            failed_live_run_id=FAILED_LIVE_RUN_ID,
            now=FIXED_NOW,
        )
    assert not (tmp_path / "outputs/campaign-recovery-manifests").exists()
    assert not any((tmp_path / "outputs/broll").glob("COFFEE-TABLE-RECOVERY-*"))


def test_local_product_cutaway_is_byte_deterministic_and_exact(tmp_path: Path) -> None:
    source = _copy(REPOSITORY / PRODUCT_SOURCE, tmp_path / "source.jpg")
    first = generate_local_product_cutaway(
        source, tmp_path / "first/LOCAL-TASK-03.mp4", project_root=tmp_path
    )
    second = generate_local_product_cutaway(
        source, tmp_path / "second/LOCAL-TASK-03.mp4", project_root=tmp_path
    )
    first_output = first["output"]
    second_output = second["output"]
    assert first_output["sha256"] == second_output["sha256"]
    assert first_output["frame_count"] == 72
    assert first_output["duration_seconds"] == pytest.approx(3.0, abs=0.01)
    assert (first_output["width"], first_output["height"]) == (1280, 720)
    assert first_output["frame_rate"] == "24/1"
    assert first_output["video_codec"] == "h264"
    assert first_output["pixel_format"] == "yuv420p"
    assert first_output["audio_stream_present"] is False
    assert first["transformation"]["filter_expression"] == LOCAL_CUTAWAY_FILTER
    assert first["transformation"]["start_zoom"] == 1.0
    assert first["transformation"]["end_zoom"] == 1.035
    assert first["provider_calls"] == first["paid_calls"] == 0


def test_pdp_sha_gate_stops_before_ffmpeg(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    source.write_bytes(b"drift")
    calls = 0

    def runner(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("FFmpeg must not run")

    with pytest.raises(ExternalInputBlocked, match="PDP source SHA"):
        generate_local_product_cutaway(
            source, tmp_path / "LOCAL-TASK-03.mp4", project_root=tmp_path, runner=runner
        )
    assert calls == 0


def test_task_04_frame_96_extraction_is_deterministic(tmp_path: Path) -> None:
    source = _copy(
        REPOSITORY / "outputs/broll" / FAILED_LIVE_RUN_ID / "TASK-02.mp4",
        tmp_path / "TASK-02.mp4",
    )
    first = extract_fixed_task_04_frame(
        source, tmp_path / "first/frame-96.png", project_root=tmp_path
    )
    second = extract_fixed_task_04_frame(
        source, tmp_path / "second/frame-96.png", project_root=tmp_path
    )
    assert first["selected_zero_based_frame_index"] == TASK_04_FRAME_INDEX == 96
    assert first["source_mp4_sha256"] == TASK_02_SHA256
    assert first["extracted_png_sha256"] == second["extracted_png_sha256"]
    assert (first["extracted_png_width"], first["extracted_png_height"]) == (1280, 720)
    assert first["ffmpeg_argv"][first["ffmpeg_argv"].index("-vf") + 1] == "select=eq(n\\,96)"
    assert first["visual_search"] is False
    assert first["fallback_frame_selection"] is False
    assert first["provider_calls"] == 0


def test_task_04_short_source_has_no_fallback(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "short.mp4"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
            "-i", "color=c=black:s=1280x720:r=24:d=1", "-an", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-y", str(source),
        ],
        check=True,
    )
    monkeypatch.setattr(recovery_module, "TASK_02_SHA256", sha256_file(source))
    with pytest.raises(RuntimeError, match="does not contain fixed zero-based frame 96"):
        extract_fixed_task_04_frame(
            source, tmp_path / "frame.png", project_root=tmp_path
        )
    assert not (tmp_path / "frame.png").exists()


def test_prepare_recovery_preserves_history_and_builds_exact_manifest(tmp_path: Path) -> None:
    root = _recovery_fixture(tmp_path)
    original_manifest_hash = sha256_file(root / PARENT_EXECUTION_MANIFEST)
    original_results = root / "runs" / FAILED_LIVE_RUN_ID / "provider-results.json"
    original_results_hash = sha256_file(original_results)
    outcome = prepare_coffee_table_recovery(
        root,
        manifest_path=PARENT_EXECUTION_MANIFEST,
        manifest_sha256=PARENT_EXECUTION_MANIFEST_SHA256,
        failed_live_run_id=FAILED_LIVE_RUN_ID,
        now=FIXED_NOW,
    )
    assert outcome.status == READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW
    assert outcome.provider_submissions == outcome.paid_calls == 0
    assert outcome.recovery_manifest_sha256 == sha256_file(outcome.recovery_manifest_path)
    assert sha256_file(root / PARENT_EXECUTION_MANIFEST) == original_manifest_hash
    assert sha256_file(original_results) == original_results_hash == ORIGINAL_PROVIDER_RESULTS_SHA256

    manifest = json.loads(outcome.recovery_manifest_path.read_text(encoding="utf-8"))
    task_01, task_02, task_03, task_04 = manifest["historical_tasks"]
    assert (task_01["status"], task_02["status"]) == ("SUCCEEDED", "SUCCEEDED")
    assert task_03["status"] == "FAILED"
    assert task_03["error_code"] == "INTERNAL.BAD_OUTPUT.CODE01"
    assert task_03["actual_runway_credits"] == 0
    assert task_03["historical_classification"] == "REAL_FAILED_PROVIDER_TASK"
    assert task_04["status"] == "NOT_SUBMITTED"
    assert manifest["local_task_03"]["task_id"] == "LOCAL-TASK-03"
    assert manifest["task_04_proposal"]["status"] == "FUTURE_NOT_SUBMITTED"
    assert manifest["task_04_proposal"]["input"]["selected_zero_based_frame_index"] == 96
    assert manifest["task_04_proposal"]["prompt"]["sha256"] == TASK_04_PROMPT_SHA256
    timeline = manifest["assembly"]["timeline"]
    assert len(timeline) == 8
    assert sum(item["duration_seconds"] for item in timeline) == 20
    assert [item["master_interval_seconds"]["start"] for item in timeline] == [0, 3, 5, 7, 10, 13, 17, 18]
    assert [item["master_interval_seconds"]["end"] for item in timeline] == [3, 5, 7, 10, 13, 17, 18, 20]
    assert manifest["budget"]["historical_actual"] == {"runway_credits": 50, "cost_usd": 0.5}
    assert manifest["budget"]["projected_additional_live"] == {"runway_credits": 25, "cost_usd": 0.25}
    assert manifest["budget"]["projected_final"] == {"runway_credits": 75, "cost_usd": 0.75}
    assert manifest["delivery"]["1:1"] == "GUARDED_LOCAL_REFRAME_ONLY"
    assert manifest["delivery"]["9:16"] == "GUARDED_LOCAL_REFRAME_ONLY"
    assert manifest["delivery"]["native_ratio_provider_regeneration"] == "NOT_AUTHORIZED"
    assert manifest["provider_submissions_during_recovery_preparation"] == 0
    assert manifest["paid_calls_during_recovery_preparation"] == 0
    assert not hasattr(recovery_module, "MotionVideoProvider")
    assert not hasattr(recovery_module, "RunwayMotionProvider")

    local_path = root / manifest["local_task_03"]["output"]["path"]
    info = inspect_video(local_path)
    assert (info.width, info.height, info.average_frame_rate) == (1280, 720, "24/1")

    with pytest.raises(ExternalInputBlocked, match="already exists"):
        prepare_coffee_table_recovery(
            root,
            manifest_path=PARENT_EXECUTION_MANIFEST,
            manifest_sha256=PARENT_EXECUTION_MANIFEST_SHA256,
            failed_live_run_id=FAILED_LIVE_RUN_ID,
            now=FIXED_NOW,
        )


def test_recovery_failure_removes_only_new_outputs(tmp_path: Path) -> None:
    root = _recovery_fixture(tmp_path)
    original_results = root / "runs" / FAILED_LIVE_RUN_ID / "provider-results.json"
    before = sha256_file(original_results)

    def fail_local_command(argv, **_kwargs):
        if argv[0] == "ffmpeg":
            raise subprocess.CalledProcessError(1, argv)
        return subprocess.run(argv, **_kwargs)

    with pytest.raises(subprocess.CalledProcessError):
        prepare_coffee_table_recovery(
            root,
            manifest_path=PARENT_EXECUTION_MANIFEST,
            manifest_sha256=PARENT_EXECUTION_MANIFEST_SHA256,
            failed_live_run_id=FAILED_LIVE_RUN_ID,
            command_runner=fail_local_command,
            now=FIXED_NOW,
        )
    assert sha256_file(original_results) == before
    assert not list((root / "outputs/broll").glob("COFFEE-TABLE-RECOVERY-*"))
    recovery_root = root / "outputs/campaign-recovery-manifests"
    assert not recovery_root.exists() or not list(recovery_root.iterdir())
