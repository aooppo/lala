from __future__ import annotations

import re
from pathlib import Path

from ..hashing import assert_within_directory, sha256_file
from .domain import ResolvedPrompt


VERSION_RE = re.compile(r"-v([1-9][0-9]*)\.txt$")


class VideoPromptError(ValueError):
    pass


def utf16_code_units(text: str) -> int:
    """Return the length used by provider APIs that count UTF-16 units."""

    return len(text.encode("utf-16-le")) // 2


def load_video_prompt(project_root: Path, relative_path: Path) -> ResolvedPrompt:
    if relative_path.is_absolute() or not relative_path.as_posix():
        raise VideoPromptError("video prompt path must be project-relative")
    try:
        path = assert_within_directory(
            project_root / relative_path, project_root / "prompts"
        )
    except ValueError as exc:
        raise VideoPromptError("video prompt must remain under prompts") from exc
    match = VERSION_RE.search(path.name)
    if not match:
        raise VideoPromptError(f"video prompt filename must be versioned: {path.name}")
    if not path.is_file():
        raise VideoPromptError(f"video prompt does not exist: {relative_path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise VideoPromptError(f"video prompt is empty: {relative_path}")
    return ResolvedPrompt(
        path=path.relative_to(project_root.resolve()),
        version=f"v{match.group(1)}",
        text=text,
        sha256=sha256_file(path),
    )
