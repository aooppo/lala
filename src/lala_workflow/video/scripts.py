from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from ..hashing import assert_within_directory, sha256_file
from .domain import ScriptRecord


HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class ScriptIntegrityError(ValueError):
    pass


def load_script_record(
    script_id: str,
    raw: Mapping[str, Any],
    project_root: Path,
    *,
    source: str,
    modification_policy: str,
) -> ScriptRecord:
    if source != "MTL":
        raise ScriptIntegrityError("script source attribution must be MTL")
    if modification_policy != "immutable":
        raise ScriptIntegrityError("script modification policy must be immutable")
    version = str(raw.get("version") or "").strip()
    if not version:
        raise ScriptIntegrityError(f"script {script_id} version is required")
    source_reference = str(raw.get("source_reference") or "").strip()
    if not source_reference:
        raise ScriptIntegrityError(f"script {script_id} source_reference is required")
    expected = str(raw.get("sha256") or "").strip().lower()
    if not HASH_RE.fullmatch(expected):
        raise ScriptIntegrityError(f"script {script_id} sha256 must be 64 lowercase hex characters")
    relative = Path(str(raw.get("path") or ""))
    if relative.is_absolute() or not relative.as_posix():
        raise ScriptIntegrityError(f"script {script_id} path must be project-relative")
    try:
        resolved = assert_within_directory(
            project_root / relative, project_root / "assets/scripts"
        )
    except ValueError as exc:
        raise ScriptIntegrityError(
            f"script {script_id} must remain under assets/scripts"
        ) from exc
    if not resolved.is_file():
        raise ScriptIntegrityError(f"script {script_id} file does not exist: {relative}")
    content = resolved.read_bytes()
    if not content:
        raise ScriptIntegrityError(f"script {script_id} is empty")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ScriptIntegrityError(f"script {script_id} must be valid UTF-8") from exc
    actual = sha256_file(resolved)
    if actual != expected:
        raise ScriptIntegrityError(
            f"script {script_id} digest mismatch: expected {expected}, got {actual}"
        )
    return ScriptRecord(
        script_id=script_id,
        path=resolved.relative_to(project_root.resolve()),
        version=version,
        sha256=actual,
        source=source,
        source_reference=source_reference,
        modification_policy=modification_policy,
        content=content,
    )


def capture_script(source: Path, destination: Path) -> Path:
    content = source.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as output:
        output.write(content)
        output.flush()
    return destination
