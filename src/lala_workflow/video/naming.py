from __future__ import annotations

import re
from pathlib import Path


PRESETS = {"product_page", "tooltip", "homepage"}


def preset_slug(preset: str) -> str:
    if preset not in PRESETS:
        raise ValueError(f"unsupported video preset: {preset}")
    return preset.replace("_", "-")


def candidate_filename(preset: str, version: int) -> str:
    if version < 1:
        raise ValueError("candidate version must be positive")
    return f"lady-lala-{preset_slug(preset)}-candidate-v{version:03d}.mp4"


def approved_filename(preset: str, version: int) -> str:
    if version < 1:
        raise ValueError("approved version must be positive")
    return f"lady-lala-{preset_slug(preset)}-approved-v{version}.mp4"


def next_candidate_path(directory: Path, preset: str) -> Path:
    return _next_path(directory, preset, "candidate", width=3)


def next_approved_path(directory: Path, preset: str) -> Path:
    return _next_path(directory, preset, "approved", width=1)


def _next_path(directory: Path, preset: str, status: str, *, width: int) -> Path:
    slug = preset_slug(preset)
    pattern = re.compile(
        rf"^lady-lala-{re.escape(slug)}-{status}-v([0-9]+)\.mp4$"
    )
    versions = []
    if directory.exists():
        for item in directory.iterdir():
            match = pattern.fullmatch(item.name)
            if match:
                versions.append(int(match.group(1)))
    version = max(versions, default=0) + 1
    name = (
        candidate_filename(preset, version)
        if status == "candidate"
        else approved_filename(preset, version)
    )
    return directory / name
