from __future__ import annotations

from pathlib import Path

from PIL import Image

from lala_workflow.hashing import sha256_file
from lala_workflow.video.keyframes import derive_talking_crop


def test_talking_crop_is_derived_provenance_and_preserves_source(
    video_project_root: Path,
) -> None:
    source = video_project_root / "assets/approved_keyframes/hero.png"
    before = source.read_bytes()
    digest = sha256_file(source)

    evidence = derive_talking_crop(video_project_root, "hero")

    assert source.read_bytes() == before
    assert sha256_file(source) == digest == evidence["source_sha256"]
    output = video_project_root / evidence["output_path"]
    assert output.is_file()
    assert output.parent == video_project_root / "outputs/keyframes/derived"
    assert evidence["status"] == "DERIVED_CANDIDATE_NOT_APPROVED"
    assert evidence["auto_approved"] is False
    with Image.open(output) as image:
        assert image.size == (1280, 720)
