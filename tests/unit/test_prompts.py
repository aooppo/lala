from pathlib import Path

import pytest

from lala_workflow.prompts import PromptError, load_prompt, prompt_version


ROOT = Path(__file__).resolve().parents[2]


def test_prompt_loads_version_hash_and_tags() -> None:
    prompt = load_prompt(
        ROOT,
        Path("prompts/baseline-identity-v1.txt"),
        selected_tags={"lala_face", "lala_look"},
        max_utf16_units=1000,
    )

    assert prompt.version == "v1"
    assert prompt.sha256 and len(prompt.sha256) == 64
    assert prompt.referenced_tags == ("lala_face", "lala_look")


def test_prompt_version_requires_versioned_filename() -> None:
    with pytest.raises(PromptError, match="versioned"):
        prompt_version("baseline.txt")


def test_prompt_rejects_unselected_tag(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "bad-v1.txt").write_text("Use @unknown_tag", encoding="utf-8")

    with pytest.raises(PromptError, match="not selected"):
        load_prompt(
            tmp_path,
            Path("prompts/bad-v1.txt"),
            selected_tags={"lala_face"},
            max_utf16_units=1000,
        )


def test_prompt_length_uses_utf16_code_units(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "emoji-v1.txt").write_text("😀😀", encoding="utf-8")

    with pytest.raises(PromptError, match="UTF-16"):
        load_prompt(
            tmp_path,
            Path("prompts/emoji-v1.txt"),
            selected_tags=set(),
            max_utf16_units=3,
        )
