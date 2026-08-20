from __future__ import annotations

from pathlib import Path

import pytest

from lala_workflow.characters.domain import CharacterStatus
from lala_workflow.characters.errors import CharacterValidationError, RegistryConflictError
from lala_workflow.characters.service import CharacterService


def test_import_success_keeps_legacy_active_and_builds_offline(project_root, character_uploads) -> None:
    service = CharacterService(project_root)
    profile = service.import_character(character_uploads, display_name="Candidate", created_by="test")
    registry = service.list_characters()
    assert profile.character_id.startswith("character-")
    assert profile.status is CharacterStatus.DRAFT
    assert registry.active_character == "lala-v1"
    assert registry.characters[profile.character_id].status is CharacterStatus.DRAFT
    for item in profile.references.values():
        source = project_root / item.path
        assert source.read_bytes() == character_uploads[item.logical_name].content
        assert source.stat().st_mode & 0o222 == 0
    build = service.build(profile.character_id)
    assert build.status is CharacterStatus.READY_FOR_GENERATION
    assert service.list_characters().active_character == "lala-v1"


def test_import_missing_role_leaves_no_half_profile(project_root, character_uploads) -> None:
    service = CharacterService(project_root)
    incomplete = dict(character_uploads)
    incomplete.pop("three_quarter")
    before = service.list_characters()
    with pytest.raises(CharacterValidationError):
        service.import_character(incomplete, created_by="test")
    after = service.list_characters()
    assert after == before
    assert list((project_root / "assets/characters").glob("character-*")) == []


def test_identical_import_is_rejected_without_overwrite(project_root, character_uploads) -> None:
    service = CharacterService(project_root)
    first = service.import_character(character_uploads, created_by="test")
    source_bytes = {name: (project_root / ref.path).read_bytes() for name, ref in first.references.items()}
    with pytest.raises(RegistryConflictError, match="identical"):
        service.import_character(character_uploads, created_by="test")
    assert {name: (project_root / ref.path).read_bytes() for name, ref in first.references.items()} == source_bytes
    assert len(service.list_characters().characters) == 2


def test_profile_write_failure_never_registers_character(project_root, character_uploads, monkeypatch) -> None:
    service = CharacterService(project_root)
    before = service.list_characters()
    monkeypatch.setattr(service.storage, "write_profile", lambda _profile: (_ for _ in ()).throw(OSError("fail")))
    with pytest.raises(OSError):
        service.import_character(character_uploads, created_by="test")
    assert service.list_characters() == before
