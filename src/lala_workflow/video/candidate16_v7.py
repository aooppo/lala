from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..hashing import sha256_file
from .storage import QA_FIELDS


REGISTRATION_SCHEMA = "candidate16-v7-registration/v1"
EXPECTED_CHARACTER_ID = "character-20260821-001"
EXPECTED_KEYFRAME_ID = "K1-V2-002"
EXPECTED_IDS = (
    "v7-a-stability-first",
    "v7-b-natural-micro-motion",
    "v7-c-controlled-upper-bound",
)
WINNER_ID = "v7-b-natural-micro-motion"
REQUIRED_WINNER_FIELDS = (
    "visual_identity",
    "face_stability",
    "age_stability",
    "hair_stability",
    "body_proportions",
    "wardrobe",
    "jewelry",
    "mouth",
    "teeth",
    "eyes",
    "background",
    "motion",
    "technical_export",
)
_FALSE = {"false", "no", "0", "fail", "failed"}
_HASH = re.compile(r"^[0-9a-f]{64}$")
_OWNER_NOTE_FRAGMENTS = {
    "v7-a-stability-first": "excessive subject position/scale movement for the stability baseline",
    "v7-b-natural-micro-motion": "APPROVE v7-b-natural-micro-motion as Candidate 16 V7 winner",
    "v7-c-controlled-upper-bound": "acceptable stability fallback, but B provides a better balance of natural micro-motion and framing stability",
}


class Candidate16V7Error(ValueError):
    pass


def register_candidate16_v7_review(
    project_root: Path,
    *,
    package: Path,
    registered_at: datetime | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    package_path = _resolve_package(root, package)
    target = package_path / "registration.json"
    if target.exists():
        raise Candidate16V7Error("Candidate 16 V7 registration already exists")
    evidence = _validate_evidence(root, package_path)
    timestamp = (registered_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    payload = {
        "schema_version": REGISTRATION_SCHEMA,
        "status": "CANDIDATE16_V7_HUMAN_QA_PASS",
        "registered_at": timestamp.isoformat(),
        "authority": "HUMAN",
        "automatic_human_qa": False,
        "character_id": EXPECTED_CHARACTER_ID,
        "keyframe_id": EXPECTED_KEYFRAME_ID,
        "keyframe_sha256": evidence["keyframe_sha256"],
        "parent_run_id": evidence["parent_run_id"],
        "recovery_run_id": evidence["recovery_run_id"],
        "review_path": evidence["review_path"],
        "review_sha256": evidence["review_sha256"],
        "selected_candidate_id": WINNER_ID,
        "selected_media_path": evidence["selected_media_path"],
        "selected_media_sha256": evidence["selected_media_sha256"],
        "selected_provider_task_id": evidence["selected_provider_task_id"],
        "selected_prompt_path": evidence["selected_prompt_path"],
        "selected_prompt_sha256": evidence["selected_prompt_sha256"],
        "candidates": evidence["candidates"],
        "provider_submissions": 0,
        "provider_task_ids_created": 0,
        "http_requests": 0,
        "paid_calls": 0,
        "coffee_table_executed": False,
    }
    _write_json_exclusive(target, payload)
    return _public_result(root, target, payload)


def load_candidate16_v7_registration(
    project_root: Path, *, candidate16_k1_sha256: str
) -> dict[str, Any]:
    root = project_root.resolve()
    package = root / "outputs/reviews/candidate16-v7"
    target = package / "registration.json"
    registration = _read_json(target, "Candidate 16 V7 registration")
    if registration.get("schema_version") != REGISTRATION_SCHEMA:
        raise Candidate16V7Error("Candidate 16 V7 registration schema mismatch")
    evidence = _validate_evidence(root, package)
    required = {
        "status": "CANDIDATE16_V7_HUMAN_QA_PASS",
        "authority": "HUMAN",
        "automatic_human_qa": False,
        "character_id": EXPECTED_CHARACTER_ID,
        "keyframe_id": EXPECTED_KEYFRAME_ID,
        "keyframe_sha256": evidence["keyframe_sha256"],
        "parent_run_id": evidence["parent_run_id"],
        "recovery_run_id": evidence["recovery_run_id"],
        "review_path": evidence["review_path"],
        "review_sha256": evidence["review_sha256"],
        "selected_candidate_id": WINNER_ID,
        "selected_media_path": evidence["selected_media_path"],
        "selected_media_sha256": evidence["selected_media_sha256"],
        "selected_provider_task_id": evidence["selected_provider_task_id"],
        "selected_prompt_path": evidence["selected_prompt_path"],
        "selected_prompt_sha256": evidence["selected_prompt_sha256"],
        "candidates": evidence["candidates"],
        "provider_submissions": 0,
        "provider_task_ids_created": 0,
        "http_requests": 0,
        "paid_calls": 0,
        "coffee_table_executed": False,
    }
    mismatches = [key for key, value in required.items() if registration.get(key) != value]
    if mismatches:
        raise Candidate16V7Error(
            "Candidate 16 V7 registration evidence mismatch: " + ", ".join(mismatches)
        )
    if candidate16_k1_sha256 != evidence["keyframe_sha256"]:
        raise Candidate16V7Error("Candidate 16 V7 registration K1 SHA-256 mismatch")
    _timezone_aware(str(registration.get("registered_at") or ""), "registered_at")
    return {
        **registration,
        "registration_path": target.relative_to(root).as_posix(),
        "registration_sha256": sha256_file(target),
    }


def _validate_evidence(root: Path, package: Path) -> dict[str, Any]:
    manifest_path = package / "manifest.json"
    review_path = package / "review.csv"
    manifest = _read_json(manifest_path, "Candidate 16 V7 manifest")
    if (
        manifest.get("character_id") != EXPECTED_CHARACTER_ID
        or manifest.get("keyframe_id") != EXPECTED_KEYFRAME_ID
        or manifest.get("state") != "READY_FOR_OWNER_CANDIDATE16_V7_REVIEW"
        or manifest.get("winner") is not None
        or manifest.get("human_review_required") is not True
        or manifest.get("coffee_table_executed") is not False
    ):
        raise Candidate16V7Error("Candidate 16 V7 manifest identity/state mismatch")
    keyframe_sha = str(manifest.get("keyframe_sha256") or "").lower()
    if not _HASH.fullmatch(keyframe_sha):
        raise Candidate16V7Error("Candidate 16 V7 keyframe SHA-256 is invalid")
    keyframe = root / "assets/approved_keyframes/K1-V2-002.png"
    if not keyframe.is_file() or sha256_file(keyframe) != keyframe_sha:
        raise Candidate16V7Error("Candidate 16 V7 keyframe SHA-256 mismatch")

    parent_id = str(manifest.get("parent_run_id") or "")
    recovery_id = str(manifest.get("recovery_run_id") or "")
    parent = _safe_run(root, parent_id)
    recovery = _safe_run(root, recovery_id)
    parent_request = _read_json(parent / "request.json", "V7 parent request")
    parent_results = _read_json(parent / "provider-results.json", "V7 parent results")
    recovery_request = _read_json(recovery / "request.json", "V7 recovery request")
    recovery_results = _read_json(recovery / "provider-results.json", "V7 recovery results")
    if (
        parent_request.get("action") != "motion_v7_live"
        or parent_request.get("run_id") != parent_id
        or parent_results.get("status") != "PARTIAL"
    ):
        raise Candidate16V7Error("Candidate 16 V7 parent evidence mismatch")
    if (
        recovery_request.get("action") != "motion_v7_recovery"
        or recovery_request.get("run_id") != recovery_id
        or recovery_request.get("parent_run_id") != parent_id
        or recovery_results.get("status") != "SUCCEEDED"
        or recovery_results.get("parent_run_id") != parent_id
    ):
        raise Candidate16V7Error("Candidate 16 V7 recovery relationship mismatch")

    parent_requests = parent_request.get("requests")
    recovery_requests = recovery_request.get("requests")
    results = recovery_results.get("results")
    if (
        not isinstance(parent_requests, list)
        or [item.get("shot_id") for item in parent_requests] != list(EXPECTED_IDS)
        or not isinstance(recovery_requests, list)
        or [item.get("shot_id") for item in recovery_requests] != list(EXPECTED_IDS[1:])
        or not isinstance(results, list)
        or [item.get("candidate_id") for item in results] != list(EXPECTED_IDS)
    ):
        raise Candidate16V7Error("Candidate 16 V7 canonical A/B/C provenance mismatch")
    if any(item.get("image_sha256") != keyframe_sha for item in parent_requests + recovery_requests):
        raise Candidate16V7Error("Candidate 16 V7 request keyframe SHA-256 mismatch")
    for run in (parent, recovery):
        keyframe_evidence = _read_json(run / "keyframe-hash.json", "V7 keyframe evidence")
        if keyframe_evidence.get("keyframe_id") != EXPECTED_KEYFRAME_ID or keyframe_evidence.get("sha256") != keyframe_sha:
            raise Candidate16V7Error("Candidate 16 V7 run keyframe provenance mismatch")
        _validate_blank_review(run / "review.csv")

    review_rows = _read_review(review_path)
    _validate_review_rows(review_rows, recovery_id)
    manifest_media = manifest.get("media")
    if not isinstance(manifest_media, list) or [item.get("candidate_id") for item in manifest_media] != list(EXPECTED_IDS):
        raise Candidate16V7Error("Candidate 16 V7 manifest media order mismatch")

    candidates = []
    selected: dict[str, Any] | None = None
    request_by_id = {item["shot_id"]: item for item in parent_requests}
    for index, (candidate_id, result, media) in enumerate(
        zip(EXPECTED_IDS, results, manifest_media, strict=True)
    ):
        expected_source = parent_id if index == 0 else recovery_id
        artifacts = result.get("artifacts")
        task_id = str(result.get("provider_task_id") or "")
        if (
            result.get("provider_status") != "SUCCEEDED"
            or result.get("evidence_source_run_id") != expected_source
            or not task_id
            or not isinstance(artifacts, list)
            or len(artifacts) != 1
            or artifacts[0].get("provider_task_id") != task_id
        ):
            raise Candidate16V7Error(f"Candidate 16 V7 {candidate_id} task provenance mismatch")
        artifact = artifacts[0]
        source = _safe_relative_file(root, str(artifact.get("path") or ""), "V7 media")
        digest = str(artifact.get("sha256") or "").lower()
        packaged = _safe_relative_file(root, str(media.get("path") or ""), "V7 package media")
        if (
            media.get("candidate_id") != candidate_id
            or not _HASH.fullmatch(digest)
            or sha256_file(source) != digest
            or media.get("sha256") != digest
            or sha256_file(packaged) != digest
        ):
            raise Candidate16V7Error(f"Candidate 16 V7 {candidate_id} media SHA-256 mismatch")
        prompt_path = str(result.get("prompt_path") or "")
        prompt_sha = str(result.get("prompt_sha256") or "").lower()
        request_item = request_by_id[candidate_id]
        prompt = _safe_relative_file(root, prompt_path, "V7 prompt")
        request_prompt = _safe_evidence_file(
            root, str(request_item.get("prompt_path") or ""), "V7 request prompt"
        )
        if (
            not _HASH.fullmatch(prompt_sha)
            or sha256_file(prompt) != prompt_sha
            or request_prompt != prompt
            or request_item.get("prompt_sha256") != prompt_sha
        ):
            raise Candidate16V7Error(f"Candidate 16 V7 {candidate_id} prompt SHA-256 mismatch")
        item = {
            "candidate_id": candidate_id,
            "source_run_id": expected_source,
            "provider_task_id": task_id,
            "media_path": packaged.relative_to(root).as_posix(),
            "media_sha256": digest,
            "prompt_path": prompt.relative_to(root).as_posix(),
            "prompt_sha256": prompt_sha,
            "human_decision": "PASS" if candidate_id == WINNER_ID else "NOT_SELECTED",
            "mtl_review_ready": candidate_id == WINNER_ID,
        }
        candidates.append(item)
        if candidate_id == WINNER_ID:
            selected = item
    if selected is None:
        raise Candidate16V7Error("Candidate 16 V7 selected evidence is missing")
    return {
        "keyframe_sha256": keyframe_sha,
        "parent_run_id": parent_id,
        "recovery_run_id": recovery_id,
        "review_path": review_path.relative_to(root).as_posix(),
        "review_sha256": sha256_file(review_path),
        "selected_media_path": selected["media_path"],
        "selected_media_sha256": selected["media_sha256"],
        "selected_provider_task_id": selected["provider_task_id"],
        "selected_prompt_path": selected["prompt_path"],
        "selected_prompt_sha256": selected["prompt_sha256"],
        "candidates": candidates,
    }


def _validate_review_rows(rows: list[dict[str, str]], recovery_id: str) -> None:
    if len(rows) != 3 or [row.get("video_id") for row in rows] != list(EXPECTED_IDS):
        raise Candidate16V7Error("Candidate 16 V7 review provenance is not canonical A/B/C")
    passing = [
        str(row.get("video_id") or "")
        for row in rows
        if all(_truthy(row.get(field)) for field in REQUIRED_WINNER_FIELDS)
        and _truthy(row.get("mtl_review_ready"))
    ]
    if passing != [WINNER_ID]:
        raise Candidate16V7Error("Candidate 16 V7 review must contain exactly one V7-B winner")
    for candidate_id, row in zip(EXPECTED_IDS, rows, strict=True):
        expected = {
            "run_id": recovery_id,
            "video_id": candidate_id,
            "preset": "motion-v7",
            "candidate": f"{candidate_id}.mp4",
        }
        if any(row.get(key) != value for key, value in expected.items()):
            raise Candidate16V7Error("Candidate 16 V7 review provenance mismatch")
        _timezone_aware(str(row.get("reviewed_at") or ""), f"{candidate_id} reviewed_at")
        if not str(row.get("reviewer") or "").strip():
            raise Candidate16V7Error("Candidate 16 V7 review requires human attribution")
        if candidate_id == WINNER_ID:
            missing = [field for field in REQUIRED_WINNER_FIELDS if not _truthy(row.get(field))]
            if missing or not _truthy(row.get("mtl_review_ready")):
                raise Candidate16V7Error("Candidate 16 V7-B review has incomplete PASS decisions")
        elif str(row.get("mtl_review_ready") or "").strip().lower() not in _FALSE:
            raise Candidate16V7Error("Candidate 16 V7 non-selected readiness must be false")
        notes = str(row.get("notes") or "").strip()
        if _OWNER_NOTE_FRAGMENTS[candidate_id] not in notes:
            raise Candidate16V7Error(
                f"Candidate 16 V7 {candidate_id} Owner decision notes mismatch"
            )


def _validate_blank_review(path: Path) -> None:
    rows = _read_review(path)
    if [row.get("video_id") for row in rows] != list(EXPECTED_IDS):
        raise Candidate16V7Error("Candidate 16 V7 append-only review provenance mismatch")
    if any(str(row.get(field) or "").strip() for row in rows for field in QA_FIELDS[4:]):
        raise Candidate16V7Error("Candidate 16 V7 append-only run review is not blank")


def _read_review(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(QA_FIELDS):
                raise Candidate16V7Error("Candidate 16 V7 review schema mismatch")
            return [dict(row) for row in reader]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise Candidate16V7Error("Candidate 16 V7 review is unreadable") from exc


def _resolve_package(root: Path, package: Path) -> Path:
    candidate = package if package.is_absolute() else root / package
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise Candidate16V7Error("Candidate 16 V7 review package does not exist") from exc
    reviews = (root / "outputs/reviews").resolve()
    if candidate.is_symlink() or reviews not in resolved.parents or not resolved.is_dir():
        raise Candidate16V7Error("Candidate 16 V7 package must be a directory under outputs/reviews")
    return resolved


def _safe_run(root: Path, run_id: str) -> Path:
    if not run_id or "/" in run_id or "\\" in run_id:
        raise Candidate16V7Error("Candidate 16 V7 run ID is invalid")
    run = (root / "runs" / run_id).resolve()
    if run.parent != (root / "runs").resolve() or not run.is_dir():
        raise Candidate16V7Error("Candidate 16 V7 run evidence is missing")
    return run


def _safe_relative_file(root: Path, value: str, label: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise Candidate16V7Error(f"{label} path is unsafe")
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file() or path.is_symlink():
        raise Candidate16V7Error(f"{label} file is missing")
    return path


def _safe_evidence_file(root: Path, value: str, label: str) -> Path:
    candidate = Path(value)
    path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if root not in path.parents or not path.is_file() or path.is_symlink():
        raise Candidate16V7Error(f"{label} file is missing or outside the project")
    return path


def _timezone_aware(value: str, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise Candidate16V7Error(f"{label} must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Candidate16V7Error(f"{label} must include a timezone")


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "yes", "1", "approved", "pass"}


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Candidate16V7Error(f"{label} is invalid") from exc
    if not isinstance(value, dict):
        raise Candidate16V7Error(f"{label} must be an object")
    return value


def _write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise Candidate16V7Error("Candidate 16 V7 registration already exists") from exc


def _public_result(root: Path, path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "winner": payload["selected_candidate_id"],
        "keyframe_sha256": payload["keyframe_sha256"],
        "selected_media_path": payload["selected_media_path"],
        "selected_media_sha256": payload["selected_media_sha256"],
        "selected_provider_task_id": payload["selected_provider_task_id"],
        "registration_path": path.relative_to(root).as_posix(),
        "registration_sha256": sha256_file(path),
        "provider_submissions": 0,
        "paid_calls": 0,
    }
