from __future__ import annotations

import pytest

from lala_workflow.video.runner import character_motion_preview_plan


def test_character_motion_preview_is_bounded_and_isolated(project_root, image_factory) -> None:
    static = image_factory(project_root / "outputs/characters/test/static.png")
    before = (project_root / "configs/keyframe-manifest.yaml").read_bytes()
    plan = character_motion_preview_plan(
        character_id="character-20260820-001",
        static_candidate=static,
    )
    assert plan["provider_tasks"] == 0
    assert plan["duration_seconds"] == 5
    assert plan["variations"] == 1
    assert "NOT_PRODUCTION_APPROVED" in plan["status"]
    assert (project_root / "configs/keyframe-manifest.yaml").read_bytes() == before
    with pytest.raises(ValueError):
        character_motion_preview_plan(
            character_id="character-20260820-001",
            static_candidate=static,
            variations=2,
        )
