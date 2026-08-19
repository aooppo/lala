from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from ..redaction import redact_text
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
        if request.prompt_text:
            payload["motion_prompt"] = request.prompt_text
        return payload

    def submit(self, request: TalkingVideoRequest) -> str:
        self.validate_request(request)
        image_asset = self._upload(request.keyframe_path, f"{request.request_id}-image")
        audio_asset = self._upload(request.audio_path, f"{request.request_id}-audio")
        payload = self.translate_request(request, image_asset, audio_asset)
        try:
            response = self.client.post(
                self.base_url + str(self.settings["submit_endpoint"]),
                headers={"X-Api-Key": self._api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise ProviderSubmissionError(
                redact_text(str(exc), secrets=(self._api_key,)) or "HeyGen submission failed"
            ) from exc
        task_id = str((data.get("data") or {}).get("video_id") or "")
        if not task_id:
            raise ProviderSubmissionError("HeyGen submission returned no video_id")
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
                    headers={"X-Api-Key": self._api_key},
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
                    error_code=str(data.get("error_code") or "provider_failed"),
                    error_message=redact_text(str(data.get("error") or "HeyGen task failed")),
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
        return (artifact,)

    def _upload(self, path: Path, idempotency_key: str) -> str:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            response = self.client.post(
                self.base_url + str(self.settings["upload_endpoint"]),
                headers={
                    "X-Api-Key": self._api_key,
                    "Content-Type": mime,
                    "Idempotency-Key": idempotency_key,
                },
                content=path.read_bytes(),
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise ProviderSubmissionError(
                redact_text(str(exc), secrets=(self._api_key,)) or "HeyGen asset upload failed"
            ) from exc
        asset_id = str((payload.get("data") or {}).get("asset_id") or "")
        if not asset_id:
            raise ProviderSubmissionError("HeyGen asset upload returned no asset_id")
        return asset_id
