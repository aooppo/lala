from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from PIL import UnidentifiedImageError

from ..hashing import assert_within_directory, inspect_image, sha256_file
from .domain import ApprovedKeyframe


HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceValidationError(ValueError):
    pass


class ExternalInputBlocked(SourceValidationError):
    """Authoritative user input or approval is missing."""


def validate_approved_keyframe(
    keyframe_id: str, raw: Mapping[str, Any], project_root: Path
) -> ApprovedKeyframe:
    relative = Path(str(raw.get("path") or ""))
    if relative.is_absolute() or not relative.as_posix():
        raise SourceValidationError(f"keyframe {keyframe_id} path must be project-relative")
    try:
        source = assert_within_directory(
            project_root / relative, project_root / "assets/approved_keyframes"
        )
    except ValueError as exc:
        raise SourceValidationError(
            f"keyframe {keyframe_id} must remain under assets/approved_keyframes"
        ) from exc
    expected = str(raw.get("sha256") or "").lower()
    if not HASH_RE.fullmatch(expected):
        raise SourceValidationError(f"keyframe {keyframe_id} sha256 is required")
    if not source.is_file():
        raise SourceValidationError(f"keyframe {keyframe_id} file does not exist: {relative}")
    actual = sha256_file(source)
    if actual != expected:
        raise SourceValidationError(
            f"keyframe {keyframe_id} digest mismatch: expected {expected}, got {actual}"
        )
    try:
        info = inspect_image(source)
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise SourceValidationError(f"keyframe {keyframe_id} is not a valid image") from exc
    if info.mime_type not in {"image/png", "image/jpeg"}:
        raise SourceValidationError(f"keyframe {keyframe_id} must be PNG or JPEG")
    provenance_type = str(raw.get("provenance_type") or "goal1_promotion").strip()
    if provenance_type == "owner_supplied_legacy_asset":
        return _validate_owner_supplied_legacy_keyframe(
            keyframe_id, raw, project_root, relative, source, actual, info
        )
    if provenance_type != "goal1_promotion":
        raise SourceValidationError(
            f"keyframe {keyframe_id} has unsupported provenance_type: {provenance_type}"
        )
    return _validate_goal1_promotion_keyframe(
        keyframe_id, raw, project_root, source, actual, info
    )


def _validate_goal1_promotion_keyframe(
    keyframe_id: str,
    raw: Mapping[str, Any],
    project_root: Path,
    source: Path,
    actual: str,
    info: Any,
) -> ApprovedKeyframe:
    promotion_relative = Path(str(raw.get("promotion_record") or ""))
    try:
        promotion = assert_within_directory(
            project_root / promotion_relative, project_root / "assets/approved_keyframes"
        )
    except ValueError as exc:
        raise SourceValidationError(
            f"keyframe {keyframe_id} promotion record must remain with approved keyframes"
        ) from exc
    if not promotion.is_file():
        raise SourceValidationError(f"keyframe {keyframe_id} promotion record does not exist")
    try:
        promotion_payload = json.loads(promotion.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceValidationError(f"keyframe {keyframe_id} promotion record is invalid JSON") from exc
    if not isinstance(promotion_payload, dict):
        raise SourceValidationError(f"keyframe {keyframe_id} promotion record must be an object")
    required = ("source_run_id", "source_output_id", "reviewer", "approved_at")
    values = {name: str(raw.get(name) or "").strip() for name in required}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise SourceValidationError(
            f"keyframe {keyframe_id} is missing approval metadata: {', '.join(missing)}"
        )
    try:
        approved_at = datetime.fromisoformat(values["approved_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceValidationError(f"keyframe {keyframe_id} approved_at is invalid") from exc
    if approved_at.tzinfo is None:
        raise SourceValidationError(f"keyframe {keyframe_id} approved_at must include a timezone")
    promotion_values = {
        "source_run_id": str(promotion_payload.get("source_run_id") or ""),
        "source_output_id": str(promotion_payload.get("source_output_id") or ""),
        "sha256": str(
            promotion_payload.get("image_sha256") or promotion_payload.get("sha256") or ""
        ),
        "reviewer": str(promotion_payload.get("reviewer") or ""),
        "approved_at": str(
            promotion_payload.get("approval_date")
            or promotion_payload.get("approved_at")
            or ""
        ),
    }
    expected_promotion = {
        "source_run_id": values["source_run_id"],
        "source_output_id": values["source_output_id"],
        "sha256": actual,
        "reviewer": values["reviewer"],
        "approved_at": values["approved_at"],
    }
    mismatches = [
        name
        for name, expected_value in expected_promotion.items()
        if promotion_values[name] != expected_value
    ]
    if mismatches:
        raise SourceValidationError(
            f"keyframe {keyframe_id} promotion provenance mismatch: {', '.join(mismatches)}"
        )
    return ApprovedKeyframe(
        keyframe_id=keyframe_id,
        path=source.relative_to(project_root.resolve()),
        sha256=actual,
        mime_type=info.mime_type,
        width=info.width,
        height=info.height,
        provenance_type="goal1_promotion",
        provenance_record=promotion.relative_to(project_root.resolve()),
        source_run_id=values["source_run_id"],
        source_output_id=values["source_output_id"],
        reviewer=values["reviewer"],
        approved_at=approved_at.isoformat(),
        roles=_roles(raw),
    )


def _validate_owner_supplied_legacy_keyframe(
    keyframe_id: str,
    raw: Mapping[str, Any],
    project_root: Path,
    relative: Path,
    source: Path,
    actual: str,
    info: Any,
) -> ApprovedKeyframe:
    prohibited = (
        "source_run_id",
        "source_output_id",
        "provider_task_id",
        "prompt_version",
        "model",
        "reviewer",
        "approved_at",
        "approval_date",
    )
    claimed = [name for name in prohibited if str(raw.get(name) or "").strip()]
    if claimed:
        raise SourceValidationError(
            f"keyframe {keyframe_id} legacy provenance must not contain generated provenance "
            f"or fabricated approval fields: {', '.join(claimed)}"
        )
    required = (
        "provenance_record",
        "source_package",
        "source_package_sha256",
        "source_path",
        "owner_approval_reference",
    )
    values = {name: str(raw.get(name) or "").strip() for name in required}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise SourceValidationError(
            f"keyframe {keyframe_id} legacy provenance is missing: {', '.join(missing)}"
        )
    if not HASH_RE.fullmatch(values["source_package_sha256"].lower()):
        raise SourceValidationError(
            f"keyframe {keyframe_id} source_package_sha256 must be 64 lowercase hex characters"
        )
    package_source = Path(values["source_path"])
    if package_source.is_absolute() or ".." in package_source.parts:
        raise SourceValidationError(
            f"keyframe {keyframe_id} source_path must be a safe package-relative path"
        )
    provenance_relative = Path(values["provenance_record"])
    try:
        provenance = assert_within_directory(
            project_root / provenance_relative,
            project_root / "assets/approved_keyframes",
        )
    except ValueError as exc:
        raise SourceValidationError(
            f"keyframe {keyframe_id} provenance record must remain with approved keyframes"
        ) from exc
    if not provenance.is_file():
        raise SourceValidationError(f"keyframe {keyframe_id} provenance record does not exist")
    try:
        payload = json.loads(provenance.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceValidationError(
            f"keyframe {keyframe_id} provenance record is invalid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise SourceValidationError(f"keyframe {keyframe_id} provenance record must be an object")
    sidecar_claims = [name for name in prohibited if str(payload.get(name) or "").strip()]
    if sidecar_claims:
        raise SourceValidationError(
            f"keyframe {keyframe_id} legacy provenance record must not contain generated "
            f"provenance or fabricated approval fields: {', '.join(sidecar_claims)}"
        )
    expected_payload = {
        "provenance_type": "owner_supplied_legacy_asset",
        "asset_path": relative.as_posix(),
        "sha256": actual,
        "source_package": values["source_package"],
        "source_package_sha256": values["source_package_sha256"].lower(),
        "source_path": values["source_path"],
        "owner_approval_reference": values["owner_approval_reference"],
    }
    mismatches = [
        name
        for name, expected_value in expected_payload.items()
        if str(payload.get(name) or "") != expected_value
    ]
    if mismatches:
        raise SourceValidationError(
            f"keyframe {keyframe_id} legacy provenance mismatch: {', '.join(mismatches)}"
        )
    return ApprovedKeyframe(
        keyframe_id=keyframe_id,
        path=source.relative_to(project_root.resolve()),
        sha256=actual,
        mime_type=info.mime_type,
        width=info.width,
        height=info.height,
        provenance_type="owner_supplied_legacy_asset",
        provenance_record=provenance.relative_to(project_root.resolve()),
        source_package=values["source_package"],
        source_package_sha256=values["source_package_sha256"].lower(),
        source_path=values["source_path"],
        owner_approval_reference=values["owner_approval_reference"],
        roles=_roles(raw),
    )


def _roles(raw: Mapping[str, Any]) -> tuple[str, ...]:
    values = raw.get("roles") or ()
    if not isinstance(values, (list, tuple)):
        raise SourceValidationError("keyframe roles must be a list")
    roles = tuple(str(value).strip() for value in values)
    if any(not value for value in roles) or len(set(roles)) != len(roles):
        raise SourceValidationError("keyframe roles must be non-empty and unique")
    return roles
