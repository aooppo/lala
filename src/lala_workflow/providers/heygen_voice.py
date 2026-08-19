from __future__ import annotations

import shutil
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable

import httpx

from ..audio.validation import AudioValidationError, inspect_wav
from ..hashing import sha256_file
from ..redaction import redact_text
from ..video.domain import MediaArtifact, ProviderDefinition, VoiceRequest
from ..video.downloads import Downloader, redacted_url
from .base import ProviderSubmissionError, ProviderTaskError, ProviderValidationError


Converter = Callable[[Path, Path, int, float], None]


class HeyGenVoiceProvider:
    """Synchronous HeyGen Starfish TTS adapter for an already-approved voice ID."""

    def __init__(
        self,
        definition: ProviderDefinition,
        *,
        api_key: str,
        client: Any | None = None,
        downloader: Downloader | None = None,
        converter: Converter | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if definition.name != "heygen_voice" or definition.responsibility != "voice":
            raise ValueError("HeyGenVoiceProvider requires the HeyGen voice definition")
        if not api_key:
            raise ValueError("HeyGen API key is required")
        self.definition = definition
        self.settings = definition.settings
        self._api_key = api_key
        self.base_url = str(self.settings.get("api_base_url") or "").rstrip("/")
        self.client = client or httpx.Client(timeout=60)
        self.downloader = downloader or _download_audio
        self.converter = converter or _convert_to_pcm_wav
        self.monotonic = monotonic

    def validate_request(self, request: VoiceRequest) -> None:
        if request.provider != "heygen_voice":
            raise ProviderValidationError("HeyGen voice request provider must be heygen_voice")
        if request.model != str(self.settings.get("model") or ""):
            raise ProviderValidationError(f"unsupported HeyGen voice model: {request.model}")
        if not request.voice_id.strip():
            raise ProviderValidationError("HeyGen voice_id is required")
        if request.output_format != "wav" or request.output_path.suffix.lower() != ".wav":
            raise ProviderValidationError("HeyGen derived voice output must be WAV")
        if request.output_path.exists():
            raise ProviderValidationError("HeyGen derived voice output already exists")
        if not request.script_path.is_file():
            raise ProviderValidationError("HeyGen voice script source is missing")
        if request.script_path.read_bytes() != request.script_content:
            raise ProviderValidationError("HeyGen voice script bytes do not match the source file")
        if sha256_file(request.script_path) != request.script_sha256:
            raise ProviderValidationError("HeyGen voice script digest does not match the source")
        try:
            text = request.script_content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProviderValidationError("HeyGen voice script must be UTF-8") from exc
        maximum = int(self.settings.get("max_text_characters") or 5000)
        if not 1 <= len(text) <= maximum:
            raise ProviderValidationError(
                f"HeyGen voice script length must be within 1..{maximum} characters"
            )
        speed = 1.0 if request.speed is None else request.speed
        if not 0.5 <= speed <= 2.0:
            raise ProviderValidationError("HeyGen voice speed must be within 0.5..2.0")
        if request.sample_rate is not None and request.sample_rate <= 0:
            raise ProviderValidationError("HeyGen voice sample rate must be positive")
        if request.timeout_seconds <= 0 or not 0 <= request.max_retries <= 2:
            raise ProviderValidationError("HeyGen voice timeout or retry bound is invalid")

    def translate_request(self, request: VoiceRequest) -> dict[str, Any]:
        self.validate_request(request)
        payload: dict[str, Any] = {
            "text": request.script_content.decode("utf-8"),
            "voice_id": request.voice_id,
            "input_type": "text",
            "speed": 1.0 if request.speed is None else request.speed,
        }
        if request.language:
            payload["language"] = request.language
        return payload

    def synthesize(self, request: VoiceRequest) -> MediaArtifact:
        payload = self.translate_request(request)
        started = self.monotonic()
        try:
            response = self.client.post(
                self.base_url + str(self.settings["submit_endpoint"]),
                headers={"X-Api-Key": self._api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=request.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json().get("data") or {}
        except Exception as exc:
            raise ProviderSubmissionError(
                redact_text(str(exc), secrets=(self._api_key,))
                or "HeyGen voice synthesis failed"
            ) from exc
        audio_url = str(data.get("audio_url") or "")
        provider_request_id = str(data.get("request_id") or "")
        if not audio_url or not provider_request_id:
            raise ProviderSubmissionError(
                "HeyGen voice synthesis returned no audio_url or request_id"
            )
        reported_duration = _optional_positive_float(data.get("duration"))
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        sample_rate = request.sample_rate or int(self.settings.get("default_sample_rate") or 48000)
        last_error: Exception | None = None
        for _attempt in range(request.max_retries + 1):
            remaining = request.timeout_seconds - (self.monotonic() - started)
            if remaining <= 0:
                last_error = TimeoutError("HeyGen voice workflow exceeded its overall timeout")
                break
            temporary = request.output_path.with_name(
                f".{request.output_path.stem}.{uuid.uuid4().hex}.source"
            )
            try:
                self.downloader(audio_url, temporary, remaining)
                remaining = request.timeout_seconds - (self.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError("HeyGen voice workflow exceeded its overall timeout")
                self.converter(
                    temporary,
                    request.output_path,
                    sample_rate,
                    remaining,
                )
                info = inspect_wav(request.output_path)
                return MediaArtifact(
                    artifact_id=f"voice-{request.preset}",
                    kind="audio",
                    path=request.output_path,
                    sha256=info.sha256,
                    size_bytes=request.output_path.stat().st_size,
                    mime_type="audio/wav",
                    duration_seconds=info.duration_seconds,
                    provider_task_id=provider_request_id,
                    source_url_redacted=redacted_url(audio_url),
                    provenance={
                        "provider": "heygen_voice",
                        "model": request.model,
                        "provider_request_id": provider_request_id,
                        "reported_duration_seconds": reported_duration,
                        "script_sha256": request.script_sha256,
                        "voice_id": request.voice_id,
                    },
                )
            except Exception as exc:
                last_error = exc
                request.output_path.unlink(missing_ok=True)
            finally:
                temporary.unlink(missing_ok=True)
        message = redact_text(str(last_error or "audio download failed"), secrets=(self._api_key,))
        raise ProviderTaskError(message or "HeyGen voice audio download failed")


def _optional_positive_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _download_audio(url: str, destination: Path, timeout_seconds: float) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "lady-lala-workflow/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        with destination.open("xb") as output:
            shutil.copyfileobj(response, output)


def _convert_to_pcm_wav(
    source: Path, destination: Path, sample_rate: int, timeout_seconds: float
) -> None:
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-c:a",
                "pcm_s16le",
                "-n",
                str(destination),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AudioValidationError("FFmpeg could not convert HeyGen speech to PCM WAV") from exc
