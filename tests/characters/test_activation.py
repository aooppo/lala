from __future__ import annotations

import shutil

import pytest
from PIL import Image

from lala_workflow.characters.domain import CharacterStatus
from lala_workflow.characters.errors import CharacterStateError, RegistryConflictError
from lala_workflow.characters.preview import GeneratedPreview
from lala_workflow.characters.service import CharacterService


class StaticOperation:
    def generate(self, profile, build, destination):
        Image.new("RGB", (128, 192), "purple").save(destination)
        return GeneratedPreview(destination, source_run_id="static-fixture")


class MotionOperation:
    def __init__(self, video):
        self.video = video

    def generate(self, profile, build, static_preview, destination):
        shutil.copyfile(self.video, destination)
        return GeneratedPreview(destination, source_run_id="motion-fixture")


def _ready_service(project_root, uploads, video):
    service = CharacterService(
        project_root,
        static_preview_operation=StaticOperation(),
        motion_preview_operation=MotionOperation(video),
    )
    profile = service.import_character(uploads, created_by="test")
    service.build(profile.character_id)
    service.preview(profile.character_id, live=True)
    return service, profile.character_id


def test_activation_requires_previews_and_promotes_exact_bytes(project_root, character_uploads, synthetic_video) -> None:
    plain = CharacterService(project_root)
    candidate = plain.import_character(character_uploads, created_by="test")
    plain.build(candidate.character_id)
    with pytest.raises(CharacterStateError, match="not ready"):
        plain.approve_and_activate(candidate.character_id)

    # Use a fresh project state with operations wired into the same service.
    service = CharacterService(
        project_root,
        static_preview_operation=StaticOperation(),
        motion_preview_operation=MotionOperation(synthetic_video),
    )
    service.preview(candidate.character_id, live=True)
    source = service.show(candidate.character_id).profile
    expected = {name: (project_root / ref.path).read_bytes() for name, ref in source.references.items()}
    event = service.approve_and_activate(candidate.character_id)
    registry = service.list_characters()
    active = service.show(candidate.character_id).profile
    assert event["previous_active_character"] == "lala-v1"
    assert registry.active_character == candidate.character_id
    assert sum(item.status is CharacterStatus.ACTIVE for item in registry.characters.values()) == 1
    assert all("assets/approved_anchors/characters" in ref.path.as_posix() for ref in active.references.values())
    assert {name: (project_root / ref.path).read_bytes() for name, ref in active.references.items()} == expected


def test_reject_and_reactivate_legacy(project_root, character_uploads, synthetic_video) -> None:
    service, candidate_id = _ready_service(project_root, character_uploads, synthetic_video)
    service.approve_and_activate(candidate_id)
    rollback = service.approve_and_activate("lala-v1")
    assert rollback["type"] == "reactivated"
    assert service.list_characters().active_character == "lala-v1"

def test_reject_retains_evidence_and_active(project_root, character_uploads) -> None:
    service = CharacterService(project_root)
    candidate = service.import_character(character_uploads, created_by="test")
    build = service.build(candidate.character_id)
    latest = project_root / "outputs/characters" / candidate.character_id / "build/latest.json"
    before = latest.read_bytes()
    rejected = service.reject(candidate.character_id)
    assert rejected.status is CharacterStatus.REJECTED
    assert service.list_characters().active_character == "lala-v1"
    assert latest.read_bytes() == before


def test_stale_session_and_registry_write_failure_preserve_active(
    project_root, character_uploads, synthetic_video, monkeypatch
) -> None:
    service, candidate_id = _ready_service(project_root, character_uploads, synthetic_video)
    current = service.list_characters()
    with pytest.raises(RegistryConflictError):
        service.approve_and_activate(candidate_id, expected_revision=current.revision - 1)
    assert service.list_characters().active_character == "lala-v1"
    before = service.registry.registry_path.read_bytes()
    monkeypatch.setattr(
        service.registry,
        "_write_unlocked",
        lambda _registry: (_ for _ in ()).throw(OSError("simulated write failure")),
    )
    with pytest.raises(OSError):
        service.approve_and_activate(candidate_id)
    assert service.registry.registry_path.read_bytes() == before
