from __future__ import annotations

import io

import pytest
from PIL import Image

from lala_workflow.characters.domain import CharacterUpload


def _image_bytes(color: str, *, image_format: str = "PNG", size=(40, 60)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format=image_format)
    return output.getvalue()


@pytest.fixture
def character_uploads():
    return {
        "face": CharacterUpload("face", _image_bytes("red"), "../front.png", "image/png"),
        "full_body": CharacterUpload("full_body", _image_bytes("green"), "body.png", "image/png"),
        "three_quarter": CharacterUpload(
            "three_quarter", _image_bytes("blue"), "three-quarter.png", "image/png"
        ),
    }
