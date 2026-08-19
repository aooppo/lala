from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from ..hashing import file_to_data_uri, sha256_file
from ..redaction import redact_text
from ..video.domain import (
    MediaArtifact,
    MotionVideoRequest,
    ProviderDefinition,
    VideoTaskResult,
    VideoTaskStatus,
)
from ..video.downloads import Downloader, download_video
from .base import ProviderSubmissionError, ProviderTaskError, ProviderValidationError


class RunwayMotionProvider:
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
        if definition.name != "runway" or definition.responsibility != "motion":
            raise ValueError("RunwayMotionProvider requires the Runway motion definition")
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
        self._estimated_credits: dict[str, float] = {}

    def validate_request(self, request: MotionVideoRequest) -> None:
        if request.provider != "runway":
            raise ProviderValidationError("Runway motion request provider must be runway")
        models = self.settings.get("supported_models")
        model = models.get(request.model) if isinstance(models, dict) else None
        if not isinstance(model, dict):
            raise ProviderValidationError(f"unsupported Runway motion model: {request.model}")
        if request.ratio not in tuple(str(value) for value in model.get("ratios", ())):
            raise ProviderValidationError(f"unsupported Runway motion ratio: {request.ratio}")
        if request.duration_seconds not in tuple(int(value) for value in model.get("durations", ())):
            raise ProviderValidationError(
                f"unsupported Runway motion duration: {request.duration_seconds}"
            )
        if model.get("prompt_required") is True and not request.prompt_text.strip():
            raise ProviderValidationError(f"Runway model {request.model} requires a prompt")
        if not request.image_path.is_file() or sha256_file(request.image_path) != request.image_sha256:
            raise ProviderValidationError("Runway motion image hash does not match approved source")
        if not request.prompt_path.is_file() or sha256_file(request.prompt_path) != request.prompt_sha256:
            raise ProviderValidationError("Runway motion prompt hash mismatch")
        if request.seed is not None and not 0 <= request.seed <= 4_294_967_295:
            raise ProviderValidationError("Runway motion seed is outside 0..4294967295")
        if request.output_format != "mp4":
            raise ProviderValidationError("Runway motion output_format must be mp4")

    def translate_request(self, request: MotionVideoRequest) -> dict[str, Any]:
        self.validate_request(request)
        mime_type = "image/png" if request.image_path.suffix.lower() == ".png" else "image/jpeg"
        payload: dict[str, Any] = {
            "model": request.model,
            "prompt_image": file_to_data_uri(request.image_path, mime_type, 32_000_000),
            "prompt_text": request.prompt_text,
            "ratio": request.ratio,
            "duration": request.duration_seconds,
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    def submit(self, request: MotionVideoRequest) -> str:
        payload = self.translate_request(request)
        try:
            response = self.client.image_to_video.create(
                **payload, timeout=min(60, request.timeout_seconds)
            )
        except Exception as exc:
            raise ProviderSubmissionError(
                redact_text(str(exc), secrets=(self._api_key,)) or "Runway motion submission failed"
            ) from exc
        task_id = str(getattr(response, "id", ""))
        if not task_id:
            raise ProviderSubmissionError("Runway motion submission returned no task ID")
        estimate = getattr(response, "estimated_cost", None) or getattr(
            response, "estimatedCost", None
        )
        credits = getattr(estimate, "credits", None)
        if credits is not None:
            self._estimated_credits[task_id] = float(credits)
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
                            or "Runway motion polling failed"
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
                    estimated_credits=self._estimated_credits.get(task_id),
                )
            if status in {"FAILED", "CANCELLED"}:
                normalized = (
                    VideoTaskStatus.FAILED if status == "FAILED" else VideoTaskStatus.CANCELLED
                )
                return VideoTaskResult(
                    task_id,
                    normalized,
                    estimated_credits=self._estimated_credits.get(task_id),
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
            raise ProviderTaskError("cannot download an unsuccessful Runway motion task")
        return (
            download_video(
                result.output_urls[0],
                output_dir / f"{output_stem}.mp4",
                provider_task_id=result.provider_task_id,
                artifact_id=output_stem,
                kind="motion",
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                downloader=self.downloader,
            ),
        )
