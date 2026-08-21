from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from lala_workflow.characters.domain import (
    CharacterStatus,
    MotionOperationState,
    PreviewArtifact,
)
from lala_workflow.characters.errors import PreviewUnavailableError
from lala_workflow.characters.motion_recovery import (
    MotionOperationExecutor,
    motion_request_fingerprint,
)
from lala_workflow.characters.preview import GeneratedPreview
from lala_workflow.characters.service import CharacterService
from lala_workflow.characters.storage import CharacterStorage
from lala_workflow.hashing import sha256_file
from lala_workflow.providers.base import ProviderValidationError
from lala_workflow.video.domain import (
    MediaArtifact,
    MotionVideoRequest,
    VideoTaskResult,
    VideoTaskStatus,
)
from lala_workflow.video.downloads import inspect_video


class HttpError(RuntimeError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"provider HTTP {status_code}")
        self.status_code = status_code


class FakeProvider:
    def __init__(
        self,
        video: Path,
        *,
        validate_error: Exception | None = None,
        submit_error: Exception | None = None,
        crash_after_task: bool = False,
        result_status: VideoTaskStatus = VideoTaskStatus.SUCCEEDED,
        download_error: Exception | None = None,
    ) -> None:
        self.video = video
        self.validate_error = validate_error
        self.submit_error = submit_error
        self.crash_after_task = crash_after_task
        self.result_status = result_status
        self.download_error = download_error
        self.sink = None
        self.submit_count = 0
        self.poll_count = 0
        self.download_count = 0
        self.download_retries = None
        self.http_request_count = 0

    def validate_request(self, _request) -> None:
        if self.validate_error:
            raise self.validate_error

    def set_task_created_sink(self, sink) -> None:
        self.sink = sink

    def submit(self, _request) -> str:
        self.submit_count += 1
        self.http_request_count += 1
        if self.submit_error:
            raise self.submit_error
        if self.sink:
            self.sink("motion-task-1", "request-1", 25.0)
        if self.crash_after_task:
            raise KeyboardInterrupt("simulated coordinator crash")
        return "motion-task-1"

    def wait(self, task_id: str, _timeout: float) -> VideoTaskResult:
        self.poll_count += 1
        if self.result_status is VideoTaskStatus.SUCCEEDED:
            return VideoTaskResult(
                task_id,
                self.result_status,
                ("https://example.test/motion.mp4",),
                estimated_credits=25.0,
                actual_credits=25.0,
            )
        return VideoTaskResult(
            task_id,
            self.result_status,
            error_code=self.result_status.value.lower(),
            error_message="simulated terminal status",
        )

    def download_results(self, result, output_dir, output_stem, _timeout, max_retries):
        self.download_count += 1
        self.download_retries = max_retries
        if self.download_error:
            raise self.download_error
        target = output_dir / f"{output_stem}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.video, target)
        info = inspect_video(target)
        return (
            MediaArtifact(
                artifact_id=output_stem,
                kind="motion",
                path=target,
                sha256=sha256_file(target),
                size_bytes=target.stat().st_size,
                mime_type="video/mp4",
                duration_seconds=info.duration_seconds,
                width=info.width,
                height=info.height,
                provider_task_id=result.provider_task_id,
            ),
        )


@pytest.fixture
def recovery_context(project_root, character_uploads, synthetic_video):
    service = CharacterService(project_root)
    imported = service.import_character(character_uploads, created_by="test")
    build = service.build(imported.character_id)
    profile = service.show(imported.character_id).profile
    static_path = project_root / "outputs/characters" / imported.character_id / "previews/static.png"
    static_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (128, 192), "purple").save(static_path)
    static = PreviewArtifact(
        kind="static",
        path=static_path.relative_to(project_root),
        sha256=sha256_file(static_path),
        mime_type="image/png",
        width=128,
        height=192,
        source_run_id="static-run",
        provider_task_id="static-task",
    )
    prompt_path = project_root / "prompts/character-motion-preview-v1.txt"
    request = MotionVideoRequest(
        request_id=f"{build.build_id}-motion-preview",
        run_id=build.build_id,
        preset="character_preview",
        shot_id="character_motion_preview",
        variation=1,
        provider="runway",
        model="gen4_turbo",
        image_path=static_path,
        image_sha256=static.sha256,
        prompt_path=prompt_path,
        prompt_text=prompt_path.read_text(encoding="utf-8"),
        prompt_sha256=sha256_file(prompt_path),
        ratio="1280:720",
        duration_seconds=5,
        seed=None,
        output_format="mp4",
        timeout_seconds=30,
        max_retries=2,
    )
    storage = CharacterStorage(project_root)
    executor = MotionOperationExecutor(project_root, storage, credit_cap=25, credit_usd=0.01)
    destination = static_path.with_name("motion.mp4")
    return profile, build, static, request, storage, executor, destination, synthetic_video


def _record(context):
    profile, _build, static, request, storage, *_rest = context
    fingerprint = motion_request_fingerprint(profile, static, request)
    return storage.load_motion_operation(profile.character_id, fingerprint)


def _override_record(context):
    profile, _build, static, request, storage, *_rest = context
    fingerprint = motion_request_fingerprint(profile, static, request)
    return storage.load_motion_override_operation(profile.character_id, fingerprint)


def _execute(context, provider, **kwargs):
    profile, _build, static, request, _storage, executor, destination, _video = context
    return executor.execute(
        profile=profile,
        static_preview=static,
        request=request,
        provider=provider,
        destination=destination,
        **kwargs,
    )


def test_failure_before_provider_submission_is_durable(recovery_context) -> None:
    provider = FakeProvider(
        recovery_context[-1], validate_error=ProviderValidationError("invalid request")
    )
    with pytest.raises(ProviderValidationError):
        _execute(recovery_context, provider)
    assert provider.submit_count == 0
    assert _record(recovery_context).state is MotionOperationState.FAILED_BEFORE_SUBMISSION


def test_task_id_is_persisted_before_coordinator_crash(recovery_context) -> None:
    provider = FakeProvider(recovery_context[-1], crash_after_task=True)
    with pytest.raises(KeyboardInterrupt):
        _execute(recovery_context, provider)
    record = _record(recovery_context)
    assert record.state is MotionOperationState.SUBMITTED
    assert record.provider_task_id == "motion-task-1"


@pytest.mark.parametrize("state", [MotionOperationState.SUBMITTED, MotionOperationState.POLLING])
def test_submitted_and_polling_operations_resume_without_submit(recovery_context, state) -> None:
    crashing = FakeProvider(recovery_context[-1], crash_after_task=True)
    with pytest.raises(KeyboardInterrupt):
        _execute(recovery_context, crashing)
    record = _record(recovery_context)
    if state is MotionOperationState.POLLING:
        recovery_context[4].write_motion_operation(replace(record, state=state))
    resumed = FakeProvider(recovery_context[-1])
    result = _execute(recovery_context, resumed)
    assert result.operation.state is MotionOperationState.SUCCEEDED
    assert resumed.submit_count == 0
    assert resumed.poll_count == 1


def test_succeeded_operation_reuses_artifact(recovery_context) -> None:
    first = FakeProvider(recovery_context[-1])
    completed = _execute(recovery_context, first)
    second = FakeProvider(recovery_context[-1])
    reused = _execute(recovery_context, second)
    assert reused.artifact.sha256 == completed.artifact.sha256
    assert second.submit_count == second.poll_count == second.download_count == 0


def test_submission_unknown_blocks_duplicate(recovery_context) -> None:
    provider = FakeProvider(recovery_context[-1])
    with pytest.raises(PreviewUnavailableError, match="duplicate paid submission"):
        _execute(recovery_context, provider, legacy_submission_unknown=True)
    assert provider.submit_count == 0
    assert _record(recovery_context).state is MotionOperationState.SUBMISSION_UNKNOWN


def test_interrupted_submitting_state_becomes_unknown_and_blocks(recovery_context) -> None:
    profile, _build, static, request, storage, executor, destination, video = recovery_context
    fingerprint = motion_request_fingerprint(profile, static, request)
    prepared = executor._prepared_record(profile, static, request, fingerprint)
    storage.write_motion_operation(
        replace(
            prepared,
            state=MotionOperationState.SUBMITTING,
            attempt=1,
            submission_started_at=prepared.prepared_at,
        )
    )
    provider = FakeProvider(video)
    with pytest.raises(PreviewUnavailableError, match="duplicate paid submission"):
        executor.execute(
            profile=profile,
            static_preview=static,
            request=request,
            provider=provider,
            destination=destination,
        )
    assert provider.submit_count == 0
    assert _record(recovery_context).state is MotionOperationState.SUBMISSION_UNKNOWN


def test_owner_risk_override_preserves_legacy_and_submits_exactly_once(
    recovery_context,
) -> None:
    initial = FakeProvider(recovery_context[-1])
    with pytest.raises(PreviewUnavailableError):
        _execute(recovery_context, initial, legacy_submission_unknown=True)
    legacy_path = recovery_context[4].motion_operation_path(
        recovery_context[0].character_id,
        _record(recovery_context).request_fingerprint,
    )
    legacy_bytes = legacy_path.read_bytes()
    provider = FakeProvider(recovery_context[-1])
    result = _execute(recovery_context, provider, owner_risk_override=True)
    override = _override_record(recovery_context)
    assert result.operation.state is MotionOperationState.SUCCEEDED
    assert provider.submit_count == 1
    assert legacy_path.read_bytes() == legacy_bytes
    assert _record(recovery_context).state is MotionOperationState.SUBMISSION_UNKNOWN
    assert override.owner_risk_override is True
    assert override.owner_risk_override_max_new_submissions == 1
    assert override.owner_risk_override_max_new_credits == 25
    assert override.owner_risk_override_max_new_usd == 0.25
    assert override.owner_risk_override_automatic_retries == 0
    assert override.legacy_submission_state == "SUBMISSION_STATE_UNKNOWN"


def test_ambiguous_owner_override_cannot_submit_again(recovery_context) -> None:
    with pytest.raises(PreviewUnavailableError):
        _execute(
            recovery_context,
            FakeProvider(recovery_context[-1]),
            legacy_submission_unknown=True,
        )
    first = FakeProvider(recovery_context[-1], submit_error=HttpError(503))
    with pytest.raises(PreviewUnavailableError):
        _execute(recovery_context, first, owner_risk_override=True)
    second = FakeProvider(recovery_context[-1])
    with pytest.raises(PreviewUnavailableError, match="duplicate paid submission"):
        _execute(recovery_context, second, owner_risk_override=True)
    assert first.submit_count == 1
    assert second.submit_count == 0
    assert _override_record(recovery_context).state is MotionOperationState.SUBMISSION_UNKNOWN


def test_failed_owner_override_exhausts_one_submission_cap(recovery_context) -> None:
    with pytest.raises(PreviewUnavailableError):
        _execute(
            recovery_context,
            FakeProvider(recovery_context[-1]),
            legacy_submission_unknown=True,
        )
    failed = FakeProvider(recovery_context[-1], result_status=VideoTaskStatus.FAILED)
    with pytest.raises(PreviewUnavailableError, match="terminal failure"):
        _execute(recovery_context, failed, owner_risk_override=True)
    retry = FakeProvider(recovery_context[-1])
    with pytest.raises(PreviewUnavailableError, match="cap is exhausted"):
        _execute(recovery_context, retry, owner_risk_override=True)
    assert failed.submit_count == 1
    assert retry.submit_count == 0


def test_request_fingerprint_is_deterministic(recovery_context) -> None:
    profile, _build, static, request, *_rest = recovery_context
    first = motion_request_fingerprint(profile, static, request)
    second = motion_request_fingerprint(profile, static, replace(request, request_id="different"))
    assert first == second


@pytest.mark.parametrize(
    ("status", "expected"),
    [(400, MotionOperationState.PROVIDER_REJECTED), (503, MotionOperationState.SUBMISSION_UNKNOWN)],
)
def test_provider_http_submission_states_are_classified(recovery_context, status, expected) -> None:
    provider = FakeProvider(recovery_context[-1], submit_error=HttpError(status))
    with pytest.raises(PreviewUnavailableError):
        _execute(recovery_context, provider)
    assert provider.submit_count == 1
    assert _record(recovery_context).state is expected


def test_poll_timeout_preserves_task_id(recovery_context) -> None:
    provider = FakeProvider(recovery_context[-1], result_status=VideoTaskStatus.TIMED_OUT)
    with pytest.raises(PreviewUnavailableError, match="timed out"):
        _execute(recovery_context, provider)
    record = _record(recovery_context)
    assert record.state is MotionOperationState.POLLING
    assert record.provider_task_id == "motion-task-1"


def test_download_failure_preserves_successful_task(recovery_context) -> None:
    provider = FakeProvider(recovery_context[-1], download_error=RuntimeError("download failed"))
    with pytest.raises(PreviewUnavailableError, match="successful provider task"):
        _execute(recovery_context, provider)
    record = _record(recovery_context)
    assert record.state is MotionOperationState.DOWNLOAD_FAILED
    assert record.provider_task_id == "motion-task-1"
    assert record.last_status == "SUCCEEDED"
    assert record.provider_output_urls
    assert all("?" not in url for url in record.provider_output_urls)


def test_automatic_paid_retry_is_disabled(recovery_context) -> None:
    provider = FakeProvider(recovery_context[-1], submit_error=HttpError(503))
    with pytest.raises(PreviewUnavailableError):
        _execute(recovery_context, provider)
    assert provider.submit_count == 1
    assert _record(recovery_context).automatic_retry == 0


def test_motion_recovery_does_not_regenerate_static(
    project_root, character_uploads, synthetic_video
) -> None:
    class StaticMustNotRun:
        def generate(self, *_args, **_kwargs):
            raise AssertionError("static generator must not run")

    class RecoverMotion:
        def preflight(self):
            return None

        def recover(self, _profile, _build, _static, destination, **_kwargs):
            shutil.copyfile(synthetic_video, destination)
            return GeneratedPreview(destination, provider_task_id="motion-task")

    service = CharacterService(
        project_root,
        static_preview_operation=StaticMustNotRun(),
        motion_preview_operation=RecoverMotion(),
    )
    profile = service.import_character(character_uploads, created_by="test")
    build = service.build(profile.character_id)
    static_path = project_root / "outputs/characters" / profile.character_id / "previews/static.png"
    static_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (128, 192), "purple").save(static_path)
    static = PreviewArtifact(
        kind="static",
        path=static_path.relative_to(project_root),
        sha256=sha256_file(static_path),
        mime_type="image/png",
        width=128,
        height=192,
    )
    service.storage.write_build(
        replace(build, status=CharacterStatus.FAILED, static_preview=static)
    )
    recovered = service.recover_motion(profile.character_id, live=True)
    assert recovered.status is CharacterStatus.READY_FOR_APPROVAL
    assert recovered.static_preview.sha256 == static.sha256
