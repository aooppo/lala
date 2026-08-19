from __future__ import annotations

import struct
import wave
from dataclasses import dataclass
from pathlib import Path

from ..hashing import assert_within_directory, sha256_file


class AudioValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AudioInfo:
    duration_seconds: float
    sample_rate: int
    channels: int
    sample_width: int
    frame_count: int
    sha256: str


def inspect_wav(path: Path) -> AudioInfo:
    if not path.is_file() or path.stat().st_size == 0:
        raise AudioValidationError(f"approved WAV is missing or empty: {path}")
    try:
        with wave.open(str(path), "rb") as source:
            if source.getcomptype() != "NONE":
                raise AudioValidationError("approved WAV must use uncompressed PCM")
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frame_count = source.getnframes()
            frames = source.readframes(frame_count)
    except (wave.Error, EOFError) as exc:
        raise AudioValidationError(f"invalid WAV content: {path}") from exc
    if channels < 1 or sample_rate < 1 or frame_count < 1 or not frames:
        raise AudioValidationError("approved WAV has no playable audio frames")
    if _is_silent_pcm(frames, sample_width):
        raise AudioValidationError("approved WAV is silent")
    return AudioInfo(
        duration_seconds=frame_count / sample_rate,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        frame_count=frame_count,
        sha256=sha256_file(path),
    )


def validate_approved_wav(path: Path, approved_root: Path) -> AudioInfo:
    try:
        resolved = assert_within_directory(path, approved_root)
    except ValueError as exc:
        raise AudioValidationError("approved audio must remain under assets/voice/approved") from exc
    if resolved.suffix.lower() != ".wav":
        raise AudioValidationError("approved audio must be a WAV file")
    return inspect_wav(resolved)


def _is_silent_pcm(data: bytes, sample_width: int) -> bool:
    if sample_width == 1:
        return all(value == 128 for value in data)
    if sample_width == 2:
        usable = len(data) - len(data) % 2
        return not any(value for (value,) in struct.iter_unpack("<h", data[:usable]))
    if sample_width == 4:
        usable = len(data) - len(data) % 4
        return not any(value for (value,) in struct.iter_unpack("<i", data[:usable]))
    return not any(data)
