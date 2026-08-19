from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..providers.base import ProviderSubmissionError
from .domain import MediaArtifact, VideoTaskResult, VideoTaskStatus
from .downloads import validate_media_artifact
from .storage import VideoRunContext, VideoRunStorage
from .validation import ExternalInputBlocked


class RetryableVideoSubmissionError(ProviderSubmissionError):
    def __init__(self, message: str, *, idempotency_safe: bool = False) -> None:
        super().__init__(message)
        self.idempotency_safe = idempotency_safe


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    request_id: str
    provider_task_id: str | None
    status: VideoTaskStatus
    submission_attempts: int
    artifacts: tuple[MediaArtifact, ...]
    error_code: str | None = None
    error_message: str | None = None
    estimated_credits: float | None = None
    actual_credits: float | None = None


def validate_live_smoke_guards(
    provider_name: str,
    result_count: int,
    audio_duration_seconds: float | None,
    environ: Mapping[str, str],
) -> None:
    validate_live_provider_guard(provider_name, environ)
    if environ.get("VIDEO_LIVE_SMOKE_TEST") != "true":
        raise ExternalInputBlocked(
            "first talking smoke requires exact VIDEO_LIVE_SMOKE_TEST=true"
        )
    if result_count != 1:
        raise ExternalInputBlocked("the first live talking smoke must request exactly one result")
    if audio_duration_seconds is not None and not 8 <= audio_duration_seconds <= 12:
        raise ExternalInputBlocked("the first live talking audio duration must be within 8..12 seconds")


def validate_live_provider_guard(
    provider_name: str, environ: Mapping[str, str]
) -> None:
    if environ.get("VIDEO_ALLOW_LIVE_CALLS") != "true":
        raise ExternalInputBlocked(
            "live video calls require exact VIDEO_ALLOW_LIVE_CALLS=true"
        )
    credential_name = (
        "HEYGEN_API_KEY" if provider_name == "heygen" else "RUNWAYML_API_SECRET"
    )
    if not str(environ.get(credential_name) or "").strip():
        raise ExternalInputBlocked(f"live provider credential is missing: {credential_name}")


def execute_provider_request(
    request: Any,
    provider: Any,
    storage: VideoRunStorage,
    run: VideoRunContext,
    output_dir: Path,
) -> ExecutionRecord:
    provider.validate_request(request)
    task_id: str | None = None
    submission_attempts = 0
    for attempt in range(request.max_retries + 1):
        submission_attempts += 1
        storage.append_event(
            run,
            "submission_attempt",
            {"request_id": request.request_id, "attempt": submission_attempts},
        )
        try:
            task_id = provider.submit(request)
            break
        except RetryableVideoSubmissionError as exc:
            if not exc.idempotency_safe or attempt >= request.max_retries:
                raise
            storage.append_event(
                run,
                "submission_retry",
                {"request_id": request.request_id, "attempt": submission_attempts},
            )
    if not task_id:
        raise ProviderSubmissionError("provider submission returned no durable task ID")
    storage.append_event(
        run,
        "task_submitted",
        {"request_id": request.request_id, "provider_task_id": task_id},
    )
    result: VideoTaskResult = provider.wait(task_id, request.timeout_seconds)
    storage.append_event(
        run,
        "task_terminal",
        {
            "request_id": request.request_id,
            "provider_task_id": task_id,
            "status": result.status.value,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "estimated_credits": result.estimated_credits,
            "actual_credits": result.actual_credits,
        },
    )
    if result.status is not VideoTaskStatus.SUCCEEDED:
        return ExecutionRecord(
            request.request_id,
            task_id,
            result.status,
            submission_attempts,
            (),
            result.error_code,
            result.error_message,
            result.estimated_credits,
            result.actual_credits,
        )
    artifacts = provider.download_results(
        result,
        output_dir,
        request.request_id,
        request.timeout_seconds,
        request.max_retries,
    )
    validated = tuple(validate_media_artifact(artifact) for artifact in artifacts)
    storage.append_event(
        run,
        "outputs_validated",
        {
            "request_id": request.request_id,
            "provider_task_id": task_id,
            "artifacts": [artifact.artifact_id for artifact in validated],
        },
    )
    return ExecutionRecord(
        request.request_id,
        task_id,
        result.status,
        submission_attempts,
        validated,
        estimated_credits=result.estimated_credits,
        actual_credits=result.actual_credits,
    )
