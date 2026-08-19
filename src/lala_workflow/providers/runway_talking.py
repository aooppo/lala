from __future__ import annotations

import base64
import time
import uuid
from pathlib import Path
from typing import Any, Callable

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


class RunwayTalkingProvider:
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
        if definition.name != "runway_talking" or definition.responsibility != "talking":
            raise ValueError("RunwayTalkingProvider requires the Runway talking definition")
        if not api_key:
            raise ValueError("Runway API key is required")
        self.definition = definition
        self.settings = definition.settings
        self._api_key = api_key
        if client is None:
            from runwayml import RunwayML

            client = RunwayML(
                api_key=api_key,
                runway_version=str(self.settings["api_version"]),
                max_retries=0,
            )
        self.client = client
        self.sleep = sleep
        self.monotonic = monotonic
        self.downloader = downloader
        self.max_poll_retries = max_poll_retries

    def validate_request(self, request: TalkingVideoRequest) -> None:
        if request.provider != "runway_talking" or request.model != "gwm1_avatars":
            raise ProviderValidationError("Runway talking requires runway_talking/gwm1_avatars")
        mappings = self.settings.get("approved_custom_avatars")
        avatar_id = mappings.get(request.keyframe_sha256) if isinstance(mappings, dict) else None
        if not avatar_id:
            raise ProviderValidationError(
                "Runway talking requires an approved custom avatar for the exact keyframe digest"
            )
        try:
            uuid.UUID(str(avatar_id))
        except ValueError as exc:
            raise ProviderValidationError("approved custom avatar ID must be a UUID") from exc
        if not request.audio_path.is_file() or request.audio_path.suffix.lower() != ".wav":
            raise ProviderValidationError("Runway avatar speech requires an approved WAV")

    def translate_request(self, request: TalkingVideoRequest) -> dict[str, Any]:
        self.validate_request(request)
        avatar_id = self.settings["approved_custom_avatars"][request.keyframe_sha256]
        audio = base64.b64encode(request.audio_path.read_bytes()).decode("ascii")
        return {
            "model": "gwm1_avatars",
            "avatar": {"type": "custom", "avatarId": str(avatar_id)},
            "speech": {"type": "audio", "audio": f"data:audio/wav;base64,{audio}"},
        }

    def submit(self, request: TalkingVideoRequest) -> str:
        payload = self.translate_request(request)
        try:
            response = self.client.avatar_videos.create(**payload, timeout=request.timeout_seconds)
        except Exception as exc:
            raise ProviderSubmissionError(
                redact_text(str(exc), secrets=(self._api_key,)) or "Runway avatar submission failed"
            ) from exc
        task_id = str(getattr(response, "id", ""))
        if not task_id:
            raise ProviderSubmissionError("Runway avatar submission returned no task ID")
        return task_id

    def wait(self, task_id: str, timeout_seconds: float) -> VideoTaskResult:
        started = self.monotonic()
        consecutive_errors = 0
        while True:
            if self.monotonic() - started >= timeout_seconds:
                return VideoTaskResult(task_id, VideoTaskStatus.TIMED_OUT, error_code="timeout")
            try:
                response = self.client.tasks.retrieve(task_id, timeout=min(60, timeout_seconds))
            except Exception as exc:
                consecutive_errors += 1
                if consecutive_errors > self.max_poll_retries:
                    return VideoTaskResult(
                        task_id,
                        VideoTaskStatus.FAILED,
                        error_code="poll_error",
                        error_message=(
                            redact_text(str(exc), secrets=(self._api_key,))
                            or "Runway polling failed"
                        ),
                    )
                self.sleep(min(5, max(0, timeout_seconds - (self.monotonic() - started))))
                continue
            consecutive_errors = 0
            status = str(getattr(response, "status", "")).upper()
            if status == "SUCCEEDED":
                return VideoTaskResult(
                    task_id,
                    VideoTaskStatus.SUCCEEDED,
                    tuple(str(url) for url in getattr(response, "output", ()) or ()),
                )
            if status in {"FAILED", "CANCELLED"}:
                normalized = (
                    VideoTaskStatus.FAILED if status == "FAILED" else VideoTaskStatus.CANCELLED
                )
                return VideoTaskResult(
                    task_id,
                    normalized,
                    error_code=str(getattr(response, "failure_code", None) or status.lower()),
                    error_message=redact_text(str(getattr(response, "failure", status.lower()))),
                )
            if status not in {"PENDING", "THROTTLED", "RUNNING"}:
                return VideoTaskResult(
                    task_id,
                    VideoTaskStatus.FAILED,
                    error_code="unknown_status",
                    error_message=f"unknown Runway task status: {status}",
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
            raise ProviderTaskError("cannot download an unsuccessful Runway avatar task")
        return (
            download_video(
                result.output_urls[0],
                output_dir / f"{output_stem}.mp4",
                provider_task_id=result.provider_task_id,
                artifact_id=output_stem,
                kind="talking",
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                downloader=self.downloader,
            ),
        )
