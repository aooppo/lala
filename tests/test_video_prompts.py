from __future__ import annotations

from pathlib import Path

import pytest

from lala_workflow.video.prompts import VideoPromptError, load_video_prompt


def test_prompt_digest_changes_with_exact_bytes(video_project_root: Path) -> None:
    relative = Path("prompts/home-broll-v1.txt")
    first = load_video_prompt(video_project_root, relative)
    path = video_project_root / relative
    path.write_bytes(path.read_bytes() + b"\n")
    second = load_video_prompt(video_project_root, relative)
    assert first.version == second.version == "v1"
    assert first.sha256 != second.sha256


def test_prompt_must_be_versioned_and_contained(video_project_root: Path) -> None:
    path = video_project_root / "prompts/unversioned.txt"
    path.write_text("motion", encoding="utf-8")
    with pytest.raises(VideoPromptError, match="versioned"):
        load_video_prompt(video_project_root, Path("prompts/unversioned.txt"))
    with pytest.raises(VideoPromptError, match="prompts"):
        load_video_prompt(video_project_root, Path("configs/providers.yaml"))
