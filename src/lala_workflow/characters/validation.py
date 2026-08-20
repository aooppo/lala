from __future__ import annotations

import hashlib
import io
import os
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from PIL import Image, UnidentifiedImageError

from ..hashing import assert_within_directory, inspect_image, sha256_file
from .domain import (
    OPTIONAL_REFERENCE_NAMES,
    REQUIRED_REFERENCE_NAMES,
    CharacterReference,
    CharacterUpload,
)
from .errors import CharacterIntegrityError, CharacterValidationError, upload_message


DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
FORMAT_INFO = {
    "PNG": ("image/png", ".png"),
    "JPEG": ("image/jpeg", ".jpg"),
    "WEBP": ("image/webp", ".webp"),
}
REFERENCE_ROLES = {
    "face": ("facial_identity", "lala_face"),
    "full_body": ("body_wardrobe_jewelry", "lala_look"),
    "three_quarter": ("identity_angle", "lala_3q"),
    "side": ("identity_side", "lala_side"),
    "expression": ("identity_expression", "lala_expr"),
    "product_pose": ("product_pose", "lala_pose"),
    "hair_accessory": ("hair_accessory", "lala_hair"),
}


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    role: str
    content: bytes
    sha256: str
    mime_type: str
    suffix: str
    width: int
    height: int
    size_bytes: int
    source_filename: str | None


def validate_uploads(
    uploads: Mapping[str, CharacterUpload],
    *,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> dict[str, ValidatedUpload]:
    allowed = set(REQUIRED_REFERENCE_NAMES) | set(OPTIONAL_REFERENCE_NAMES)
    unknown = sorted(set(uploads) - allowed)
    if unknown:
        raise CharacterValidationError(f"unknown upload roles: {', '.join(unknown)}")
    missing = [role for role in REQUIRED_REFERENCE_NAMES if role not in uploads]
    if missing:
        role = missing[0]
        raise CharacterValidationError(
            f"missing required upload: {role}", user_message=upload_message(role, "missing")
        )
    if max_upload_bytes < 1:
        raise CharacterValidationError("max upload bytes must be positive")
    result: dict[str, ValidatedUpload] = {}
    seen_hashes: dict[str, str] = {}
    for role in (*REQUIRED_REFERENCE_NAMES, *OPTIONAL_REFERENCE_NAMES):
        upload = uploads.get(role)
        if upload is None:
            continue
        if upload.role != role:
            raise CharacterValidationError(f"upload role mismatch: {upload.role} != {role}")
        item = validate_upload(upload, max_upload_bytes=max_upload_bytes)
        previous = seen_hashes.get(item.sha256)
        if previous is not None:
            raise CharacterValidationError(
                f"duplicate upload bytes for {previous} and {role}",
                user_message=upload_message(role, "duplicate"),
            )
        seen_hashes[item.sha256] = role
        result[role] = item
    return result


def validate_upload(
    upload: CharacterUpload, *, max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES
) -> ValidatedUpload:
    role = upload.role
    content = upload.content
    if not content:
        raise CharacterValidationError(
            f"empty upload: {role}", user_message=upload_message(role, "empty")
        )
    if len(content) > max_upload_bytes:
        raise CharacterValidationError(
            f"upload exceeds {max_upload_bytes} bytes: {role}",
            user_message=upload_message(role, "oversized"),
        )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                image_format = (image.format or "").upper()
                width, height = image.size
                image.verify()
    except Image.DecompressionBombError as exc:
        raise CharacterValidationError(
            f"decompression bomb rejected: {role}", user_message=upload_message(role, "oversized")
        ) from exc
    except (Image.DecompressionBombWarning, UnidentifiedImageError, OSError, ValueError) as exc:
        raise CharacterValidationError(
            f"corrupt image upload: {role}", user_message=upload_message(role, "corrupt")
        ) from exc
    if image_format not in FORMAT_INFO or width <= 0 or height <= 0:
        raise CharacterValidationError(
            f"unsupported image upload: {role}", user_message=upload_message(role, "unsupported")
        )
    mime_type, suffix = FORMAT_INFO[image_format]
    declared = (upload.declared_mime_type or "").split(";", 1)[0].strip().lower()
    if declared and declared not in {mime_type, "image/jpg" if mime_type == "image/jpeg" else mime_type}:
        raise CharacterValidationError(
            f"declared MIME does not match decoded image for {role}",
            user_message=upload_message(role, "unsupported"),
        )
    display_name = None
    if upload.filename:
        basename = Path(upload.filename).name
        display_name = re.sub(r"[\x00-\x1f\x7f<>\"'&]", "_", basename)[:200] or None
    return ValidatedUpload(
        role=role,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        mime_type=mime_type,
        suffix=suffix,
        width=width,
        height=height,
        size_bytes=len(content),
        source_filename=display_name,
    )


def reference_from_validated(
    item: ValidatedUpload, *, project_relative_path: Path
) -> CharacterReference:
    role, tag = REFERENCE_ROLES[item.role]
    return CharacterReference(
        logical_name=item.role,
        path=project_relative_path,
        sha256=item.sha256,
        role=role,
        tag=tag,
        mime_type=item.mime_type,
        width=item.width,
        height=item.height,
        size_bytes=item.size_bytes,
        source_filename=item.source_filename,
    )


def validate_reference_file(
    project_root: Path,
    reference: CharacterReference,
    *,
    allow_staging: bool,
) -> Path:
    root = project_root.resolve()
    source = root / reference.path
    if source.is_symlink():
        raise CharacterIntegrityError(f"character source is missing or unsafe: {reference.logical_name}")
    allowed_roots = [root / "assets/approved_anchors"]
    if allow_staging:
        allowed_roots.append(root / "assets/characters")
    resolved: Path | None = None
    for allowed in allowed_roots:
        try:
            resolved = assert_within_directory(source, allowed)
            break
        except ValueError:
            continue
    if resolved is None:
        raise CharacterIntegrityError(
            f"character source is outside allowed roots: {reference.logical_name}"
        )
    if not resolved.is_file():
        raise CharacterIntegrityError(f"character source is missing or unsafe: {reference.logical_name}")
    if not os.access(resolved, os.R_OK):
        raise CharacterIntegrityError(f"character source is not readable: {reference.logical_name}")
    if resolved.stat().st_size != reference.size_bytes or sha256_file(resolved) != reference.sha256:
        raise CharacterIntegrityError(f"character source digest mismatch: {reference.logical_name}")
    info = inspect_image(resolved)
    if (
        info.mime_type != reference.mime_type
        or info.width != reference.width
        or info.height != reference.height
    ):
        raise CharacterIntegrityError(f"character source metadata mismatch: {reference.logical_name}")
    return resolved
