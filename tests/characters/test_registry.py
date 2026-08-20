from __future__ import annotations

from dataclasses import replace

import pytest

from lala_workflow.characters.domain import CharacterStatus
from lala_workflow.characters.errors import CharacterIntegrityError, RegistryConflictError
from lala_workflow.characters.registry import CharacterRegistryStore
from lala_workflow.characters.service import CharacterService


def test_seed_loads_and_matches_profiles(project_root) -> None:
    registry = CharacterRegistryStore(project_root).load()
    assert registry.active_character == "lala-v1"
    assert registry.revision == 0
    assert sum(entry.status is CharacterStatus.ACTIVE for entry in registry.characters.values()) == 1


def test_stale_revision_and_failure_do_not_replace_registry(project_root, monkeypatch) -> None:
    store = CharacterRegistryStore(project_root)
    before = store.registry_path.read_bytes()
    with pytest.raises(RegistryConflictError):
        store.mutate(lambda item: replace(item, revision=item.revision + 1), expected_revision=9)
    assert store.registry_path.read_bytes() == before

    def fail(_registry):
        raise OSError("simulated write failure")

    monkeypatch.setattr(store, "_write_unlocked", fail)
    with pytest.raises(OSError):
        store.mutate(lambda item: replace(item, revision=item.revision + 1))
    assert store.registry_path.read_bytes() == before


def test_invalid_profile_is_rejected_before_registry_replace(project_root, monkeypatch) -> None:
    store = CharacterRegistryStore(project_root)
    before = store.registry_path.read_bytes()
    current = store.load()
    broken = replace(
        current,
        revision=current.revision + 1,
        characters={
            "lala-v1": replace(current.characters["lala-v1"], profile_sha256="b" * 64)
        },
    )
    with pytest.raises(CharacterIntegrityError):
        store.mutate(lambda _item: broken)
    assert store.registry_path.read_bytes() == before
