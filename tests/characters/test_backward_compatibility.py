from __future__ import annotations

import json

from lala_workflow.runner import RunOptions, run_generation
from lala_workflow.video.runner import validate_video_project


def test_missing_registry_preserves_legacy_static_request(project_root) -> None:
    (project_root / "configs/characters/registry.yaml").unlink()
    outcome = run_generation(project_root, RunOptions(preset="home_decor", count=1))
    request = json.loads((outcome.run_dir / "request.json").read_text())["requests"][0]
    assert request["character_id"] is None
    assert [(item["name"], item["tag"]) for item in request["references"]] == [
        ("face", "lala_face"),
        ("full_body", "lala_look"),
        ("scene", "lala_scene"),
    ]
    assert len(list(outcome.run_dir.iterdir())) == 8


def test_character_install_does_not_change_video_validation_blocker(project_root) -> None:
    # Goal 2 authoritative inputs are intentionally absent from this fixture.
    try:
        validate_video_project(project_root)
    except Exception as exc:
        assert "character" not in str(exc).lower()
