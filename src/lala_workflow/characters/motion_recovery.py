from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ..domain import utc_now
from ..hashing import sha256_file
from ..providers.base import ProviderValidationError
from ..redaction import redact_text
from ..video.domain import MediaArtifact, MotionVideoRequest, VideoTaskResult, VideoTaskStatus
from ..video.downloads import inspect_video, redacted_url
from .domain import (
    CharacterProfile,
    MotionOperationRecord,
    MotionOperationState,
    PreviewArtifact,
)
from .errors import (
    CharacterIntegrityError,
    MotionSubmissionUnknownError,
    PreviewUnavailableError,
)
from .storage import CharacterStorage


PURPOSE = "candidate_character_motion_preview"
OWNER_RISK_OVERRIDE_REASON = (
    "Owner accepts possible duplicate billing risk for the unrecoverable legacy Candidate 16 "
    "motion attempt and authorizes exactly one new motion-only submission after persistence/"
    "recovery protections were fixed and fully tested."
)


@dataclass(frozen=True, slots=True)
class MotionExecutionOutcome:
    artifact: MediaArtifact
    operation: MotionOperationRecord


def motion_request_fingerprint(
    profile: CharacterProfile,
    static_preview: PreviewArtifact,
    request: MotionVideoRequest,
) -> str:
    payload = {
        "provider": request.provider,
        "model": request.model,
        "purpose": PURPOSE,
        "character_id": profile.character_id,
        "source_ids": sorted(profile.references),
        "source_sha256": {
            name: profile.references[name].sha256 for name in sorted(profile.references)
        },
        "motion_source_sha256": static_preview.sha256,
        "duration_seconds": request.duration_seconds,
        "resolution": request.ratio,
        "prompt_sha256": request.prompt_sha256,
        "seed": request.seed,
        "output_format": request.output_format,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class MotionOperationExecutor:
    def __init__(
        self,
        project_root: Path,
        storage: CharacterStorage,
        *,
        credit_cap: float,
        credit_usd: float,
    ) -> None:
        self.root = project_root.resolve()
        self.storage = storage
        self.credit_cap = credit_cap
        self.credit_usd = credit_usd

    def execute(
        self,
        *,
        profile: CharacterProfile,
        static_preview: PreviewArtifact,
        request: MotionVideoRequest,
        provider: Any,
        destination: Path,
        legacy_submission_unknown: bool = False,
        owner_risk_override: bool = False,
    ) -> MotionExecutionOutcome:
        fingerprint = motion_request_fingerprint(profile, static_preview, request)
        legacy_record = self.storage.load_motion_operation(profile.character_id, fingerprint)
        if owner_risk_override:
            if (
                legacy_record is None
                or legacy_record.state is not MotionOperationState.SUBMISSION_UNKNOWN
            ):
                raise CharacterIntegrityError(
                    "owner-risk override requires preserved legacy SUBMISSION_UNKNOWN evidence"
                )
            record = self.storage.load_motion_override_operation(
                profile.character_id, fingerprint
            )
        else:
            record = legacy_record
        if record is None:
            record = self._prepared_record(profile, static_preview, request, fingerprint)
            if owner_risk_override:
                record = replace(
                    record,
                    operation_id=f"character-motion-{fingerprint[:20]}-owner-risk-override-001",
                    owner_risk_override=True,
                    owner_risk_override_reason=OWNER_RISK_OVERRIDE_REASON,
                    owner_risk_override_max_new_submissions=1,
                    owner_risk_override_max_new_credits=25.0,
                    owner_risk_override_max_new_usd=0.25,
                    owner_risk_override_automatic_retries=0,
                    legacy_operation_id=legacy_record.operation_id if legacy_record else None,
                    legacy_submission_state="SUBMISSION_STATE_UNKNOWN",
                )
            self.storage.write_motion_operation(record)
            if legacy_submission_unknown and not owner_risk_override:
                record = replace(
                    record,
                    state=MotionOperationState.SUBMISSION_UNKNOWN,
                    attempt=1,
                    error_stage="legacy_reconciliation",
                    error_category="missing_provider_acceptance_evidence",
                    sanitized_error=(
                        "legacy motion attempt has no durable provider task or rejection evidence"
                    ),
                )
                self.storage.write_motion_operation(record)

        if record.state is MotionOperationState.SUBMITTING:
            record = replace(
                record,
                state=MotionOperationState.SUBMISSION_UNKNOWN,
                error_stage="submission",
                error_category="interrupted_while_submitting",
                sanitized_error=(
                    "operation resumed from SUBMITTING without a durable provider task ID"
                ),
            )
            self.storage.write_motion_operation(record)

        if record.state is MotionOperationState.SUBMISSION_UNKNOWN:
            raise MotionSubmissionUnknownError(
                "motion submission state is unknown; duplicate paid submission is blocked"
            )
        if record.state is MotionOperationState.SUCCEEDED:
            return MotionExecutionOutcome(self._reuse_artifact(record), record)
        try:
            provider.validate_request(request)
        except Exception as exc:
            record = replace(
                record,
                state=MotionOperationState.FAILED_BEFORE_SUBMISSION,
                error_stage="validation",
                error_category="before_provider_submission",
                sanitized_error=self._sanitize_error(exc),
            )
            self.storage.write_motion_operation(record)
            raise
        if record.state is MotionOperationState.DOWNLOAD_FAILED:
            # Query the durable task again for a fresh signed URL; signed query strings are never
            # persisted in runtime evidence.
            return self._poll(record, request, provider, destination)
        if record.state in {MotionOperationState.SUBMITTED, MotionOperationState.POLLING}:
            return self._poll(record, request, provider, destination)
        if record.state not in {
            MotionOperationState.PREPARED,
            MotionOperationState.FAILED_BEFORE_SUBMISSION,
            MotionOperationState.PROVIDER_REJECTED,
            MotionOperationState.PROVIDER_FAILED,
        }:
            raise CharacterIntegrityError(f"unsupported motion operation state: {record.state.value}")
        if (
            record.owner_risk_override
            and record.attempt >= int(record.owner_risk_override_max_new_submissions or 0)
        ):
            raise PreviewUnavailableError(
                "owner-risk motion override submission cap is exhausted; no retry is allowed"
            )
        return self._submit(record, request, provider, destination)

    def _prepared_record(
        self,
        profile: CharacterProfile,
        static_preview: PreviewArtifact,
        request: MotionVideoRequest,
        fingerprint: str,
    ) -> MotionOperationRecord:
        estimate = self._estimated_credits(request)
        return MotionOperationRecord(
            operation_id=f"character-motion-{fingerprint[:20]}",
            request_fingerprint=fingerprint,
            provider=request.provider,
            model=request.model,
            purpose=PURPOSE,
            character_id=profile.character_id,
            source_ids=tuple(sorted(profile.references)),
            source_sha256={
                name: profile.references[name].sha256 for name in sorted(profile.references)
            },
            motion_source_sha256=static_preview.sha256,
            prompt_sha256=request.prompt_sha256,
            duration_seconds=request.duration_seconds,
            resolution=request.ratio,
            credit_cap=self.credit_cap,
            usd_cap=self.credit_cap * self.credit_usd,
            attempt=0,
            automatic_retry=0,
            state=MotionOperationState.PREPARED,
            prepared_at=utc_now().isoformat(),
            estimated_credits=estimate,
            estimated_cost=estimate * self.credit_usd,
        )

    def _submit(
        self,
        record: MotionOperationRecord,
        request: MotionVideoRequest,
        provider: Any,
        destination: Path,
    ) -> MotionExecutionOutcome:
        started = utc_now().isoformat()
        record = replace(
            record,
            state=MotionOperationState.SUBMITTING,
            attempt=record.attempt + 1,
            submission_started_at=started,
            submission_completed_at=None,
            provider_task_id=None,
            provider_request_id=None,
            last_status=None,
            last_polled_at=None,
            provider_output_urls=(),
            artifact_path=None,
            artifact_sha256=None,
            error_stage=None,
            error_category=None,
            sanitized_error=None,
        )
        self.storage.write_motion_operation(record)

        def persist_task(
            task_id: str, provider_request_id: str | None, estimated_credits: float | None
        ) -> None:
            nonlocal record
            record = replace(
                record,
                state=MotionOperationState.SUBMITTED,
                submission_completed_at=utc_now().isoformat(),
                provider_task_id=task_id,
                provider_request_id=provider_request_id,
                estimated_credits=(
                    estimated_credits
                    if estimated_credits is not None
                    else record.estimated_credits
                ),
                estimated_cost=(
                    estimated_credits * self.credit_usd
                    if estimated_credits is not None
                    else record.estimated_cost
                ),
            )
            self.storage.write_motion_operation(record)

        set_sink = getattr(provider, "set_task_created_sink", None)
        if callable(set_sink):
            set_sink(persist_task)
        before_http_count = getattr(provider, "http_request_count", None)
        try:
            task_id = provider.submit(request)
        except Exception as exc:
            if record.provider_task_id:
                return self._poll(record, request, provider, destination)
            after_http_count = getattr(provider, "http_request_count", None)
            state, category = self._submission_failure_state(
                exc, before_http_count, after_http_count
            )
            record = replace(
                record,
                state=state,
                error_stage="submission",
                error_category=category,
                sanitized_error=self._sanitize_error(exc),
            )
            self.storage.write_motion_operation(record)
            error_type = (
                MotionSubmissionUnknownError
                if state is MotionOperationState.SUBMISSION_UNKNOWN
                else PreviewUnavailableError
            )
            raise error_type(
                f"motion provider submission did not produce a recoverable task: {state.value}"
            ) from exc
        finally:
            if callable(set_sink):
                set_sink(None)
        if not record.provider_task_id:
            persist_task(str(task_id), None, None)
        return self._poll(record, request, provider, destination)

    def _poll(
        self,
        record: MotionOperationRecord,
        request: MotionVideoRequest,
        provider: Any,
        destination: Path,
    ) -> MotionExecutionOutcome:
        if not record.provider_task_id:
            raise CharacterIntegrityError("cannot poll motion operation without task ID")
        record = replace(
            record,
            state=MotionOperationState.POLLING,
            last_polled_at=utc_now().isoformat(),
            error_stage=None,
            error_category=None,
            sanitized_error=None,
        )
        self.storage.write_motion_operation(record)
        try:
            result: VideoTaskResult = provider.wait(
                record.provider_task_id, request.timeout_seconds
            )
        except Exception as exc:
            record = replace(
                record,
                error_stage="poll",
                error_category="poll_exception",
                sanitized_error=self._sanitize_error(exc),
                last_polled_at=utc_now().isoformat(),
            )
            self.storage.write_motion_operation(record)
            raise PreviewUnavailableError("motion polling failed; durable task can be resumed") from exc
        record = replace(
            record,
            last_status=result.status.value,
            last_polled_at=utc_now().isoformat(),
            estimated_credits=result.estimated_credits or record.estimated_credits,
            estimated_cost=(
                result.estimated_credits * self.credit_usd
                if result.estimated_credits is not None
                else record.estimated_cost
            ),
            actual_credits=result.actual_credits,
            actual_cost=(
                result.actual_credits * self.credit_usd
                if result.actual_credits is not None
                else None
            ),
            provider_output_urls=tuple(redacted_url(url) for url in result.output_urls),
        )
        if result.status is VideoTaskStatus.SUCCEEDED:
            self.storage.write_motion_operation(record)
            return self._download(record, request, provider, destination, result=result)
        if result.status is VideoTaskStatus.TIMED_OUT:
            record = replace(
                record,
                state=MotionOperationState.POLLING,
                error_stage="poll",
                error_category="timeout",
                sanitized_error=result.error_message or "provider polling timed out",
            )
            self.storage.write_motion_operation(record)
            raise PreviewUnavailableError("motion polling timed out; durable task can be resumed")
        record = replace(
            record,
            state=MotionOperationState.PROVIDER_FAILED,
            error_stage="provider_task",
            error_category=result.error_code or result.status.value.lower(),
            sanitized_error=result.error_message or result.status.value,
        )
        self.storage.write_motion_operation(record)
        raise PreviewUnavailableError("motion provider task reached a terminal failure")

    def _download(
        self,
        record: MotionOperationRecord,
        request: MotionVideoRequest,
        provider: Any,
        destination: Path,
        *,
        result: VideoTaskResult | None = None,
    ) -> MotionExecutionOutcome:
        if not record.provider_task_id:
            raise CharacterIntegrityError("cannot download motion operation without task ID")
        result = result or VideoTaskResult(
            record.provider_task_id,
            VideoTaskStatus.SUCCEEDED,
            record.provider_output_urls,
            estimated_credits=record.estimated_credits,
            actual_credits=record.actual_credits,
        )
        try:
            artifacts = provider.download_results(
                result,
                destination.parent,
                destination.stem,
                request.timeout_seconds,
                0,
            )
            if len(artifacts) != 1:
                raise CharacterIntegrityError("motion preview did not produce exactly one result")
            artifact = artifacts[0]
            info = inspect_video(artifact.path)
            if info.duration_seconds <= 0 or artifact.path.stat().st_size <= 0:
                raise CharacterIntegrityError("motion preview artifact is invalid")
        except Exception as exc:
            record = replace(
                record,
                state=MotionOperationState.DOWNLOAD_FAILED,
                error_stage="download",
                error_category="download_or_validation_failure",
                sanitized_error=self._sanitize_error(exc),
            )
            self.storage.write_motion_operation(record)
            raise PreviewUnavailableError(
                "motion download failed; successful provider task is preserved"
            ) from exc
        try:
            relative = artifact.path.resolve().relative_to(self.root)
        except ValueError as exc:
            raise CharacterIntegrityError("motion artifact is outside project root") from exc
        record = replace(
            record,
            state=MotionOperationState.SUCCEEDED,
            artifact_path=relative,
            artifact_sha256=sha256_file(artifact.path),
            error_stage=None,
            error_category=None,
            sanitized_error=None,
        )
        self.storage.write_motion_operation(record)
        return MotionExecutionOutcome(artifact, record)

    def _reuse_artifact(self, record: MotionOperationRecord) -> MediaArtifact:
        if record.artifact_path is None or record.artifact_sha256 is None:
            raise CharacterIntegrityError("successful motion operation artifact is missing")
        path = (self.root / record.artifact_path).resolve()
        if not path.is_file() or sha256_file(path) != record.artifact_sha256:
            raise CharacterIntegrityError("successful motion operation artifact digest mismatch")
        info = inspect_video(path)
        return MediaArtifact(
            artifact_id=record.operation_id,
            kind="motion",
            path=path,
            sha256=record.artifact_sha256,
            size_bytes=path.stat().st_size,
            mime_type="video/mp4",
            width=info.width,
            height=info.height,
            duration_seconds=info.duration_seconds,
            provider_task_id=str(record.provider_task_id),
        )

    def _estimated_credits(self, request: MotionVideoRequest) -> float:
        return min(self.credit_cap, float(request.duration_seconds) * 5.0)

    def _sanitize_error(self, exc: BaseException) -> str:
        return redact_text(str(exc), secrets=self.storage.secrets) or type(exc).__name__

    @staticmethod
    def _submission_failure_state(
        exc: BaseException, before_http_count: Any, after_http_count: Any
    ) -> tuple[MotionOperationState, str]:
        if isinstance(exc, ProviderValidationError) or (
            isinstance(before_http_count, int)
            and isinstance(after_http_count, int)
            and after_http_count == before_http_count
        ):
            return MotionOperationState.FAILED_BEFORE_SUBMISSION, "before_provider_submission"
        current: BaseException | None = exc
        while current is not None:
            status = getattr(current, "status_code", None)
            if isinstance(status, int):
                if 400 <= status < 500:
                    return MotionOperationState.PROVIDER_REJECTED, f"provider_http_{status}"
                if status >= 500:
                    return MotionOperationState.SUBMISSION_UNKNOWN, f"provider_http_{status}"
            current = current.__cause__
        return MotionOperationState.SUBMISSION_UNKNOWN, "ambiguous_transport_or_provider_error"
