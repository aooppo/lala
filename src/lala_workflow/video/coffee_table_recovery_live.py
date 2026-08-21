from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image

from ..hashing import sha256_file
from ..providers.motion_base import MotionVideoProvider
from ..providers.runway_video import RunwayMotionProvider
from ..redaction import redact_text
from .config import load_video_config
from .domain import MediaArtifact, MotionVideoRequest, VideoTaskStatus
from .downloads import inspect_video, validate_media_artifact
from .storage import VideoRunContext, VideoRunStorage
from .validation import ExternalInputBlocked


RECOVERY_ID = "COFFEE-TABLE-RECOVERY-20260821-204901-001"
RECOVERY_V2_MANIFEST = Path(
    "outputs/campaign-recovery-manifests/"
    f"{RECOVERY_ID}/coffee-table-recovery-manifest-v2.json"
)
RECOVERY_V2_MANIFEST_SHA256 = (
    "e97ea0d34f4ea541ab07e6898083e7a35c3b82502030f8f40a06d58fb43e6cc3"
)
RECOVERY_V2_SCHEMA = "candidate16-coffee-table-recovery-manifest/v2"
HISTORICAL_RECOVERY_MANIFEST_SHA256 = (
    "8adaab7e3c3c128e7b1ae8c160804002aabae6b7a3ce11b5bb00646a2917b7b4"
)
PARENT_EXECUTION_MANIFEST_SHA256 = (
    "ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea"
)
ORIGINAL_PROVIDER_RESULTS_SHA256 = (
    "111a05f526944b26381fdf023cbcba4d8aaa58124490e3f7e9ceeedc3301c609"
)
TASK_01_PROVIDER_ID = "43da0f57-b584-4738-bbf1-05c33f653a3f"
TASK_01_SHA256 = "2c61cb10a6563d9d4c1e43811be17ef06c3244fc6eb2356d349f064cff6ffd4b"
TASK_02_PROVIDER_ID = "a7bb1630-21ff-4a2e-8d40-c3c9085d45ac"
TASK_02_SHA256 = "9565691a30e312518cc867792063194ae2a667b70d586fbee06d821cc9b7413f"
TASK_03_PROVIDER_ID = "03b195ab-98b0-4631-a845-03843656cbc5"
TASK_03_ERROR = "INTERNAL.BAD_OUTPUT.CODE01"
LOCAL_TASK_03_SHA256 = "edda268e70ce2af85ab4e11b93e684bbfd363b098f692bb45ae369f0c5928cef"
TASK_04_FRAME_INDEX = 92
TASK_04_FRAME_SHA256 = "95f68fa1f9bd3dcf6db94c2298511a224484c85c1fc5f278c3c67aa72e765e2e"
TASK_04_PROMPT_SHA256 = "e73cc7844806f8a25249c22da261e57df67ba7c3762172746b33a3b45b24f669"
FRAME_REVIEW_MANIFEST_SHA256 = (
    "8a0b888f51cd47523d98ed8ee7ffa3c550112257da0ad9af0b6c596a4bff5ce1"
)
FRAME_REVIEW_CSV_SHA256 = "7067c48fe59a87dffea2f74c7fd302deac4a8d8d3a967a34a9f0d972ee8221fa"
APPROVED_SOURCE_AGGREGATE_SHA256 = (
    "9c228cd1a31952d0709738f3891a3d3e335afac1e20cb9c0bccea40dd893acf2"
)
READY_FOR_OWNER_REVIEW = "READY_FOR_OWNER_REVIEW"

APPROVED_SOURCE_DIRS = (
    Path("assets/approved_anchors"),
    Path("assets/approved_keyframes"),
    Path("assets/voice/source"),
    Path("assets/voice/approved"),
    Path("assets/scripts"),
)
OWNER_REVIEW_ITEMS = (
    "Candidate 16 identity",
    "face",
    "hair",
    "red dress",
    "jewelry",
    "body proportions",
    "TASK-01 to TASK-02 continuity",
    "walking motion",
    "wine glass state",
    "wine glass placement",
    "hands",
    "Coffee Table geometry",
    "Coffee Table finish",
    "LOCAL-TASK-03 quality",
    "TASK-02 to TASK-04 continuity",
    "TASK-04 sit motion",
    "sofa interaction",
    "hero ending",
    "scene continuity",
    "20-sec pacing",
    "16:9 composition",
    "1:1 composition if created",
    "9:16 composition if created",
    "overall commercial quality",
    "MTL suitability",
)


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
ProviderFactory = Callable[
    [Callable[[str, str | None, float | None], None]], MotionVideoProvider
]


class CoffeeTableRecoveryLiveStopped(RuntimeError):
    def __init__(self, message: str, *, run_id: str, status: str) -> None:
        super().__init__(f"{message}; run_id={run_id}; status={status}")
        self.run_id = run_id
        self.status = status


@dataclass(frozen=True, slots=True)
class CoffeeTableRecoveryLiveOutcome:
    run_id: str
    run_dir: Path
    status: str
    recovery_id: str
    manifest_sha256: str
    provider_task_id: str
    task_04: Mapping[str, Any]
    delivery: Mapping[str, Any]
    review_package: Mapping[str, Any]
    integrity: Mapping[str, Any]
    provider_submissions: int
    automatic_paid_retries: int
    automatic_replacement_tasks: int
    actual_credits: float | None
    actual_cost_usd: float | None
    historical_credits: float
    historical_cost_usd: float
    total_credits: float | None
    total_cost_usd: float | None


def execute_coffee_table_recovery_live(
    project_root: Path,
    *,
    manifest_path: Path,
    manifest_sha256: str,
    confirm_owner_authorized_live: bool,
    max_runway_credits: float,
    max_provider_cost_usd: float,
    environ: Mapping[str, str] | None = None,
    provider_factory: ProviderFactory | None = None,
    command_runner: CommandRunner = subprocess.run,
    now: datetime | None = None,
) -> CoffeeTableRecoveryLiveOutcome:
    root = project_root.resolve()
    environment = os.environ if environ is None else environ
    if manifest_path != RECOVERY_V2_MANIFEST:
        raise ExternalInputBlocked(
            "BLOCKED_RECOVERY_MANIFEST_INTEGRITY: exact Recovery Manifest V2 path required"
        )
    if manifest_sha256 != RECOVERY_V2_MANIFEST_SHA256:
        raise ExternalInputBlocked(
            "BLOCKED_RECOVERY_MANIFEST_INTEGRITY: exact Recovery Manifest V2 SHA-256 required"
        )
    if not confirm_owner_authorized_live:
        raise ExternalInputBlocked("Coffee Table Recovery Live requires explicit Owner authorization")
    if max_runway_credits != 25 or max_provider_cost_usd != 0.25:
        raise ExternalInputBlocked(
            "Coffee Table Recovery Live caps must be exactly 25 credits and USD 0.25"
        )
    if environment.get("VIDEO_ALLOW_LIVE_CALLS") != "true":
        raise ExternalInputBlocked("live video calls require exact VIDEO_ALLOW_LIVE_CALLS=true")
    credential = str(environment.get("RUNWAYML_API_SECRET") or "").strip()
    if not credential:
        raise ExternalInputBlocked("live provider credential is missing: RUNWAYML_API_SECRET")

    validated = _validate_v2_and_protected_inputs(root)
    _block_prior_recovery_live(root)

    storage = VideoRunStorage(root, secrets=(credential,))
    run = storage.create_run("coffee-table-recovery-live", now=now)
    raw_dir = root / "outputs/broll" / run.run_id
    raw_dir.mkdir(parents=True, exist_ok=False)
    authorization = {
        "recovery_id": RECOVERY_ID,
        "manifest_path": RECOVERY_V2_MANIFEST.as_posix(),
        "manifest_sha256": RECOVERY_V2_MANIFEST_SHA256,
        "owner_authorized_live": True,
        "task": "TASK-04_ONLY",
        "max_new_provider_submissions": 1,
        "max_new_runway_tasks": 1,
        "max_runway_credits": 25,
        "max_provider_cost_usd": 0.25,
        "automatic_paid_retries": 0,
        "automatic_replacement_tasks": 0,
        "video_live_permission_enabled": True,
        "runway_credential_configured": True,
    }
    storage.write_json_new(run, "coffee-table-recovery-live-authorization.json", authorization)
    storage.append_event(
        run,
        "recovery_live_prepared",
        {"state": "PREPARED", "manifest_sha256": RECOVERY_V2_MANIFEST_SHA256},
    )

    request = _task_04_request(root, run, validated["manifest"])
    storage.write_json_new(
        run,
        "request.json",
        {
            "mode": "LIVE",
            "action": "coffee-table-recovery-live",
            "recovery_id": RECOVERY_ID,
            "manifest_sha256": RECOVERY_V2_MANIFEST_SHA256,
            "provider_call_count": 1,
            "submission_attempts": 1,
            "automatic_paid_retries": 0,
            "automatic_replacements": 0,
            "task": _request_evidence(request, root),
        },
    )

    current: dict[str, Any] = {"provider_task_id": None, "estimated_credits": None}

    def task_created_sink(
        task_id: str, _request_id: str | None, estimated_credits: float | None
    ) -> None:
        if current["provider_task_id"] not in (None, task_id):
            raise RuntimeError("provider task ID changed during durable persistence")
        current["provider_task_id"] = task_id
        current["estimated_credits"] = estimated_credits
        storage.append_event(
            run,
            "provider_task_id_durable",
            {
                "state": "TASK_ID_DURABLE",
                "task_id": "TASK-04",
                "provider_task_id": task_id,
                "estimated_credits": estimated_credits,
            },
        )

    if provider_factory is None:
        definition = load_video_config(root, require_inputs=False).providers["runway"]

        def provider_factory(
            sink: Callable[[str, str | None, float | None], None]
        ) -> MotionVideoProvider:
            return RunwayMotionProvider(
                definition,
                api_key=credential,
                max_poll_retries=2,
                task_created_sink=sink,
            )

    provider = provider_factory(task_created_sink)
    provider.validate_request(request)
    storage.append_event(
        run,
        "task_submitting",
        {
            "state": "SUBMITTING",
            "task_id": "TASK-04",
            "submission_attempt": 1,
            "planned_credits": 25,
        },
    )
    submitted_at = datetime.now().astimezone().isoformat()
    try:
        returned_task_id = provider.submit(request)
    except Exception as exc:
        known_id = current.get("provider_task_id")
        if not known_id:
            status = "BLOCKED_SUBMISSION_UNKNOWN"
            _write_stopped_evidence(
                storage,
                run,
                status=status,
                provider_task_id=None,
                actual_credits=None,
                error_code="SUBMISSION_UNKNOWN",
                error_message=redact_text(str(exc), secrets=(credential,)),
            )
            raise CoffeeTableRecoveryLiveStopped(
                "TASK-04 submission acceptance is unknown",
                run_id=run.run_id,
                status=status,
            ) from exc
        returned_task_id = str(known_id)
        storage.append_event(
            run,
            "submit_return_interrupted_after_durable_id",
            {"task_id": "TASK-04", "provider_task_id": returned_task_id},
        )
    if current["provider_task_id"] is None:
        task_created_sink(str(returned_task_id), None, None)
    elif current["provider_task_id"] != str(returned_task_id):
        status = "BLOCKED_SUBMISSION_UNKNOWN"
        _write_stopped_evidence(
            storage,
            run,
            status=status,
            provider_task_id=str(current["provider_task_id"]),
            actual_credits=None,
            error_code="TASK_ID_MISMATCH",
            error_message="provider task ID changed after durable persistence",
        )
        raise CoffeeTableRecoveryLiveStopped(
            "provider task ID mismatch",
            run_id=run.run_id,
            status=status,
        )
    provider_task_id = str(current["provider_task_id"])
    storage.append_event(
        run,
        "task_submitted",
        {
            "state": "SUBMITTED",
            "task_id": "TASK-04",
            "provider_task_id": provider_task_id,
        },
    )

    result = provider.wait(provider_task_id, request.timeout_seconds)
    completed_at = datetime.now().astimezone().isoformat()
    storage.append_event(
        run,
        "provider_task_terminal",
        {
            "task_id": "TASK-04",
            "provider_task_id": provider_task_id,
            "status": result.status.value,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "estimated_credits": result.estimated_credits,
            "actual_credits": result.actual_credits,
        },
    )
    actual_credits = (
        float(result.actual_credits) if result.actual_credits is not None else None
    )
    if actual_credits is not None and actual_credits > 25:
        status = "BLOCKED_TASK04_PROVIDER"
        _write_stopped_evidence(
            storage,
            run,
            status=status,
            provider_task_id=provider_task_id,
            actual_credits=actual_credits,
            error_code="CREDIT_CAP_EXCEEDED",
            error_message="provider reported TASK-04 credits above authorized cap",
        )
        raise CoffeeTableRecoveryLiveStopped(
            "TASK-04 credit cap exceeded", run_id=run.run_id, status=status
        )
    if result.status is not VideoTaskStatus.SUCCEEDED:
        status = "BLOCKED_TASK04_PROVIDER"
        _write_stopped_evidence(
            storage,
            run,
            status=status,
            provider_task_id=provider_task_id,
            actual_credits=actual_credits,
            error_code=result.error_code,
            error_message=result.error_message,
        )
        raise CoffeeTableRecoveryLiveStopped(
            "TASK-04 provider task did not succeed", run_id=run.run_id, status=status
        )

    try:
        artifacts = provider.download_results(
            result, raw_dir, "TASK-04", request.timeout_seconds, 0
        )
        if len(artifacts) != 1:
            raise RuntimeError("TASK-04 must yield exactly one MP4")
        artifact = _validate_task_04_artifact(validate_media_artifact(artifacts[0]))
    except Exception as exc:
        status = "BLOCKED_TASK04_PROVIDER"
        _write_stopped_evidence(
            storage,
            run,
            status=status,
            provider_task_id=provider_task_id,
            actual_credits=actual_credits,
            error_code="INVALID_TASK04_OUTPUT",
            error_message=redact_text(str(exc), secrets=(credential,)),
        )
        raise CoffeeTableRecoveryLiveStopped(
            "TASK-04 output validation failed", run_id=run.run_id, status=status
        ) from exc

    task_04 = {
        "task_id": "TASK-04",
        "operation_id": run.run_id,
        "provider_task_id": provider_task_id,
        "status": "SUCCEEDED",
        "submission_timestamp": submitted_at,
        "completion_timestamp": completed_at,
        "input_frame_index": 92,
        "input_png_sha256": TASK_04_FRAME_SHA256,
        "prompt_sha256": TASK_04_PROMPT_SHA256,
        "artifact": _artifact_evidence(artifact, root),
        "estimated_credits": result.estimated_credits,
        "actual_credits": actual_credits,
        "actual_cost_usd": None if actual_credits is None else actual_credits * 0.01,
        "cost_status": "UNKNOWN" if actual_credits is None else "ACTUAL_REPORTED",
    }
    storage.write_json_new(
        run,
        "provider-results.json",
        {
            "status": "TASK04_SUCCEEDED",
            "submission_count": 1,
            "successful_outputs": 1,
            "failed_outputs": 0,
            "provider_task_id": provider_task_id,
            "results": [task_04],
        },
    )
    storage.append_event(run, "assembly_started", {"state": "ASSEMBLING"})
    try:
        delivery = assemble_recovery_delivery(
            validated["task_01_path"],
            validated["task_02_path"],
            validated["local_task_03_path"],
            artifact.path,
            root / "outputs/final" / run.run_id,
            runner=command_runner,
        )
    except Exception as exc:
        status = "BLOCKED_ASSEMBLY"
        _write_cost(storage, run, actual_credits)
        storage.write_text_new(
            run,
            "summary.md",
            f"# Coffee Table Recovery Live {run.run_id}\n\n- Status: `{status}`\n"
            f"- Reason: `{redact_text(str(exc), secrets=(credential,))}`\n",
        )
        storage.append_event(run, "recovery_live_stopped", {"status": status})
        raise CoffeeTableRecoveryLiveStopped(
            "local assembly failed", run_id=run.run_id, status=status
        ) from exc

    storage.write_json_new(run, "delivery.json", delivery)
    cost = _write_cost(storage, run, actual_credits)
    integrity = _validate_v2_and_protected_inputs(root)["integrity"]
    review_package = _build_review_package(
        root,
        run,
        validated,
        artifact,
        delivery,
        task_04,
        cost,
        integrity,
    )
    storage.write_json_new(run, "review-package.json", review_package)
    storage.write_text_new(
        run,
        "summary.md",
        f"# Coffee Table Recovery Live {run.run_id}\n\n"
        f"- Status: `{READY_FOR_OWNER_REVIEW}`\n"
        f"- Recovery Manifest SHA-256: `{RECOVERY_V2_MANIFEST_SHA256}`\n"
        "- Provider submissions: 1\n"
        "- Automatic paid retries/replacements: 0 / 0\n"
        "- 1:1: `BLOCKED_SAFE_AREA`\n"
        "- 9:16: `BLOCKED_SAFE_AREA`\n"
        "- Human review: blank\n",
    )
    storage.append_event(run, "ready_for_owner_review", {"status": READY_FOR_OWNER_REVIEW})
    total_credits = None if actual_credits is None else 50 + actual_credits
    total_cost = None if actual_credits is None else 0.50 + actual_credits * 0.01
    return CoffeeTableRecoveryLiveOutcome(
        run_id=run.run_id,
        run_dir=run.path,
        status=READY_FOR_OWNER_REVIEW,
        recovery_id=RECOVERY_ID,
        manifest_sha256=RECOVERY_V2_MANIFEST_SHA256,
        provider_task_id=provider_task_id,
        task_04=task_04,
        delivery=delivery,
        review_package=review_package,
        integrity=integrity,
        provider_submissions=1,
        automatic_paid_retries=0,
        automatic_replacement_tasks=0,
        actual_credits=actual_credits,
        actual_cost_usd=None if actual_credits is None else actual_credits * 0.01,
        historical_credits=50,
        historical_cost_usd=0.50,
        total_credits=total_credits,
        total_cost_usd=total_cost,
    )


def assemble_recovery_delivery(
    task_01: Path,
    task_02: Path,
    local_task_03: Path,
    task_04: Path,
    output_dir: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    for path in (task_01, task_02, local_task_03, task_04):
        if not path.is_file():
            raise RuntimeError(f"assembly input is missing: {path}")
        inspect_video(path)
    output_dir.mkdir(parents=True, exist_ok=False)
    terminal_png = output_dir / "TASK-04-last-valid-frame.png"
    terminal_hold = _extract_last_decoded_frame(task_04, terminal_png, runner=runner)
    master = output_dir / "coffee-table-master-16x9.mp4"
    filter_graph = (
        "[0:v]split=2[t1a][t1b];"
        "[1:v]split=2[t2a][t2b];"
        "[3:v]split=2[t4a][t4b];"
        "[t1a]trim=start=0:end=3,setpts=PTS-STARTPTS,fps=24,scale=1280:720,setsar=1[v0];"
        "[t1b]trim=start=3:end=5,setpts=PTS-STARTPTS,fps=24,scale=1280:720,setsar=1[v1];"
        "[t2a]trim=start=0:end=2,setpts=PTS-STARTPTS,fps=24,scale=1280:720,setsar=1[v2];"
        "[t2b]trim=start=2:end=5,setpts=PTS-STARTPTS,fps=24,scale=1280:720,setsar=1[v3];"
        "[2:v]trim=start=0:end=3,setpts=PTS-STARTPTS,fps=24,scale=1280:720,setsar=1[v4];"
        "[t4a]trim=start=0:end=4,setpts=PTS-STARTPTS,fps=24,scale=1280:720,setsar=1[v5];"
        "[t4b]trim=start=4:end=5,setpts=PTS-STARTPTS,fps=24,scale=1280:720,setsar=1[v6];"
        "[4:v]trim=duration=2,setpts=PTS-STARTPTS,fps=24,scale=1280:720,setsar=1[v7];"
        "[v0][v1][v2][v3][v4][v5][v6][v7]concat=n=8:v=1:a=0,format=yuv420p[v]"
    )
    argv = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", str(task_01), "-i", str(task_02), "-i", str(local_task_03),
        "-i", str(task_04), "-loop", "1", "-framerate", "24", "-t", "2",
        "-i", str(terminal_png), "-filter_complex", filter_graph, "-map", "[v]",
        "-an", "-r", "24", "-frames:v", "480", "-c:v", "libx264",
        "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-threads", "1", "-fflags", "+bitexact", "-flags:v", "+bitexact",
        "-map_metadata", "-1", "-movflags", "+faststart", "-n", str(master),
    ]
    runner(argv, check=True, capture_output=True, text=True, timeout=1800)
    master_evidence = _strict_master_evidence(master, runner=runner)
    safe_area_reason = (
        "No Owner-approved objective subject/ROI safe-area contract exists to prove that "
        "Candidate 16, Coffee Table, wine glass, and interaction context survive this crop."
    )
    safe_area = {
        "status": "BLOCKED_SAFE_AREA",
        "reason": safe_area_reason,
        "output_created": False,
        "provider_calls": 0,
        "native_provider_regeneration": "NOT_AUTHORIZED",
    }
    return {
        "status": READY_FOR_OWNER_REVIEW,
        "master": master_evidence,
        "terminal_hold": terminal_hold,
        "input_sha256": {
            "TASK-01": sha256_file(task_01),
            "TASK-02": sha256_file(task_02),
            "LOCAL-TASK-03": sha256_file(local_task_03),
            "TASK-04": sha256_file(task_04),
        },
        "assembly_ffmpeg_argv": argv,
        "timeline_validation": "PASS",
        "local_1_1": dict(safe_area),
        "local_9_16": dict(safe_area),
        "provider_calls": 0,
        "native_provider_regeneration": "NOT_AUTHORIZED",
    }


def approved_source_aggregate_sha256(root: Path) -> tuple[str, int]:
    paths = sorted(
        path
        for relative in APPROVED_SOURCE_DIRS
        for path in (root / relative).rglob("*")
        if path.is_file()
    )
    lines = "".join(
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n" for path in paths
    )
    return sha256(lines.encode("utf-8")).hexdigest(), len(paths)


def _validate_v2_and_protected_inputs(root: Path) -> dict[str, Any]:
    manifest_file = root / RECOVERY_V2_MANIFEST
    _require_sha(manifest_file, RECOVERY_V2_MANIFEST_SHA256, "Recovery Manifest V2")
    manifest = _read_json(manifest_file)
    if (
        manifest.get("schema_version") != RECOVERY_V2_SCHEMA
        or manifest.get("recovery_id") != RECOVERY_ID
        or manifest.get("status") != "READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_MANIFEST_REVIEW"
    ):
        raise ExternalInputBlocked("BLOCKED_RECOVERY_MANIFEST_INTEGRITY: V2 identity drift")

    supersedes = manifest.get("supersedes") or {}
    _require_manifest_path_sha(
        root,
        supersedes,
        "previous_recovery_manifest_path",
        "previous_recovery_manifest_sha256",
        HISTORICAL_RECOVERY_MANIFEST_SHA256,
        "historical Recovery Manifest",
    )
    parent = manifest.get("parent_execution_manifest") or {}
    _require_manifest_path_sha(
        root,
        parent,
        "path",
        "sha256",
        PARENT_EXECUTION_MANIFEST_SHA256,
        "parent Execution Manifest",
    )
    original = (manifest.get("immutable_original_evidence") or {}).get(
        "original_provider_results"
    ) or {}
    _require_manifest_path_sha(
        root,
        original,
        "path",
        "sha256",
        ORIGINAL_PROVIDER_RESULTS_SHA256,
        "original provider results",
    )
    decision = manifest.get("source_frame_owner_decision") or {}
    _require_manifest_path_sha(
        root,
        decision,
        "frame_review_manifest_path",
        "frame_review_manifest_sha256",
        FRAME_REVIEW_MANIFEST_SHA256,
        "frame review manifest",
    )
    _require_manifest_path_sha(
        root,
        decision,
        "review_file_path",
        "review_file_sha256",
        FRAME_REVIEW_CSV_SHA256,
        "frame review CSV",
    )
    if (
        decision.get("decision") != "FRAME_92_SELECTED"
        or decision.get("selected_zero_based_frame_index") != TASK_04_FRAME_INDEX
        or decision.get("selected_png_sha256") != TASK_04_FRAME_SHA256
        or decision.get("reviewer") != "Project owner (explicit human decision)"
    ):
        raise ExternalInputBlocked("BLOCKED_TASK04_SOURCE_INTEGRITY: Owner decision drift")

    tasks = manifest.get("historical_tasks")
    if not isinstance(tasks, list) or len(tasks) != 4:
        raise ExternalInputBlocked("BLOCKED_INTEGRITY: historical task list drift")
    expected = (
        ("TASK-01", TASK_01_PROVIDER_ID, "SUCCEEDED", 25.0, TASK_01_SHA256),
        ("TASK-02", TASK_02_PROVIDER_ID, "SUCCEEDED", 25.0, TASK_02_SHA256),
        ("TASK-03", TASK_03_PROVIDER_ID, "FAILED", 0.0, None),
        ("TASK-04", None, "NOT_SUBMITTED", 0.0, None),
    )
    for task, facts in zip(tasks, expected, strict=True):
        task_id, provider_id, status, credits, artifact_sha = facts
        if (
            task.get("task_id") != task_id
            or task.get("provider_task_id") != provider_id
            or task.get("status") != status
            or float(task.get("actual_runway_credits", -1)) != credits
        ):
            raise ExternalInputBlocked(f"BLOCKED_INTEGRITY: historical {task_id} drift")
        if artifact_sha is not None and (task.get("artifact") or {}).get("sha256") != artifact_sha:
            raise ExternalInputBlocked(f"BLOCKED_INTEGRITY: historical {task_id} artifact drift")
    if (
        tasks[2].get("error_code") != TASK_03_ERROR
        or tasks[2].get("historical_classification") != "REAL_FAILED_PROVIDER_TASK"
    ):
        raise ExternalInputBlocked("BLOCKED_INTEGRITY: historical TASK-03 failure drift")

    task_01_path = root / str(tasks[0]["artifact"]["path"])
    task_02_path = root / str(tasks[1]["artifact"]["path"])
    _require_motion_video(task_01_path, TASK_01_SHA256, minimum_duration=5.0)
    _require_motion_video(task_02_path, TASK_02_SHA256, minimum_duration=5.0)

    local = manifest.get("local_task_03") or {}
    local_output = local.get("output") or {}
    if (
        local.get("task_id") != "LOCAL-TASK-03"
        or local.get("reuse_policy") != "EXACT_BYTE_REUSE_FROM_PREVIOUS_RECOVERY"
        or local_output.get("sha256") != LOCAL_TASK_03_SHA256
        or local.get("provider_calls") != 0
    ):
        raise ExternalInputBlocked("BLOCKED_LOCAL_TASK03_INTEGRITY: manifest drift")
    local_path = root / str(local_output.get("path") or "")
    _require_motion_video(
        local_path,
        LOCAL_TASK_03_SHA256,
        minimum_duration=3.0,
        exact_duration=3.0,
        exact_frame_count=72,
    )

    proposal = manifest.get("task_04_proposal") or {}
    source = proposal.get("input") or {}
    prompt = proposal.get("prompt") or {}
    request = proposal.get("request") or {}
    if (
        source.get("selected_zero_based_frame_index") != TASK_04_FRAME_INDEX
        or source.get("extracted_png_sha256") != TASK_04_FRAME_SHA256
        or source.get("source_mp4_sha256") != TASK_02_SHA256
        or prompt.get("sha256") != TASK_04_PROMPT_SHA256
        or request
        != {
            "provider": "runway",
            "model": "gen4_turbo",
            "ratio": "1280:720",
            "duration_seconds": 5,
            "projected_runway_credits": 25,
            "projected_cost_usd": 0.25,
            "submission_retries": 0,
            "replacement_tasks": 0,
        }
    ):
        raise ExternalInputBlocked("BLOCKED_TASK04_SOURCE_INTEGRITY: proposal drift")
    frame_path = root / str(source.get("extracted_png_path") or "")
    _require_sha(frame_path, TASK_04_FRAME_SHA256, "TASK-04 frame 92 PNG")
    with Image.open(frame_path) as image:
        image.verify()
    with Image.open(frame_path) as image:
        if image.size != (1280, 720) or image.mode != "RGB":
            raise ExternalInputBlocked("BLOCKED_TASK04_SOURCE_INTEGRITY: PNG media drift")
    prompt_path = root / str(prompt.get("path") or "")
    _require_sha(prompt_path, TASK_04_PROMPT_SHA256, "TASK-04 prompt v3")

    budget = manifest.get("budget") or {}
    if (
        budget.get("historical_actual") != {"runway_credits": 50, "cost_usd": 0.5}
        or budget.get("projected_additional_live")
        != {"runway_credits": 25, "cost_usd": 0.25}
        or budget.get("projected_final") != {"runway_credits": 75, "cost_usd": 0.75}
        or budget.get("automatic_retries") != 0
        or budget.get("automatic_replacements") != 0
    ):
        raise ExternalInputBlocked("BLOCKED_INTEGRITY: Recovery V2 budget drift")
    _validate_timeline(manifest)
    aggregate, count = approved_source_aggregate_sha256(root)
    if aggregate != APPROVED_SOURCE_AGGREGATE_SHA256 or count != 35:
        raise ExternalInputBlocked("BLOCKED_INTEGRITY: approved-source aggregate drift")
    integrity = {
        "recovery_manifest_v2_sha256": RECOVERY_V2_MANIFEST_SHA256,
        "historical_recovery_manifest_sha256": HISTORICAL_RECOVERY_MANIFEST_SHA256,
        "parent_execution_manifest_sha256": PARENT_EXECUTION_MANIFEST_SHA256,
        "original_provider_results_sha256": ORIGINAL_PROVIDER_RESULTS_SHA256,
        "task_01_sha256": TASK_01_SHA256,
        "task_02_sha256": TASK_02_SHA256,
        "local_task_03_sha256": LOCAL_TASK_03_SHA256,
        "task_04_frame_92_sha256": TASK_04_FRAME_SHA256,
        "task_04_prompt_v3_sha256": TASK_04_PROMPT_SHA256,
        "approved_source_aggregate_sha256": aggregate,
        "approved_source_file_count": count,
        "status": "PASS",
    }
    return {
        "manifest": manifest,
        "task_01_path": task_01_path,
        "task_02_path": task_02_path,
        "local_task_03_path": local_path,
        "frame_path": frame_path,
        "prompt_path": prompt_path,
        "integrity": integrity,
    }


def _task_04_request(
    root: Path, run: VideoRunContext, manifest: Mapping[str, Any]
) -> MotionVideoRequest:
    proposal = manifest["task_04_proposal"]
    source = proposal["input"]
    prompt = proposal["prompt"]
    request = proposal["request"]
    return MotionVideoRequest(
        request_id="TASK-04",
        run_id=run.run_id,
        preset="coffee-table-recovery-live",
        shot_id="TASK-04",
        variation=1,
        provider="runway",
        model=str(request["model"]),
        image_path=root / str(source["extracted_png_path"]),
        image_sha256=str(source["extracted_png_sha256"]),
        prompt_path=root / str(prompt["path"]),
        prompt_text=str(prompt["text"]),
        prompt_sha256=str(prompt["sha256"]),
        ratio=str(request["ratio"]),
        duration_seconds=int(request["duration_seconds"]),
        seed=None,
        output_format="mp4",
        timeout_seconds=1800,
        max_retries=0,
    )


def _extract_last_decoded_frame(
    source: Path, output_png: Path, *, runner: CommandRunner
) -> dict[str, Any]:
    probe = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=nb_read_frames", "-of",
        "default=nokey=1:noprint_wrappers=1", str(source),
    ]
    completed = runner(probe, check=True, capture_output=True, text=True, timeout=60)
    try:
        frame_count = int(completed.stdout.strip())
    except (TypeError, ValueError) as exc:
        raise RuntimeError("FFprobe returned invalid decoded frame count") from exc
    if frame_count <= 0:
        raise RuntimeError("TASK-04 contains no decoded frame")
    selected = frame_count - 1
    extract = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i",
        str(source), "-vf", f"select=eq(n\\,{selected})", "-frames:v", "1",
        "-c:v", "png", "-n", str(output_png),
    ]
    runner(extract, check=True, capture_output=True, text=True, timeout=120)
    with Image.open(output_png) as image:
        image.verify()
    with Image.open(output_png) as image:
        width, height = image.size
        mode = image.mode
    if (width, height) != (1280, 720):
        raise RuntimeError("TASK-04 terminal frame must be 1280x720")
    return {
        "frame_selector": "LAST_VALID_DECODED_FRAME",
        "frame_count": frame_count,
        "selected_zero_based_frame_index": selected,
        "source_mp4_path": str(source),
        "source_mp4_sha256": sha256_file(source),
        "extracted_png_path": str(output_png),
        "extracted_png_sha256": sha256_file(output_png),
        "extracted_png_width": width,
        "extracted_png_height": height,
        "extracted_png_mode": mode,
        "hold_duration_seconds": 2,
        "hold_frame_count": 48,
        "ffprobe_argv": probe,
        "ffmpeg_argv": extract,
        "provider_calls": 0,
    }


def _strict_master_evidence(path: Path, *, runner: CommandRunner) -> dict[str, Any]:
    info = inspect_video(path)
    frame_count = _decoded_frame_count(path, runner=runner)
    if (
        info.width != 1280
        or info.height != 720
        or info.video_codec != "h264"
        or info.pixel_format != "yuv420p"
        or info.average_frame_rate != "24/1"
        or info.audio_stream_present
        or frame_count != 480
        or abs(info.duration_seconds - 20.0) > 0.01
    ):
        raise RuntimeError("Coffee Table master fails exact twenty-second media contract")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "duration_seconds": info.duration_seconds,
        "frame_count": frame_count,
        "frame_rate": info.average_frame_rate,
        "width": info.width,
        "height": info.height,
        "container": info.container,
        "video_codec": info.video_codec,
        "pixel_format": info.pixel_format,
        "audio_stream_present": info.audio_stream_present,
    }


def _decoded_frame_count(path: Path, *, runner: CommandRunner) -> int:
    completed = runner(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
            "-show_entries", "stream=nb_read_frames", "-of",
            "default=nokey=1:noprint_wrappers=1", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        return int(completed.stdout.strip())
    except (TypeError, ValueError) as exc:
        raise RuntimeError("FFprobe returned invalid decoded frame count") from exc


def _validate_task_04_artifact(artifact: MediaArtifact) -> MediaArtifact:
    if (
        artifact.width != 1280
        or artifact.height != 720
        or artifact.video_codec != "h264"
        or artifact.duration_seconds is None
        or not 4.8 <= artifact.duration_seconds <= 5.2
        or artifact.size_bytes <= 0
    ):
        raise RuntimeError("TASK-04 output fails frozen media bounds")
    return artifact


def _build_review_package(
    root: Path,
    run: VideoRunContext,
    validated: Mapping[str, Any],
    task_04_artifact: MediaArtifact,
    delivery: Mapping[str, Any],
    task_04: Mapping[str, Any],
    cost: Mapping[str, Any],
    integrity: Mapping[str, Any],
) -> dict[str, Any]:
    package = root / "outputs/reviews/coffee-table-final" / run.run_id
    package.mkdir(parents=True, exist_ok=False)
    sources = (
        (validated["task_01_path"], "TASK-01.mp4"),
        (validated["task_02_path"], "TASK-02.mp4"),
        (validated["local_task_03_path"], "LOCAL-TASK-03.mp4"),
        (task_04_artifact.path, "TASK-04.mp4"),
        (Path(str(delivery["master"]["path"])), "coffee-table-master-16x9.mp4"),
        (root / RECOVERY_V2_MANIFEST, "coffee-table-recovery-manifest-v2.json"),
    )
    items = []
    for source, name in sources:
        target = package / name
        shutil.copyfile(source, target)
        if sha256_file(target) != sha256_file(source):
            raise RuntimeError(f"review package copy hash mismatch: {name}")
        items.append(
            {"path": str(target), "sha256": sha256_file(target), "size_bytes": target.stat().st_size}
        )
    review_csv = package / "review.csv"
    with review_csv.open("x", encoding="utf-8", newline="") as output:
        fieldnames = ("check_item", "decision", "notes", "reviewer", "reviewed_at")
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in OWNER_REVIEW_ITEMS:
            writer.writerow(
                {
                    "check_item": item,
                    "decision": "",
                    "notes": "",
                    "reviewer": "",
                    "reviewed_at": "",
                }
            )
        output.flush()
        os.fsync(output.fileno())
    evidence = {
        "run_id": run.run_id,
        "status": READY_FOR_OWNER_REVIEW,
        "recovery_id": RECOVERY_ID,
        "recovery_manifest_sha256": RECOVERY_V2_MANIFEST_SHA256,
        "historical_provider_task_ids": {
            "TASK-01": TASK_01_PROVIDER_ID,
            "TASK-02": TASK_02_PROVIDER_ID,
            "TASK-03": TASK_03_PROVIDER_ID,
        },
        "task_04": dict(task_04),
        "delivery": dict(delivery),
        "cost": dict(cost),
        "integrity": dict(integrity),
        "human_review_fields": "BLANK",
        "automatic_paid_retries": 0,
        "automatic_replacements": 0,
        "native_provider_regeneration": "NOT_AUTHORIZED",
    }
    evidence_path = package / "evidence.json"
    _write_json_exclusive(evidence_path, evidence)
    manifest = {
        "run_id": run.run_id,
        "status": READY_FOR_OWNER_REVIEW,
        "items": items,
        "evidence": {"path": str(evidence_path), "sha256": sha256_file(evidence_path)},
        "review_csv": {
            "path": str(review_csv),
            "sha256": sha256_file(review_csv),
            "human_fields": "BLANK",
            "checklist_item_count": len(OWNER_REVIEW_ITEMS),
        },
        "safe_area": {
            "1:1": delivery["local_1_1"]["status"],
            "9:16": delivery["local_9_16"]["status"],
        },
    }
    manifest_path = package / "manifest.json"
    _write_json_exclusive(manifest_path, manifest)
    return {
        "path": str(package),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "review_csv_path": str(review_csv),
        "review_csv_sha256": sha256_file(review_csv),
        "human_review_fields": "BLANK",
        "item_count": len(items),
    }


def _write_stopped_evidence(
    storage: VideoRunStorage,
    run: VideoRunContext,
    *,
    status: str,
    provider_task_id: str | None,
    actual_credits: float | None,
    error_code: str | None,
    error_message: str | None,
) -> None:
    storage.write_json_new(
        run,
        "provider-results.json",
        {
            "status": status,
            "submission_count": 1,
            "successful_outputs": 0,
            "failed_outputs": 0 if status == "BLOCKED_SUBMISSION_UNKNOWN" else 1,
            "provider_task_id": provider_task_id,
            "error_code": error_code,
            "error_message": error_message,
            "automatic_paid_retries": 0,
            "automatic_replacement_tasks": 0,
        },
    )
    _write_cost(storage, run, actual_credits)
    storage.write_text_new(
        run,
        "summary.md",
        f"# Coffee Table Recovery Live {run.run_id}\n\n"
        f"- Status: `{status}`\n"
        "- Provider submit invocations: 1\n"
        "- Automatic paid retries/replacements: 0 / 0\n",
    )
    storage.append_event(run, "recovery_live_stopped", {"status": status})


def _write_cost(
    storage: VideoRunStorage, run: VideoRunContext, actual_credits: float | None
) -> dict[str, Any]:
    value = {
        "historical_actual_runway_credits": 50,
        "historical_actual_provider_cost_usd": 0.50,
        "projected_new_runway_credits": 25,
        "projected_new_provider_cost_usd": 0.25,
        "actual_new_runway_credits": actual_credits,
        "actual_new_provider_cost_usd": (
            None if actual_credits is None else actual_credits * 0.01
        ),
        "actual_total_runway_credits": None if actual_credits is None else 50 + actual_credits,
        "actual_total_provider_cost_usd": (
            None if actual_credits is None else 0.50 + actual_credits * 0.01
        ),
        "currency": "USD",
        "cost_status": "UNKNOWN" if actual_credits is None else "ACTUAL_REPORTED",
        "automatic_paid_retries": 0,
        "automatic_replacement_tasks": 0,
    }
    storage.write_json_new(run, "cost.json", value)
    return value


def _block_prior_recovery_live(root: Path) -> None:
    for path in (root / "runs").glob("*/coffee-table-recovery-live-authorization.json"):
        try:
            value = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("manifest_sha256") == RECOVERY_V2_MANIFEST_SHA256:
            raise ExternalInputBlocked(
                f"Recovery Manifest V2 already has Live execution evidence: {path.parent.name}"
            )


def _validate_timeline(manifest: Mapping[str, Any]) -> None:
    timeline = ((manifest.get("assembly") or {}).get("timeline"))
    expected = (
        (0, 3, "TASK-01", 0, 3),
        (3, 5, "TASK-01", 3, 5),
        (5, 7, "TASK-02", 0, 2),
        (7, 10, "TASK-02", 2, 5),
        (10, 13, "LOCAL-TASK-03", 0, 3),
        (13, 17, "FUTURE-TASK-04", 0, 4),
        (17, 18, "FUTURE-TASK-04", 4, 5),
        (18, 20, "FUTURE-TASK-04-LAST_VALID_FRAME", 5, 5),
    )
    if not isinstance(timeline, list) or len(timeline) != 8:
        raise ExternalInputBlocked("BLOCKED_INTEGRITY: Recovery V2 timeline drift")
    for item, facts in zip(timeline, expected, strict=True):
        master_start, master_end, source_id, source_start, source_end = facts
        if (
            item.get("master_interval_seconds")
            != {"start": master_start, "end": master_end}
            or item.get("source_id") != source_id
            or item.get("source_interval_seconds")
            != {"start": source_start, "end": source_end}
            or item.get("duration_seconds") != master_end - master_start
        ):
            raise ExternalInputBlocked("BLOCKED_INTEGRITY: Recovery V2 timeline drift")


def _require_motion_video(
    path: Path,
    expected_sha: str,
    *,
    minimum_duration: float,
    exact_duration: float | None = None,
    exact_frame_count: int | None = None,
) -> None:
    _require_sha(path, expected_sha, path.name)
    info = inspect_video(path)
    if (
        info.width != 1280
        or info.height != 720
        or info.video_codec != "h264"
        or info.pixel_format != "yuv420p"
        or info.average_frame_rate != "24/1"
        or info.audio_stream_present
        or info.duration_seconds < minimum_duration
        or (exact_duration is not None and abs(info.duration_seconds - exact_duration) > 0.01)
    ):
        raise ExternalInputBlocked(f"BLOCKED_INTEGRITY: media facts drifted for {path.name}")
    if exact_frame_count is not None and _decoded_frame_count(path, runner=subprocess.run) != exact_frame_count:
        raise ExternalInputBlocked(f"BLOCKED_INTEGRITY: frame count drifted for {path.name}")


def _require_manifest_path_sha(
    root: Path,
    value: Mapping[str, Any],
    path_key: str,
    sha_key: str,
    expected_sha: str,
    label: str,
) -> None:
    if value.get(sha_key) != expected_sha:
        raise ExternalInputBlocked(f"BLOCKED_INTEGRITY: {label} manifest SHA drift")
    relative = value.get(path_key)
    if not isinstance(relative, str) or not relative:
        raise ExternalInputBlocked(f"BLOCKED_INTEGRITY: {label} path missing")
    _require_sha(root / relative, expected_sha, label)


def _require_sha(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or sha256_file(path) != expected:
        raise ExternalInputBlocked(f"BLOCKED_INTEGRITY: {label} SHA-256 drift")


def _artifact_evidence(artifact: MediaArtifact, root: Path) -> dict[str, Any]:
    value = asdict(artifact)
    value["path"] = str(artifact.path.relative_to(root))
    value.pop("source_url_redacted", None)
    return value


def _request_evidence(request: MotionVideoRequest, root: Path) -> dict[str, Any]:
    return {
        "task_id": "TASK-04",
        "provider": request.provider,
        "model": request.model,
        "image_path": str(request.image_path.relative_to(root)),
        "image_sha256": request.image_sha256,
        "prompt_path": str(request.prompt_path.relative_to(root)),
        "prompt_sha256": request.prompt_sha256,
        "ratio": request.ratio,
        "duration_seconds": request.duration_seconds,
        "max_retries": request.max_retries,
    }


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ExternalInputBlocked(f"expected JSON object: {path}")
    return value


def _write_json_exclusive(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
