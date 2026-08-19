from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

from PIL import Image

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
    video_codec: str | None = None
    pixel_format: str | None = None
    average_frame_rate: str | None = None
    audio_stream_present: bool = False
    audio_codec: str | None = None
    sample_rate: int | None = None
    channel_count: int | None = None
    bit_rate: int | None = None

    @property
    def container(self) -> str:
        return self.format_name

    def as_dict(self) -> dict[str, Any]:
        return {
            "container": self.format_name,
            "duration": self.duration_seconds,
            "width": self.width,
            "height": self.height,
            "video_codec": self.video_codec,
            "pixel_format": self.pixel_format,
            "average_frame_rate": self.average_frame_rate,
            "audio_stream_present": self.audio_stream_present,
            "audio_codec": self.audio_codec,
            "sample_rate": self.sample_rate,
            "channel_count": self.channel_count,
            "bit_rate": self.bit_rate,
        }


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
                (
                    "format=format_name,duration,bit_rate:"
                    "stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate,"
                    "sample_rate,channels,bit_rate"
                ),
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
    audio_streams = [
        item for item in payload.get("streams", []) if item.get("codec_type") == "audio"
    ]
    audio = audio_streams[0] if audio_streams else {}
    width = _optional_int(stream.get("width")) or 0
    height = _optional_int(stream.get("height")) or 0
    try:
        duration = float(payload.get("format", {}).get("duration") or 0)
    except (TypeError, ValueError) as exc:
        raise VideoDownloadError(f"video output has invalid duration: {path.name}") from exc
    format_name = str(payload.get("format", {}).get("format_name") or "")
    if width <= 0 or height <= 0 or duration <= 0:
        raise VideoDownloadError(f"video output has invalid dimensions or duration: {path.name}")
    if "mp4" not in format_name and "mov" not in format_name:
        raise VideoDownloadError(f"video output is not an MP4-compatible container: {path.name}")
    return VideoInfo(
        duration,
        width,
        height,
        format_name,
        video_codec=_optional_text(stream.get("codec_name")),
        pixel_format=_optional_text(stream.get("pix_fmt")),
        average_frame_rate=_optional_text(stream.get("avg_frame_rate")),
        audio_stream_present=bool(audio_streams),
        audio_codec=_optional_text(audio.get("codec_name")),
        sample_rate=_optional_int(audio.get("sample_rate")),
        channel_count=_optional_int(audio.get("channels")),
        bit_rate=(
            _optional_int(payload.get("format", {}).get("bit_rate"))
            or _optional_int(stream.get("bit_rate"))
        ),
    )


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
            try:
                # Link-then-unlink is collision-safe: unlike os.replace it can
                # never overwrite a target created after the initial check.
                os.link(temporary, target)
            except FileExistsError as exc:
                raise VideoDownloadError(f"video output target already exists: {target}") from exc
            finally:
                temporary.unlink(missing_ok=True)
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
                container=info.container,
                video_codec=info.video_codec,
                pixel_format=info.pixel_format,
                average_frame_rate=info.average_frame_rate,
                audio_stream_present=info.audio_stream_present,
                audio_codec=info.audio_codec,
                sample_rate=info.sample_rate,
                channel_count=info.channel_count,
                bit_rate=info.bit_rate,
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
        container=info.container,
        video_codec=info.video_codec,
        pixel_format=info.pixel_format,
        average_frame_rate=info.average_frame_rate,
        audio_stream_present=info.audio_stream_present,
        audio_codec=info.audio_codec,
        sample_rate=info.sample_rate,
        channel_count=info.channel_count,
        bit_rate=info.bit_rate,
        provenance=artifact.provenance,
    )


def generate_video_evidence(
    path: Path,
    output_dir: Path,
    *,
    prefix: str,
    ffmpeg: str = "ffmpeg",
    runner: CommandRunner = subprocess.run,
    timeout_seconds: float = 60,
) -> dict[str, Any]:
    """Create non-overwriting first/middle/last frames and a deterministic contact sheet."""

    info = inspect_video(path, runner=runner, timeout_seconds=min(timeout_seconds, 30))
    if not prefix or Path(prefix).name != prefix:
        raise VideoDownloadError("video evidence prefix must be a single safe filename component")
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        "first": output_dir / f"{prefix}-first.png",
        "middle": output_dir / f"{prefix}-middle.png",
        "last": output_dir / f"{prefix}-last.png",
    }
    contact = output_dir / f"{prefix}-contact-sheet.png"
    for target in (*targets.values(), contact):
        if target.exists():
            raise VideoDownloadError(f"video evidence output already exists: {target}")
    positions = {
        "first": 0.0,
        "middle": info.duration_seconds / 2.0,
        # Leave enough decode headroom for CFR/VFR sources whose reported
        # container duration extends slightly beyond their final coded frame.
        "last": max(0.0, info.duration_seconds - min(0.5, info.duration_seconds / 4)),
    }
    created: list[Path] = []
    commands: list[list[str]] = []
    try:
        for label, target in targets.items():
            command = [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{positions[label]:.6f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-n",
                str(target),
            ]
            commands.append(command)
            runner(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            if not target.is_file() or target.stat().st_size == 0:
                raise VideoDownloadError(f"FFmpeg did not create {label} frame")
            created.append(target)
        _write_contact_sheet(tuple(targets.values()), contact)
        created.append(contact)
    except (OSError, subprocess.SubprocessError, VideoDownloadError) as exc:
        for target in created:
            target.unlink(missing_ok=True)
        for target in targets.values():
            target.unlink(missing_ok=True)
        contact.unlink(missing_ok=True)
        if isinstance(exc, VideoDownloadError):
            raise
        raise VideoDownloadError("could not generate video frame evidence") from exc
    return {
        "media": info.as_dict(),
        "frames": {
            label: {"path": target, "sha256": sha256_file(target), "at_seconds": positions[label]}
            for label, target in targets.items()
        },
        "contact_sheet": {"path": contact, "sha256": sha256_file(contact)},
        "commands": commands,
    }


def redacted_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _default_downloader(url: str, destination: Path, timeout_seconds: float) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "lady-lala-workflow/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        with destination.open("xb") as output:
            shutil.copyfileobj(response, output)


def _write_contact_sheet(frames: tuple[Path, ...], target: Path) -> None:
    images: list[Image.Image] = []
    try:
        for frame in frames:
            with Image.open(frame) as source:
                images.append(source.convert("RGB"))
        if not images:
            raise VideoDownloadError("contact sheet requires at least one frame")
        width = max(image.width for image in images)
        height = max(image.height for image in images)
        sheet = Image.new("RGB", (width * len(images), height), "black")
        for index, image in enumerate(images):
            sheet.paste(image, (index * width, 0))
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            sheet.save(temporary, format="PNG", optimize=False)
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
            sheet.close()
    finally:
        for image in images:
            image.close()


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value not in {None, "", "N/A"} else None
    except (TypeError, ValueError):
        return None


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
