from __future__ import annotations

import shutil

from PIL import Image

from lala_workflow.characters.domain import CharacterStatus
from lala_workflow.characters.preview import GeneratedPreview
from lala_workflow.characters.service import CharacterService


class Static:
    def generate(self, profile, build, destination):
        Image.new("RGB", (96, 144), "orange").save(destination)
        return GeneratedPreview(destination, provenance={"fake": True})


class Motion:
    def __init__(self, source):
        self.source = source

    def generate(self, profile, build, static_preview, destination):
        shutil.copyfile(self.source, destination)
        return GeneratedPreview(destination, provenance={"fake": True})


def test_full_mocked_lifecycle_has_one_final_switch(project_root, character_uploads, synthetic_video) -> None:
    service = CharacterService(
        project_root,
        static_preview_operation=Static(),
        motion_preview_operation=Motion(synthetic_video),
    )
    profile = service.import_character(character_uploads, display_name="Candidate", created_by="test")
    assert service.list_characters().active_character == "lala-v1"
    assert service.build(profile.character_id).status is CharacterStatus.READY_FOR_GENERATION
    assert service.preview(profile.character_id, live=True).status is CharacterStatus.READY_FOR_APPROVAL
    assert service.list_characters().active_character == "lala-v1"
    service.approve_and_activate(profile.character_id)
    assert service.list_characters().active_character == profile.character_id
