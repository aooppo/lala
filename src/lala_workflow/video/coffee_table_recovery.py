from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image

from ..hashing import sha256_file
from .downloads import inspect_video
from .validation import ExternalInputBlocked


PARENT_EXECUTION_MANIFEST = Path(
    "outputs/campaign-execution-manifests/"
    "COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json"
)
PARENT_EXECUTION_MANIFEST_SHA256 = (
    "ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea"
)
FAILED_LIVE_RUN_ID = "LALA-VIDEO-20260821-082100-COFFEE-TABLE-LIVE-001"
ORIGINAL_PROVIDER_RESULTS_SHA256 = (
    "111a05f526944b26381fdf023cbcba4d8aaa58124490e3f7e9ceeedc3301c609"
)

TASK_01_PROVIDER_ID = "43da0f57-b584-4738-bbf1-05c33f653a3f"
TASK_01_SHA256 = "2c61cb10a6563d9d4c1e43811be17ef06c3244fc6eb2356d349f064cff6ffd4b"
TASK_02_PROVIDER_ID = "a7bb1630-21ff-4a2e-8d40-c3c9085d45ac"
TASK_02_SHA256 = "9565691a30e312518cc867792063194ae2a667b70d586fbee06d821cc9b7413f"
TASK_03_PROVIDER_ID = "03b195ab-98b0-4631-a845-03843656cbc5"
TASK_03_ERROR = "INTERNAL.BAD_OUTPUT.CODE01"

PRODUCT_SOURCE = Path("outputs/reviews/candidate16-keyframes-v2/references/02.jpg")
PRODUCT_SOURCE_SHA256 = "4bf6e13b82f9c9c4d4525180aa412ebc22e4ca6c541e6d9c33c905271814b5c5"
TASK_04_PROMPT = Path("prompts/coffee-table-task-04-sit-hero-v3.txt")
TASK_04_PROMPT_SHA256 = "e73cc7844806f8a25249c22da261e57df67ba7c3762172746b33a3b45b24f669"

READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW = (
    "READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW"
)
RECOVERY_SCHEMA = "candidate16-coffee-table-recovery-manifest/v1"
LOCAL_CUTAWAY_FILTER = (
    "crop=1280:720:0:280,"
    "zoompan=z='1+0.035*on/71':x='(iw-iw/zoom)/2':"
    "y='(ih-ih/zoom)/2':d=72:s=1280x720:fps=24,"
    "scale=1280:720:in_range=pc:out_range=tv,format=yuv420p"
)
TASK_04_FRAME_INDEX = 96


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class CoffeeTableRecoveryOutcome:
    recovery_id: str
    status: str
    parent_manifest_sha256: str
    failed_live_run_id: str
    local_task_03: Mapping[str, Any]
    task_04_source: Mapping[str, Any]
    task_04_prompt: Mapping[str, Any]
    recovery_manifest_path: Path
    recovery_manifest_sha256: str
    historical_actual_credits: float
    historical_actual_cost_usd: float
    projected_additional_live_credits: float
    projected_additional_live_cost_usd: float
    projected_final_credits: float
    projected_final_cost_usd: float
    provider_submissions: int
    paid_calls: int


def prepare_coffee_table_recovery(
    project_root: Path,
    *,
    manifest_path: Path,
    manifest_sha256: str,
    failed_live_run_id: str,
    command_runner: CommandRunner = subprocess.run,
    now: datetime | None = None,
) -> CoffeeTableRecoveryOutcome:
    root = project_root.resolve()
    validated = _validate_recovery_inputs(
        root,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        failed_live_run_id=failed_live_run_id,
    )
    _block_existing_recovery(root, manifest_sha256, failed_live_run_id)
    created_at = (now or datetime.now().astimezone()).isoformat()
    recovery_id, media_dir, manifest_dir = _allocate_recovery_paths(root, now=now)
    manifest_file = manifest_dir / "coffee-table-recovery-manifest.json"
    try:
        local_task_03 = generate_local_product_cutaway(
            validated["product_source"],
            media_dir / "LOCAL-TASK-03.mp4",
            project_root=root,
            runner=command_runner,
        )
        task_04_source = extract_fixed_task_04_frame(
            validated["task_02_path"],
            media_dir / "TASK-02-frame-000096.png",
            project_root=root,
            runner=command_runner,
        )
        prompt = _prompt_evidence(root)
        manifest = _recovery_manifest(
            recovery_id=recovery_id,
            created_at=created_at,
            original_evidence=validated["original_evidence"],
            historical_tasks=validated["historical_tasks"],
            local_task_03=local_task_03,
            task_04_source=task_04_source,
            task_04_prompt=prompt,
        )
        _write_json_exclusive(manifest_file, manifest)
        _revalidate_after_write(root, validated, local_task_03, task_04_source, prompt)
        manifest_digest = sha256_file(manifest_file)
    except Exception:
        shutil.rmtree(manifest_dir, ignore_errors=True)
        shutil.rmtree(media_dir, ignore_errors=True)
        raise
    return CoffeeTableRecoveryOutcome(
        recovery_id=recovery_id,
        status=READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW,
        parent_manifest_sha256=PARENT_EXECUTION_MANIFEST_SHA256,
        failed_live_run_id=FAILED_LIVE_RUN_ID,
        local_task_03=local_task_03,
        task_04_source=task_04_source,
        task_04_prompt=prompt,
        recovery_manifest_path=manifest_file,
        recovery_manifest_sha256=manifest_digest,
        historical_actual_credits=50.0,
        historical_actual_cost_usd=0.50,
        projected_additional_live_credits=25.0,
        projected_additional_live_cost_usd=0.25,
        projected_final_credits=75.0,
        projected_final_cost_usd=0.75,
        provider_submissions=0,
        paid_calls=0,
    )


def generate_local_product_cutaway(
    source_image: Path,
    output_mp4: Path,
    *,
    project_root: Path,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    if sha256_file(source_image) != PRODUCT_SOURCE_SHA256:
        raise ExternalInputBlocked("Coffee Table recovery PDP source SHA-256 drift")
    with Image.open(source_image) as image:
        image.verify()
    with Image.open(source_image) as image:
        if image.size != (1280, 1280):
            raise ExternalInputBlocked("Coffee Table recovery PDP source must be 1280x1280")
    if output_mp4.exists():
        raise RuntimeError("LOCAL-TASK-03 output already exists")
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", str(source_image), "-vf", LOCAL_CUTAWAY_FILTER,
        "-frames:v", "72", "-r", "24", "-an", "-c:v", "libx264",
        "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-threads", "1", "-fflags", "+bitexact", "-flags:v", "+bitexact",
        "-map_metadata", "-1", "-movflags", "+faststart", "-n", str(output_mp4),
    ]
    runner(argv, check=True, capture_output=True, text=True, timeout=1800)
    info = inspect_video(output_mp4)
    frame_count, ffprobe_argv = _decoded_frame_count(output_mp4, runner=runner)
    if (
        info.width != 1280
        or info.height != 720
        or info.video_codec != "h264"
        or info.pixel_format != "yuv420p"
        or info.average_frame_rate != "24/1"
        or info.audio_stream_present
        or frame_count != 72
        or abs(info.duration_seconds - 3.0) > 0.01
    ):
        raise RuntimeError("LOCAL-TASK-03 fails the frozen deterministic media contract")
    return {
        "task_id": "LOCAL-TASK-03",
        "semantic_purpose": "COFFEE_TABLE_PRODUCT_DETAIL_LOCAL_CUTAWAY",
        "provider_task_id": None,
        "source": {
            "product_reference_id": "IN3725-PDP-02",
            "product_sku": "IN3725",
            "product_name": "Chunky Chestnut Coffee Table",
            "path": _relative(source_image, project_root),
            "sha256": PRODUCT_SOURCE_SHA256,
            "width": 1280,
            "height": 1280,
        },
        "transformation": {
            "type": "DETERMINISTIC_LOCAL_CENTER_CROP_OPTICAL_PUSH",
            "center_crop": {"x": 0, "y": 280, "width": 1280, "height": 720},
            "start_zoom": 1.0,
            "end_zoom": 1.035,
            "center_anchored": True,
            "filter_expression": LOCAL_CUTAWAY_FILTER,
            "ffmpeg_argv": argv,
            "ffprobe_argv": ffprobe_argv,
            "ai_generation": False,
            "background_replacement": False,
            "product_modification": False,
            "text_logo_or_new_objects": False,
        },
        "output": {
            "path": _relative(output_mp4, project_root),
            "sha256": sha256_file(output_mp4),
            "size_bytes": output_mp4.stat().st_size,
            "duration_seconds": info.duration_seconds,
            "frame_count": frame_count,
            "frame_rate": info.average_frame_rate,
            "width": info.width,
            "height": info.height,
            "video_codec": info.video_codec,
            "pixel_format": info.pixel_format,
            "audio_stream_present": info.audio_stream_present,
        },
        "provider_calls": 0,
        "paid_calls": 0,
        "actual_runway_credits": 0,
        "actual_cost_usd": 0.0,
    }


def extract_fixed_task_04_frame(
    source_mp4: Path,
    output_png: Path,
    *,
    project_root: Path,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    if sha256_file(source_mp4) != TASK_02_SHA256:
        raise ExternalInputBlocked("Coffee Table recovery TASK-02 source SHA-256 drift")
    if output_png.exists():
        raise RuntimeError("TASK-04 recovery frame output already exists")
    frame_count, ffprobe_argv = _decoded_frame_count(source_mp4, runner=runner)
    if frame_count <= TASK_04_FRAME_INDEX:
        raise RuntimeError("TASK-02 does not contain fixed zero-based frame 96")
    output_png.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_argv = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", str(source_mp4), "-vf", "select=eq(n\\,96)",
        "-frames:v", "1", "-c:v", "png", "-n", str(output_png),
    ]
    runner(ffmpeg_argv, check=True, capture_output=True, text=True, timeout=120)
    with Image.open(output_png) as image:
        image.verify()
    with Image.open(output_png) as image:
        width, height = image.size
        mode = image.mode
    if (width, height) != (1280, 720):
        raise RuntimeError("TASK-04 recovery frame must be 1280x720")
    if sha256_file(source_mp4) != TASK_02_SHA256:
        raise ExternalInputBlocked("Coffee Table recovery TASK-02 source changed during extraction")
    return {
        "source_task_id": "TASK-02",
        "source_provider_task_id": TASK_02_PROVIDER_ID,
        "source_status": "SUCCEEDED",
        "frame_selector": "FIXED_ZERO_BASED_FRAME_INDEX",
        "selected_zero_based_frame_index": TASK_04_FRAME_INDEX,
        "source_frame_count": frame_count,
        "source_mp4_path": _relative(source_mp4, project_root),
        "source_mp4_sha256": TASK_02_SHA256,
        "extracted_png_path": _relative(output_png, project_root),
        "extracted_png_sha256": sha256_file(output_png),
        "extracted_png_size_bytes": output_png.stat().st_size,
        "extracted_png_width": width,
        "extracted_png_height": height,
        "extracted_png_mode": mode,
        "ffprobe_argv": ffprobe_argv,
        "ffmpeg_argv": ffmpeg_argv,
        "visual_search": False,
        "fallback_frame_selection": False,
        "provider_calls": 0,
    }


def _validate_recovery_inputs(
    root: Path,
    *,
    manifest_path: Path,
    manifest_sha256: str,
    failed_live_run_id: str,
) -> dict[str, Any]:
    if manifest_path != PARENT_EXECUTION_MANIFEST:
        raise ExternalInputBlocked("Coffee Table recovery requires the exact parent manifest path")
    if manifest_sha256 != PARENT_EXECUTION_MANIFEST_SHA256:
        raise ExternalInputBlocked("Coffee Table recovery requires the exact parent manifest SHA-256")
    if failed_live_run_id != FAILED_LIVE_RUN_ID:
        raise ExternalInputBlocked("Coffee Table recovery requires the exact failed Live run ID")
    parent = root / manifest_path
    provider_results_path = root / "runs" / failed_live_run_id / "provider-results.json"
    if sha256_file(parent) != PARENT_EXECUTION_MANIFEST_SHA256:
        raise ExternalInputBlocked("Coffee Table parent execution manifest bytes drifted")
    if sha256_file(provider_results_path) != ORIGINAL_PROVIDER_RESULTS_SHA256:
        raise ExternalInputBlocked("Coffee Table original provider results bytes drifted")
    provider_results = _read_json(provider_results_path)
    historical = _validate_historical_results(provider_results, root)
    task_02_path = root / "outputs/broll" / failed_live_run_id / "TASK-02.mp4"
    _validate_reused_video(
        root / "outputs/broll" / failed_live_run_id / "TASK-01.mp4", TASK_01_SHA256, "TASK-01"
    )
    _validate_reused_video(task_02_path, TASK_02_SHA256, "TASK-02")
    product_source = root / PRODUCT_SOURCE
    if sha256_file(product_source) != PRODUCT_SOURCE_SHA256:
        raise ExternalInputBlocked("Coffee Table recovery PDP source SHA-256 drift")
    with Image.open(product_source) as image:
        image.verify()
    with Image.open(product_source) as image:
        if image.size != (1280, 1280):
            raise ExternalInputBlocked("Coffee Table recovery PDP source must be 1280x1280")
    prompt_path = root / TASK_04_PROMPT
    if sha256_file(prompt_path) != TASK_04_PROMPT_SHA256:
        raise ExternalInputBlocked("Coffee Table recovery TASK-04 prompt SHA-256 drift")
    original_evidence = {
        "parent_execution_manifest": {
            "path": manifest_path.as_posix(),
            "sha256": PARENT_EXECUTION_MANIFEST_SHA256,
        },
        "original_provider_results": {
            "path": _relative(provider_results_path, root),
            "sha256": ORIGINAL_PROVIDER_RESULTS_SHA256,
        },
    }
    return {
        "original_evidence": original_evidence,
        "historical_tasks": historical,
        "task_02_path": task_02_path,
        "product_source": product_source,
    }


def _validate_historical_results(value: Mapping[str, Any], root: Path) -> list[dict[str, Any]]:
    if (
        value.get("status") != "STOPPED"
        or value.get("stop_reason") != "STOPPED_TASK_FAILED"
        or value.get("submission_count") != 3
        or value.get("successful_outputs") != 2
        or value.get("failed_outputs") != 1
    ):
        raise ExternalInputBlocked("Coffee Table failed Live run summary drifted")
    results = value.get("results")
    if not isinstance(results, list) or len(results) != 3:
        raise ExternalInputBlocked("Coffee Table failed Live task history must contain three records")
    expected = (
        ("TASK-01", TASK_01_PROVIDER_ID, "SUCCEEDED", None, 25.0, TASK_01_SHA256),
        ("TASK-02", TASK_02_PROVIDER_ID, "SUCCEEDED", None, 25.0, TASK_02_SHA256),
        ("TASK-03", TASK_03_PROVIDER_ID, "FAILED", TASK_03_ERROR, 0.0, None),
    )
    normalized: list[dict[str, Any]] = []
    for record, facts in zip(results, expected, strict=True):
        task_id, provider_id, status, error_code, credits, artifact_sha = facts
        artifact = record.get("artifact") or {}
        if (
            record.get("task_id") != task_id
            or record.get("provider_task_id") != provider_id
            or record.get("status") != status
            or record.get("error_code") != error_code
            or float(record.get("actual_credits", -1)) != credits
            or record.get("submission_attempts") != 1
            or (artifact_sha is not None and artifact.get("sha256") != artifact_sha)
        ):
            raise ExternalInputBlocked(f"Coffee Table historical {task_id} facts drifted")
        item = {
            "task_id": task_id,
            "provider_task_id": provider_id,
            "status": status,
            "submission_attempts": 1,
            "actual_runway_credits": credits,
            "reuse_policy": "REUSE_IMMUTABLE_RESULT" if status == "SUCCEEDED" else "HISTORICAL_FAILURE_NO_RETRY",
            "automatic_retry": False,
            "automatic_replacement": False,
        }
        if artifact_sha is not None:
            item["artifact"] = {
                "path": str(artifact["path"]),
                "sha256": artifact_sha,
            }
        else:
            item["error_code"] = TASK_03_ERROR
            item["error_message"] = str(record.get("error_message") or "")
            item["historical_classification"] = "REAL_FAILED_PROVIDER_TASK"
            item["prohibited_reclassifications"] = [
                "NOT_SUBMITTED", "REJECTED_BEFORE_SUBMISSION", "ZERO-TASK"
            ]
        normalized.append(item)
    normalized.append(
        {
            "task_id": "TASK-04",
            "provider_task_id": None,
            "status": "NOT_SUBMITTED",
            "actual_runway_credits": 0,
            "future_submission_authorized": False,
        }
    )
    return normalized


def _validate_reused_video(path: Path, expected_sha: str, task_id: str) -> None:
    if sha256_file(path) != expected_sha:
        raise ExternalInputBlocked(f"Coffee Table recovery {task_id} MP4 SHA-256 drift")
    info = inspect_video(path)
    if (
        info.width != 1280
        or info.height != 720
        or info.video_codec != "h264"
        or info.pixel_format != "yuv420p"
        or info.average_frame_rate != "24/1"
        or info.audio_stream_present
        or info.duration_seconds < 5.0
    ):
        raise ExternalInputBlocked(f"Coffee Table recovery {task_id} media facts drifted")


def _prompt_evidence(root: Path) -> dict[str, Any]:
    path = root / TASK_04_PROMPT
    text = path.read_text(encoding="utf-8")
    if sha256_file(path) != TASK_04_PROMPT_SHA256:
        raise ExternalInputBlocked("Coffee Table recovery TASK-04 prompt SHA-256 drift")
    return {
        "path": TASK_04_PROMPT.as_posix(),
        "sha256": TASK_04_PROMPT_SHA256,
        "text": text,
        "utf16_code_units": len(text.encode("utf-16-le")) // 2,
        "version": 3,
    }


def _recovery_manifest(
    *,
    recovery_id: str,
    created_at: str,
    original_evidence: Mapping[str, Any],
    historical_tasks: list[dict[str, Any]],
    local_task_03: Mapping[str, Any],
    task_04_source: Mapping[str, Any],
    task_04_prompt: Mapping[str, Any],
) -> dict[str, Any]:
    timeline = [
        _segment(0, 3, "TASK-01", 0, 3, "ESTABLISH"),
        _segment(3, 5, "TASK-01", 3, 5, "WALK_START"),
        _segment(5, 7, "TASK-02", 0, 2, "WALK_COMPLETE"),
        _segment(7, 10, "TASK-02", 2, 5, "GLASS_PLACE"),
        _segment(10, 13, "LOCAL-TASK-03", 0, 3, "PRODUCT_DETAIL"),
        _segment(13, 17, "FUTURE-TASK-04", 0, 4, "CONTROLLED_SIT"),
        _segment(17, 18, "FUTURE-TASK-04", 4, 5, "HERO_POSE"),
        {
            "master_interval_seconds": {"start": 18, "end": 20},
            "source_id": "FUTURE-TASK-04-LAST_VALID_FRAME",
            "source_interval_seconds": {"start": 5, "end": 5},
            "role": "LOCAL_LAST_VALID_FRAME_HOLD",
            "duration_seconds": 2,
            "provider_calls": 0,
        },
    ]
    return {
        "schema_version": RECOVERY_SCHEMA,
        "recovery_id": recovery_id,
        "created_at": created_at,
        "status": READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW,
        "parent_execution_manifest": {
            "path": PARENT_EXECUTION_MANIFEST.as_posix(),
            "sha256": PARENT_EXECUTION_MANIFEST_SHA256,
        },
        "failed_live_run": {
            "run_id": FAILED_LIVE_RUN_ID,
            "status": "STOPPED_TASK_FAILED",
        },
        "immutable_original_evidence": dict(original_evidence),
        "historical_tasks": historical_tasks,
        "local_task_03": dict(local_task_03),
        "task_04_proposal": {
            "status": "FUTURE_NOT_SUBMITTED",
            "semantic_purpose": "CONTROLLED_SIT_AND_HERO",
            "input": dict(task_04_source),
            "prompt": dict(task_04_prompt),
            "request": {
                "provider": "runway",
                "model": "gen4_turbo",
                "ratio": "1280:720",
                "duration_seconds": 5,
                "projected_runway_credits": 25,
                "projected_cost_usd": 0.25,
                "submission_retries": 0,
                "replacement_tasks": 0,
            },
            "submission_authorized": False,
            "authorization_gate": "SEPARATE_OWNER_AUTHORIZATION_OF_THIS_RECOVERY_MANIFEST_SHA_REQUIRED",
        },
        "assembly": {
            "master_ratio": "16:9",
            "duration_seconds": 20,
            "timeline": timeline,
        },
        "delivery": {
            "master": "16:9",
            "1:1": "GUARDED_LOCAL_REFRAME_ONLY",
            "9:16": "GUARDED_LOCAL_REFRAME_ONLY",
            "native_ratio_provider_regeneration": "NOT_AUTHORIZED",
        },
        "budget": {
            "historical_actual": {"runway_credits": 50, "cost_usd": 0.50},
            "local_recovery_task_03": {"runway_credits": 0, "cost_usd": 0.0},
            "projected_additional_live": {"runway_credits": 25, "cost_usd": 0.25},
            "projected_final": {"runway_credits": 75, "cost_usd": 0.75},
            "automatic_retries": 0,
            "automatic_replacements": 0,
        },
        "provider_submissions_during_recovery_preparation": 0,
        "provider_calls_during_recovery_preparation": 0,
        "paid_calls_during_recovery_preparation": 0,
        "human_review": {
            "decision": None,
            "reviewer": None,
            "reviewed_at": None,
            "next_action": "OWNER_REVIEW_RECOVERY_MANIFEST_SHA",
        },
    }


def _segment(
    master_start: int,
    master_end: int,
    source_id: str,
    source_start: int,
    source_end: int,
    role: str,
) -> dict[str, Any]:
    return {
        "master_interval_seconds": {"start": master_start, "end": master_end},
        "source_id": source_id,
        "source_interval_seconds": {"start": source_start, "end": source_end},
        "role": role,
        "duration_seconds": master_end - master_start,
    }


def _revalidate_after_write(
    root: Path,
    validated: Mapping[str, Any],
    local_task_03: Mapping[str, Any],
    task_04_source: Mapping[str, Any],
    prompt: Mapping[str, Any],
) -> None:
    original = validated["original_evidence"]
    for item in original.values():
        if sha256_file(root / str(item["path"])) != item["sha256"]:
            raise RuntimeError("immutable original Coffee Table evidence changed during recovery")
    if sha256_file(validated["product_source"]) != PRODUCT_SOURCE_SHA256:
        raise RuntimeError("Coffee Table PDP source changed during recovery")
    if sha256_file(validated["task_02_path"]) != TASK_02_SHA256:
        raise RuntimeError("Coffee Table TASK-02 source changed during recovery")
    local_output = root / str(local_task_03["output"]["path"])
    if sha256_file(local_output) != local_task_03["output"]["sha256"]:
        raise RuntimeError("LOCAL-TASK-03 changed before manifest completion")
    frame_output = root / str(task_04_source["extracted_png_path"])
    if sha256_file(frame_output) != task_04_source["extracted_png_sha256"]:
        raise RuntimeError("TASK-04 frame changed before manifest completion")
    if sha256_file(root / str(prompt["path"])) != prompt["sha256"]:
        raise RuntimeError("TASK-04 prompt changed before manifest completion")


def _decoded_frame_count(
    path: Path,
    *,
    runner: CommandRunner,
) -> tuple[int, list[str]]:
    argv = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=nb_read_frames", "-of",
        "default=nokey=1:noprint_wrappers=1", str(path),
    ]
    completed = runner(argv, check=True, capture_output=True, text=True, timeout=60)
    try:
        count = int(completed.stdout.strip())
    except (AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError("FFprobe returned an invalid decoded frame count") from exc
    if count <= 0:
        raise RuntimeError("video source has no decoded frames")
    return count, argv


def _allocate_recovery_paths(
    root: Path,
    *,
    now: datetime | None,
) -> tuple[str, Path, Path]:
    current = now or datetime.now().astimezone()
    stamp = current.strftime("%Y%m%d-%H%M%S")
    media_root = root / "outputs/broll"
    manifest_root = root / "outputs/campaign-recovery-manifests"
    media_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    for sequence in range(1, 1000):
        recovery_id = f"COFFEE-TABLE-RECOVERY-{stamp}-{sequence:03d}"
        media_dir = media_root / recovery_id
        manifest_dir = manifest_root / recovery_id
        if media_dir.exists() or manifest_dir.exists():
            continue
        media_dir.mkdir(exist_ok=False)
        try:
            manifest_dir.mkdir(exist_ok=False)
        except Exception:
            media_dir.rmdir()
            raise
        return recovery_id, media_dir, manifest_dir
    raise RuntimeError("could not allocate a unique Coffee Table recovery ID")


def _block_existing_recovery(root: Path, manifest_sha: str, failed_run_id: str) -> None:
    recovery_root = root / "outputs/campaign-recovery-manifests"
    if not recovery_root.exists():
        return
    for path in recovery_root.glob("*/coffee-table-recovery-manifest.json"):
        try:
            value = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if (
            value.get("parent_execution_manifest", {}).get("sha256") == manifest_sha
            and value.get("failed_live_run", {}).get("run_id") == failed_run_id
        ):
            raise ExternalInputBlocked(
                f"Coffee Table recovery evidence already exists: {path.parent.name}"
            )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalInputBlocked(f"Coffee Table recovery cannot read evidence: {path.name}") from exc
    if not isinstance(value, dict):
        raise ExternalInputBlocked(f"Coffee Table recovery evidence must be an object: {path.name}")
    return value


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise RuntimeError(f"Coffee Table recovery manifest already exists: {path}")
        temporary.unlink()
    finally:
        temporary.unlink(missing_ok=True)


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()
