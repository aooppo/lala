from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit, urlunsplit

from ..hashing import sha256_file
from .domain import MediaArtifact


class VideoDownloadError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VideoInfo:
    duration_seconds: float
    width: int
    height: int
    format_name: str


Downloader = Callable[[str, Path, float], None]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def inspect_video(
    path: Path,
    *,
    ffprobe: str = "ffprobe",
    runner: CommandRunner = subprocess.run,
    timeout_seconds: float = 30,
) -> VideoInfo:
    if not path.is_file() or path.stat().st_size == 0:
        raise VideoDownloadError(f"video output is missing or empty: {path}")
    try:
        completed = runner(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=format_name,duration:stream=codec_type,width,height",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        payload = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise VideoDownloadError(f"FFprobe could not validate video output: {path.name}") from exc
    video_streams = [
        stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"
    ]
    if not video_streams:
        raise VideoDownloadError(f"video output has no video stream: {path.name}")
    stream = video_streams[0]
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    try:
        duration = float(payload.get("format", {}).get("duration") or 0)
    except (TypeError, ValueError) as exc:
        raise VideoDownloadError(f"video output has invalid duration: {path.name}") from exc
    format_name = str(payload.get("format", {}).get("format_name") or "")
    if width <= 0 or height <= 0 or duration <= 0:
        raise VideoDownloadError(f"video output has invalid dimensions or duration: {path.name}")
    if "mp4" not in format_name and "mov" not in format_name:
        raise VideoDownloadError(f"video output is not an MP4-compatible container: {path.name}")
    return VideoInfo(duration, width, height, format_name)


def download_video(
    url: str,
    target: Path,
    *,
    provider_task_id: str,
    artifact_id: str,
    kind: str,
    timeout_seconds: float,
    max_retries: int,
    downloader: Downloader | None = None,
) -> MediaArtifact:
    if target.exists():
        raise VideoDownloadError(f"video output target already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    retrieve = downloader or _default_downloader
    last_error: Exception | None = None
    for _attempt in range(max_retries + 1):
        temporary = target.with_name(f".{target.stem}.{uuid.uuid4().hex}.part.mp4")
        try:
            retrieve(url, temporary, timeout_seconds)
            info = inspect_video(temporary, timeout_seconds=min(timeout_seconds, 30))
            os.replace(temporary, target)
            return MediaArtifact(
                artifact_id=artifact_id,
                kind=kind,
                path=target,
                sha256=sha256_file(target),
                size_bytes=target.stat().st_size,
                mime_type="video/mp4",
                duration_seconds=info.duration_seconds,
                width=info.width,
                height=info.height,
                provider_task_id=provider_task_id,
                source_url_redacted=redacted_url(url),
            )
        except Exception as exc:
            last_error = exc
            temporary.unlink(missing_ok=True)
    raise VideoDownloadError(str(last_error or "video download failed"))


def validate_media_artifact(artifact: MediaArtifact) -> MediaArtifact:
    info = inspect_video(artifact.path)
    actual = sha256_file(artifact.path)
    if actual != artifact.sha256:
        raise VideoDownloadError(f"downloaded video digest mismatch: {artifact.artifact_id}")
    if artifact.mime_type != "video/mp4":
        raise VideoDownloadError(f"downloaded video MIME must be video/mp4: {artifact.artifact_id}")
    return MediaArtifact(
        artifact_id=artifact.artifact_id,
        kind=artifact.kind,
        path=artifact.path,
        sha256=actual,
        size_bytes=artifact.path.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=info.duration_seconds,
        width=info.width,
        height=info.height,
        provider_task_id=artifact.provider_task_id,
        source_url_redacted=artifact.source_url_redacted,
        provenance=artifact.provenance,
    )


def redacted_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _default_downloader(url: str, destination: Path, timeout_seconds: float) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "lady-lala-workflow/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        with destination.open("xb") as output:
            shutil.copyfileobj(response, output)
