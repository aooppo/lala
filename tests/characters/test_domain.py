from __future__ import annotations

from pathlib import Path

import pytest

from lala_workflow.characters.domain import (
    CharacterProfile,
    CharacterLifecycleEvent,
    CharacterReference,
    CharacterRegistry,
    CharacterRegistryEntry,
    CharacterStatus,
    profile_payload,
)
from lala_workflow.characters.errors import CharacterIntegrityError, CharacterStateError


def _reference(name: str) -> CharacterReference:
    return CharacterReference(
        logical_name=name,
        path=Path(f"assets/characters/character-20260820-001/source/{name}.png"),
        sha256={"face": "a" * 64, "full_body": "b" * 64, "three_quarter": "c" * 64}[name],
        role=f"role_{name}",
        tag={"face": "lala_face", "full_body": "lala_look", "three_quarter": "lala_3q"}[name],
        mime_type="image/png",
        width=10,
        height=20,
        size_bytes=100,
    )


def test_profile_hash_round_trip_and_transition() -> None:
    profile = CharacterProfile(
        character_id="character-20260820-001",
        display_name="候选人物",
        profile_version=1,
        status=CharacterStatus.DRAFT,
        created_at="2026-08-20T12:00:00+08:00",
        created_by="test",
        references={name: _reference(name) for name in ("face", "full_body", "three_quarter")},
    ).with_hash()
    loaded = CharacterProfile.from_dict(profile_payload(profile))
    assert loaded == profile
    building = profile.transition(CharacterStatus.BUILDING)
    assert building.profile_version == 2
    assert building.profile_sha256 != profile.profile_sha256
    with pytest.raises(CharacterStateError):
        profile.transition(CharacterStatus.ACTIVE)


def test_profile_rejects_unsafe_id_path_and_digest() -> None:
    with pytest.raises(CharacterIntegrityError):
        _reference("face").__class__(
            **{**profile_payload(_reference("face")), "path": Path("../../escape.png")}
        )
    with pytest.raises(CharacterIntegrityError):
        CharacterProfile(
            character_id="../../bad",
            display_name=None,
            profile_version=1,
            status=CharacterStatus.DRAFT,
            created_at="2026-08-20T12:00:00+08:00",
            created_by="test",
            references={name: _reference(name) for name in ("face", "full_body", "three_quarter")},
        )


def test_registry_requires_exactly_one_matching_active() -> None:
    entry = CharacterRegistryEntry(
        "lala-v1",
        "legacy",
        CharacterStatus.INACTIVE,
        Path("configs/characters/profiles/lala-v1-v001.yaml"),
        "a" * 64,
        "2026-08-20T12:00:00+08:00",
    )
    with pytest.raises(CharacterIntegrityError):
        CharacterRegistry(0, "lala-v1", None, {"lala-v1": entry})


def test_lifecycle_event_is_typed_and_serializable() -> None:
    event = CharacterLifecycleEvent(
        event_id="event-1",
        event_type="approved_and_activated",
        character_id="character-20260820-001",
        profile_sha256="a" * 64,
        previous_active_character="lala-v1",
        registry_revision=4,
        at="2026-08-20T12:00:00+08:00",
        actor="local_user",
    )
    assert event["type"] == "approved_and_activated"
    assert event["previous_active_character"] == "lala-v1"
