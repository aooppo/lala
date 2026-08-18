from __future__ import annotations

import re
from pathlib import Path
from typing import AbstractSet

from .domain import PromptTemplate
from .hashing import assert_within_directory, sha256_file


TAG_RE = re.compile(r"@([A-Za-z][A-Za-z0-9_]*)")
VERSION_RE = re.compile(r"-(v[0-9]+(?:[._-][A-Za-z0-9]+)*)\.txt$")


class PromptError(ValueError):
    pass


def prompt_version(filename: str) -> str:
    match = VERSION_RE.search(filename)
    if not match:
        raise PromptError(f"prompt filename must be versioned with -vN.txt: {filename}")
    return match.group(1)


def utf16_code_units(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def referenced_tags(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(TAG_RE.findall(text)))


def load_prompt(
    project_root: Path,
    relative_path: Path,
    *,
    selected_tags: AbstractSet[str],
    max_utf16_units: int,
) -> PromptTemplate:
    prompt_root = project_root / "prompts"
    path = project_root / relative_path
    try:
        resolved = assert_within_directory(path, prompt_root)
    except ValueError as exc:
        raise PromptError(str(exc)) from exc
    if not resolved.is_file():
        raise PromptError(f"prompt file does not exist: {relative_path}")
    try:
        text = resolved.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError as exc:
        raise PromptError(f"prompt must be UTF-8: {relative_path}") from exc
    if not text:
        raise PromptError(f"prompt is empty: {relative_path}")
    units = utf16_code_units(text)
    if units > max_utf16_units:
        raise PromptError(
            f"prompt exceeds provider UTF-16 limit ({units} > {max_utf16_units}): {relative_path}"
        )
    tags = referenced_tags(text)
    missing = sorted(set(tags) - set(selected_tags))
    if missing:
        raise PromptError(f"prompt references tags not selected by preset: {', '.join(missing)}")
    relative = resolved.relative_to(project_root.resolve())
    return PromptTemplate(
        path=relative,
        filename=relative.name,
        version=prompt_version(relative.name),
        text=text,
        sha256=sha256_file(resolved),
        referenced_tags=tags,
    )
