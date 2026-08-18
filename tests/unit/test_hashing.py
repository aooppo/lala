import hashlib
from pathlib import Path

import pytest
from PIL import Image

from lala_workflow.hashing import (
    assert_within_directory,
    encoded_data_uri_length,
    inspect_image,
    sha256_file,
)


def test_sha256_file_hashes_exact_bytes(tmp_path: Path) -> None:
    path = tmp_path / "value.bin"
    path.write_bytes(b"lady-lala")

    assert sha256_file(path) == hashlib.sha256(b"lady-lala").hexdigest()


def test_inspect_image_returns_verified_dimensions_and_mime(tmp_path: Path) -> None:
    path = tmp_path / "anchor.png"
    Image.new("RGB", (16, 24), "red").save(path)

    info = inspect_image(path)

    assert (info.width, info.height) == (16, 24)
    assert info.mime_type == "image/png"


def test_approved_path_rejects_escape(tmp_path: Path) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"x")

    with pytest.raises(ValueError, match="outside approved directory"):
        assert_within_directory(outside, approved)


def test_encoded_data_uri_length_includes_prefix_and_base64(tmp_path: Path) -> None:
    path = tmp_path / "small.png"
    path.write_bytes(b"1234")

    assert encoded_data_uri_length(path, "image/png") == len("data:image/png;base64,MTIzNA==")
