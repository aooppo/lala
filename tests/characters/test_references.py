from __future__ import annotations

import pytest

from lala_workflow.characters.errors import CharacterStateError
from lala_workflow.characters.references import context_for_preset, select_references
from lala_workflow.characters.service import CharacterService
from lala_workflow.config import load_project_config


def test_context_order_and_provider_limit(project_root, character_uploads) -> None:
    service = CharacterService(project_root)
    profile = service.import_character(character_uploads, created_by="test")
    scene = load_project_config(project_root).manifest.anchors["scene"]
    expected = {
        "baseline": ["face", "full_body"],
        "home": ["face", "full_body", "scene"],
        "medium": ["face", "three_quarter", "full_body"],
        "product": ["face", "full_body", "scene"],
    }
    for context, names in expected.items():
        selection = select_references(profile, scene=scene, context=context, max_references=3)
        assert [item.logical_name for item in selection.references] == names
    product_two = select_references(profile, scene=scene, context="product", max_references=2)
    assert [item.logical_name for item in product_two.references] == ["face", "full_body"]
    with pytest.raises(CharacterStateError, match="cannot fit"):
        select_references(profile, scene=scene, context="medium", max_references=2)


def test_keyframe_presets_select_role_specific_references(project_root, character_uploads) -> None:
    service = CharacterService(project_root)
    profile = service.import_character(character_uploads, created_by="test")
    scene = load_project_config(project_root).manifest.anchors["scene"]
    expected = {
        "pilot_home_keyframe": ["face", "full_body", "scene"],
        "pilot_talking_keyframe": ["face", "three_quarter", "full_body"],
        "pilot_product_keyframe": ["face", "full_body", "scene"],
    }

    for preset, names in expected.items():
        selection = select_references(
            profile,
            scene=scene,
            context=context_for_preset(preset),
            max_references=3,
        )
        assert [item.logical_name for item in selection.references] == names
