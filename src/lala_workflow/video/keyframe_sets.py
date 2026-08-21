from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..hashing import inspect_image, sha256_file


PACKAGE_SCHEMA = "candidate16-keyframe-review-package/v2"
REVIEW_SCHEMA = "candidate16-keyframe-review/v2"
PROMOTION_SCHEMA = "candidate16-reviewed-keyframe-promotion/v1"
PROMOTION_TYPE = "candidate16_review_package_promotion"
SET_SCHEMA = "candidate16-keyframe-set/v1"
PUBLISH_EVENT_SCHEMA = "candidate16-keyframe-set-publish-event/v1"
REGISTRY_SCHEMA = "candidate16-keyframe-set-registry/v1"
GOAL2_BINDING_SCHEMA = "candidate16-goal2-binding/v1"
EXPECTED_CHARACTER_ID = "character-20260821-001"
EXPECTED_CHARACTER_NAME = "Candidate 16"
SET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$")

IDENTITY_FIELDS = (
    "schema_version",
    "candidate_id",
    "role",
    "candidate_file",
    "candidate_sha256",
)
QA_FIELDS = (
    "face_identity_pass",
    "age_pass",
    "hair_pass",
    "eyes_pass",
    "mouth_pass",
    "body_proportions_pass",
    "wardrobe_pass",
    "jewelry_pass",
    "hands_pass",
    "scene_pass",
    "product_geometry_pass",
    "product_finish_pass",
    "wine_glass_pass",
    "no_extra_people_pass",
    "no_text_logo_pass",
    "video_keyframe_ready",
)
ATTRIBUTION_FIELDS = ("reviewer", "reviewed_at", "notes")
REVIEW_FIELDS = IDENTITY_FIELDS + QA_FIELDS + ATTRIBUTION_FIELDS
_IDENTITY_QA = (
    "face_identity_pass",
    "age_pass",
    "hair_pass",
    "eyes_pass",
    "mouth_pass",
    "body_proportions_pass",
    "wardrobe_pass",
    "jewelry_pass",
    "no_extra_people_pass",
    "no_text_logo_pass",
    "video_keyframe_ready",
)
_FULL_QA = QA_FIELDS
ROLE_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "pilot_home_context": _FULL_QA,
    "pilot_talking_medium_closeup": _IDENTITY_QA,
    "pilot_product_present": _FULL_QA,
}
ROLE_SLOTS = {
    "pilot_home_context": "K1",
    "pilot_talking_medium_closeup": "K2",
    "pilot_product_present": "K3",
}
APPROVED_ROLES = {
    "pilot_home_context": ["pilot_home_context", "establishing_keyframe"],
    "pilot_talking_medium_closeup": ["talking_medium_closeup"],
    "pilot_product_present": ["pilot_product_present"],
}


class KeyframeSetError(ValueError):
    pass


def validate_review_package(project_root: Path, package: Path) -> dict[str, Any]:
    root = project_root.resolve()
    package_path = _resolve_package(root, package)
    manifest_path = package_path / "manifest.json"
    review_path = package_path / "review.csv"
    manifest = _read_json(manifest_path, "review package manifest")
    if manifest.get("schema_version") != PACKAGE_SCHEMA:
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: unsupported review package schema")
    if manifest.get("status") != "READY_FOR_OWNER_KEYFRAME_REVIEW":
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: review package status mismatch")
    character = manifest.get("character")
    if not isinstance(character, Mapping):
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: character evidence is missing")
    _validate_active_character(root, character)
    candidates = _manifest_candidates(manifest)
    rows = _read_review(review_path)
    if len(rows) != len(candidates) or {row["candidate_id"] for row in rows} != set(candidates):
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: review rows do not match manifest candidates")

    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        candidate = candidates[row["candidate_id"]]
        expected = {
            "schema_version": REVIEW_SCHEMA,
            "candidate_id": candidate["candidate_id"],
            "role": candidate["role"],
            "candidate_file": candidate["file"],
            "candidate_sha256": candidate["sha256"],
        }
        mismatches = [field for field, value in expected.items() if row.get(field) != value]
        if mismatches:
            raise KeyframeSetError(
                "BLOCKED_KEYFRAME_INTEGRITY: review candidate identity mismatch: "
                + ", ".join(mismatches)
            )
        image = _safe_package_file(package_path, candidate["file"])
        actual = sha256_file(image)
        if actual != candidate["sha256"]:
            raise KeyframeSetError(
                f"BLOCKED_KEYFRAME_INTEGRITY: {candidate['candidate_id']} actual SHA-256 mismatch"
            )
        try:
            inspect_image(image)
        except ValueError as exc:
            raise KeyframeSetError(
                f"BLOCKED_KEYFRAME_INTEGRITY: {candidate['candidate_id']} is not a valid image"
            ) from exc
        human_values = [str(row.get(field) or "").strip() for field in QA_FIELDS + ATTRIBUTION_FIELDS]
        if not any(human_values):
            continue
        role = candidate["role"]
        required = ROLE_REQUIRED_FIELDS[role]
        failed = [field for field in required if str(row.get(field) or "").strip().upper() != "PASS"]
        if failed:
            raise KeyframeSetError(
                f"selected {candidate['candidate_id']} required role QA must all be PASS: "
                + ", ".join(failed)
            )
        inapplicable = [
            field for field in QA_FIELDS if field not in required and str(row.get(field) or "").strip()
        ]
        if inapplicable:
            raise KeyframeSetError(
                f"selected {candidate['candidate_id']} has populated QA that is not applicable: "
                + ", ".join(inapplicable)
            )
        reviewer = str(row.get("reviewer") or "").strip()
        if not reviewer:
            raise KeyframeSetError("selected review reviewer is required")
        reviewed_at = _timezone_aware(str(row.get("reviewed_at") or ""), "reviewed_at")
        slot = ROLE_SLOTS[role]
        if slot in selected:
            raise KeyframeSetError(f"exactly one selected candidate is required for {slot}")
        selected[slot] = {
            **candidate,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "notes": str(row.get("notes") or ""),
            "required_qa_fields": list(required),
            "staged_path": image.relative_to(root).as_posix(),
        }

    nonselected_populated = [
        row["candidate_id"]
        for row in rows
        if row["candidate_id"] not in {item["candidate_id"] for item in selected.values()}
        and any(str(row.get(field) or "").strip() for field in QA_FIELDS + ATTRIBUTION_FIELDS)
    ]
    if nonselected_populated:
        raise KeyframeSetError(
            "non-selected candidate subjective fields must remain blank: "
            + ", ".join(nonselected_populated)
        )
    if set(selected) != {"K1", "K2", "K3"}:
        raise KeyframeSetError("exactly one selected candidate is required for each of K1, K2, and K3")
    return {
        "status": "OWNER_KEYFRAME_REVIEW_VALID",
        "package": package_path.relative_to(root).as_posix(),
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "review_path": review_path.relative_to(root).as_posix(),
        "review_sha256": sha256_file(review_path),
        "character": dict(character),
        "selections": {item["role"]: item["candidate_id"] for item in selected.values()},
        "selected": selected,
        "selected_count": 3,
        "provider_submissions": 0,
        "paid_calls": 0,
    }


def promote_reviewed_candidate(
    project_root: Path, *, package: Path, candidate_id: str
) -> dict[str, Any]:
    root = project_root.resolve()
    review = validate_review_package(root, package)
    matches = [item for item in review["selected"].values() if item["candidate_id"] == candidate_id]
    if len(matches) != 1:
        raise KeyframeSetError(f"candidate is not an Owner-selected authority: {candidate_id}")
    selected = matches[0]
    staged = root / selected["staged_path"]
    before = sha256_file(staged)
    if before != selected["sha256"]:
        raise KeyframeSetError("BLOCKED_PROMOTION_INTEGRITY: staged candidate SHA-256 drift")
    manifest_path = root / "configs/keyframe-manifest.yaml"
    manifest_bytes = manifest_path.read_bytes()
    manifest = _read_yaml(manifest_path, "keyframe manifest")
    keyframes = manifest.get("keyframes")
    if not isinstance(keyframes, dict):
        raise KeyframeSetError("keyframe manifest keyframes must be a mapping")
    if candidate_id in keyframes:
        raise KeyframeSetError(f"approved keyframe already exists: {candidate_id}")
    suffix = staged.suffix.lower()
    approved = root / "assets/approved_keyframes" / f"{candidate_id}{suffix}"
    promotion_path = approved.with_suffix(".promotion.json")
    if approved.exists() or promotion_path.exists():
        raise KeyframeSetError(f"approved keyframe target already exists: {candidate_id}")
    character = review["character"]
    record = {
        "schema_version": PROMOTION_SCHEMA,
        "provenance_type": PROMOTION_TYPE,
        "candidate_id": candidate_id,
        "formal_role": selected["role"],
        "roles": APPROVED_ROLES[selected["role"]],
        "character_id": character["character_id"],
        "character_display_name": character["display_name"],
        "character_profile_sha256": character["profile_sha256"],
        "source_package": review["package"],
        "source_manifest": review["manifest_path"],
        "source_manifest_sha256": review["manifest_sha256"],
        "source_review": review["review_path"],
        "source_review_sha256": review["review_sha256"],
        "source_run_id": selected.get("run_id"),
        "provider": selected.get("provider"),
        "model": selected.get("model"),
        "provider_task_id": selected.get("provider_task_id"),
        "staged_path": selected["staged_path"],
        "staged_sha256": before,
        "reviewer": selected["reviewer"],
        "approved_at": selected["reviewed_at"],
        "approved_path": approved.relative_to(root).as_posix(),
        "approved_sha256": before,
        "copy_policy": "exact-byte",
    }
    replaced = False
    try:
        _copy_exclusive(staged, approved)
        if sha256_file(staged) != before or sha256_file(approved) != before:
            raise KeyframeSetError("BLOCKED_PROMOTION_INTEGRITY: exact-byte verification failed")
        _write_json_exclusive(promotion_path, record)
        keyframes[candidate_id] = {
            "roles": record["roles"],
            "path": record["approved_path"],
            "sha256": before,
            "provenance_type": PROMOTION_TYPE,
            "promotion_record": promotion_path.relative_to(root).as_posix(),
            "character_id": character["character_id"],
            "character_profile_sha256": character["profile_sha256"],
            "source_candidate_id": candidate_id,
            "source_candidate_sha256": before,
            "source_manifest_sha256": review["manifest_sha256"],
            "review_file_sha256": review["review_sha256"],
            "reviewer": selected["reviewer"],
            "approved_at": selected["reviewed_at"],
        }
        _atomic_write_yaml(manifest_path, manifest)
        replaced = True
    except Exception:
        if replaced:
            _atomic_write_bytes(manifest_path, manifest_bytes)
        promotion_path.unlink(missing_ok=True)
        approved.unlink(missing_ok=True)
        raise
    return {
        **record,
        "promotion_record": promotion_path.relative_to(root).as_posix(),
        "exact_byte_match": True,
        "provider_submissions": 0,
        "paid_calls": 0,
    }


def build_keyframe_set(
    project_root: Path, *, set_id: str, review_package: Path, created_at: datetime | None = None
) -> dict[str, Any]:
    root = project_root.resolve()
    _validate_set_id(set_id)
    review = validate_review_package(root, review_package)
    manifest = _read_yaml(root / "configs/keyframe-manifest.yaml", "keyframe manifest")
    raw_keyframes = manifest.get("keyframes")
    if not isinstance(raw_keyframes, Mapping):
        raise KeyframeSetError("keyframe manifest keyframes must be a mapping")
    members: dict[str, dict[str, Any]] = {}
    for slot, selected in review["selected"].items():
        raw = raw_keyframes.get(selected["candidate_id"])
        if not isinstance(raw, Mapping):
            raise KeyframeSetError(f"approved authority is missing for {slot}")
        approved = root / str(raw.get("path") or "")
        promotion = root / str(raw.get("promotion_record") or "")
        if not approved.is_file() or approved.is_symlink() or not promotion.is_file():
            raise KeyframeSetError(f"approved authority provenance is missing for {slot}")
        digest = sha256_file(approved)
        if digest != selected["sha256"] or digest != raw.get("sha256"):
            raise KeyframeSetError(f"approved authority SHA-256 mismatch for {slot}")
        promotion_payload = _read_json(promotion, f"{slot} promotion")
        if promotion_payload.get("character_id") != review["character"]["character_id"]:
            raise KeyframeSetError("keyframe set members must use the same active character")
        if promotion_payload.get("source_review_sha256") != review["review_sha256"]:
            raise KeyframeSetError(f"review provenance mismatch for {slot}")
        members[slot] = {
            "candidate_id": selected["candidate_id"],
            "formal_role": selected["role"],
            "approved_roles": list(raw.get("roles") or []),
            "approved_path": approved.relative_to(root).as_posix(),
            "sha256": digest,
            "promotion_record": promotion.relative_to(root).as_posix(),
            "promotion_record_sha256": sha256_file(promotion),
            "review_sha256": review["review_sha256"],
        }
    member_digest = _json_digest(members)
    timestamp = (created_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    payload = {
        "schema_version": SET_SCHEMA,
        "status": "BUILT",
        "set_id": set_id,
        "version": 1,
        "character": review["character"],
        "members": members,
        "member_digest": member_digest,
        "review_package": review["package"],
        "review_manifest_sha256": review["manifest_sha256"],
        "review_file_sha256": review["review_sha256"],
        "created_at": timestamp,
    }
    set_dir = root / "outputs/keyframe-sets" / set_id
    try:
        set_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise KeyframeSetError(f"keyframe set already exists: {set_id}") from exc
    manifest_path = set_dir / "manifest.json"
    try:
        _write_json_exclusive(manifest_path, payload)
    except Exception:
        shutil.rmtree(set_dir, ignore_errors=True)
        raise
    return {
        "status": "BUILT",
        "set_id": set_id,
        "version": 1,
        "character_id": review["character"]["character_id"],
        "members": members,
        "member_count": 3,
        "member_digest": member_digest,
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "created_at": timestamp,
        "provider_submissions": 0,
        "paid_calls": 0,
    }


def publish_keyframe_set(
    project_root: Path, *, set_id: str, published_at: datetime | None = None
) -> dict[str, Any]:
    root = project_root.resolve()
    set_record = _validate_set(root, set_id)
    registry_path = root / "configs/keyframe-set-registry.yaml"
    old_bytes = registry_path.read_bytes() if registry_path.exists() else None
    registry = _read_yaml(registry_path, "keyframe set registry") if old_bytes is not None else {}
    if registry.get("current_set_id") == set_id:
        raise KeyframeSetError(f"keyframe set is already published: {set_id}")
    prior_revision = int(registry.get("revision") or 0)
    revision = prior_revision + 1
    timestamp = (published_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    event_path = root / "outputs/keyframe-sets/publish-events" / f"{set_id}-r{revision:03d}.json"
    event = {
        "schema_version": PUBLISH_EVENT_SCHEMA,
        "event_type": "KEYFRAME_SET_PUBLISHED",
        "set_id": set_id,
        "manifest_path": set_record["manifest_path"],
        "manifest_sha256": set_record["manifest_sha256"],
        "member_digest": set_record["member_digest"],
        "character_id": set_record["character"]["character_id"],
        "prior_revision": prior_revision,
        "registry_revision": revision,
        "published_at": timestamp,
        "authority": "Project owner (explicit publish authorization)",
    }
    registry_payload: dict[str, Any] | None = None
    try:
        event_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_exclusive(event_path, event)
        registry_payload = {
            "schema_version": REGISTRY_SCHEMA,
            "revision": revision,
            "current_set_id": set_id,
            "manifest_path": set_record["manifest_path"],
            "manifest_sha256": set_record["manifest_sha256"],
            "character_id": set_record["character"]["character_id"],
            "publish_event": event_path.relative_to(root).as_posix(),
            "publish_event_sha256": sha256_file(event_path),
            "updated_at": timestamp,
        }
        _atomic_write_yaml(registry_path, registry_payload)
    except Exception:
        if old_bytes is None:
            registry_path.unlink(missing_ok=True)
        else:
            _atomic_write_bytes(registry_path, old_bytes)
        event_path.unlink(missing_ok=True)
        raise
    return {
        "status": "PUBLISHED",
        "set_id": set_id,
        "manifest_path": set_record["manifest_path"],
        "manifest_sha256": set_record["manifest_sha256"],
        "publish_event": event_path.relative_to(root).as_posix(),
        "publish_event_sha256": registry_payload["publish_event_sha256"],
        "registry_revision": revision,
        "published_at": timestamp,
        "provider_submissions": 0,
        "paid_calls": 0,
    }


def bind_goal2(
    project_root: Path, *, set_id: str, bound_at: datetime | None = None
) -> dict[str, Any]:
    root = project_root.resolve()
    registry = _validate_registry(root)
    if registry["current_set_id"] != set_id:
        raise KeyframeSetError("Goal 2 can bind only the current published keyframe set")
    set_record = _validate_set(root, set_id)
    character = _validate_active_character(root, set_record["character"])
    binding_path = root / "configs/goal2-binding.yaml"
    old = _read_yaml(binding_path, "Goal 2 binding") if binding_path.exists() else {}
    revision = int(old.get("revision") or 0) + 1
    timestamp = (bound_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    v7 = _classify_v7(root, set_record["members"]["K1"]["sha256"])
    payload = {
        "schema_version": GOAL2_BINDING_SCHEMA,
        "revision": revision,
        "active_character": character,
        "published_registry_revision": registry["revision"],
        "set_id": set_id,
        "set_manifest": set_record["manifest_path"],
        "set_manifest_sha256": set_record["manifest_sha256"],
        "members": set_record["members"],
        "v7": v7,
        "bound_at": timestamp,
    }
    _atomic_write_yaml(binding_path, payload)
    return {
        "status": "GOAL2_BOUND",
        "revision": revision,
        "active_character": character["character_id"],
        "display_name": character["display_name"],
        "set_id": set_id,
        "set_manifest_sha256": set_record["manifest_sha256"],
        "members": set_record["members"],
        "v7": v7,
        "binding_path": binding_path.relative_to(root).as_posix(),
        "binding_sha256": sha256_file(binding_path),
        "provider_submissions": 0,
        "paid_calls": 0,
    }


def preflight_goal2(project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    registry = _validate_registry(root)
    binding_path = root / "configs/goal2-binding.yaml"
    binding = _read_yaml(binding_path, "Goal 2 binding")
    if binding.get("schema_version") != GOAL2_BINDING_SCHEMA:
        raise KeyframeSetError("Goal 2 binding schema mismatch")
    if binding.get("set_id") != registry["current_set_id"]:
        raise KeyframeSetError("Goal 2 binding is stale relative to published registry")
    if binding.get("published_registry_revision") != registry["revision"]:
        raise KeyframeSetError("Goal 2 binding registry revision is stale")
    set_record = _validate_set(root, str(binding["set_id"]))
    if binding.get("set_manifest_sha256") != set_record["manifest_sha256"]:
        raise KeyframeSetError("Goal 2 binding set manifest SHA-256 mismatch")
    character = _validate_active_character(root, set_record["character"])
    if binding.get("members") != set_record["members"]:
        raise KeyframeSetError("Goal 2 member binding mismatch")
    v7 = _classify_v7(root, set_record["members"]["K1"]["sha256"])
    status = (
        "GOAL2_READY"
        if v7["status"] == "CANDIDATE16_V7_MATCH"
        else "READY_FOR_OWNER_CANDIDATE16_V7_EXECUTION"
    )
    return {
        "status": status,
        "active_character": character["character_id"],
        "display_name": character["display_name"],
        "set_id": set_record["set_id"],
        "set_manifest_sha256": set_record["manifest_sha256"],
        "registry_revision": registry["revision"],
        "members": set_record["members"],
        "v7": v7,
        "binding_path": binding_path.relative_to(root).as_posix(),
        "binding_sha256": sha256_file(binding_path),
        "provider_submissions": 0,
        "paid_calls": 0,
    }


def current_goal2_member_ids(project_root: Path) -> dict[str, str]:
    """Resolve only the published current visual authorities, without transferring V7 QA."""

    root = project_root.resolve()
    registry = _validate_registry(root)
    binding = _read_yaml(root / "configs/goal2-binding.yaml", "Goal 2 binding")
    if binding.get("schema_version") != GOAL2_BINDING_SCHEMA:
        raise KeyframeSetError("Goal 2 binding schema mismatch")
    if binding.get("set_id") != registry["current_set_id"]:
        raise KeyframeSetError("Goal 2 binding is stale relative to published registry")
    if binding.get("published_registry_revision") != registry["revision"]:
        raise KeyframeSetError("Goal 2 binding registry revision is stale")
    set_record = _validate_set(root, str(binding["set_id"]))
    _validate_active_character(root, set_record["character"])
    return {
        slot: str(member["candidate_id"])
        for slot, member in set_record["members"].items()
    }


def _manifest_candidates(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    roles = manifest.get("roles")
    if not isinstance(roles, Mapping):
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: manifest roles are missing")
    result: dict[str, dict[str, Any]] = {}
    for slot in ("K1", "K2", "K3"):
        value = roles.get(slot)
        if not isinstance(value, Mapping):
            raise KeyframeSetError(f"BLOCKED_KEYFRAME_INTEGRITY: manifest {slot} is missing")
        items = value.get("candidates") if slot != "K2" else [value]
        if not isinstance(items, list):
            raise KeyframeSetError(f"BLOCKED_KEYFRAME_INTEGRITY: manifest {slot} candidates invalid")
        expected_role = {
            "K1": "pilot_home_context",
            "K2": "pilot_talking_medium_closeup",
            "K3": "pilot_product_present",
        }[slot]
        for raw in items:
            if not isinstance(raw, Mapping):
                raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: candidate metadata invalid")
            candidate_id = str(raw.get("candidate_id") or "")
            file_value = str(raw.get("file") or "")
            digest = str(raw.get("sha256") or "").lower()
            role = str(raw.get("role") or value.get("role") or "")
            if not candidate_id or not file_value or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: candidate identity is incomplete")
            if role != expected_role or candidate_id in result:
                raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: candidate role/ID mismatch")
            result[candidate_id] = {
                "candidate_id": candidate_id,
                "role": role,
                "file": file_value,
                "sha256": digest,
                "run_id": raw.get("run_id") or value.get("run_id"),
                "provider_task_id": raw.get("provider_task_id") or value.get("provider_task_id"),
                "provider": manifest.get("provider"),
                "model": manifest.get("model"),
            }
    if len(result) != 7:
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: V2 manifest must contain seven candidates")
    return result


def _read_review(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != REVIEW_FIELDS:
                raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: review schema mismatch")
            rows = [dict(row) for row in reader]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: review CSV is unreadable") from exc
    if len(rows) != 7:
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: review must contain seven rows")
    return rows


def _validate_active_character(root: Path, expected: Mapping[str, Any]) -> dict[str, Any]:
    registry = _read_yaml(root / "configs/characters/registry.yaml", "character registry")
    character_id = str(expected.get("character_id") or "")
    if character_id != EXPECTED_CHARACTER_ID or expected.get("display_name") != EXPECTED_CHARACTER_NAME:
        raise KeyframeSetError("Candidate 16 character evidence mismatch")
    if expected.get("active") is False:
        raise KeyframeSetError("Candidate 16 package does not mark the character active")
    if registry.get("active_character") != character_id:
        raise KeyframeSetError("active character is not Candidate 16")
    raw = (registry.get("characters") or {}).get(character_id)
    if not isinstance(raw, Mapping) or raw.get("status") != "ACTIVE":
        raise KeyframeSetError("active character registry entry is invalid")
    if raw.get("display_name") != EXPECTED_CHARACTER_NAME:
        raise KeyframeSetError("active character display name mismatch")
    expected_profile = str(expected.get("profile_sha256") or "")
    if expected_profile and raw.get("profile_sha256") != expected_profile:
        raise KeyframeSetError("active character profile SHA-256 mismatch")
    expected_revision = expected.get("registry_revision")
    if expected_revision is not None and registry.get("revision") != expected_revision:
        raise KeyframeSetError("active character registry revision mismatch")
    return {
        "character_id": character_id,
        "display_name": EXPECTED_CHARACTER_NAME,
        "profile": raw.get("profile"),
        "profile_sha256": raw.get("profile_sha256"),
        "registry_revision": registry.get("revision"),
        "status": "ACTIVE",
    }


def _validate_set(root: Path, set_id: str) -> dict[str, Any]:
    _validate_set_id(set_id)
    path = root / "outputs/keyframe-sets" / set_id / "manifest.json"
    payload = _read_json(path, "keyframe set manifest")
    if payload.get("schema_version") != SET_SCHEMA or payload.get("set_id") != set_id:
        raise KeyframeSetError("keyframe set manifest identity mismatch")
    members = payload.get("members")
    if not isinstance(members, Mapping) or set(members) != {"K1", "K2", "K3"}:
        raise KeyframeSetError("keyframe set must contain exactly K1, K2, and K3")
    if payload.get("member_digest") != _json_digest(members):
        raise KeyframeSetError("keyframe set member digest mismatch")
    for slot, member in members.items():
        if not isinstance(member, Mapping):
            raise KeyframeSetError(f"keyframe set member {slot} is invalid")
        approved = root / str(member.get("approved_path") or "")
        promotion = root / str(member.get("promotion_record") or "")
        if not approved.is_file() or sha256_file(approved) != member.get("sha256"):
            raise KeyframeSetError(f"keyframe set approved SHA-256 mismatch for {slot}")
        if not promotion.is_file() or sha256_file(promotion) != member.get("promotion_record_sha256"):
            raise KeyframeSetError(f"keyframe set promotion provenance mismatch for {slot}")
    return {
        **payload,
        "manifest_path": path.relative_to(root).as_posix(),
        "manifest_sha256": sha256_file(path),
    }


def _validate_registry(root: Path) -> dict[str, Any]:
    path = root / "configs/keyframe-set-registry.yaml"
    registry = _read_yaml(path, "keyframe set registry")
    if registry.get("schema_version") != REGISTRY_SCHEMA:
        raise KeyframeSetError("published keyframe set registry schema mismatch")
    set_record = _validate_set(root, str(registry.get("current_set_id") or ""))
    if registry.get("manifest_sha256") != set_record["manifest_sha256"]:
        raise KeyframeSetError("published keyframe set manifest SHA-256 mismatch")
    event = root / str(registry.get("publish_event") or "")
    if not event.is_file() or sha256_file(event) != registry.get("publish_event_sha256"):
        raise KeyframeSetError("published keyframe set event provenance mismatch")
    if registry.get("character_id") != set_record["character"]["character_id"]:
        raise KeyframeSetError("published keyframe set character mismatch")
    return dict(registry)


def _classify_v7(root: Path, candidate16_k1_sha256: str) -> dict[str, Any]:
    registration_path = root / "outputs/reviews/candidate16-v7/registration.json"
    if registration_path.is_file():
        from .candidate16_v7 import load_candidate16_v7_registration

        registration = load_candidate16_v7_registration(
            root, candidate16_k1_sha256=candidate16_k1_sha256
        )
        return {
            "status": "CANDIDATE16_V7_MATCH",
            "methodology_reusable": True,
            "character_bound_evidence_reusable": True,
            "source_run_id": registration["recovery_run_id"],
            "parent_run_id": registration["parent_run_id"],
            "source_request": registration["registration_path"],
            "source_keyframe_sha256": registration["keyframe_sha256"],
            "candidate16_k1_sha256": candidate16_k1_sha256,
            "selected_candidate_id": registration["selected_candidate_id"],
            "selected_media_path": registration["selected_media_path"],
            "selected_media_sha256": registration["selected_media_sha256"],
            "selected_provider_task_id": registration["selected_provider_task_id"],
            "selected_prompt_path": registration["selected_prompt_path"],
            "selected_prompt_sha256": registration["selected_prompt_sha256"],
            "review_path": registration["review_path"],
            "review_sha256": registration["review_sha256"],
            "registration_sha256": registration["registration_sha256"],
            "tasks": 3,
            "generated_seconds": 15,
            "estimated_runway_credits": 75,
            "paid_calls_authorized": False,
        }
    request_path = root / "runs/LALA-VIDEO-20260820-075843-MOTION-V7-001/request.json"
    if not request_path.is_file():
        return {
            "status": "CANDIDATE16_V7_MISSING",
            "methodology_reusable": True,
            "character_bound_evidence_reusable": False,
            "candidate16_k1_sha256": candidate16_k1_sha256,
            "tasks": 3,
            "generated_seconds": 15,
            "estimated_runway_credits": 75,
        }
    payload = _read_json(request_path, "historical V7 request")
    requests = payload.get("requests")
    digests = {
        str(item.get("image_sha256") or "")
        for item in requests or []
        if isinstance(item, Mapping)
    }
    if len(digests) != 1:
        raise KeyframeSetError("historical V7 request has ambiguous keyframe provenance")
    source_digest = next(iter(digests))
    matches = source_digest == candidate16_k1_sha256
    return {
        "status": "CANDIDATE16_V7_MATCH" if matches else "LEGACY_CHARACTER_BOUND_MISMATCH",
        "methodology_reusable": True,
        "character_bound_evidence_reusable": matches,
        "source_run_id": payload.get("run_id") or request_path.parent.name,
        "source_request": request_path.relative_to(root).as_posix(),
        "source_keyframe_sha256": source_digest,
        "candidate16_k1_sha256": candidate16_k1_sha256,
        "tasks": 3,
        "generated_seconds": 15,
        "estimated_runway_credits": 75,
        "paid_calls_authorized": False,
    }


def _resolve_package(root: Path, package: Path) -> Path:
    unresolved = package if package.is_absolute() else root / package
    if unresolved.is_symlink():
        raise KeyframeSetError("review package symlink is forbidden")
    try:
        resolved = unresolved.resolve(strict=True)
    except OSError as exc:
        raise KeyframeSetError("review package does not exist") from exc
    reviews = (root / "outputs/reviews").resolve()
    if reviews not in resolved.parents or not resolved.is_dir():
        raise KeyframeSetError("review package must remain under outputs/reviews")
    return resolved


def _safe_package_file(package: Path, relative_value: str) -> Path:
    relative = Path(relative_value)
    if relative.is_absolute() or ".." in relative.parts:
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: unsafe candidate path")
    unresolved = package / relative
    if unresolved.is_symlink():
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: candidate symlink is forbidden")
    resolved = unresolved.resolve()
    if package.resolve() not in resolved.parents or not resolved.is_file():
        raise KeyframeSetError("BLOCKED_KEYFRAME_INTEGRITY: candidate file is missing")
    return resolved


def _validate_set_id(set_id: str) -> None:
    if not SET_ID_RE.fullmatch(set_id):
        raise KeyframeSetError("keyframe set ID must be a safe lowercase slug")


def _timezone_aware(value: str, label: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise KeyframeSetError(f"{label} must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise KeyframeSetError(f"{label} must include a timezone")
    return value.strip()


def _json_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KeyframeSetError(f"{label} is invalid") from exc
    if not isinstance(value, dict):
        raise KeyframeSetError(f"{label} must be an object")
    return value


def _read_yaml(path: Path, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise KeyframeSetError(f"{label} is invalid") from exc
    if not isinstance(value, dict):
        raise KeyframeSetError(f"{label} must be a mapping")
    return value


def _copy_exclusive(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_handle, target.open("xb") as output:
        shutil.copyfileobj(input_handle, output, length=1024 * 1024)
        output.flush()
        os.fsync(output.fileno())


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    content = yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False).encode("utf-8")
    _atomic_write_bytes(path, content)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
