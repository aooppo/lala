from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from lala_workflow.providers.base import ProviderSubmissionError, ProviderTaskError
from lala_workflow.video.domain import VideoTaskResult, VideoTaskStatus
from lala_workflow.video.execution import (
    RetryableVideoSubmissionError,
    execute_provider_request,
    validate_live_smoke_guards,
)
from lala_workflow.video.downloads import download_video
from lala_workflow.video.runner import VideoRunOptions
from lala_workflow.video.storage import VideoRunStorage
from lala_workflow.video.validation import ExternalInputBlocked
from tests.fakes_video import FakeTalkingProvider
from tests.test_heygen_talking_provider import make_request


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"VIDEO_ALLOW_LIVE_CALLS": "TRUE", "VIDEO_LIVE_SMOKE_TEST": "true", "HEYGEN_API_KEY": "x"},
        {"VIDEO_ALLOW_LIVE_CALLS": "true", "HEYGEN_API_KEY": "x"},
        {"VIDEO_ALLOW_LIVE_CALLS": "true", "VIDEO_LIVE_SMOKE_TEST": "true"},
    ],
)
def test_live_smoke_guards_fail_closed(environment: dict[str, str]) -> None:
    with pytest.raises(ExternalInputBlocked):
        validate_live_smoke_guards("heygen", 1, 10, environment)


def test_live_smoke_guards_require_exactly_one_and_8_to_12_seconds() -> None:
    environment = {
        "VIDEO_ALLOW_LIVE_CALLS": "true",
        "VIDEO_LIVE_SMOKE_TEST": "true",
        "HEYGEN_API_KEY": "x",
    }
    validate_live_smoke_guards("heygen", 1, 8, environment)
    with pytest.raises(ExternalInputBlocked, match="exactly one"):
        validate_live_smoke_guards("heygen", 2, 10, environment)
    with pytest.raises(ExternalInputBlocked, match="8..12"):
        validate_live_smoke_guards("heygen", 1, 13, environment)


class RetryingProvider(FakeTalkingProvider):
    def __init__(self, fixture_video: Path):
        super().__init__(fixture_video)
        self.calls = 0

    def submit(self, request):
        self.calls += 1
        if self.calls == 1:
            raise RetryableVideoSubmissionError("safe transient", idempotency_safe=True)
        return super().submit(request)


class FailedWaitProvider(FakeTalkingProvider):
    def wait(self, task_id, timeout_seconds):
        return VideoTaskResult(task_id, VideoTaskStatus.TIMED_OUT, error_code="timeout")

    def download_results(self, *args, **kwargs):
        raise AssertionError("failed task must not download")


def test_submission_retry_stops_after_task_id_and_persists_it(
    video_project_root: Path, synthetic_video: Path
) -> None:
    storage = VideoRunStorage(video_project_root)
    run = storage.create_run("tooltip")
    provider = RetryingProvider(synthetic_video)
    request = replace(make_request(video_project_root), run_id=run.run_id)
    record = execute_provider_request(
        request, provider, storage, run, video_project_root / "outputs/talking_shots" / run.run_id
    )
    assert provider.calls == 2
    assert record.provider_task_id.startswith("fake-talking-")
    events = (run.path / "task-events.jsonl").read_text(encoding="utf-8")
    assert record.provider_task_id in events


def test_terminal_timeout_never_resubmits_or_downloads(video_project_root: Path) -> None:
    storage = VideoRunStorage(video_project_root)
    run = storage.create_run("tooltip")
    provider = FailedWaitProvider()
    request = replace(make_request(video_project_root), run_id=run.run_id)
    record = execute_provider_request(
        request, provider, storage, run, video_project_root / "outputs/talking_shots" / run.run_id
    )
    assert len(provider.submitted) == 1
    assert record.status is VideoTaskStatus.TIMED_OUT
    assert record.artifacts == ()


class AmbiguousSubmissionProvider(FakeTalkingProvider):
    def submit(self, request):
        self.submitted.append(request)
        raise ProviderSubmissionError("response lost after possible acceptance")


def test_ambiguous_submission_is_never_blindly_retried(video_project_root: Path) -> None:
    storage = VideoRunStorage(video_project_root)
    run = storage.create_run("tooltip")
    provider = AmbiguousSubmissionProvider()
    request = replace(make_request(video_project_root), run_id=run.run_id)
    with pytest.raises(ProviderSubmissionError, match="possible acceptance"):
        execute_provider_request(
            request,
            provider,
            storage,
            run,
            video_project_root / "outputs/talking_shots" / run.run_id,
        )
    assert len(provider.submitted) == 1


def test_video_download_retries_then_content_validates(
    tmp_path: Path, synthetic_video: Path
) -> None:
    calls = 0

    def downloader(_url: str, destination: Path, _timeout: float) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("temporary download failure")
        destination.write_bytes(synthetic_video.read_bytes())

    artifact = download_video(
        "https://example.test/output.mp4?signature=secret",
        tmp_path / "downloaded.mp4",
        provider_task_id="task-1",
        artifact_id="artifact-1",
        kind="talking",
        timeout_seconds=10,
        max_retries=2,
        downloader=downloader,
    )
    assert calls == 2
    assert artifact.width == 128
    assert artifact.height == 72
    assert artifact.source_url_redacted == "https://example.test/output.mp4"
