from __future__ import annotations

import shutil
import subprocess
import time
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

import httpx

from ..audio.validation import AudioValidationError, inspect_wav
from ..hashing import sha256_file
from ..redaction import redact_text
from ..video.domain import MediaArtifact, ProviderDefinition, VoiceRequest
from ..video.downloads import Downloader, redacted_url
from .base import ProviderSubmissionError, ProviderTaskError, ProviderValidationError


Converter = Callable[[Path, Path, int, float], None]


@dataclass(frozen=True, slots=True)
class HeyGenVoiceVerification:
    voice_id: str
    name: str
    gender: str | None
    language: str | None
    engine: str
    voice_type: str
    created_at: str | None
    preview_url_safe: str | None


class HeyGenVoiceVerifier:
    """Read-only verifier for an existing private Starfish voice."""

    def __init__(
        self,
        definition: ProviderDefinition,
        *,
        api_key: str,
        client: Any | None = None,
    ) -> None:
        if definition.name != "heygen_voice" or definition.responsibility != "voice":
            raise ValueError("HeyGenVoiceVerifier requires the HeyGen voice definition")
        if not api_key:
            raise ValueError("HeyGen API key is required")
        self.settings = definition.settings
        self._api_key = api_key
        self.base_url = str(self.settings.get("api_base_url") or "").rstrip("/")
        self.client = client or httpx.Client(timeout=60)

    def verify(self, voice_id: str, *, expected_name: str) -> HeyGenVoiceVerification:
        if not voice_id.strip():
            raise ProviderValidationError("HeyGen voice_id is required")
        detail = self._get_json(
            str(self.settings.get("detail_endpoint") or "/v3/voices/{voice_id}").format(
                voice_id=voice_id
            )
        ).get("data") or {}
        if str(detail.get("voice_id") or "") != voice_id:
            raise ProviderValidationError("HeyGen voice detail returned a different voice_id")
        name = str(detail.get("name") or "")
        if name != expected_name:
            raise ProviderValidationError(
                f"HeyGen voice name mismatch: expected {expected_name!r}, got {name!r}"
            )
        compatible = False
        token: str | None = None
        for _page in range(10):
            params: dict[str, Any] = {
                "type": "private",
                "engine": "starfish",
                "limit": 100,
            }
            if token:
                params["token"] = token
            listed = self._get_json(
                str(self.settings.get("list_endpoint") or "/v3/voices"), params=params
            )
            for item in listed.get("data") or []:
                if isinstance(item, dict) and str(item.get("voice_id") or "") == voice_id:
                    compatible = True
                    if str(item.get("name") or name) != expected_name:
                        raise ProviderValidationError("HeyGen voice list name does not match")
                    break
            if compatible or not listed.get("has_more"):
                break
            token = str(listed.get("next_token") or "") or None
            if token is None:
                break
        if not compatible:
            raise ProviderValidationError(
                "HeyGen voice is not present in the private Starfish-compatible voice list"
            )
        preview = str(detail.get("preview_audio_url") or "") or None
        return HeyGenVoiceVerification(
            voice_id=voice_id,
            name=name,
            gender=_optional_text(detail.get("gender")),
            language=_optional_text(detail.get("language")),
            engine="starfish",
            voice_type="private",
            created_at=_created_at(detail.get("created_at")),
            preview_url_safe=redacted_url(preview) if preview else None,
        )

    def preview_url(self, voice_id: str, *, expected_name: str) -> str:
        detail = self._get_json(
            str(self.settings.get("detail_endpoint") or "/v3/voices/{voice_id}").format(
                voice_id=voice_id
            )
        ).get("data") or {}
        if str(detail.get("voice_id") or "") != voice_id or detail.get("name") != expected_name:
            raise ProviderValidationError("HeyGen preview voice identity does not match")
        url = str(detail.get("preview_audio_url") or "")
        if not url:
            raise ProviderValidationError("HeyGen voice has no preview_audio_url")
        return url

    def _get_json(self, endpoint: str, *, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self.client.get(
                self.base_url + endpoint,
                headers={"x-api-key": self._api_key},
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise ProviderTaskError(
                redact_text(str(exc), secrets=(self._api_key,)) or "HeyGen voice verification failed"
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderTaskError("HeyGen voice verification returned malformed JSON")
        return payload


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
                headers={"x-api-key": self._api_key},
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
                        "speed": 1.0 if request.speed is None else request.speed,
                        "language": request.language,
                        "sample_rate": sample_rate,
                        "channels": 1,
                        "output_codec": "pcm_s16le",
                        "conversion": "ffmpeg -ac 1 -ar <sample_rate> -c:a pcm_s16le",
                        "submission_policy": "single_submit_no_automatic_replay",
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


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _created_at(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return _optional_text(value)
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


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
