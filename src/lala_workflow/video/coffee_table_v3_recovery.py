from __future__ import annotations

import csv
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image

from ..hashing import sha256_file
from .downloads import inspect_video
from .validation import ExternalInputBlocked


FINAL_RUN_ID = "LALA-VIDEO-20260821-131803-COFFEE-TABLE-RECOVERY-LIVE-001"
FAILED_RUN_ID = "LALA-VIDEO-20260821-082100-COFFEE-TABLE-LIVE-001"
FINAL_REVIEW_PACKAGE = Path("outputs/reviews/coffee-table-final") / FINAL_RUN_ID
FINAL_REVIEW_MANIFEST_SHA256 = "7701f0f78d28972ba6260562878f6ddf365ce42a7abd24768aba8cf07d6b13b1"
FINAL_REVIEW_EVIDENCE_SHA256 = "5153779a090c90e4e5aadc47e10633c17845aa84853256379a6e13f6bdbaf165"
FINAL_MASTER = Path("outputs/final") / FINAL_RUN_ID / "coffee-table-master-16x9.mp4"
FINAL_MASTER_SHA256 = "412311e5d96d6a9fd97a9a2c57b0b07e784fb13c2a9ea85a6f22a8ba24a027e8"
RECOVERY_V2_MANIFEST = Path("outputs/campaign-recovery-manifests/COFFEE-TABLE-RECOVERY-20260821-204901-001/coffee-table-recovery-manifest-v2.json")
RECOVERY_V2_MANIFEST_SHA256 = "e97ea0d34f4ea541ab07e6898083e7a35c3b82502030f8f40a06d58fb43e6cc3"
PARENT_MANIFEST = Path("outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json")
PARENT_MANIFEST_SHA256 = "ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea"
PROVIDER_RESULTS = Path("runs") / FAILED_RUN_ID / "provider-results.json"
PROVIDER_RESULTS_SHA256 = "111a05f526944b26381fdf023cbcba4d8aaa58124490e3f7e9ceeedc3301c609"
TASK_01 = Path("outputs/broll") / FAILED_RUN_ID / "TASK-01.mp4"
TASK_01_SHA256 = "2c61cb10a6563d9d4c1e43811be17ef06c3244fc6eb2356d349f064cff6ffd4b"
TASK_02 = Path("outputs/broll") / FAILED_RUN_ID / "TASK-02.mp4"
TASK_02_SHA256 = "9565691a30e312518cc867792063194ae2a667b70d586fbee06d821cc9b7413f"
LOCAL_TASK_03 = Path("outputs/broll/COFFEE-TABLE-RECOVERY-20260821-164849-001/LOCAL-TASK-03.mp4")
LOCAL_TASK_03_SHA256 = "edda268e70ce2af85ab4e11b93e684bbfd363b098f692bb45ae369f0c5928cef"
TASK_04 = Path("outputs/broll") / FINAL_RUN_ID / "TASK-04.mp4"
TASK_04_SHA256 = "a310a5ebcd66dad419febe9df18895aa30470b2dd4b3bf2a09d9a4287fa0b43d"
V4_PROMPT = Path("prompts/coffee-table-task-04-sofa-hero-v4.txt")
APPROVED_DIRS = tuple(Path(path) for path in (
    "assets/approved_anchors", "assets/approved_keyframes", "assets/voice/source",
    "assets/voice/approved", "assets/scripts",
))
APPROVED_AGGREGATE_SHA256 = "9c228cd1a31952d0709738f3891a3d3e335afac1e20cb9c0bccea40dd893acf2"
FRAME_INDICES = (92, 96, 100, 104, 108, 112, 116)
READY_FOR_OWNER_COFFEE_TABLE_V3_RECOVERY_REVIEW = "READY_FOR_OWNER_COFFEE_TABLE_V3_RECOVERY_REVIEW"
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class CoffeeTableV3RecoveryOutcome:
    recovery_id: str
    status: str
    owner_decision_path: Path
    owner_decision_sha256: str
    source_frame_review_path: Path
    source_frame_review_sha256: str
    manifest_path: Path
    manifest_sha256: str
    provider_calls: int
    paid_calls: int


def prepare_coffee_table_v3_recovery(
    project_root: Path, *, now: datetime | None = None, runner: CommandRunner = subprocess.run,
) -> CoffeeTableV3RecoveryOutcome:
    root = project_root.resolve()
    protected = _validate_inputs(root)
    recovery_id, manifest_dir, decision_dir, frame_dir = _allocate(root, now)
    try:
        owner_decision = _owner_decision(root, decision_dir)
        frame_review = _extract_frame_review(root, frame_dir, runner)
        prompt = _prompt_evidence(root)
        manifest = _manifest(recovery_id, protected, owner_decision, frame_review, prompt)
        manifest_path = manifest_dir / "coffee-table-v3-recovery-manifest.json"
        _write_json_new(manifest_path, manifest)
        _validate_inputs(root)
        _require_sha(manifest_path, sha256_file(manifest_path), "V3 manifest")
    except Exception:
        for path in (manifest_dir, decision_dir, frame_dir):
            _remove_new_tree(path)
        raise
    return CoffeeTableV3RecoveryOutcome(
        recovery_id=recovery_id,
        status=READY_FOR_OWNER_COFFEE_TABLE_V3_RECOVERY_REVIEW,
        owner_decision_path=decision_dir / "owner-decision.json",
        owner_decision_sha256=sha256_file(decision_dir / "owner-decision.json"),
        source_frame_review_path=frame_dir / "manifest.json",
        source_frame_review_sha256=sha256_file(frame_dir / "manifest.json"),
        manifest_path=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
        provider_calls=0,
        paid_calls=0,
    )


def _validate_inputs(root: Path) -> dict[str, Any]:
    for path, digest, label in (
        (FINAL_REVIEW_PACKAGE / "manifest.json", FINAL_REVIEW_MANIFEST_SHA256, "final review manifest"),
        (FINAL_REVIEW_PACKAGE / "evidence.json", FINAL_REVIEW_EVIDENCE_SHA256, "final review evidence"),
        (FINAL_MASTER, FINAL_MASTER_SHA256, "20-second master"),
        (RECOVERY_V2_MANIFEST, RECOVERY_V2_MANIFEST_SHA256, "Recovery V2 manifest"),
        (PARENT_MANIFEST, PARENT_MANIFEST_SHA256, "parent manifest"),
        (PROVIDER_RESULTS, PROVIDER_RESULTS_SHA256, "provider results"),
        (TASK_01, TASK_01_SHA256, "TASK-01"), (TASK_02, TASK_02_SHA256, "TASK-02"),
        (LOCAL_TASK_03, LOCAL_TASK_03_SHA256, "LOCAL-TASK-03"), (TASK_04, TASK_04_SHA256, "TASK-04"),
    ):
        _require_sha(root / path, digest, label)
    results = _read_json(root / PROVIDER_RESULTS)
    expected = (
        ("TASK-01", "43da0f57-b584-4738-bbf1-05c33f653a3f", "SUCCEEDED", 25.0),
        ("TASK-02", "a7bb1630-21ff-4a2e-8d40-c3c9085d45ac", "SUCCEEDED", 25.0),
        ("TASK-03", "03b195ab-98b0-4631-a845-03843656cbc5", "FAILED", 0.0),
    )
    if results.get("status") != "STOPPED" or results.get("stop_reason") != "STOPPED_TASK_FAILED":
        raise ExternalInputBlocked("Coffee Table historical stop evidence drifted")
    for row, facts in zip(results.get("results", ()), expected, strict=True):
        if (row.get("task_id"), row.get("provider_task_id"), row.get("status"), float(row.get("actual_credits", -1))) != facts:
            raise ExternalInputBlocked("Coffee Table historical provider task facts drifted")
    for path, expected_sha in ((TASK_01, TASK_01_SHA256), (TASK_02, TASK_02_SHA256), (LOCAL_TASK_03, LOCAL_TASK_03_SHA256), (TASK_04, TASK_04_SHA256), (FINAL_MASTER, FINAL_MASTER_SHA256)):
        if not (root / path).is_file() or inspect_video(root / path).audio_stream_present:
            raise ExternalInputBlocked(f"Coffee Table media contract drifted: {path.name}")
    aggregate, count = approved_source_aggregate_sha256(root)
    if (aggregate, count) != (APPROVED_AGGREGATE_SHA256, 35):
        raise ExternalInputBlocked("Coffee Table protected source aggregate drifted")
    return {"approved_source_aggregate_sha256": aggregate, "approved_source_file_count": count}


def approved_source_aggregate_sha256(root: Path) -> tuple[str, int]:
    paths = sorted(
        path for directory in APPROVED_DIRS for path in (root / directory).rglob("*")
        if path.is_file()
    )
    lines = "".join(
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n" for path in paths
    )
    return sha256(lines.encode("utf-8")).hexdigest(), len(paths)


def _owner_decision(root: Path, directory: Path) -> dict[str, Any]:
    original_csv = FINAL_REVIEW_PACKAGE / "review.csv"
    original_sha = sha256_file(root / original_csv)
    reviewed_csv = directory / "review.csv"
    rows = [
        ("wine glass state", "PASS", "Wine glass is correct according to Henry's source requirement."),
        ("wine glass placement", "PASS", "Wine glass placement is not the rejection root cause."),
        ("Coffee Table geometry", "PASS", "Coffee Table remains the product concept; it must remain a table."),
        ("TASK-04 sit motion", "REJECT", "SOFA_SEATING_CONTRACT_VIOLATION: the final motion sits/perches on the Coffee Table."),
        ("sofa interaction", "FAIL", "Henry requires sitting on the sofa; hips/body weight are not supported by the sofa."),
        ("hero ending", "FAIL", "The final relaxation scene violates the table/sofa spatial contract."),
        ("scene continuity", "FAIL", "Reference/storyboard fidelity fails at final seating."),
        ("20-sec pacing", "", "Not the root cause of this Owner rejection."),
        ("16:9 composition", "REJECT", "Master rejected for reference semantics, not ratio."),
    ]
    with reviewed_csv.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=("check_item", "decision", "notes", "reviewer", "reviewed_at"))
        writer.writeheader()
        for check_item, decision, notes in rows:
            writer.writerow({"check_item": check_item, "decision": decision, "notes": notes, "reviewer": "Project owner (explicit decision)", "reviewed_at": "2026-08-21"})
    decision = {
        "schema_version": "coffee-table-owner-decision/v3", "status": "OWNER_REJECTED_REFERENCE_SEMANTICS",
        "decision": "REJECT", "reason": "SOFA_SEATING_CONTRACT_VIOLATION", "reviewed_after_generation": True,
        "source_review_package": {"path": FINAL_REVIEW_PACKAGE.as_posix(), "manifest_sha256": FINAL_REVIEW_MANIFEST_SHA256, "original_blank_review_csv": original_csv.as_posix(), "original_blank_review_sha256": original_sha},
        "findings": {"wine_glass": "Wine glass is correct according to Henry's source requirement.", "pass_not_root_cause": ["wine glass", "fireplace concept", "Coffee Table product concept", "walking-from-fireplace concept", "placing wine glass onto Coffee Table"], "hard_fail": ["spatial relationship", "product interaction", "reference/storyboard fidelity", "final relaxation scene", "20-second master approval"]},
        "review_csv": {"path": reviewed_csv.name, "sha256": sha256_file(reviewed_csv)},
        "historical_media_modified": False, "provider_calls": 0, "paid_calls": 0,
    }
    decision_path = directory / "owner-decision.json"
    _write_json_new(decision_path, decision)
    return {"path": _relative(decision_path, root), "sha256": sha256_file(decision_path), "review_csv_path": _relative(reviewed_csv, root), "review_csv_sha256": sha256_file(reviewed_csv)}


def _extract_frame_review(root: Path, directory: Path, runner: CommandRunner) -> dict[str, Any]:
    source = root / TASK_02
    count = _frame_count(source, runner)
    candidates = []
    assessments = {
        92: ("standing beside table", "on tabletop", "clear", "clear", "MEDIUM", "REVIEWABLE"),
        96: ("standing, moving right", "on tabletop", "clear", "clear", "LOW", "RECOMMENDED"),
        100: ("standing, moving toward sofa", "on tabletop", "clear", "clear", "LOW", "RECOMMENDED"),
        104: ("standing beyond table toward sofa", "on tabletop", "clear", "clear", "LOW", "RECOMMENDED"),
        108: ("standing near sofa path", "on tabletop", "clear", "clear", "LOW", "RECOMMENDED"),
        112: ("standing at right frame edge", "on tabletop", "clear", "clear", "MEDIUM", "NOT_RECOMMENDED_CONTINUITY_RISK"),
        116: ("mostly leaving right frame edge", "on tabletop", "clear", "clear", "HIGH", "NOT_RECOMMENDED_CONTINUITY_RISK"),
    }
    for index in FRAME_INDICES:
        if count <= index:
            raise ExternalInputBlocked("TASK-02 lacks a required V3 source-frame candidate")
        png = directory / f"TASK-02-frame-{index:06d}.png"
        argv = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(source), "-vf", f"select=eq(n\\,{index})", "-frames:v", "1", "-c:v", "png", "-n", str(png)]
        runner(argv, check=True, capture_output=True, text=True, timeout=120)
        with Image.open(png) as image:
            image.verify()
        position, glass, table, sofa, risk, recommendation = assessments[index]
        candidates.append({"zero_based_frame_index": index, "timestamp_seconds": index / 24, "png_path": _relative(png, root), "png_sha256": sha256_file(png), "character_position": position, "wine_glass_state": glass, "coffee_table_visibility": table, "sofa_visibility": sofa, "sofa_reachability": "reachable_without_using_table_as_seating", "table_sofa_semantic_ambiguity_risk": risk, "recommendation": recommendation, "ffmpeg_argv": argv})
    review_csv = directory / "review.csv"
    with review_csv.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=("frame_index", "decision", "notes", "reviewer", "reviewed_at"))
        writer.writeheader()
        for item in candidates:
            writer.writerow({"frame_index": item["zero_based_frame_index"], "decision": "", "notes": "", "reviewer": "", "reviewed_at": ""})
    manifest = {"schema_version": "coffee-table-v3-source-frame-review/v1", "status": "READY_FOR_OWNER_COFFEE_TABLE_V3_SOURCE_FRAME_REVIEW", "source_task": {"task_id": "TASK-02", "provider_task_id": "a7bb1630-21ff-4a2e-8d40-c3c9085d45ac", "path": TASK_02.as_posix(), "sha256": TASK_02_SHA256, "decoded_frame_count": count, "frame_rate": "24/1"}, "semantic_contract": "V3_SOFA_SEATING", "candidates": candidates, "owner_selection": {"selected_frame": None, "selected_frame_sha256": None, "status": "EMPTY_UNAUTHORIZED"}, "review_csv": {"path": review_csv.name, "sha256": sha256_file(review_csv), "human_fields": "BLANK"}, "provider_calls": 0, "paid_calls": 0}
    manifest_path = directory / "manifest.json"
    _write_json_new(manifest_path, manifest)
    return {"path": _relative(manifest_path, root), "sha256": sha256_file(manifest_path), "review_csv_path": _relative(review_csv, root), "review_csv_sha256": sha256_file(review_csv), "candidates": candidates}


def _prompt_evidence(root: Path) -> dict[str, Any]:
    path = root / V4_PROMPT
    if not path.is_file():
        raise ExternalInputBlocked("Coffee Table V3 prompt is missing")
    return {"path": V4_PROMPT.as_posix(), "sha256": sha256_file(path), "version": 4, "text": path.read_text(encoding="utf-8")}


def _manifest(recovery_id: str, protected: Mapping[str, Any], owner: Mapping[str, Any], frames: Mapping[str, Any], prompt: Mapping[str, Any]) -> dict[str, Any]:
    return {"schema_version": "candidate16-coffee-table-v3-recovery-manifest/v1", "recovery_id": recovery_id, "status": READY_FOR_OWNER_COFFEE_TABLE_V3_RECOVERY_REVIEW, "source_requirement_reference": "Henry: walk from fireplace holding wine glass, place it on Coffee Table, then sit on sofa.", "owner_rejection": dict(owner), "semantic_contract": {"product": {"Coffee Table": "foreground hero product and table; never seating"}, "relationships": ["PERSON -> seated on SOFA", "COFFEE TABLE -> foreground/in front", "FIREPLACE -> background", "WINE GLASS -> resting on COFFEE TABLE"], "hard_negatives": ["never sit/perch/stand on Coffee Table", "never use Coffee Table as bench/chair/stool", "never place hips or body weight on tabletop", "never confuse sofa with Coffee Table"], "acceptance_gates": ["wine glass correct", "Coffee Table remains table", "Lady LaLa sits on sofa", "body weight supported by sofa", "body/table separation", "Coffee Table hero product", "wine glass continuity", "foreground/midground/background final composition"]}, "reuse_analysis": {"TASK-01": {"decision": "REUSE_ELIGIBLE", "reason": "Establishes fireplace, wine glass, Coffee Table, and sofa without seating violation."}, "TASK-02": {"decision": "REUSE_ELIGIBLE", "reason": "Post-placement candidates show wine glass on table, a standing/moving person, and visible sofa/table separation."}, "LOCAL-TASK-03": {"decision": "REUSE_ELIGIBLE", "reason": "Exact-byte local product detail; no person/seating semantic claim."}, "TASK-04": {"decision": "REGEN_REQUIRED", "reason": "Existing output caused SOFA_SEATING_CONTRACT_VIOLATION and cannot be promoted or reused as final seating."}}, "source_frame_review": dict(frames), "task_04_v3_proposal": {"task_scope": "TASK-04 ONLY", "selected_frame": None, "selection_status": "EMPTY_UNAUTHORIZED", "prompt": dict(prompt), "request": {"provider": "runway", "model": "gen4_turbo", "duration_seconds": 5, "ratio": "1280:720", "expected_credits": 25, "expected_cost_usd": 0.25}, "authorization": {"provider_live_calls": False, "paid_generation": False, "maximum_authorized_credits": 0, "maximum_authorized_cost_usd": 0, "owner_frame_selection_required": True, "owner_live_authorization_required": True, "automatic_retry": False, "replacement_scope": "TASK-04 ONLY"}}, "historical": {"provider_task_ids": {"TASK-01": "43da0f57-b584-4738-bbf1-05c33f653a3f", "TASK-02": "a7bb1630-21ff-4a2e-8d40-c3c9085d45ac", "TASK-03": "03b195ab-98b0-4631-a845-03843656cbc5", "TASK-04": "c480792c-a6ad-4d18-a68b-e47f1b3a1677"}, "artifact_sha256": {"TASK-01": TASK_01_SHA256, "TASK-02": TASK_02_SHA256, "LOCAL-TASK-03": LOCAL_TASK_03_SHA256, "TASK-04": TASK_04_SHA256, "master": FINAL_MASTER_SHA256}, "accounting": {"historical_spent_credits": 75, "historical_spent_usd": 0.75, "this_run_credits": 0, "this_run_usd": 0, "proposed_task_04_only_credits": 25, "proposed_task_04_only_usd": 0.25}}, "protected_sources": dict(protected), "alternate_ratios": {"1:1": "BLOCKED_SAFE_AREA", "9:16": "BLOCKED_SAFE_AREA", "native_provider_regeneration": "NOT_AUTHORIZED"}, "provider_calls": 0, "paid_calls": 0}


def _frame_count(path: Path, runner: CommandRunner) -> int:
    completed = runner(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "default=nokey=1:noprint_wrappers=1", str(path)], check=True, capture_output=True, text=True, timeout=60)
    return int(completed.stdout.strip())


def _allocate(root: Path, now: datetime | None) -> tuple[str, Path, Path, Path]:
    stamp = (now or datetime.now().astimezone()).strftime("%Y%m%d-%H%M%S")
    for sequence in range(1, 1000):
        recovery_id = f"COFFEE-TABLE-V3-RECOVERY-{stamp}-{sequence:03d}"
        paths = (root / "outputs/campaign-v3-recovery-manifests" / recovery_id, root / "outputs/reviews/coffee-table-v3-owner-rejection" / recovery_id, root / "outputs/reviews/coffee-table-v3-source-frame-review" / recovery_id)
        if any(path.exists() for path in paths):
            continue
        for path in paths:
            path.mkdir(parents=True, exist_ok=False)
        return recovery_id, *paths
    raise RuntimeError("could not allocate Coffee Table V3 recovery paths")


def _require_sha(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or sha256_file(path) != expected:
        raise ExternalInputBlocked(f"Coffee Table V3 {label} SHA-256 drift")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ExternalInputBlocked(f"Coffee Table V3 expected JSON object: {path}")
    return value


def _write_json_new(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path)
        temporary.unlink()
    finally:
        temporary.unlink(missing_ok=True)


def _remove_new_tree(path: Path) -> None:
    if path.exists():
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()
