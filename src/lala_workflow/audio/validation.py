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
        # Python 3.11's ``wave`` module does not understand the
        # WAVE_FORMAT_EXTENSIBLE container (format tag 65534), even when its
        # subtype is ordinary, uncompressed PCM.  The authoritative voice
        # clips use that container, so retain a small, read-only parser for
        # this standards-compliant case rather than transforming the source.
        try:
            return _inspect_extensible_pcm_wav(path)
        except (AudioValidationError, OSError, struct.error):
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


def _inspect_extensible_pcm_wav(path: Path) -> AudioInfo:
    """Inspect a WAVE_FORMAT_EXTENSIBLE file whose subtype is PCM.

    This is intentionally limited to little-endian RIFF/WAVE and PCM.  It
    does not attempt to decode arbitrary WAV codecs; those remain invalid for
    approved narration inputs just as they are when handled by ``wave``.
    """

    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise AudioValidationError("not a RIFF/WAVE file")

    fmt: bytes | None = None
    audio_data: bytes | None = None
    offset = 12
    while offset + 8 <= len(data):
        chunk_id = data[offset : offset + 4]
        chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
        chunk_start = offset + 8
        chunk_end = chunk_start + chunk_size
        if chunk_end > len(data):
            raise AudioValidationError("WAV chunk extends beyond file")
        if chunk_id == b"fmt " and fmt is None:
            fmt = data[chunk_start:chunk_end]
        elif chunk_id == b"data" and audio_data is None:
            audio_data = data[chunk_start:chunk_end]
        # RIFF chunks are word-aligned; a pad byte is not part of the chunk.
        offset = chunk_end + (chunk_size & 1)

    if fmt is None or audio_data is None or len(fmt) < 40:
        raise AudioValidationError("WAV is missing an extensible fmt or data chunk")
    format_tag, channels, sample_rate, byte_rate, block_align, bits = struct.unpack_from(
        "<HHIIHH", fmt, 0
    )
    if format_tag != 0xFFFE:
        raise AudioValidationError("WAV format is not extensible PCM")
    extension_size = struct.unpack_from("<H", fmt, 16)[0]
    if extension_size < 22 or len(fmt) < 18 + extension_size:
        raise AudioValidationError("WAV extensible format metadata is truncated")
    valid_bits, _channel_mask = struct.unpack_from("<HI", fmt, 18)
    pcm_subtype_guid = fmt[24:40]
    # KSDATAFORMAT_SUBTYPE_PCM: {00000001-0000-0010-8000-00AA00389B71}.
    if pcm_subtype_guid != bytes.fromhex("0100000000001000800000aa00389b71"):
        raise AudioValidationError("WAV extensible subtype is not PCM")
    sample_width = (bits + 7) // 8
    if (
        channels < 1
        or sample_rate < 1
        or bits < 1
        or sample_width not in {1, 2, 3, 4}
        or valid_bits < 1
        or valid_bits > bits
        or block_align != channels * sample_width
        or byte_rate != sample_rate * block_align
    ):
        raise AudioValidationError("WAV PCM format metadata is invalid")
    if len(audio_data) < block_align:
        raise AudioValidationError("approved WAV has no playable audio frames")
    frame_count, remainder = divmod(len(audio_data), block_align)
    if remainder:
        raise AudioValidationError("WAV data is not aligned to complete frames")
    frames = audio_data[: frame_count * block_align]
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
