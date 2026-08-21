from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Protocol

from ..domain import utc_now
from ..hashing import inspect_image, sha256_file
from ..video.downloads import inspect_video
from .domain import CharacterBuild, CharacterProfile, CharacterStatus, PreviewArtifact
from .errors import CharacterIntegrityError, PreviewUnavailableError
from .storage import CharacterStorage
from .motion_recovery import MotionOperationExecutor


@dataclass(frozen=True, slots=True)
class GeneratedPreview:
    path: Path
    source_run_id: str | None = None
    provider_task_id: str | None = None
    provenance: Mapping[str, Any] | None = None
    subject_lock: Mapping[str, Any] | None = None


class StaticCharacterPreviewOperation(Protocol):
    def generate(
        self, profile: CharacterProfile, build: CharacterBuild, destination: Path
    ) -> GeneratedPreview: ...


class MotionCharacterPreviewOperation(Protocol):
    def generate(
        self,
        profile: CharacterProfile,
        build: CharacterBuild,
        static_preview: PreviewArtifact,
        destination: Path,
    ) -> GeneratedPreview: ...


class PreviewCoordinator:
    def __init__(
        self,
        project_root: Path,
        *,
        storage: CharacterStorage | None = None,
        static_operation: StaticCharacterPreviewOperation | None = None,
        motion_operation: MotionCharacterPreviewOperation | None = None,
    ) -> None:
        self.root = project_root.resolve()
        self.storage = storage or CharacterStorage(self.root)
        self.static_operation = static_operation
        self.motion_operation = motion_operation

    def create_build(self, profile: CharacterProfile) -> CharacterBuild:
        return CharacterBuild(
            build_id=f"build-{utc_now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}",
            character_id=profile.character_id,
            character_profile_version=profile.profile_version,
            character_profile_sha256=profile.profile_sha256,
            status=CharacterStatus.READY_FOR_GENERATION,
            created_at=utc_now().isoformat(),
            selected_references=tuple(
                {
                    "logical_name": item.logical_name,
                    "path": item.path.as_posix(),
                    "sha256": item.sha256,
                    "role": item.role,
                    "tag": item.tag,
                }
                for item in profile.references.values()
            ),
            technical_checks={
                "profile_integrity": "PASS",
                "static_preview": "NOT_RUN",
                "motion_preview": "NOT_RUN",
            },
            events_path=Path(
                f"outputs/characters/{profile.character_id}/provenance/events.jsonl"
            ),
        )

    def run(
        self,
        profile: CharacterProfile,
        build: CharacterBuild,
        *,
        live: bool,
    ) -> CharacterBuild:
        if not live:
            return replace(
                build,
                status=CharacterStatus.READY_FOR_GENERATION,
                technical_checks={
                    **dict(build.technical_checks),
                    "static_preview": "NOT_RUN",
                    "motion_preview": "NOT_RUN",
                    "paid_calls": "0",
                },
            )
        if self.static_operation is None or self.motion_operation is None:
            raise PreviewUnavailableError(
                "live preview operations are not configured",
                user_message="预览生成尚未获授权；人物资料已安全保存，可稍后继续。",
            )
        for operation in (self.static_operation, self.motion_operation):
            preflight = getattr(operation, "preflight", None)
            if callable(preflight):
                preflight()
        preview_root = self.storage.preview_root(profile.character_id)
        attempt = uuid.uuid4().hex[:8]
        current = replace(build, status=CharacterStatus.READY_FOR_PREVIEW)
        try:
            static_destination = preview_root / f"{build.build_id}-{attempt}-static.png"
            static_generated = self.static_operation.generate(
                profile, current, static_destination
            )
            static = self._store_static(profile, static_generated, static_destination)
            current = replace(
                current,
                static_preview=static,
                technical_checks={**dict(current.technical_checks), "static_preview": "PASS"},
            )
            motion_destination = preview_root / f"{build.build_id}-{attempt}-motion.mp4"
            motion_generated = self.motion_operation.generate(
                profile, current, static, motion_destination
            )
            motion = self._store_motion(profile, motion_generated, motion_destination)
            subject_lock = dict(motion_generated.subject_lock or {})
            if subject_lock:
                subject_lock.setdefault("authority", "diagnostic_only_not_automatic_approval")
            return replace(
                current,
                status=CharacterStatus.READY_FOR_APPROVAL,
                motion_preview=motion,
                technical_checks={
                    **dict(current.technical_checks),
                    "motion_preview": "PASS",
                },
                subject_lock=subject_lock or None,
            )
        except Exception as exc:
            code = getattr(exc, "code", "preview_failed")
            return replace(
                current,
                status=CharacterStatus.FAILED,
                technical_checks={**dict(current.technical_checks), "preview_pipeline": "FAIL"},
                errors=(
                    *current.errors,
                    {
                        "code": str(code),
                        "message": "预览生成未完成；已有证据已保留，当前人物未改变。",
                    },
                ),
            )

    def revalidate(self, build: CharacterBuild) -> None:
        if build.static_preview is None or build.motion_preview is None:
            raise CharacterIntegrityError("both static and motion previews are required")
        self._validate_artifact_path(build.static_preview)
        self._validate_artifact_path(build.motion_preview)

    def recover_motion(
        self,
        profile: CharacterProfile,
        build: CharacterBuild,
        *,
        live: bool,
        legacy_submission_unknown: bool,
    ) -> CharacterBuild:
        if not live:
            raise PreviewUnavailableError("motion recovery requires explicit --live")
        if build.static_preview is None:
            raise CharacterIntegrityError("motion recovery requires the existing static preview")
        self._validate_artifact_path(build.static_preview)
        if build.motion_preview is not None:
            self._validate_artifact_path(build.motion_preview)
            return build
        if self.motion_operation is None:
            raise PreviewUnavailableError("motion preview operation is not configured")
        preflight = getattr(self.motion_operation, "preflight", None)
        if callable(preflight):
            preflight()
        recover = getattr(self.motion_operation, "recover", None)
        if not callable(recover):
            raise PreviewUnavailableError("motion preview operation does not support recovery")
        destination = self.storage.preview_root(profile.character_id) / (
            f"{build.build_id}-motion-recovery.mp4"
        )
        generated = recover(
            profile,
            build,
            build.static_preview,
            destination,
            legacy_submission_unknown=legacy_submission_unknown,
        )
        motion = self._store_motion(profile, generated, destination)
        subject_lock = dict(generated.subject_lock or {})
        if subject_lock:
            subject_lock.setdefault("authority", "diagnostic_only_not_automatic_approval")
        return replace(
            build,
            status=CharacterStatus.READY_FOR_APPROVAL,
            motion_preview=motion,
            technical_checks={
                **dict(build.technical_checks),
                "static_preview": "PASS_REUSED",
                "motion_preview": "PASS",
                "preview_pipeline": "PASS_RECOVERED",
            },
            subject_lock=subject_lock or None,
        )

    def _store_static(
        self, profile: CharacterProfile, generated: GeneratedPreview, target: Path
    ) -> PreviewArtifact:
        target = self._copy_or_accept(generated.path, target)
        info = inspect_image(target)
        return PreviewArtifact(
            kind="static",
            path=target.relative_to(self.root),
            sha256=sha256_file(target),
            mime_type=info.mime_type,
            width=info.width,
            height=info.height,
            source_run_id=generated.source_run_id,
            provider_task_id=generated.provider_task_id,
            provenance={
                "character_id": profile.character_id,
                "character_profile_sha256": profile.profile_sha256,
                "production_approved": False,
                **dict(generated.provenance or {}),
            },
        )

    def _store_motion(
        self, profile: CharacterProfile, generated: GeneratedPreview, target: Path
    ) -> PreviewArtifact:
        target = self._copy_or_accept(generated.path, target)
        info = inspect_video(target)
        return PreviewArtifact(
            kind="motion",
            path=target.relative_to(self.root),
            sha256=sha256_file(target),
            mime_type="video/mp4",
            width=info.width,
            height=info.height,
            duration_seconds=info.duration_seconds,
            source_run_id=generated.source_run_id,
            provider_task_id=generated.provider_task_id,
            provenance={
                "character_id": profile.character_id,
                "character_profile_sha256": profile.profile_sha256,
                "preview_only": True,
                "production_approved": False,
                **dict(generated.provenance or {}),
            },
        )

    def _copy_or_accept(self, source: Path, target: Path) -> Path:
        if source.is_symlink():
            raise CharacterIntegrityError("preview operation returned a missing or unsafe file")
        resolved = source.resolve()
        if not resolved.is_file():
            raise CharacterIntegrityError("preview operation returned a missing or unsafe file")
        if resolved == target.resolve():
            return target
        if target.exists():
            raise CharacterIntegrityError("preview evidence target collision")
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            with resolved.open("rb") as incoming, temporary.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def _validate_artifact_path(self, artifact: PreviewArtifact) -> None:
        source = (self.root / artifact.path).resolve()
        allowed = (self.storage.outputs_root / artifact.provenance.get("character_id", "")).resolve()
        try:
            source.relative_to(allowed)
        except ValueError as exc:
            raise CharacterIntegrityError("preview artifact is outside character outputs") from exc
        if not source.is_file() or source.is_symlink() or sha256_file(source) != artifact.sha256:
            raise CharacterIntegrityError("preview artifact digest mismatch")
        if artifact.kind == "static":
            inspect_image(source)
        else:
            inspect_video(source)


class StaticRunnerPreviewOperation:
    """Adapter over the existing static runner with a staging-only 3-reference request."""

    def __init__(self, project_root: Path, *, environment: Mapping[str, str] | None = None) -> None:
        self.root = project_root.resolve()
        self.environment = dict(os.environ if environment is None else environment)

    def preflight(self) -> None:
        if self.environment.get("RUNWAY_ALLOW_LIVE_CALLS") != "true":
            raise PreviewUnavailableError("static preview requires exact RUNWAY_ALLOW_LIVE_CALLS=true")
        if not str(self.environment.get("RUNWAYML_API_SECRET") or "").strip():
            raise PreviewUnavailableError("static preview requires a local Runway credential")

    def generate(
        self, profile: CharacterProfile, build: CharacterBuild, destination: Path
    ) -> GeneratedPreview:
        from ..runner import RunOptions, run_generation

        outcome = run_generation(
            self.root,
            RunOptions(
                preset="baseline_identity",
                count=1,
                concurrency=1,
                live=True,
                character_id=profile.character_id,
                allow_staging_character=True,
                reference_names=("face", "three_quarter", "full_body"),
                prompt_file=Path("prompts/character-static-preview-v1.txt"),
            ),
            environment=self.environment,
        )
        if len(outcome.result.outputs) != 1:
            raise PreviewUnavailableError("static preview did not produce exactly one result")
        artifact = outcome.result.outputs[0]
        task = outcome.result.tasks[0] if outcome.result.tasks else {}
        request = outcome.result.requests[0] if outcome.result.requests else {}
        prompt = request.get("prompt") if isinstance(request, Mapping) else {}
        references = request.get("references") if isinstance(request, Mapping) else ()
        return GeneratedPreview(
            self.root / artifact.file,
            source_run_id=outcome.run_id,
            provider_task_id=str(task.get("provider_task_id") or "") or None,
            provenance={
                "static_run_status": outcome.result.status.value,
                "prompt_sha256": prompt.get("sha256") if isinstance(prompt, Mapping) else None,
                "selected_reference_hashes": {
                    str(item.get("name")): str(item.get("sha256"))
                    for item in references or ()
                    if isinstance(item, Mapping)
                },
                "model": "gen4_image",
                "cost_status": "UNKNOWN_NOT_EXPOSED_BY_PROVIDER",
                "pricing_contract": "configs/generation.yaml",
                "estimated_credits": None,
                "estimated_usd": None,
            },
        )


class RunwayMotionPreviewOperation:
    """One-submit preview-only Runway motion adapter; no approved-keyframe mutation."""

    def __init__(
        self,
        project_root: Path,
        *,
        environment: Mapping[str, str] | None = None,
        max_runway_credits: float = 25.0,
        provider: Any | None = None,
        storage: CharacterStorage | None = None,
    ) -> None:
        self.root = project_root.resolve()
        self.environment = dict(os.environ if environment is None else environment)
        self.max_runway_credits = max_runway_credits
        self.provider = provider
        self.storage = storage or CharacterStorage(self.root)

    def preflight(self) -> None:
        if self.environment.get("VIDEO_ALLOW_LIVE_CALLS") != "true":
            raise PreviewUnavailableError("motion preview requires exact VIDEO_ALLOW_LIVE_CALLS=true")
        if self.environment.get("VIDEO_MOTION_LIVE_SMOKE_TEST") != "true":
            raise PreviewUnavailableError(
                "motion preview requires exact VIDEO_MOTION_LIVE_SMOKE_TEST=true"
            )
        if not str(self.environment.get("RUNWAYML_API_SECRET") or "").strip():
            raise PreviewUnavailableError("motion preview requires a local Runway credential")
        if self.max_runway_credits <= 0 or self.max_runway_credits > 25:
            raise PreviewUnavailableError("motion preview requires a credit cap no greater than 25")

    def generate(
        self,
        profile: CharacterProfile,
        build: CharacterBuild,
        static_preview: PreviewArtifact,
        destination: Path,
    ) -> GeneratedPreview:
        return self._generate(
            profile,
            build,
            static_preview,
            destination,
            legacy_submission_unknown=False,
        )

    def recover(
        self,
        profile: CharacterProfile,
        build: CharacterBuild,
        static_preview: PreviewArtifact,
        destination: Path,
        *,
        legacy_submission_unknown: bool,
    ) -> GeneratedPreview:
        return self._generate(
            profile,
            build,
            static_preview,
            destination,
            legacy_submission_unknown=legacy_submission_unknown,
        )

    def _generate(
        self,
        profile: CharacterProfile,
        build: CharacterBuild,
        static_preview: PreviewArtifact,
        destination: Path,
        *,
        legacy_submission_unknown: bool,
    ) -> GeneratedPreview:
        from ..hashing import sha256_file
        from ..providers.runway_video import RunwayMotionProvider
        from ..video.config import load_video_config
        from ..video.domain import MotionVideoRequest, VideoTaskStatus
        from ..video.prompts import load_video_prompt

        config = load_video_config(self.root, require_inputs=False)
        definition = config.providers.get("runway")
        if definition is None or definition.responsibility != "motion":
            raise PreviewUnavailableError("Runway motion provider is not configured")
        prompt = load_video_prompt(self.root, Path("prompts/character-motion-preview-v1.txt"))
        source = (self.root / static_preview.path).resolve()
        request = MotionVideoRequest(
            request_id=f"{build.build_id}-motion-preview",
            run_id=build.build_id,
            preset="character_preview",
            shot_id="character_motion_preview",
            variation=1,
            provider="runway",
            model="gen4_turbo",
            image_path=source,
            image_sha256=sha256_file(source),
            prompt_path=self.root / prompt.path,
            prompt_text=prompt.text,
            prompt_sha256=prompt.sha256,
            ratio="1280:720",
            duration_seconds=5,
            seed=None,
            output_format="mp4",
            timeout_seconds=config.limits.provider_timeout_seconds,
            max_retries=config.limits.max_retries,
        )
        provider = self.provider or RunwayMotionProvider(
            definition, api_key=str(self.environment["RUNWAYML_API_SECRET"])
        )
        credit_usd = float(definition.settings.get("credit_usd") or 0.01)
        outcome = MotionOperationExecutor(
            self.root,
            self.storage,
            credit_cap=self.max_runway_credits,
            credit_usd=credit_usd,
        ).execute(
            profile=profile,
            static_preview=static_preview,
            request=request,
            provider=provider,
            destination=destination,
            legacy_submission_unknown=legacy_submission_unknown,
        )
        artifact = outcome.artifact
        operation = outcome.operation
        if operation.actual_credits is not None and operation.actual_credits > self.max_runway_credits:
            raise PreviewUnavailableError("motion preview actual credits exceeded the explicit cap")
        return GeneratedPreview(
            artifact.path,
            source_run_id=build.build_id,
            provider_task_id=operation.provider_task_id,
            provenance={
                "model": "gen4_turbo",
                "duration_seconds": 5,
                "prompt_sha256": prompt.sha256,
                "static_preview_sha256": static_preview.sha256,
                "max_runway_credits": self.max_runway_credits,
                "operation_id": operation.operation_id,
                "request_fingerprint": operation.request_fingerprint,
                "estimated_runway_credits": operation.estimated_credits,
                "actual_runway_credits": operation.actual_credits,
                "estimated_usd": operation.estimated_cost,
                "actual_usd": operation.actual_cost,
                "cost_status": (
                    "ACTUAL" if operation.actual_cost is not None else "ESTIMATED"
                ),
                "automatic_paid_retry": 0,
            },
        )
