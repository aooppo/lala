from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from lala_workflow.characters.domain import CharacterUpload
from lala_workflow.characters.errors import CharacterIntegrityError, CharacterValidationError
from lala_workflow.characters.storage import CharacterStorage
from lala_workflow.characters.validation import validate_reference_file, validate_uploads


def test_required_roles_mime_decode_size_and_duplicate(character_uploads) -> None:
    missing = dict(character_uploads)
    missing.pop("face")
    with pytest.raises(CharacterValidationError, match="missing"):
        validate_uploads(missing)
    bad_mime = dict(character_uploads)
    original = bad_mime["face"]
    bad_mime["face"] = CharacterUpload("face", original.content, "face.png", "image/jpeg")
    with pytest.raises(CharacterValidationError, match="MIME"):
        validate_uploads(bad_mime)
    corrupt = dict(character_uploads)
    corrupt["face"] = CharacterUpload("face", b"not an image")
    with pytest.raises(CharacterValidationError, match="corrupt"):
        validate_uploads(corrupt)
    with pytest.raises(CharacterValidationError, match="exceeds"):
        validate_uploads(character_uploads, max_upload_bytes=4)
    duplicate = dict(character_uploads)
    duplicate["full_body"] = CharacterUpload("full_body", duplicate["face"].content)
    with pytest.raises(CharacterValidationError, match="duplicate"):
        validate_uploads(duplicate)


def test_canonical_copy_ignores_traversal_filename_and_rejects_symlink(project_root, character_uploads, tmp_path) -> None:
    storage = CharacterStorage(project_root)
    validated = validate_uploads(character_uploads)
    refs = storage.write_sources("character-20260820-001", validated)
    assert refs["face"].path.name == "face.png"
    assert not (project_root / "front.png").exists()
    validate_reference_file(project_root, refs["face"], allow_staging=True)
    source = project_root / refs["face"].path
    source.chmod(0o644)
    source.unlink()
    source.symlink_to(tmp_path / "outside.png")
    with pytest.raises(CharacterIntegrityError):
        validate_reference_file(project_root, refs["face"], allow_staging=True)


def test_decompression_bomb_warning_is_rejected(monkeypatch, character_uploads) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
    with pytest.raises(CharacterValidationError, match="decompression bomb"):
        validate_uploads(character_uploads)
