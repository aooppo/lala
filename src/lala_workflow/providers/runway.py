from __future__ import annotations

import os
import shutil
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

from ..domain import (
    GenerationRequest,
    OutputArtifact,
    ProviderCapabilities,
    ProviderTaskResult,
    TaskStatus,
)
from ..hashing import file_to_data_uri, inspect_image, sha256_file
from ..redaction import redact_text
from .base import (
    ProviderDownloadError,
    ProviderSubmissionError,
    validate_request_capabilities,
)


EventSink = Callable[[str, dict[str, Any]], None]
Downloader = Callable[[str, Path, float], None]


class RunwayImageProvider:
    """Official Runway text/image-to-image adapter for verified Gen-4 Image models."""

    def __init__(
        self,
        capabilities: ProviderCapabilities,
        *,
        api_key: str,
        client: Any | None = None,
        network_timeout_seconds: float = 60,
        max_poll_retries: int = 3,
        event_sink: EventSink | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        downloader: Downloader | None = None,
    ) -> None:
        if capabilities.provider != "runway":
            raise ValueError("RunwayImageProvider requires runway capabilities")
        if not api_key:
            raise ValueError("Runway API key is required for a live provider")
        self.capabilities = capabilities
        self._api_key = api_key
        if client is None:
            from runwayml import RunwayML

            client = RunwayML(
                api_key=api_key,
                runway_version=capabilities.api_version,
                max_retries=0,
            )
        self.client = client
        self.network_timeout_seconds = network_timeout_seconds
        self.max_poll_retries = max_poll_retries
        self.event_sink = event_sink or (lambda _event, _details: None)
        self.sleep = sleep
        self.monotonic = monotonic
        self.downloader = downloader or self._default_downloader

    def validate_request(self, request: GenerationRequest) -> None:
        validate_request_capabilities(request, self.capabilities)

    def translate_request(self, request: GenerationRequest) -> dict[str, Any]:
        self.validate_request(request)
        payload: dict[str, Any] = {
            "model": request.model,
            "prompt_text": request.prompt.text,
            "ratio": request.resolution,
            "reference_images": [
                {
                    "uri": file_to_data_uri(
                        reference.path,
                        reference.mime_type,
                        self.capabilities.data_uri_max_chars,
                    ),
                    "tag": reference.tag,
                }
                for reference in request.references
            ],
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    def submit(self, request: GenerationRequest) -> str:
        payload = self.translate_request(request)
        try:
            task = self.client.text_to_image.create(
                **payload,
                timeout=self.network_timeout_seconds,
            )
        except Exception as exc:
            raise ProviderSubmissionError(
                redact_text(str(exc), secrets=(self._api_key,)) or "Runway submission failed"
            ) from exc
        task_id = str(getattr(task, "id", ""))
        if not task_id:
            raise ProviderSubmissionError("Runway submission returned no task ID")
        return task_id

    def wait(self, task_id: str, timeout_seconds: float) -> ProviderTaskResult:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        started_at = datetime.now(UTC)
        started = self.monotonic()
        first_poll = True
        consecutive_poll_errors = 0
        while True:
            elapsed = self.monotonic() - started
            if not first_poll and elapsed >= timeout_seconds:
                completed = datetime.now(UTC)
                self.event_sink("task_timed_out", {"provider_task_id": task_id})
                return ProviderTaskResult(
                    task_id,
                    TaskStatus.TIMED_OUT,
                    error_code="timeout",
                    error_message=f"task exceeded {timeout_seconds:g} seconds",
                    started_at=started_at,
                    completed_at=completed,
                )
            first_poll = False
            try:
                details = self.client.tasks.retrieve(
                    task_id,
                    timeout=self.network_timeout_seconds,
                )
            except Exception as exc:
                consecutive_poll_errors += 1
                self.event_sink(
                    "poll_retry" if consecutive_poll_errors <= self.max_poll_retries else "poll_failed",
                    {
                        "provider_task_id": task_id,
                        "attempt": consecutive_poll_errors,
                        "error": redact_text(str(exc), secrets=(self._api_key,)),
                    },
                )
                if consecutive_poll_errors > self.max_poll_retries:
                    completed = datetime.now(UTC)
                    return ProviderTaskResult(
                        task_id,
                        TaskStatus.FAILED,
                        error_code="poll_error",
                        error_message=redact_text(str(exc), secrets=(self._api_key,)),
                        started_at=started_at,
                        completed_at=completed,
                    )
                remaining = timeout_seconds - (self.monotonic() - started)
                if remaining <= 0:
                    continue
                self.sleep(min(self.capabilities.poll_interval_seconds, remaining))
                continue
            consecutive_poll_errors = 0
            status = str(getattr(details, "status", "UNKNOWN"))
            self.event_sink(
                "task_polled",
                {
                    "provider_task_id": task_id,
                    "status": status,
                    "progress": getattr(details, "progress", None),
                },
            )
            if status == "SUCCEEDED":
                completed = datetime.now(UTC)
                return ProviderTaskResult(
                    task_id,
                    TaskStatus.SUCCEEDED,
                    tuple(str(url) for url in getattr(details, "output", []) or []),
                    started_at=started_at,
                    completed_at=completed,
                )
            if status in {"FAILED", "CANCELLED"}:
                completed = datetime.now(UTC)
                normalized = TaskStatus.FAILED if status == "FAILED" else TaskStatus.CANCELLED
                return ProviderTaskResult(
                    task_id,
                    normalized,
                    error_code=str(getattr(details, "failure_code", None) or status.lower()),
                    error_message=redact_text(
                        str(getattr(details, "failure", f"task {status.lower()}")),
                        secrets=(self._api_key,),
                    ),
                    started_at=started_at,
                    completed_at=completed,
                )
            if status not in {"PENDING", "THROTTLED", "RUNNING"}:
                completed = datetime.now(UTC)
                return ProviderTaskResult(
                    task_id,
                    TaskStatus.FAILED,
                    error_code="unknown_task_status",
                    error_message=f"unknown Runway task status: {status}",
                    started_at=started_at,
                    completed_at=completed,
                )
            remaining = timeout_seconds - (self.monotonic() - started)
            if remaining <= 0:
                continue
            self.sleep(min(self.capabilities.poll_interval_seconds, remaining))

    def download_results(
        self,
        result: ProviderTaskResult,
        destination: Path,
        output_id: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> tuple[OutputArtifact, ...]:
        if result.status is not TaskStatus.SUCCEEDED:
            raise ProviderDownloadError("cannot download a non-successful provider result")
        if not result.output_urls:
            raise ProviderDownloadError("successful Runway task returned no output URLs")
        destination.mkdir(parents=True, exist_ok=True)
        artifacts: list[OutputArtifact] = []
        multiple = len(result.output_urls) > 1
        for index, url in enumerate(result.output_urls, start=1):
            suffix = Path(urlsplit(url).path).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                suffix = ".png"
            artifact_id = f"{output_id}-{index:02d}" if multiple else output_id
            target = destination / f"{artifact_id}{suffix}"
            if target.exists():
                raise ProviderDownloadError(f"output target already exists: {target.name}")
            last_error: Exception | None = None
            for attempt in range(max_retries + 1):
                temp = destination / f".{target.stem}.{uuid.uuid4().hex}.part{target.suffix}"
                try:
                    self.event_sink(
                        "download_attempt",
                        {
                            "provider_task_id": result.provider_task_id,
                            "output_id": output_id,
                            "attempt": attempt + 1,
                        },
                    )
                    self.downloader(url, temp, timeout_seconds)
                    inspect_image(temp)
                    os.replace(temp, target)
                    artifacts.append(
                        OutputArtifact(
                            output_id=artifact_id,
                            provider_task_id=result.provider_task_id,
                            file=target,
                            sha256=sha256_file(target),
                            size_bytes=target.stat().st_size,
                            source_url_redacted=_redacted_url(url),
                        )
                    )
                    self.event_sink(
                        "download_completed",
                        {
                            "provider_task_id": result.provider_task_id,
                            "output_id": artifact_id,
                            "file": target.name,
                        },
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    temp.unlink(missing_ok=True)
                    if attempt >= max_retries:
                        raise ProviderDownloadError(
                            redact_text(str(exc), secrets=(self._api_key,))
                            or f"failed to download output {artifact_id}"
                        ) from exc
            if last_error is not None and not target.exists():
                raise ProviderDownloadError(str(last_error))
        return tuple(artifacts)

    @staticmethod
    def _default_downloader(url: str, destination: Path, timeout_seconds: float) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": "lady-lala-workflow/0.1"})
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            with destination.open("xb") as handle:
                shutil.copyfileobj(response, handle)


def _redacted_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
