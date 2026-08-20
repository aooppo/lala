from __future__ import annotations

from lala_workflow.characters.service import CharacterService
from lala_workflow.config import load_project_config
from lala_workflow.hashing import sha256_file


def test_lala_v1_seed_points_to_exact_legacy_bytes_without_scene(project_root) -> None:
    service = CharacterService(project_root)
    profile = service.show("lala-v1").profile
    manifest = load_project_config(project_root).manifest
    assert set(profile.references) == {"face", "full_body"}
    for name, reference in profile.references.items():
        assert reference.path == manifest.anchors[name].path
        assert reference.sha256 == manifest.anchors[name].sha256
        assert sha256_file(project_root / reference.path) == reference.sha256
    assert "scene" not in profile.references
