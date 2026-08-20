from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..domain import AnchorImage
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
