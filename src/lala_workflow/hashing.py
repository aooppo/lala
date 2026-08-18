from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


SUPPORTED_IMAGE_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


@dataclass(frozen=True, slots=True)
class ImageInfo:
    width: int
    height: int
    mime_type: str
    image_format: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_image(path: Path) -> ImageInfo:
    if not path.is_file():
        raise ValueError(f"image file does not exist: {path}")
    try:
        with Image.open(path) as image:
            image_format = (image.format or "").upper()
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"invalid or unsupported image: {path}") from exc
    if image_format not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(f"unsupported image format {image_format or 'unknown'}: {path}")
    if width <= 0 or height <= 0:
        raise ValueError(f"image has invalid dimensions: {path}")
    return ImageInfo(width, height, SUPPORTED_IMAGE_FORMATS[image_format], image_format)


def assert_within_directory(path: Path, directory: Path) -> Path:
    resolved_path = path.resolve(strict=False)
    resolved_directory = directory.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_directory)
    except ValueError as exc:
        raise ValueError(f"path is outside approved directory: {path}") from exc
    return resolved_path


def encoded_data_uri_length(path: Path, mime_type: str) -> int:
    encoded_length = ((path.stat().st_size + 2) // 3) * 4
    return len(f"data:{mime_type};base64,") + encoded_length


def file_to_data_uri(path: Path, mime_type: str, max_chars: int) -> str:
    expected = encoded_data_uri_length(path, mime_type)
    if expected > max_chars:
        raise ValueError(
            f"encoded reference exceeds provider data URI limit ({expected} > {max_chars}): {path}"
        )
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"
