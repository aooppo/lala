from __future__ import annotations

import mimetypes
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from ..redaction import redact_text
from ..hashing import sha256_file
from ..video.domain import (
    MediaArtifact,
    ProviderDefinition,
    TalkingVideoRequest,
    VideoTaskResult,
    VideoTaskStatus,
)
from ..video.downloads import Downloader, download_video
from .base import ProviderSubmissionError, ProviderTaskError, ProviderValidationError


class HeyGenTalkingProvider:
    def __init__(
        self,
        definition: ProviderDefinition,
        *,
        api_key: str,
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        downloader: Downloader | None = None,
        max_poll_retries: int = 2,
    ) -> None:
        if definition.name != "heygen" or definition.responsibility != "talking":
            raise ValueError("HeyGenTalkingProvider requires the HeyGen talking definition")
        if not api_key:
            raise ValueError("HeyGen API key is required")
        self.definition = definition
        self.settings = definition.settings
        self._api_key = api_key
        self.base_url = str(self.settings.get("api_base_url") or "").rstrip("/")
        self.client = client or httpx.Client(timeout=60)
        self.sleep = sleep
        self.monotonic = monotonic
        self.downloader = downloader
        self.max_poll_retries = max_poll_retries
        self._asset_cache: dict[tuple[str, str, str], str] = {}
        self._task_provenance: dict[str, dict[str, str]] = {}

    def validate_request(self, request: TalkingVideoRequest) -> None:
        if request.provider != "heygen":
            raise ProviderValidationError("HeyGen request provider must be heygen")
        if request.model != str(self.settings.get("model")):
            raise ProviderValidationError(f"unsupported HeyGen talking model: {request.model}")
        if request.aspect_ratio != "16:9" or request.resolution != "1280:720":
            raise ProviderValidationError("HeyGen MVP supports 16:9 at 1280:720")
        maximum = int(self.settings.get("max_asset_bytes") or 0)
        for label, path, suffixes in (
            ("keyframe", request.keyframe_path, {".png", ".jpg", ".jpeg"}),
            ("audio", request.audio_path, {".wav", ".mp3"}),
        ):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                raise ProviderValidationError(f"HeyGen {label} asset is invalid")
            if path.stat().st_size > maximum:
                raise ProviderValidationError(f"HeyGen {label} asset exceeds provider limit")
        if sha256_file(request.keyframe_path) != request.keyframe_sha256:
            raise ProviderValidationError("HeyGen keyframe digest mismatch")
        if sha256_file(request.audio_path) != request.audio_sha256:
            raise ProviderValidationError("HeyGen audio digest mismatch")
        if request.audio_duration_seconds <= 0:
            raise ProviderValidationError("talking audio duration must be positive")

    def translate_request(
        self, request: TalkingVideoRequest, image_asset_id: str, audio_asset_id: str
    ) -> dict[str, Any]:
        self.validate_request(request)
        payload: dict[str, Any] = {
            "type": "image",
            "image": {"type": "asset_id", "asset_id": image_asset_id},
            "audio_asset_id": audio_asset_id,
            "aspect_ratio": request.aspect_ratio,
            "resolution": "720p",
        }
        capability = self.settings.get("capabilities", {}).get("arbitrary_image", {})
        if request.prompt_text and capability.get("motion_prompt") is True:
            payload["motion_prompt"] = request.prompt_text
        return payload

    def submit(self, request: TalkingVideoRequest) -> str:
        self.validate_request(request)
        image_asset = self._upload(
            request.keyframe_path,
            content_sha256=request.keyframe_sha256,
            asset_kind="image",
        )
        audio_asset = self._upload(
            request.audio_path,
            content_sha256=request.audio_sha256,
            asset_kind="audio",
        )
        payload = self.translate_request(request, image_asset, audio_asset)
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        idempotency_key = _idempotency_key(
            f"video:{request.run_id}:{request.request_id}:{payload_hash}"
        )
        try:
            response = self._post_json_mutation(
                str(self.settings["submit_endpoint"]),
                payload,
                idempotency_key=idempotency_key,
            )
            data = response.json()
        except Exception as exc:
            raise ProviderSubmissionError(
                redact_text(str(exc), secrets=(self._api_key,)) or "HeyGen submission failed"
            ) from exc
        task_id = str((data.get("data") or {}).get("video_id") or "")
        if not task_id:
            raise ProviderSubmissionError("HeyGen submission returned no video_id")
        self._task_provenance[task_id] = {
            "image_asset_id": image_asset,
            "audio_asset_id": audio_asset,
            "video_idempotency_key": idempotency_key,
            "payload_sha256": payload_hash,
        }
        return task_id

    def wait(self, task_id: str, timeout_seconds: float) -> VideoTaskResult:
        started = self.monotonic()
        consecutive_errors = 0
        endpoint = str(self.settings["poll_endpoint"]).format(task_id=task_id)
        while True:
            if self.monotonic() - started >= timeout_seconds:
                return VideoTaskResult(
                    task_id,
                    VideoTaskStatus.TIMED_OUT,
                    error_code="timeout",
                    error_message=f"HeyGen task exceeded {timeout_seconds:g} seconds",
                )
            try:
                response = self.client.get(
                    self.base_url + endpoint,
                    headers={"x-api-key": self._api_key},
                )
                response.raise_for_status()
                data = response.json().get("data") or {}
            except Exception as exc:
                consecutive_errors += 1
                if consecutive_errors > self.max_poll_retries:
                    return VideoTaskResult(
                        task_id,
                        VideoTaskStatus.FAILED,
                        error_code="poll_error",
                        error_message=(
                            redact_text(str(exc), secrets=(self._api_key,))
                            or "HeyGen polling failed"
                        ),
                    )
                self.sleep(min(5, max(0, timeout_seconds - (self.monotonic() - started))))
                continue
            consecutive_errors = 0
            status = str(data.get("status") or "").lower()
            if status == str(self.settings.get("terminal_success")):
                url = str(data.get("video_url") or "")
                if not url:
                    return VideoTaskResult(
                        task_id,
                        VideoTaskStatus.FAILED,
                        error_code="missing_output",
                        error_message="HeyGen completed without video_url",
                    )
                return VideoTaskResult(task_id, VideoTaskStatus.SUCCEEDED, (url,))
            if status == str(self.settings.get("terminal_failure")):
                return VideoTaskResult(
                    task_id,
                    VideoTaskStatus.FAILED,
                    error_code=str(data.get("failure_code") or "provider_failed"),
                    error_message=redact_text(
                        str(data.get("failure_message") or "HeyGen task failed")
                    ),
                )
            if status not in {"pending", "processing", "running", "waiting"}:
                return VideoTaskResult(
                    task_id,
                    VideoTaskStatus.FAILED,
                    error_code="unknown_status",
                    error_message=f"unknown HeyGen task status: {status}",
                )
            self.sleep(min(5, max(0, timeout_seconds - (self.monotonic() - started))))

    def download_results(
        self,
        result: VideoTaskResult,
        output_dir: Path,
        output_stem: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> tuple[MediaArtifact, ...]:
        if result.status is not VideoTaskStatus.SUCCEEDED or not result.output_urls:
            raise ProviderTaskError("cannot download an unsuccessful HeyGen task")
        artifact = download_video(
            result.output_urls[0],
            output_dir / f"{output_stem}.mp4",
            provider_task_id=result.provider_task_id,
            artifact_id=output_stem,
            kind="talking",
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            downloader=self.downloader,
        )
        return (
            MediaArtifact(
                artifact_id=artifact.artifact_id,
                kind=artifact.kind,
                path=artifact.path,
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
                mime_type=artifact.mime_type,
                duration_seconds=artifact.duration_seconds,
                width=artifact.width,
                height=artifact.height,
                provider_task_id=artifact.provider_task_id,
                source_url_redacted=artifact.source_url_redacted,
                container=artifact.container,
                video_codec=artifact.video_codec,
                pixel_format=artifact.pixel_format,
                average_frame_rate=artifact.average_frame_rate,
                audio_stream_present=artifact.audio_stream_present,
                audio_codec=artifact.audio_codec,
                sample_rate=artifact.sample_rate,
                channel_count=artifact.channel_count,
                bit_rate=artifact.bit_rate,
                provenance=self._task_provenance.get(result.provider_task_id, {}),
            ),
        )

    def _upload(self, path: Path, *, content_sha256: str, asset_kind: str) -> str:
        mime = _asset_mime_type(path)
        endpoint = str(self.settings["upload_endpoint"])
        cache_key = (endpoint, content_sha256, mime)
        if cache_key in self._asset_cache:
            return self._asset_cache[cache_key]
        # Asset identity is content-addressed and endpoint/mime scoped.  The
        # cache key above prevents duplicate uploads within a provider run;
        # this idempotency key also remains safe across retries and runs.
        idempotency_key = _idempotency_key(
            f"asset:{endpoint}:{content_sha256}:{mime}-{asset_kind}"
        )
        try:
            with path.open("rb") as stream:
                response = self._post_file_mutation(
                    endpoint,
                    path,
                    stream,
                    mime,
                    idempotency_key=idempotency_key,
                )
            payload = response.json()
        except Exception as exc:
            raise ProviderSubmissionError(
                redact_text(str(exc), secrets=(self._api_key,)) or "HeyGen asset upload failed"
            ) from exc
        asset_id = str((payload.get("data") or {}).get("asset_id") or "")
        if not asset_id:
            raise ProviderSubmissionError("HeyGen asset upload returned no asset_id")
        self._asset_cache[cache_key] = asset_id
        return asset_id

    def _post_json_mutation(
        self, endpoint: str, payload: dict[str, Any], *, idempotency_key: str
    ) -> Any:
        for retry in range(self.max_poll_retries + 1):
            response = self.client.post(
                self.base_url + endpoint,
                headers={"x-api-key": self._api_key, "Idempotency-Key": idempotency_key},
                json=payload,
            )
            if not _retryable_mutation_response(response):
                response.raise_for_status()
                return response
            if retry >= self.max_poll_retries:
                response.raise_for_status()
            self.sleep(_retry_after(response))
        raise ProviderSubmissionError("HeyGen mutation did not produce a response")

    def _post_file_mutation(
        self,
        endpoint: str,
        path: Path,
        stream: Any,
        mime: str,
        *,
        idempotency_key: str,
    ) -> Any:
        for retry in range(self.max_poll_retries + 1):
            stream.seek(0)
            response = self.client.post(
                self.base_url + endpoint,
                headers={"x-api-key": self._api_key, "Idempotency-Key": idempotency_key},
                files={"file": (path.name, stream, mime)},
            )
            if not _retryable_mutation_response(response):
                response.raise_for_status()
                return response
            if retry >= self.max_poll_retries:
                response.raise_for_status()
            self.sleep(_retry_after(response))
        raise ProviderSubmissionError("HeyGen upload did not produce a response")


def _idempotency_key(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_:.-]", "-", value)
    if len(safe) <= 255:
        return safe
    digest = hashlib.sha256(safe.encode("utf-8")).hexdigest()
    return f"{safe[:190]}:{digest}"


def _request_in_progress(response: Any) -> bool:
    if getattr(response, "status_code", None) != 409:
        return False
    try:
        payload = response.json()
    except Exception:
        return False
    code = str(payload.get("code") or (payload.get("error") or {}).get("code") or "")
    return code == "request_in_progress"


def _retryable_mutation_response(response: Any) -> bool:
    """Return true only for bounded, provider-documented in-flight/rate-limit responses."""

    status = getattr(response, "status_code", None)
    if status == 429:
        return True
    return _request_in_progress(response)


def _retry_after(response: Any) -> float:
    try:
        return min(30.0, max(0.0, float(response.headers.get("Retry-After", "1"))))
    except (TypeError, ValueError):
        return 1.0


def _asset_mime_type(path: Path) -> str:
    # Python/platform mimetypes may report audio/x-wav; use the canonical
    # provider contract value for the supported asset extensions.
    explicit = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
    }
    return explicit.get(
        path.suffix.lower(),
        mimetypes.guess_type(path.name)[0] or "application/octet-stream",
    )
