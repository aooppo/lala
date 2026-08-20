from __future__ import annotations

import pytest

from lala_workflow.characters.errors import CharacterStateError
from lala_workflow.characters.resolver import CharacterResolver
from lala_workflow.characters.service import CharacterService


def test_resolver_explicit_active_legacy_and_staging_rules(project_root, character_uploads) -> None:
    service = CharacterService(project_root)
    resolver = CharacterResolver(project_root)
    active = resolver.resolve()
    assert active.profile.character_id == "lala-v1"
    assert active.selection_source == "active_registry"
    candidate = service.import_character(character_uploads, created_by="test")
    service.build(candidate.character_id)
    with pytest.raises(CharacterStateError, match="active"):
        resolver.resolve(candidate.character_id)
    staging = resolver.resolve(candidate.character_id, allow_staging=True)
    assert staging.profile.character_id == candidate.character_id
    assert staging.manifest.status == "staging"
    with pytest.raises(CharacterStateError):
        resolver.resolve("character-20260820-999", allow_staging=True)


def test_missing_registry_uses_legacy_fallback(project_root) -> None:
    (project_root / "configs/characters/registry.yaml").unlink()
    resolved = CharacterResolver(project_root).resolve()
    assert resolved.profile.character_id == "lala-v1"
    assert resolved.selection_source == "legacy_fallback"
