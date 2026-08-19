from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from ..hashing import sha256_file
from .config import VideoConfigError, load_video_config


def derive_talking_crop(project_root: Path, source_id: str) -> dict[str, Any]:
    """Create a deterministic, review-only 16:9 medium-closeup crop candidate."""

    config = load_video_config(project_root, require_inputs=False)
    source = config.keyframes.get(source_id)
    if source is None:
        raise VideoConfigError(f"approved source keyframe does not exist: {source_id}")
    source_path = config.root / source.path
    before = sha256_file(source_path)
    if before != source.sha256:
        raise VideoConfigError("approved source keyframe digest mismatch before crop")
    output_dir = config.root / "outputs/keyframes/derived"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _next_crop_path(output_dir, source_id)
    provenance_path = output_path.with_suffix(".json")
    try:
        with Image.open(source_path) as image:
            image.load()
            crop_box = _medium_closeup_box(image.width, image.height)
            candidate = image.convert("RGB").crop(crop_box).resize(
                (1280, 720), Image.Resampling.LANCZOS
            )
            temporary = output_path.with_name(
                f".{output_path.name}.{uuid.uuid4().hex}.tmp"
            )
            try:
                candidate.save(temporary, format="PNG", optimize=False)
                os.link(temporary, output_path)
            finally:
                temporary.unlink(missing_ok=True)
                candidate.close()
    except (OSError, ValueError) as exc:
        output_path.unlink(missing_ok=True)
        raise VideoConfigError("could not derive talking crop candidate") from exc
    after = sha256_file(source_path)
    if after != before:
        output_path.unlink(missing_ok=True)
        raise VideoConfigError("approved source changed during crop derivation")
    evidence = {
        "status": "DERIVED_CANDIDATE_NOT_APPROVED",
        "role": "talking_medium_closeup",
        "source_keyframe_id": source_id,
        "source_path": source.path.as_posix(),
        "source_sha256": before,
        "crop_box": {
            "left": crop_box[0],
            "top": crop_box[1],
            "right": crop_box[2],
            "bottom": crop_box[3],
        },
        "output_path": output_path.relative_to(config.root).as_posix(),
        "output_sha256": sha256_file(output_path),
        "output_width": 1280,
        "output_height": 720,
        "resampling": "Pillow LANCZOS",
        "auto_approved": False,
    }
    _write_json_new(provenance_path, evidence)
    return {**evidence, "provenance_path": provenance_path.relative_to(config.root).as_posix()}


def _medium_closeup_box(width: int, height: int) -> tuple[int, int, int, int]:
    if width <= 0 or height <= 0:
        raise VideoConfigError("source keyframe dimensions are invalid")
    crop_width = min(width, max(2, int(round(width * 0.70))))
    crop_height = min(height, max(2, int(round(crop_width * 9 / 16))))
    if crop_height > height:
        crop_height = height
        crop_width = min(width, int(round(crop_height * 16 / 9)))
    left = max(0, (width - crop_width) // 2)
    # Bias upward for head-and-torso framing without any identity inference.
    top = max(0, min(height - crop_height, int(round(height * 0.05))))
    return left, top, left + crop_width, top + crop_height


def _next_crop_path(directory: Path, source_id: str) -> Path:
    safe = re.sub(r"[^a-z0-9-]+", "-", source_id.lower().replace("_", "-")).strip("-")
    pattern = re.compile(
        rf"^{re.escape(safe)}-talking-medium-closeup-v([0-9]{{3}})\.png$"
    )
    versions = [
        int(match.group(1))
        for item in directory.iterdir()
        if (match := pattern.fullmatch(item.name))
    ]
    return directory / f"{safe}-talking-medium-closeup-v{max(versions, default=0) + 1:03d}.png"


def _write_json_new(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as output:
            json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
