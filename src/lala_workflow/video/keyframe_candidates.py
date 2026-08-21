from __future__ import annotations

import csv
import json
import os
import re
import shutil
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..hashing import inspect_image, sha256_file


EXTERNAL_CANDIDATE_SCHEMA = "external-keyframe-candidate/v1"
EXTERNAL_REVIEW_SCHEMA = "external-k2-review/v1"
EXTERNAL_PROMOTION_SCHEMA = "external-keyframe-promotion/v1"
EXTERNAL_SOURCE_TYPE = "owner_supplied_external_candidate"
EXTERNAL_PROMOTION_TYPE = "owner_supplied_external_promotion"
K2_ROLE = "talking_medium_closeup"
MAX_EXTERNAL_IMAGE_BYTES = 20 * 1024 * 1024
_CANDIDATE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$")

EXTERNAL_K2_IDENTITY_FIELDS = (
    "schema_version",
    "candidate_id",
    "role",
    "candidate_file",
    "candidate_sha256",
    "source_type",
)
EXTERNAL_K2_HUMAN_FIELDS = (
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
    "reviewer",
    "reviewed_at",
    "notes",
)
EXTERNAL_K2_REVIEW_FIELDS = EXTERNAL_K2_IDENTITY_FIELDS + EXTERNAL_K2_HUMAN_FIELDS
_PASS_FIELDS = EXTERNAL_K2_HUMAN_FIELDS[:11]


class ExternalKeyframeError(ValueError):
    pass


def import_external_keyframe_candidate(
    project_root: Path,
    *,
    source: Path,
    candidate_id: str,
    role: str,
    source_reference: str,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    _validate_candidate_id(candidate_id)
    if role != K2_ROLE:
        raise ExternalKeyframeError(f"external candidate role must be {K2_ROLE}")
    reference = source_reference.strip()
    if not reference:
        raise ExternalKeyframeError("external candidate source-reference is required")
    source_path = _resolve_source(root, source)
    try:
        source_stat = source_path.stat()
    except OSError as exc:
        raise ExternalKeyframeError("external candidate source is unreadable") from exc
    if not stat.S_ISREG(source_stat.st_mode):
        raise ExternalKeyframeError("external candidate source must be a regular file")
    if source_stat.st_size <= 0 or source_stat.st_size > MAX_EXTERNAL_IMAGE_BYTES:
        raise ExternalKeyframeError(
            f"external candidate size must be within 1..{MAX_EXTERNAL_IMAGE_BYTES} bytes"
        )
    try:
        info = inspect_image(source_path)
    except ValueError as exc:
        raise ExternalKeyframeError("external candidate is not a valid PNG or JPEG") from exc
    expected_suffix = {"image/png": ".png", "image/jpeg": ".jpg"}.get(info.mime_type)
    if expected_suffix is None:
        raise ExternalKeyframeError("external candidate must be PNG or JPEG")
    suffix = source_path.suffix.lower()
    valid_suffixes = {".png"} if expected_suffix == ".png" else {".jpg", ".jpeg"}
    if suffix not in valid_suffixes:
        raise ExternalKeyframeError("external candidate extension does not match decoded MIME")

    candidate_dir = root / "outputs/keyframes/candidates" / candidate_id
    try:
        candidate_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ExternalKeyframeError(f"external candidate already exists: {candidate_id}") from exc
    staged = candidate_dir / f"candidate{expected_suffix}"
    provenance = candidate_dir / "provenance.json"
    review = candidate_dir / "review.csv"
    source_hash = sha256_file(source_path)
    try:
        with source_path.open("rb") as source_handle, staged.open("xb") as output:
            shutil.copyfileobj(source_handle, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        staged_hash = sha256_file(staged)
        if sha256_file(source_path) != source_hash or staged_hash != source_hash:
            raise ExternalKeyframeError("external candidate source changed during exact-byte staging")
        timestamp = (created_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        payload = {
            "schema_version": EXTERNAL_CANDIDATE_SCHEMA,
            "candidate_id": candidate_id,
            "role": role,
            "source_type": EXTERNAL_SOURCE_TYPE,
            "source_reference": reference,
            "source_identity": source_path.name,
            "source_sha256": source_hash,
            "staged_path": staged.relative_to(root).as_posix(),
            "staged_sha256": staged_hash,
            "size_bytes": staged.stat().st_size,
            "mime_type": info.mime_type,
            "width": info.width,
            "height": info.height,
            "created_at": timestamp.isoformat().replace("+00:00", "Z"),
            "created_by": "Project owner (source declaration)",
            "approval_status": "PENDING_HUMAN_REVIEW",
        }
        _write_json_exclusive(provenance, payload)
        _write_blank_review(review, payload)
    except Exception:
        shutil.rmtree(candidate_dir, ignore_errors=True)
        raise
    return {
        **payload,
        "status": "READY_FOR_K2_HUMAN_REVIEW",
        "provenance_path": provenance.relative_to(root).as_posix(),
        "blank_review_path": review.relative_to(root).as_posix(),
        "provider_calls": 0,
        "paid_calls": 0,
    }


def promote_external_keyframe_candidate(
    project_root: Path, *, candidate_id: str, review_file: Path
) -> dict[str, Any]:
    root = project_root.resolve()
    _validate_candidate_id(candidate_id)
    candidate_dir = root / "outputs/keyframes/candidates" / candidate_id
    provenance_path = candidate_dir / "provenance.json"
    baseline_review = candidate_dir / "review.csv"
    if not candidate_dir.is_dir() or not provenance_path.is_file() or not baseline_review.is_file():
        raise ExternalKeyframeError(f"external candidate does not exist: {candidate_id}")
    provenance = _read_json_object(provenance_path, "candidate provenance")
    _validate_candidate_provenance(root, candidate_id, provenance)
    staged = root / str(provenance["staged_path"])
    staged_hash = sha256_file(staged)
    if staged_hash != provenance["staged_sha256"] or staged_hash != provenance["source_sha256"]:
        raise ExternalKeyframeError("external candidate staged hash drift")
    baseline = _read_single_review(baseline_review)
    if any(str(baseline.get(field) or "").strip() for field in EXTERNAL_K2_HUMAN_FIELDS):
        raise ExternalKeyframeError("candidate-local blank review must remain blank")
    expected_identity = _review_identity(provenance)
    _validate_review_identity(baseline, expected_identity)

    reviewed_path = _resolve_review_path(root, review_file)
    reviewed = _read_single_review(reviewed_path)
    _validate_review_identity(reviewed, expected_identity)
    failed = [field for field in _PASS_FIELDS if str(reviewed.get(field) or "").strip().upper() != "PASS"]
    if failed:
        raise ExternalKeyframeError("required K2 QA decisions must all be PASS: " + ", ".join(failed))
    reviewer = str(reviewed.get("reviewer") or "").strip()
    if not reviewer:
        raise ExternalKeyframeError("reviewer is required for external keyframe promotion")
    reviewed_at_raw = str(reviewed.get("reviewed_at") or "").strip()
    try:
        reviewed_at = datetime.fromisoformat(reviewed_at_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExternalKeyframeError("reviewed_at must be ISO 8601") from exc
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise ExternalKeyframeError("reviewed_at must include a timezone")

    manifest_path = root / "configs/keyframe-manifest.yaml"
    manifest_bytes = manifest_path.read_bytes()
    manifest = yaml.safe_load(manifest_bytes) or {}
    keyframes = manifest.get("keyframes")
    if not isinstance(keyframes, dict):
        raise ExternalKeyframeError("keyframe manifest keyframes must be a mapping")
    if candidate_id in keyframes:
        raise ExternalKeyframeError(f"approved keyframe already exists: {candidate_id}")
    duplicates = [
        key
        for key, value in keyframes.items()
        if isinstance(value, Mapping) and K2_ROLE in (value.get("roles") or [])
    ]
    if duplicates:
        raise ExternalKeyframeError("approved talking_medium_closeup authority already exists")

    approved = root / "assets/approved_keyframes" / f"{candidate_id}{staged.suffix.lower()}"
    promotion_path = approved.with_suffix(".promotion.json")
    if approved.exists() or promotion_path.exists():
        raise ExternalKeyframeError(f"approved keyframe target already exists: {candidate_id}")
    record = {
        "schema_version": EXTERNAL_PROMOTION_SCHEMA,
        "provenance_type": EXTERNAL_PROMOTION_TYPE,
        "candidate_id": candidate_id,
        "role": K2_ROLE,
        "source_type": EXTERNAL_SOURCE_TYPE,
        "source_reference": provenance["source_reference"],
        "source_identity": provenance["source_identity"],
        "source_sha256": provenance["source_sha256"],
        "staged_path": provenance["staged_path"],
        "staged_sha256": staged_hash,
        "review_file": reviewed_path.relative_to(root).as_posix(),
        "review_sha256": sha256_file(reviewed_path),
        "reviewer": reviewer,
        "approved_at": reviewed_at_raw,
        "approved_path": approved.relative_to(root).as_posix(),
        "approved_sha256": staged_hash,
    }
    manifest_replaced = False
    try:
        _copy_exclusive(staged, approved)
        if sha256_file(approved) != staged_hash:
            raise ExternalKeyframeError("approved keyframe hash does not match staged candidate")
        _write_json_exclusive(promotion_path, record)
        keyframes[candidate_id] = {
            "roles": [K2_ROLE],
            "path": record["approved_path"],
            "sha256": staged_hash,
            "provenance_type": EXTERNAL_PROMOTION_TYPE,
            "promotion_record": promotion_path.relative_to(root).as_posix(),
            "source_candidate_id": candidate_id,
            "source_candidate_sha256": staged_hash,
            "source_reference": provenance["source_reference"],
            "review_file_sha256": record["review_sha256"],
            "reviewer": reviewer,
            "approved_at": reviewed_at_raw,
        }
        _atomic_write_yaml(manifest_path, manifest)
        manifest_replaced = True
    except Exception:
        if manifest_replaced:
            _atomic_write_bytes(manifest_path, manifest_bytes)
        promotion_path.unlink(missing_ok=True)
        approved.unlink(missing_ok=True)
        raise
    return {**record, "promotion_record": promotion_path.relative_to(root).as_posix()}


def _validate_candidate_id(candidate_id: str) -> None:
    if not _CANDIDATE_ID_RE.fullmatch(candidate_id):
        raise ExternalKeyframeError("candidate ID must be a safe lowercase slug")


def _resolve_source(root: Path, source: Path) -> Path:
    if not source.is_absolute() and ".." in source.parts:
        raise ExternalKeyframeError("external candidate source path traversal is forbidden")
    path = source if source.is_absolute() else root / source
    if path.is_symlink():
        raise ExternalKeyframeError("external candidate source symlink is forbidden")
    try:
        return path.resolve(strict=True)
    except OSError as exc:
        raise ExternalKeyframeError("external candidate source does not exist") from exc


def _validate_candidate_provenance(root: Path, candidate_id: str, value: Mapping[str, Any]) -> None:
    expected = {
        "schema_version": EXTERNAL_CANDIDATE_SCHEMA,
        "candidate_id": candidate_id,
        "role": K2_ROLE,
        "source_type": EXTERNAL_SOURCE_TYPE,
        "approval_status": "PENDING_HUMAN_REVIEW",
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            raise ExternalKeyframeError(f"candidate provenance {field} mismatch")
    for field in ("source_reference", "source_identity", "source_sha256", "staged_path", "staged_sha256", "created_at", "created_by"):
        if not str(value.get(field) or "").strip():
            raise ExternalKeyframeError(f"candidate provenance {field} is required")
    staged_input = root / str(value["staged_path"])
    if staged_input.is_symlink():
        raise ExternalKeyframeError("candidate provenance staged_path symlink is forbidden")
    staged = staged_input.resolve()
    expected_root = (root / "outputs/keyframes/candidates" / candidate_id).resolve()
    if expected_root not in staged.parents or not staged.is_file() or staged.is_symlink():
        raise ExternalKeyframeError("candidate provenance staged_path is invalid")


def _review_identity(provenance: Mapping[str, Any]) -> dict[str, str]:
    return {
        "schema_version": EXTERNAL_REVIEW_SCHEMA,
        "candidate_id": str(provenance["candidate_id"]),
        "role": str(provenance["role"]),
        "candidate_file": str(provenance["staged_path"]),
        "candidate_sha256": str(provenance["staged_sha256"]),
        "source_type": str(provenance["source_type"]),
    }


def _validate_review_identity(row: Mapping[str, str], expected: Mapping[str, str]) -> None:
    for field, expected_value in expected.items():
        if row.get(field) != expected_value:
            raise ExternalKeyframeError(f"review candidate provenance mismatch: {field}")


def _write_blank_review(path: Path, provenance: Mapping[str, Any]) -> None:
    row = {field: "" for field in EXTERNAL_K2_REVIEW_FIELDS}
    row.update(_review_identity(provenance))
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXTERNAL_K2_REVIEW_FIELDS)
        writer.writeheader(); writer.writerow(row)
        handle.flush(); os.fsync(handle.fileno())


def _read_single_review(path: Path) -> dict[str, str]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != EXTERNAL_K2_REVIEW_FIELDS:
                raise ExternalKeyframeError("external K2 review schema mismatch")
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ExternalKeyframeError("external K2 review is unreadable") from exc
    if len(rows) != 1:
        raise ExternalKeyframeError("external K2 review must contain exactly one candidate row")
    return dict(rows[0])


def _resolve_review_path(root: Path, value: Path) -> Path:
    if not value.is_absolute() and ".." in value.parts:
        raise ExternalKeyframeError("review path traversal is forbidden")
    unresolved = value if value.is_absolute() else root / value
    if unresolved.is_symlink():
        raise ExternalKeyframeError("review file symlink is forbidden")
    path = unresolved.resolve()
    reviews_root = (root / "outputs/reviews").resolve()
    if reviews_root not in path.parents or not path.is_file():
        raise ExternalKeyframeError("review file must be a regular copy under outputs/reviews")
    return path


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExternalKeyframeError(f"{label} is invalid") from exc
    if not isinstance(value, dict):
        raise ExternalKeyframeError(f"{label} must be an object")
    return value


def _copy_exclusive(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as source_handle, target.open("xb") as output:
        shutil.copyfileobj(source_handle, output, length=1024 * 1024)
        output.flush(); os.fsync(output.fileno())


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _atomic_write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    content = yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False).encode("utf-8")
    _atomic_write_bytes(path, content)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(content); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
