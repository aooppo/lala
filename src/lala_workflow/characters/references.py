from __future__ import annotations

import os
import re
import stat
from dataclasses import replace
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from ..domain import AnchorImage, ReferenceImage
from ..hashing import inspect_image, sha256_file
from .domain import (
    CharacterProfile,
    ReferenceSelection,
    SelectedReference,
)
from .errors import CharacterStateError


CONTEXT_ORDER = {
    "baseline": ("face", "full_body"),
    "home": ("face", "full_body", "scene"),
    "medium": ("face", "three_quarter", "full_body"),
    "product": ("face", "full_body", "scene"),
}
PRESET_CONTEXT = {
    "baseline_identity": "baseline",
    "home_decor": "home",
    "product_page_clean": "product",
    "character_static_preview": "medium",
    "pilot_home_keyframe": "home",
    "pilot_talking_keyframe": "medium",
    "pilot_product_keyframe": "product",
}

MAX_EXTERNAL_REFERENCE_BYTES = 10 * 1024 * 1024
PILOT_REFERENCE_POLICIES = {
    "pilot_home_keyframe": (
        "character_face",
        "character_full_body",
        "external_scene_product_reference",
    ),
    "pilot_product_keyframe": (
        "character_face",
        "external_scene_product_reference",
        "external_product_reference",
    ),
}


def select_references(
    profile: CharacterProfile,
    *,
    scene: AnchorImage | None,
    context: str,
    max_references: int,
) -> ReferenceSelection:
    if context not in CONTEXT_ORDER:
        raise CharacterStateError(f"unknown reference context: {context}")
    preferred = CONTEXT_ORDER[context]
    required = tuple(name for name in preferred if name != "scene")
    missing = [name for name in required if name not in profile.references]
    if missing:
        raise CharacterStateError(
            f"character lacks required references for {context}: {', '.join(missing)}"
        )
    if len(required) > max_references:
        raise CharacterStateError("provider reference limit cannot fit required character inputs")
    selected: list[SelectedReference] = []
    for name in preferred:
        if len(selected) >= max_references:
            break
        if name == "scene":
            if scene is not None:
                selected.append(
                    SelectedReference(
                        logical_name="scene",
                        path=scene.path,
                        sha256=scene.sha256,
                        role=scene.role,
                        tag=scene.tag,
                    )
                )
            continue
        reference = profile.references[name]
        selected.append(
            SelectedReference(
                logical_name=name,
                path=reference.path,
                sha256=reference.sha256,
                role=reference.role,
                tag=reference.tag,
            )
        )
    return ReferenceSelection(context, tuple(selected), max_references)


def context_for_preset(preset: str) -> str:
    return PRESET_CONTEXT.get(preset, "baseline")


def plan_pilot_references(
    project_root: Path,
    profile: CharacterProfile,
    *,
    preset: str,
    scene_reference: Path | None,
    product_reference: Path | None,
    source_url: str | None,
    sku: str | None,
    max_references: int,
) -> tuple[ReferenceImage, ...]:
    policy = PILOT_REFERENCE_POLICIES.get(preset)
    if policy is None:
        raise CharacterStateError(f"unknown pilot reference policy: {preset}")
    if len(policy) > max_references:
        raise CharacterStateError(
            f"BLOCKED_REFERENCE_LIMIT: {preset} requires {len(policy)} references but provider "
            f"permits {max_references}"
        )
    if scene_reference is None:
        raise CharacterStateError(
            f"BLOCKED_PRODUCT_REFERENCE_CONDITIONING: {preset} requires --scene-reference"
        )
    if preset == "pilot_product_keyframe" and product_reference is None:
        raise CharacterStateError(
            "BLOCKED_PRODUCT_REFERENCE_CONDITIONING: pilot_product_keyframe requires "
            "--product-reference"
        )
    if preset == "pilot_home_keyframe" and product_reference is not None:
        raise CharacterStateError(
            "pilot_home_keyframe does not accept --product-reference; the scene reference owns "
            "the third and final slot"
        )
    _validate_external_provenance(source_url, sku)

    planned: list[ReferenceImage] = []
    for semantic_role in policy:
        if semantic_role == "character_face":
            planned.append(_character_reference(project_root, profile, "face", semantic_role))
        elif semantic_role == "character_full_body":
            planned.append(
                _character_reference(project_root, profile, "full_body", semantic_role)
            )
        elif semantic_role == "external_scene_product_reference":
            planned.append(
                _external_reference(
                    project_root,
                    scene_reference,
                    name="scene_reference",
                    role="external_scene_product_reference",
                    tag="henry_scene",
                    source_url=source_url,
                    sku=sku,
                )
            )
        elif semantic_role == "external_product_reference":
            planned.append(
                _external_reference(
                    project_root,
                    product_reference,
                    name="product_reference",
                    role="external_product_reference",
                    tag="henry_product",
                    source_url=source_url,
                    sku=sku,
                )
            )

    unique: list[ReferenceImage] = []
    seen_hashes: set[str] = set()
    for reference in planned:
        if reference.sha256 in seen_hashes:
            continue
        seen_hashes.add(reference.sha256)
        unique.append(reference)
    if len(unique) != len(policy):
        raise CharacterStateError(
            "BLOCKED_PRODUCT_REFERENCE_CONDITIONING: duplicate reference bytes cannot satisfy "
            f"the required {preset} semantic slots"
        )
    if len(unique) > max_references:
        raise CharacterStateError(
            f"BLOCKED_REFERENCE_LIMIT: planned {len(unique)} references but provider permits "
            f"{max_references}"
        )
    return tuple(replace(reference, slot=index) for index, reference in enumerate(unique, start=1))


def _character_reference(
    project_root: Path,
    profile: CharacterProfile,
    logical_name: str,
    semantic_role: str,
) -> ReferenceImage:
    reference = profile.references.get(logical_name)
    if reference is None:
        raise CharacterStateError(f"character lacks required reference: {logical_name}")
    return ReferenceImage(
        name=logical_name,
        path=project_root.resolve() / reference.path,
        role=reference.role,
        tag=reference.tag,
        sha256=reference.sha256,
        mime_type=reference.mime_type,
        semantic_role=semantic_role,
        source_type="active_character_authority",
        width=reference.width,
        height=reference.height,
    )


def _external_reference(
    project_root: Path,
    path: Path | None,
    *,
    name: str,
    role: str,
    tag: str,
    source_url: str | None,
    sku: str | None,
) -> ReferenceImage:
    if path is None:
        raise CharacterStateError(f"missing external reference: {name}")
    root = project_root.resolve()
    if not path.is_absolute() and ".." in path.parts:
        raise CharacterStateError(f"unsafe external reference path: {path}")
    source = path if path.is_absolute() else root / path
    try:
        lexical_relative = source.relative_to(root)
    except ValueError as exc:
        raise CharacterStateError(f"external reference is outside project root: {path}") from exc
    current = root
    for part in lexical_relative.parts:
        current = current / part
        if current.is_symlink():
            raise CharacterStateError(f"unsafe symlink external reference: {path}")
    try:
        resolved = source.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as exc:
        raise CharacterStateError(f"missing or unsafe external reference: {path}") from exc
    metadata = resolved.stat()
    if not stat.S_ISREG(metadata.st_mode) or not os.access(resolved, os.R_OK):
        raise CharacterStateError(f"external reference must be a readable regular file: {path}")
    if metadata.st_size <= 0 or metadata.st_size > MAX_EXTERNAL_REFERENCE_BYTES:
        raise CharacterStateError(
            f"external reference size must be 1..{MAX_EXTERNAL_REFERENCE_BYTES} bytes: {path}"
        )
    try:
        info = inspect_image(resolved)
    except ValueError as exc:
        raise CharacterStateError(f"invalid external reference image: {path}") from exc
    return ReferenceImage(
        name=name,
        path=resolved,
        role=role,
        tag=tag,
        sha256=sha256_file(resolved),
        mime_type=info.mime_type,
        semantic_role=role,
        source_type="external_local_pdp_reference",
        width=info.width,
        height=info.height,
        source_url=source_url,
        sku=sku,
    )


def _validate_external_provenance(source_url: str | None, sku: str | None) -> None:
    if not source_url or not sku:
        raise CharacterStateError(
            "external references require --reference-source-url and --reference-sku provenance"
        )
    parsed = urlsplit(source_url)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise CharacterStateError("reference source URL must be a clean credential-free HTTPS URL")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", sku):
        raise CharacterStateError("reference SKU is invalid")
