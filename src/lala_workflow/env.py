from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Mapping, MutableMapping

from dotenv import dotenv_values, load_dotenv


ENV_NAMES = (
    "HEYGEN_API_KEY",
    "HEYGEN_VOICE_ID",
    "RUNWAYML_API_SECRET",
    "VIDEO_ALLOW_LIVE_CALLS",
    "VIDEO_LIVE_SMOKE_TEST",
    "VIDEO_MOTION_LIVE_SMOKE_TEST",
    "VIDEO_FULL_PILOT_LIVE",
)

_ENV_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


class EnvironmentConfigError(ValueError):
    pass


def load_project_env(
    project_root: Path,
    *,
    environ: MutableMapping[str, str] | None = None,
    enabled: bool | None = None,
) -> Mapping[str, Mapping[str, int | str]]:
    """Load only the project-root .env without overriding process values.

    Automated pytest processes skip the developer file by default. Tests that exercise this
    function pass ``enabled=True`` with an isolated project root.
    """

    target = os.environ if environ is None else environ
    if enabled is None:
        enabled = not (
            "PYTEST_CURRENT_TEST" in target
            or "pytest" in sys.modules
            or str(target.get("LALA_DISABLE_DOTENV") or "").lower() == "true"
        )
    path = project_root.resolve() / ".env"
    if enabled and path.is_file():
        if environ is None:
            load_dotenv(dotenv_path=path, override=False)
        else:
            for name, value in dotenv_values(path).items():
                if value is not None:
                    target.setdefault(name, value)
    return environment_status(target)


def environment_status(environ: Mapping[str, str]) -> Mapping[str, Mapping[str, int | str]]:
    return {
        name: {
            "status": "configured" if str(environ.get(name) or "") else "missing",
            "length": len(str(environ.get(name) or "")),
        }
        for name in ENV_NAMES
    }


def require_canonical_voice_env(environ: Mapping[str, str]) -> str:
    canonical = str(environ.get("HEYGEN_VOICE_ID") or "").strip()
    if canonical:
        return canonical
    if str(environ.get("voice_id") or "").strip():
        raise EnvironmentConfigError(
            "legacy voice_id is configured; run `python -m lala_workflow video voice init-env` "
            "to migrate it explicitly to HEYGEN_VOICE_ID"
        )
    raise EnvironmentConfigError("HEYGEN_VOICE_ID is missing")


def migrate_legacy_voice_env(project_root: Path) -> Mapping[str, str]:
    """Copy a legacy lowercase voice_id entry to the canonical name without exposing its value."""

    path = project_root.resolve() / ".env"
    if not path.is_file():
        raise EnvironmentConfigError("project environment file is missing")
    raw = path.read_text(encoding="utf-8")
    names = {
        match.group(1)
        for line in raw.splitlines()
        if (match := _ENV_LINE_RE.match(line)) is not None
    }
    parsed = dotenv_values(path)
    if "HEYGEN_VOICE_ID" in names:
        raise EnvironmentConfigError("HEYGEN_VOICE_ID is already configured")
    legacy = str(parsed.get("voice_id") or "").strip()
    if not legacy:
        raise EnvironmentConfigError("legacy voice_id is missing")
    separator = "" if raw.endswith("\n") or not raw else "\n"
    with path.open("a", encoding="utf-8", newline="") as output:
        output.write(f"{separator}HEYGEN_VOICE_ID={legacy}\n")
    return {"status": "migrated", "variable": "HEYGEN_VOICE_ID"}
