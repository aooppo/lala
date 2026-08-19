from __future__ import annotations

import os
import json
import shutil
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from ..domain import to_primitive
from ..hashing import sha256_file
from .config import VideoConfigError, load_video_config
from .costing import estimate_plan_cost
from .domain import (
    ApprovedAudio,
    ApprovedKeyframe,
    MotionVideoRequest,
    ScriptRecord,
    ShotPlan,
    TalkingVideoRequest,
    VideoProjectConfig,
    VideoTaskStatus,
)
from .execution import (
    ExecutionRecord,
    execute_provider_request,
    validate_live_provider_guard,
    validate_live_smoke_guards,
)
from .planning import build_shot_plan
from .reporting import blank_review_rows, read_video_summary, summary_markdown
from .review import ReviewError, load_external_review_row
from .storage import QA_FIELDS, VideoRunContext, VideoRunStorage
from .validation import ExternalInputBlocked
from .voice import resolve_approved_audio, resolve_or_synthesize_audio


@dataclass(frozen=True, slots=True)
class VideoRunOptions:
    preset: str
    action: str = "generate"
    single_shot: bool = False
    talking_variations: int | None = None
    motion_variations: int | None = None
    keyframe_id: str | None = None
    audio_override: Path | None = None
    live: bool = False
    smoke_run_id: str | None = None
    smoke_review_file: Path | None = None
    provider_name: str | None = None


@dataclass(frozen=True, slots=True)
class VideoRunOutcome:
    run_id: str
    run_dir: Path
    context: VideoRunContext
    plan: ShotPlan
    provider_call_count: int
    submission_count: int
    status: str


def validate_video_project(project_root: Path) -> dict[str, Any]:
    config = load_video_config(project_root, require_inputs=True)
    for preset in config.presets.values():
        script = _script(config, preset.script_id)
        if script.script_id in config.voice_profile.script_audio:
            resolve_approved_audio(config, script)
        build_shot_plan(config, preset.name)
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise VideoConfigError("FFmpeg and FFprobe are required for video workflows")
    return {
        "status": "valid",
        "keyframes": len(config.keyframes),
        "scripts": sorted(config.scripts),
        "presets": sorted(config.presets),
        "providers_verified_on": config.verified_on,
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "paid_calls": 0,
    }


def preview_video(project_root: Path, options: VideoRunOptions) -> VideoRunOutcome:
    if options.live:
        raise ValueError("preview_video cannot execute live work")
    config = load_video_config(project_root, require_inputs=True)
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise VideoConfigError("FFmpeg and FFprobe are required for video preview and assembly")
    if options.preset not in config.presets:
        raise VideoConfigError(f"unknown video preset: {options.preset}")
    preset = config.presets[options.preset]
    script = _script(config, preset.script_id)
    keyframe = _keyframe(config, options.keyframe_id)
    if script.script_id in config.voice_profile.script_audio:
        audio: ApprovedAudio | None = resolve_approved_audio(
            config, script, override=options.audio_override
        )
    else:
        if options.audio_override is not None:
            raise VideoConfigError("audio override is unavailable in cloned-voice preview mode")
        audio = None
    mode = "talking_smoke" if options.action == "talking_smoke" else "generate"
    plan = build_shot_plan(
        config,
        options.preset,
        mode=mode,
        single_shot=options.single_shot,
        talking_variations=options.talking_variations,
        motion_variations=options.motion_variations,
    )
    cost = estimate_plan_cost(
        plan,
        config,
        talking_duration_seconds=audio.duration_seconds if audio is not None else None,
    )
    storage = VideoRunStorage(config.root)
    run = storage.create_run(options.preset)
    storage.append_event(
        run,
        "validated",
        {"mode": "DRY_RUN", "provider_call_count": plan.provider_call_count},
    )
    requests = _request_previews(run.run_id, plan, script, keyframe, audio, config)
    storage.write_json_new(
        run,
        "request.json",
        {
            "run_id": run.run_id,
            "mode": "DRY_RUN",
            "action": options.action,
            "preset": options.preset,
            "provider_call_count": plan.provider_call_count,
            "requests": requests,
        },
    )
    storage.write_yaml_new(run, "resolved-config.yaml", _resolved_config(config, options, plan))
    storage.write_bytes_new(run, "script.txt", script.content)
    storage.write_json_new(run, "script-hash.json", _script_evidence(script))
    storage.write_json_new(
        run,
        "audio-hash.json",
        to_primitive(audio) if audio is not None else _planned_voice_evidence(config, script, run.run_id),
    )
    storage.write_json_new(run, "keyframe-hash.json", _keyframe_evidence(keyframe, config))
    storage.write_json_new(run, "shot-plan.json", to_primitive(plan))
    storage.write_json_new(
        run,
        "provider-results.json",
        {"status": "DRY_RUN", "submission_count": 0, "results": []},
    )
    storage.write_text_new(run, "edit-commands.txt", "")
    storage.write_review_new(run, blank_review_rows(run.run_id, options.preset, ()))
    storage.write_json_new(run, "cost.json", cost)
    storage.write_text_new(
        run,
        "summary.md",
        summary_markdown(
            run_id=run.run_id,
            preset=options.preset,
            status="DRY_RUN_COMPLETE",
            provider_call_count=plan.provider_call_count,
            output_count=0,
            total_provider_cost=cost["total_provider_cost"],
        ),
    )
    storage.append_event(run, "dry_run_completed", {"submission_count": 0})
    storage.assert_complete(run)
    return VideoRunOutcome(
        run.run_id,
        run.path,
        run,
        plan,
        plan.provider_call_count,
        0,
        "DRY_RUN_COMPLETE",
    )


def run_talking_smoke(
    project_root: Path,
    options: VideoRunOptions,
    *,
    provider: Any | None = None,
    voice_provider: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> VideoRunOutcome:
    if not options.live or options.action != "talking_smoke":
        raise ValueError("run_talking_smoke requires a live talking_smoke option")
    environment = os.environ if environ is None else environ
    config = load_video_config(project_root, require_inputs=True)
    preset = config.presets.get(options.preset)
    if preset is None:
        raise VideoConfigError(f"unknown video preset: {options.preset}")
    script = _script(config, preset.script_id)
    keyframe = _keyframe(config, options.keyframe_id)
    provider_name = options.provider_name or preset.talking_provider
    if provider_name == "runway":
        provider_name = "runway_talking"
    first_live_smoke = options.smoke_run_id is None
    prior_review_evidence: dict[str, str] | None = None
    if first_live_smoke and options.smoke_review_file is not None:
        raise ExternalInputBlocked(
            "--smoke-review-file requires a prior --smoke-run-id"
        )
    if not first_live_smoke:
        prior_smoke, prior_review_evidence = _validate_passing_smoke(
            config.root, options.smoke_run_id, options.smoke_review_file
        )
        prior_request = _first_talking_request(prior_smoke)
        if prior_request.get("keyframe_sha256") != keyframe.sha256:
            raise ExternalInputBlocked(
                "passing smoke run used a different approved keyframe digest"
            )
        if prior_request.get("provider") != provider_name:
            raise ExternalInputBlocked(
                "passing smoke run used a different talking provider"
            )
    plan = build_shot_plan(
        config,
        options.preset,
        mode="talking_smoke",
        talking_variations=options.talking_variations,
        first_live_smoke=first_live_smoke,
    )
    if first_live_smoke:
        validate_live_smoke_guards(provider_name, 1, None, environment)
    else:
        validate_live_provider_guard(provider_name, environment)
    if plan.voice_request_count:
        voice_name = str(config.voice_profile.provider or "")
        credential = _credential_name(voice_name)
        if not str(environment.get(credential) or "").strip():
            raise ExternalInputBlocked(f"live provider credential is missing: {credential}")
        if voice_provider is None:
            voice_provider = _create_voice_provider(config, voice_name, environment)
        if options.audio_override is not None:
            raise VideoConfigError("audio override is unavailable when voice synthesis is required")
        audio: ApprovedAudio | None = None
    else:
        audio = resolve_approved_audio(config, script, override=options.audio_override)
        _validate_talking_validation_audio(
            provider_name, audio.duration_seconds, environment, first_live_smoke
        )
    if provider is None:
        provider = _create_talking_provider(config, provider_name, environment)
    secrets = tuple(
        value
        for key, value in environment.items()
        if (key.endswith("_API_KEY") or key.endswith("_API_SECRET")) and value
    )
    storage = VideoRunStorage(config.root, secrets=secrets)
    run = storage.create_run(options.preset)
    storage.append_event(
        run,
        "live_authorized",
        {
            "stage": (
                "first_talking_smoke" if first_live_smoke else "expanded_talking_validation"
            ),
            "talking_result_limit": len(plan.shots[0].requests),
            "provider_call_count": plan.provider_call_count,
            "provider": provider_name,
        },
    )
    voice_called = 0
    requests: list[TalkingVideoRequest] = []
    executions: list[ExecutionRecord] = []
    try:
        if plan.voice_request_count:
            voice_called = 1
            audio = resolve_or_synthesize_audio(
                config, script, run_id=run.run_id, provider=voice_provider
            )
            storage.append_event(
                run,
                "voice_synthesized",
                {
                    "provider": config.voice_profile.provider,
                    "model": config.voice_profile.model,
                    "audio_sha256": audio.sha256,
                },
            )
            _validate_talking_validation_audio(
                provider_name,
                audio.duration_seconds,
                environment,
                first_live_smoke,
            )
        if audio is None:
            raise VideoConfigError("talking smoke audio could not be resolved")
        output_dir = config.root / "outputs/talking_shots" / run.run_id
        for planned_request in plan.shots[0].requests:
            request = TalkingVideoRequest(
                request_id=planned_request.request_id,
                run_id=run.run_id,
                preset=options.preset,
                shot_id=planned_request.shot_id,
                variation=planned_request.variation,
                provider=provider_name,
                model=(
                    preset.talking_model
                    if provider_name == "heygen"
                    else "gwm1_avatars"
                ),
                keyframe_path=config.root / keyframe.path,
                keyframe_sha256=keyframe.sha256,
                audio_path=config.root / audio.path,
                audio_sha256=audio.sha256,
                audio_duration_seconds=audio.duration_seconds,
                script_path=config.root / script.path,
                script_version=script.version,
                script_sha256=script.sha256,
                aspect_ratio=preset.aspect_ratio,
                resolution=preset.resolution,
                prompt_text=(
                    plan.shots[0].prompt.text if plan.shots[0].prompt else None
                ),
                timeout_seconds=config.limits.provider_timeout_seconds,
                max_retries=config.limits.max_retries,
            )
            requests.append(request)
            try:
                execution = execute_provider_request(
                    request, provider, storage, run, output_dir
                )
            except Exception as exc:
                if first_live_smoke:
                    raise
                storage.append_event(
                    run,
                    "request_failed",
                    {"request_id": request.request_id, "error": str(exc)},
                )
                executions.append(
                    ExecutionRecord(
                        request.request_id,
                        None,
                        VideoTaskStatus.FAILED,
                        1,
                        (),
                        getattr(exc, "code", "submission_or_download_error"),
                        str(exc),
                    )
                )
                break
            executions.append(execution)
            if execution.status is not VideoTaskStatus.SUCCEEDED:
                break
    except Exception as exc:
        failed_requests: list[dict[str, Any]] = []
        if plan.voice_request_count:
            failed_requests.append(_planned_voice_evidence(config, script, run.run_id))
        failed_requests.extend(to_primitive(request) for request in requests)
        failure_context: dict[str, Any] = {}
        if not first_live_smoke:
            failure_context = {
                "prior_smoke_run_id": options.smoke_run_id,
                "prior_smoke_review": prior_review_evidence,
            }
        _write_failure_bundle(
            config,
            options,
            plan,
            script,
            keyframe,
            storage,
            run,
            exc,
            stage="talking_smoke",
            audio=audio,
            requests=failed_requests,
            known_submissions=voice_called,
            context=failure_context,
        )
        raise
    artifacts = tuple(artifact for record in executions for artifact in record.artifacts)
    successful_requests = sum(
        1
        for record in executions
        if record.status is VideoTaskStatus.SUCCEEDED and record.artifacts
    )
    failed_requests_count = sum(
        1
        for record in executions
        if record.status is not VideoTaskStatus.SUCCEEDED or not record.artifacts
    )
    not_attempted_requests = len(plan.shots[0].requests) - len(executions)
    if successful_requests == len(plan.shots[0].requests):
        status = "SUCCEEDED"
    elif successful_requests:
        status = "PARTIAL"
    else:
        status = "FAILED"
    cost = estimate_plan_cost(plan, config, talking_duration_seconds=audio.duration_seconds)
    for component in cost["components"]:
        if component["category"] == "voice":
            component["attempts"] = voice_called
            component["successful_outputs"] = voice_called
            component["failed_outputs"] = 0
        elif component["category"] == "talking":
            component["attempts"] = sum(
                record.submission_attempts for record in executions
            )
            component["successful_outputs"] = len(artifacts)
            component["failed_outputs"] = failed_requests_count
    candidates = [_artifact_evidence(artifact, config.root) for artifact in artifacts]
    request_evidence = [to_primitive(request) for request in requests]
    result_evidence: list[dict[str, Any]] = []
    if voice_called:
        request_evidence.insert(0, _voice_live_request_evidence(config, script, run.run_id, audio))
        result_evidence.append(
            {
                "request_id": f"{run.run_id}-{script.script_id}-voice",
                "provider_task_id": audio.provider_task_id,
                "status": "SUCCEEDED",
                "submission_attempts": 1,
                "error_code": None,
                "error_message": None,
                "artifacts": [
                    {
                        "artifact_id": audio.audio_id,
                        "kind": "audio",
                        "path": audio.path,
                        "sha256": audio.sha256,
                        "duration_seconds": audio.duration_seconds,
                        "provider_task_id": audio.provider_task_id,
                        "provenance": audio.provenance,
                    }
                ],
            }
        )
    result_evidence.extend(
        {
            "request_id": execution.request_id,
            "provider_task_id": execution.provider_task_id,
            "status": execution.status.value,
            "submission_attempts": execution.submission_attempts,
            "error_code": execution.error_code,
            "error_message": execution.error_message,
            "artifacts": [
                _artifact_evidence(artifact, config.root)
                for artifact in execution.artifacts
            ],
        }
        for execution in executions
    )
    prior_context: dict[str, Any] = {}
    if not first_live_smoke:
        prior_context = {
            "prior_smoke_run_id": options.smoke_run_id,
            "prior_smoke_review": prior_review_evidence,
        }
    storage.write_json_new(
        run,
        "request.json",
        {
            "run_id": run.run_id,
            "mode": "LIVE",
            "action": "talking_smoke",
            "preset": options.preset,
            "provider_call_count": plan.provider_call_count,
            "requests": request_evidence,
            **prior_context,
        },
    )
    storage.write_yaml_new(
        run,
        "resolved-config.yaml",
        {
            **_resolved_config(config, options, plan),
            "live": True,
            "talking_result_limit": len(plan.shots[0].requests),
            "first_live_smoke": first_live_smoke,
            **prior_context,
        },
    )
    storage.write_bytes_new(run, "script.txt", script.content)
    storage.write_json_new(run, "script-hash.json", _script_evidence(script))
    storage.write_json_new(run, "audio-hash.json", to_primitive(audio))
    storage.write_json_new(run, "keyframe-hash.json", _keyframe_evidence(keyframe, config))
    storage.write_json_new(run, "shot-plan.json", to_primitive(plan))
    storage.write_json_new(
        run,
        "provider-results.json",
        {
            "status": status,
            "submission_count": voice_called
            + sum(1 for execution in executions if execution.provider_task_id),
            "submission_attempts": voice_called
            + sum(execution.submission_attempts for execution in executions),
            "successful_outputs": len(artifacts),
            "failed_outputs": failed_requests_count,
            "not_attempted_requests": not_attempted_requests,
            "submission_count_known": all(
                execution.provider_task_id is not None
                or execution.error_code == "provider_validation_error"
                for execution in executions
            ),
            "results": result_evidence,
        },
    )
    storage.write_text_new(run, "edit-commands.txt", "")
    storage.write_review_new(run, blank_review_rows(run.run_id, options.preset, candidates))
    storage.write_json_new(run, "cost.json", cost)
    storage.write_text_new(
        run,
        "summary.md",
        summary_markdown(
            run_id=run.run_id,
            preset=options.preset,
            status=status,
            provider_call_count=plan.provider_call_count,
            output_count=len(artifacts),
            total_provider_cost=cost["total_provider_cost"],
        ),
    )
    storage.append_event(run, "talking_smoke_completed", {"status": status})
    storage.assert_complete(run)
    return VideoRunOutcome(
        run.run_id,
        run.path,
        run,
        plan,
        plan.provider_call_count,
        voice_called + sum(1 for execution in executions if execution.provider_task_id),
        status,
    )


def generate_video(
    project_root: Path,
    options: VideoRunOptions,
    *,
    providers: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> VideoRunOutcome:
    if not options.live or options.action != "generate":
        raise ValueError("generate_video requires a live generate option")
    environment = os.environ if environ is None else environ
    config = load_video_config(project_root, require_inputs=True)
    preset = config.presets.get(options.preset)
    if preset is None:
        raise VideoConfigError(f"unknown video preset: {options.preset}")
    script = _script(config, preset.script_id)
    keyframe = _keyframe(config, options.keyframe_id)
    plan = build_shot_plan(
        config,
        options.preset,
        single_shot=options.single_shot,
        talking_variations=options.talking_variations,
        motion_variations=options.motion_variations,
    )
    smoke, smoke_review_evidence = _validate_passing_smoke(
        config.root, options.smoke_run_id, options.smoke_review_file
    )
    smoke_request = _first_talking_request(smoke)
    if smoke_request.get("keyframe_sha256") != keyframe.sha256:
        raise ExternalInputBlocked("passing smoke run used a different approved keyframe digest")
    if smoke_request.get("provider") != preset.talking_provider:
        raise ExternalInputBlocked("passing smoke run used a different talking provider")
    _validate_full_live_guards(config, plan, environment)

    selected_providers = dict(providers or {})
    if providers is None:
        selected_providers = _create_generation_providers(config, plan, environment)
    secret_values = tuple(
        value
        for key, value in environment.items()
        if (key.endswith("_API_KEY") or key.endswith("_API_SECRET")) and value
    )
    storage = VideoRunStorage(config.root, secrets=secret_values)
    run = storage.create_run(options.preset)
    voice_provider = (
        selected_providers.get(config.voice_profile.provider or "")
        if plan.voice_request_count
        else None
    )
    voice_call_count = plan.voice_request_count
    audio: ApprovedAudio | None = None
    try:
        audio = resolve_or_synthesize_audio(
            config, script, run_id=run.run_id, provider=voice_provider
        )
    except Exception as exc:
        failure_requests = (
            [_planned_voice_evidence(config, script, run.run_id)]
            if voice_call_count
            else []
        )
        _write_failure_bundle(
            config,
            options,
            plan,
            script,
            keyframe,
            storage,
            run,
            exc,
            stage="voice_resolution",
            audio=None,
            requests=failure_requests,
            known_submissions=voice_call_count,
            context={
                "smoke_run_id": options.smoke_run_id,
                "smoke_review": smoke_review_evidence,
            },
        )
        raise
    if voice_call_count:
        storage.append_event(
            run,
            "voice_synthesized",
            {
                "provider": config.voice_profile.provider,
                "model": config.voice_profile.model,
                "audio_sha256": audio.sha256,
            },
        )
    storage.append_event(
        run,
        "live_authorized",
        {
            "stage": "pilot_shot_generation",
            "smoke_run_id": options.smoke_run_id,
            "smoke_review": smoke_review_evidence,
            "provider_call_count": plan.provider_call_count,
            "concurrency": 1,
        },
    )

    requests: list[TalkingVideoRequest | MotionVideoRequest] = []
    request_responsibilities: dict[str, str] = {}
    executions: list[ExecutionRecord] = []
    for shot in plan.shots:
        for planned in shot.requests:
            if planned.responsibility == "talking":
                request = _talking_request(
                    run.run_id, config, preset, planned, shot, script, keyframe, audio
                )
                output_dir = config.root / "outputs/talking_shots" / run.run_id
            else:
                request = _motion_request(
                    run.run_id, config, preset, planned, shot, keyframe
                )
                output_dir = config.root / "outputs/broll" / run.run_id
            requests.append(request)
            request_responsibilities[request.request_id] = planned.responsibility
            try:
                provider = selected_providers.get(request.provider)
                if provider is None:
                    raise VideoConfigError(
                        f"provider instance is unavailable: {request.provider}"
                    )
                execution = execute_provider_request(request, provider, storage, run, output_dir)
            except Exception as exc:
                storage.append_event(
                    run,
                    "request_failed",
                    {"request_id": request.request_id, "error": str(exc)},
                )
                execution = ExecutionRecord(
                    request.request_id,
                    None,
                    VideoTaskStatus.FAILED,
                    1,
                    (),
                    getattr(exc, "code", "submission_or_download_error"),
                    str(exc),
                )
            executions.append(execution)

    artifacts = tuple(artifact for record in executions for artifact in record.artifacts)
    successful_requests = sum(
        1 for record in executions if record.status is VideoTaskStatus.SUCCEEDED and record.artifacts
    )
    failed_requests = len(executions) - successful_requests
    if failed_requests == 0:
        status = "AWAITING_SELECTION"
    elif successful_requests:
        status = "PARTIAL"
    else:
        status = "FAILED"
    cost = estimate_plan_cost(plan, config, talking_duration_seconds=audio.duration_seconds)
    _apply_execution_cost_facts(cost, executions, request_responsibilities)
    if voice_call_count:
        for component in cost.get("components", []):
            if component.get("category") == "voice":
                component["attempts"] = 1
                component["successful_outputs"] = 1
                component["failed_outputs"] = 0
    candidates = [_artifact_evidence(artifact, config.root) for artifact in artifacts]
    result_rows = [
        {
            "request_id": record.request_id,
            "provider_task_id": record.provider_task_id,
            "status": record.status.value,
            "submission_attempts": record.submission_attempts,
            "error_code": record.error_code,
            "error_message": record.error_message,
            "artifacts": [
                _artifact_evidence(artifact, config.root) for artifact in record.artifacts
            ],
        }
        for record in executions
    ]
    if voice_call_count:
        result_rows.insert(
            0,
            {
                "request_id": f"{run.run_id}-{script.script_id}-voice",
                "provider_task_id": audio.provider_task_id,
                "status": "SUCCEEDED",
                "submission_attempts": 1,
                "error_code": None,
                "error_message": None,
                "artifacts": [
                    {
                        "artifact_id": audio.audio_id,
                        "kind": "audio",
                        "path": audio.path,
                        "sha256": audio.sha256,
                        "duration_seconds": audio.duration_seconds,
                        "provider_task_id": audio.provider_task_id,
                        "provenance": audio.provenance,
                    }
                ],
            },
        )
    request_evidence = [to_primitive(request) for request in requests]
    if voice_call_count:
        request_evidence.insert(0, _voice_live_request_evidence(config, script, run.run_id, audio))
    storage.write_json_new(
        run,
        "request.json",
        {
            "run_id": run.run_id,
            "mode": "LIVE",
            "action": "generate",
            "preset": options.preset,
            "smoke_run_id": options.smoke_run_id,
            "smoke_review": smoke_review_evidence,
            "provider_call_count": plan.provider_call_count,
            "requests": request_evidence,
        },
    )
    storage.write_yaml_new(
        run,
        "resolved-config.yaml",
        {
            **_resolved_config(config, options, plan),
            "live": True,
            "smoke_run_id": options.smoke_run_id,
            "smoke_review": smoke_review_evidence,
        },
    )
    storage.write_bytes_new(run, "script.txt", script.content)
    storage.write_json_new(run, "script-hash.json", _script_evidence(script))
    storage.write_json_new(run, "audio-hash.json", to_primitive(audio))
    storage.write_json_new(run, "keyframe-hash.json", _keyframe_evidence(keyframe, config))
    storage.write_json_new(run, "shot-plan.json", to_primitive(plan))
    storage.write_json_new(
        run,
        "provider-results.json",
        {
            "status": status,
            "submission_count": voice_call_count + sum(
                1 for record in executions if record.provider_task_id
            ),
            "submission_attempts": voice_call_count + sum(
                record.submission_attempts for record in executions
            ),
            "successful_outputs": len(artifacts),
            "failed_outputs": failed_requests,
            "results": result_rows,
        },
    )
    storage.write_text_new(run, "edit-commands.txt", "")
    storage.write_review_new(run, blank_review_rows(run.run_id, options.preset, candidates))
    storage.write_json_new(run, "cost.json", cost)
    storage.write_text_new(
        run,
        "summary.md",
        summary_markdown(
            run_id=run.run_id,
            preset=options.preset,
            status=status,
            provider_call_count=plan.provider_call_count,
            output_count=len(artifacts),
            total_provider_cost=cost["total_provider_cost"],
        ),
    )
    storage.append_event(
        run,
        "shot_generation_completed",
        {"status": status, "successful_outputs": len(artifacts), "failed_requests": failed_requests},
    )
    storage.assert_complete(run)
    return VideoRunOutcome(
        run.run_id,
        run.path,
        run,
        plan,
        plan.provider_call_count,
        voice_call_count + sum(1 for record in executions if record.provider_task_id),
        status,
    )


def _write_failure_bundle(
    config: VideoProjectConfig,
    options: VideoRunOptions,
    plan: ShotPlan,
    script: ScriptRecord,
    keyframe: ApprovedKeyframe,
    storage: VideoRunStorage,
    run: VideoRunContext,
    error: Exception,
    *,
    stage: str,
    audio: ApprovedAudio | None,
    requests: list[dict[str, Any]],
    known_submissions: int,
    context: Mapping[str, Any] | None = None,
) -> None:
    storage.append_event(
        run,
        "workflow_failed",
        {"stage": stage, "error_type": type(error).__name__, "error": str(error)},
    )
    cost = estimate_plan_cost(
        plan,
        config,
        talking_duration_seconds=(audio.duration_seconds if audio is not None else None),
    )
    for component in cost.get("components", []):
        component["attempts"] = known_submissions if component.get("category") == "voice" else 0
        component["successful_outputs"] = 0
        component["failed_outputs"] = 1 if component["attempts"] else 0
    audio_evidence = (
        to_primitive(audio)
        if audio is not None
        else {**_planned_voice_evidence(config, script, run.run_id), "status": "FAILED"}
    )
    storage.write_json_new(
        run,
        "request.json",
        {
            "run_id": run.run_id,
            "mode": "LIVE",
            "action": options.action,
            "preset": options.preset,
            "provider_call_count": plan.provider_call_count,
            "requests": requests,
            **dict(context or {}),
        },
    )
    storage.write_yaml_new(
        run,
        "resolved-config.yaml",
        {
            **_resolved_config(config, options, plan),
            "live": True,
            "failure_stage": stage,
            **dict(context or {}),
        },
    )
    storage.write_bytes_new(run, "script.txt", script.content)
    storage.write_json_new(run, "script-hash.json", _script_evidence(script))
    storage.write_json_new(run, "audio-hash.json", audio_evidence)
    storage.write_json_new(run, "keyframe-hash.json", _keyframe_evidence(keyframe, config))
    storage.write_json_new(run, "shot-plan.json", to_primitive(plan))
    storage.write_json_new(
        run,
        "provider-results.json",
        {
            "status": "FAILED",
            "submission_count": known_submissions,
            "submission_count_known": False,
            "successful_outputs": 0,
            "failed_outputs": 1,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "results": [],
        },
    )
    storage.write_text_new(run, "edit-commands.txt", "")
    storage.write_review_new(run, ())
    storage.write_json_new(run, "cost.json", cost)
    storage.write_text_new(
        run,
        "summary.md",
        summary_markdown(
            run_id=run.run_id,
            preset=options.preset,
            status="FAILED",
            provider_call_count=plan.provider_call_count,
            output_count=0,
            total_provider_cost=cost["total_provider_cost"],
        ),
    )
    storage.assert_complete(run)


def handle_video_command(args: Any) -> tuple[int, Any]:
    if args.video_command == "validate":
        return 0, validate_video_project(args.project_root)
    if args.video_command in {"talking-smoke-test", "generate"}:
        options = VideoRunOptions(
            preset=args.preset,
            action="talking_smoke" if args.video_command == "talking-smoke-test" else "generate",
            single_shot=bool(getattr(args, "single_shot", False)),
            talking_variations=(
                getattr(args, "variations", None)
                if args.video_command == "talking-smoke-test"
                else getattr(args, "talking_variations", None)
            ),
            motion_variations=getattr(args, "motion_variations", None),
            keyframe_id=getattr(args, "keyframe", None),
            audio_override=(Path(args.audio) if getattr(args, "audio", None) else None),
            live=bool(args.live),
            smoke_run_id=getattr(args, "smoke_run_id", None),
            smoke_review_file=(
                Path(args.smoke_review_file)
                if getattr(args, "smoke_review_file", None)
                else None
            ),
            provider_name=getattr(args, "provider", None),
        )
        if args.live and args.video_command == "talking-smoke-test":
            outcome = run_talking_smoke(args.project_root, options)
            return (0 if outcome.status == "SUCCEEDED" else 3), {
                "run_id": outcome.run_id,
                "run_dir": str(outcome.run_dir),
                "status": outcome.status,
                "planned_provider_calls": outcome.provider_call_count,
                "paid_calls": outcome.submission_count,
            }
        if args.live:
            options = replace(
                options,
                smoke_run_id=getattr(args, "smoke_run_id", None),
                smoke_review_file=(
                    Path(args.smoke_review_file)
                    if getattr(args, "smoke_review_file", None)
                    else None
                ),
            )
            outcome = generate_video(args.project_root, options)
            return (0 if outcome.status == "AWAITING_SELECTION" else 3), {
                "run_id": outcome.run_id,
                "run_dir": str(outcome.run_dir),
                "status": outcome.status,
                "planned_provider_calls": outcome.provider_call_count,
                "paid_calls": outcome.submission_count,
            }
        outcome = preview_video(args.project_root, options)
        return 0, {
            "run_id": outcome.run_id,
            "run_dir": str(outcome.run_dir),
            "status": outcome.status,
            "planned_provider_calls": outcome.provider_call_count,
            "paid_calls": outcome.submission_count,
        }
    if args.video_command == "report":
        from .reporting import build_video_report

        return 0, build_video_report(args.project_root, args.run_id)
    if args.video_command == "assemble":
        from .assembly import assemble_video

        outcome = assemble_video(
            args.project_root,
            args.run_id,
            Path(args.selection_file),
            final_edits=args.final_edits,
        )
        return 0, {
            "run_id": outcome.run_id,
            "run_dir": str(outcome.run_dir),
            "source_run_id": outcome.source_run_id,
            "status": outcome.status,
            "candidates": [item.path.name for item in outcome.candidates],
            "paid_calls": 0,
        }
    if args.video_command == "promote":
        from .promotion import promote_video

        record = promote_video(
            args.project_root,
            args.run_id,
            args.candidate,
            review_file=Path(args.review_file),
            approved_version=args.approved_version,
        )
        return 0, record
    raise ValueError(f"video command is not implemented yet: {args.video_command}")


def _script(config: VideoProjectConfig, script_id: str) -> ScriptRecord:
    try:
        return config.scripts[script_id]
    except KeyError as exc:
        raise ExternalInputBlocked(f"authoritative MTL script is unavailable: {script_id}") from exc


def _keyframe(config: VideoProjectConfig, selected: str | None) -> ApprovedKeyframe:
    if selected:
        if selected not in config.keyframes:
            raise ExternalInputBlocked(f"approved keyframe does not exist: {selected}")
        return config.keyframes[selected]
    if not config.keyframes:
        raise ExternalInputBlocked("at least one approved keyframe is required")
    return config.keyframes[sorted(config.keyframes)[0]]


def _request_previews(
    run_id: str,
    plan: ShotPlan,
    script: ScriptRecord,
    keyframe: ApprovedKeyframe,
    audio: ApprovedAudio | None,
    config: VideoProjectConfig,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if audio is None:
        result.append(
            {
                "request_id": f"{run_id}-{script.script_id}-voice",
                "run_id": run_id,
                "responsibility": "voice",
                "provider": config.voice_profile.provider,
                "model": config.voice_profile.model,
                "voice_id": config.voice_profile.voice_id,
                "script_sha256": script.sha256,
                "output_path": f"outputs/audio/{run_id}/{script.script_id}.wav",
            }
        )
    for shot in plan.shots:
        for request in shot.requests:
            payload = to_primitive(request)
            payload.update(
                {
                    "run_id": run_id,
                    "script_sha256": script.sha256,
                    "keyframe_sha256": keyframe.sha256,
                    "audio_sha256": audio.sha256 if audio is not None else None,
                    "audio_source_request_id": (
                        None if audio is not None else f"{run_id}-{script.script_id}-voice"
                    ),
                    "prompt_sha256": shot.prompt.sha256 if shot.prompt else None,
                }
            )
            result.append(payload)
    return result


def _planned_voice_evidence(
    config: VideoProjectConfig, script: ScriptRecord, run_id: str
) -> dict[str, Any]:
    profile = config.voice_profile
    return {
        "mode": "cloned_voice",
        "status": "PLANNED_DRY_RUN",
        "provider": profile.provider,
        "model": profile.model,
        "voice_id": profile.voice_id,
        "voice_version": profile.voice_version,
        "script_sha256": script.sha256,
        "path": f"outputs/audio/{run_id}/{script.script_id}.wav",
        "sha256": None,
        "duration_seconds": None,
        "output_format": profile.output_format,
        "sample_rate": profile.sample_rate,
    }


def _voice_live_request_evidence(
    config: VideoProjectConfig,
    script: ScriptRecord,
    run_id: str,
    audio: ApprovedAudio,
) -> dict[str, Any]:
    profile = config.voice_profile
    return {
        "request_id": f"{run_id}-{script.script_id}-voice",
        "run_id": run_id,
        "responsibility": "voice",
        "provider": profile.provider,
        "model": profile.model,
        "voice_id": profile.voice_id,
        "script_sha256": script.sha256,
        "output_path": audio.path,
        "output_sha256": audio.sha256,
        "provider_task_id": audio.provider_task_id,
        "provenance": audio.provenance,
    }


def _resolved_config(
    config: VideoProjectConfig, options: VideoRunOptions, plan: ShotPlan
) -> dict[str, Any]:
    preset = config.presets[options.preset]
    return {
        "preset": options.preset,
        "action": options.action,
        "aspect_ratio": preset.aspect_ratio,
        "resolution": preset.resolution,
        "frame_rate": preset.frame_rate,
        "talking_provider": preset.talking_provider,
        "talking_model": preset.talking_model,
        "motion_provider": preset.motion_provider,
        "motion_model": preset.motion_model,
        "limits": to_primitive(config.limits),
        "providers_verified_on": config.verified_on,
        "provider_call_count": plan.provider_call_count,
        "live": False,
    }


def _script_evidence(script: ScriptRecord) -> dict[str, Any]:
    return {
        "script_id": script.script_id,
        "path": script.path,
        "version": script.version,
        "sha256": script.sha256,
        "source": script.source,
        "source_reference": script.source_reference,
        "modification_policy": script.modification_policy,
    }


def _keyframe_evidence(
    keyframe: ApprovedKeyframe, config: VideoProjectConfig
) -> dict[str, Any]:
    payload = to_primitive(keyframe)
    payload["anchor_set_version"] = config.anchor_manifest.get("anchor_set_version")
    payload["anchor_hashes"] = {
        name: item["sha256"]
        for name, item in config.anchor_manifest.get("anchors", {}).items()
    }
    return payload


def _create_talking_provider(
    config: VideoProjectConfig, provider_name: str, environment: Mapping[str, str]
) -> Any:
    if provider_name == "heygen":
        from ..providers.heygen_talking import HeyGenTalkingProvider

        return HeyGenTalkingProvider(
            config.providers["heygen"], api_key=str(environment["HEYGEN_API_KEY"])
        )
    if provider_name in {"runway", "runway_talking"}:
        from ..providers.runway_talking import RunwayTalkingProvider

        return RunwayTalkingProvider(
            config.providers["runway_talking"],
            api_key=str(environment["RUNWAYML_API_SECRET"]),
        )
    raise VideoConfigError(f"unsupported talking provider: {provider_name}")


def _validate_passing_smoke(
    project_root: Path, run_id: str | None, review_file: Path | None
) -> tuple[dict[str, Any], dict[str, str]]:
    if not run_id or "/" in run_id or "\\" in run_id:
        raise ExternalInputBlocked("full generation requires a reviewed passing --smoke-run-id")
    run_dir = (project_root / "runs" / run_id).resolve()
    runs_root = (project_root / "runs").resolve()
    if runs_root not in run_dir.parents or not run_dir.is_dir():
        raise ExternalInputBlocked(f"smoke run does not exist: {run_id}")
    try:
        request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
        results = json.loads((run_dir / "provider-results.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalInputBlocked(f"smoke run evidence is incomplete: {run_id}") from exc
    if request.get("action") != "talking_smoke" or results.get("status") != "SUCCEEDED":
        raise ExternalInputBlocked("smoke run is not a successful talking result")
    result_items = results.get("results") or []
    artifacts = result_items[-1].get("artifacts") if result_items else []
    if len(artifacts or []) != 1:
        raise ExternalInputBlocked("smoke run output provenance is missing")
    artifact = artifacts[0]
    candidate = str(artifact.get("candidate") or artifact.get("video_id") or "")
    if not candidate:
        raise ExternalInputBlocked("smoke run candidate identity is missing")
    if review_file is None:
        raise ExternalInputBlocked(
            "full generation requires an immutable --smoke-review-file copy under outputs/reviews"
        )
    try:
        row, review_evidence = load_external_review_row(
            project_root, run_dir, candidate, review_file, require_ready=False
        )
    except ReviewError as exc:
        raise ExternalInputBlocked(str(exc)) from exc
    required_passes = QA_FIELDS[4:18]
    if any(not _truthy(row.get(field)) for field in required_passes):
        raise ExternalInputBlocked("smoke run has incomplete or failing QA decisions")
    if not _truthy(row.get("mtl_review_ready")):
        raise ExternalInputBlocked("smoke run is not explicitly MTL-review ready")
    if not str(row.get("reviewer") or "").strip():
        raise ExternalInputBlocked("smoke run reviewer is required")
    try:
        reviewed_at = datetime.fromisoformat(str(row.get("reviewed_at") or "").replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExternalInputBlocked("smoke run reviewed_at is invalid") from exc
    if reviewed_at.tzinfo is None:
        raise ExternalInputBlocked("smoke run reviewed_at must include a timezone")
    source_path = (project_root / str(artifact.get("path") or "")).resolve()
    outputs_root = (project_root / "outputs/talking_shots").resolve()
    if outputs_root not in source_path.parents or not source_path.is_file():
        raise ExternalInputBlocked("smoke run output is missing or outside talking outputs")
    if sha256_file(source_path) != artifact.get("sha256"):
        raise ExternalInputBlocked("smoke run output hash no longer matches evidence")
    return request, review_evidence


def _first_talking_request(request_evidence: Mapping[str, Any]) -> dict[str, Any]:
    for item in request_evidence.get("requests") or []:
        if isinstance(item, dict) and item.get("keyframe_sha256"):
            return item
    raise ExternalInputBlocked("smoke run talking-request provenance is missing")


def _validate_talking_validation_audio(
    provider_name: str,
    duration_seconds: float,
    environment: Mapping[str, str],
    first_live_smoke: bool,
) -> None:
    if first_live_smoke:
        validate_live_smoke_guards(
            provider_name, 1, duration_seconds, environment
        )
        return
    if not 8 <= duration_seconds <= 12:
        raise ExternalInputBlocked(
            "expanded talking validation audio duration must be within 8..12 seconds"
        )


def _validate_full_live_guards(
    config: VideoProjectConfig,
    plan: ShotPlan,
    environment: Mapping[str, str],
) -> None:
    if environment.get("VIDEO_ALLOW_LIVE_CALLS") != "true":
        raise ExternalInputBlocked("live video calls require exact VIDEO_ALLOW_LIVE_CALLS=true")
    provider_names = {request.provider for shot in plan.shots for request in shot.requests}
    if plan.voice_request_count and config.voice_profile.provider:
        provider_names.add(config.voice_profile.provider)
    for provider_name in sorted(provider_names):
        credential = _credential_name(provider_name)
        if not str(environment.get(credential) or "").strip():
            raise ExternalInputBlocked(f"live provider credential is missing: {credential}")
    if config.limits.max_concurrency != 1:
        raise VideoConfigError("live video concurrency must remain one")


def _credential_name(provider_name: str) -> str:
    if provider_name in {"heygen", "heygen_voice"}:
        return "HEYGEN_API_KEY"
    if provider_name in {"runway", "runway_talking"}:
        return "RUNWAYML_API_SECRET"
    return f"{provider_name.upper()}_API_KEY"


def _create_generation_providers(
    config: VideoProjectConfig, plan: ShotPlan, environment: Mapping[str, str]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    names = {request.provider for shot in plan.shots for request in shot.requests}
    if "heygen" in names:
        result["heygen"] = _create_talking_provider(config, "heygen", environment)
    if "runway_talking" in names:
        result["runway_talking"] = _create_talking_provider(
            config, "runway_talking", environment
        )
    if "runway" in names:
        from ..providers.runway_video import RunwayMotionProvider

        result["runway"] = RunwayMotionProvider(
            config.providers["runway"], api_key=str(environment["RUNWAYML_API_SECRET"])
        )
    if plan.voice_request_count and config.voice_profile.provider:
        voice_name = config.voice_profile.provider
        result[voice_name] = _create_voice_provider(config, voice_name, environment)
    return result


def _create_voice_provider(
    config: VideoProjectConfig, provider_name: str, environment: Mapping[str, str]
) -> Any:
    if provider_name == "heygen_voice":
        from ..providers.heygen_voice import HeyGenVoiceProvider

        return HeyGenVoiceProvider(
            config.providers[provider_name],
            api_key=str(environment["HEYGEN_API_KEY"]),
        )
    raise ExternalInputBlocked(
        f"approved cloned voice requires a configured live adapter: {provider_name}"
    )


def _talking_request(
    run_id: str,
    config: VideoProjectConfig,
    preset: Any,
    planned: Any,
    shot: Any,
    script: ScriptRecord,
    keyframe: ApprovedKeyframe,
    audio: ApprovedAudio,
) -> TalkingVideoRequest:
    return TalkingVideoRequest(
        request_id=planned.request_id,
        run_id=run_id,
        preset=preset.name,
        shot_id=planned.shot_id,
        variation=planned.variation,
        provider=planned.provider,
        model=planned.model,
        keyframe_path=config.root / keyframe.path,
        keyframe_sha256=keyframe.sha256,
        audio_path=config.root / audio.path,
        audio_sha256=audio.sha256,
        audio_duration_seconds=audio.duration_seconds,
        script_path=config.root / script.path,
        script_version=script.version,
        script_sha256=script.sha256,
        aspect_ratio=preset.aspect_ratio,
        resolution=preset.resolution,
        prompt_text=shot.prompt.text if shot.prompt else None,
        timeout_seconds=config.limits.provider_timeout_seconds,
        max_retries=config.limits.max_retries,
    )


def _motion_request(
    run_id: str,
    config: VideoProjectConfig,
    preset: Any,
    planned: Any,
    shot: Any,
    keyframe: ApprovedKeyframe,
) -> MotionVideoRequest:
    if shot.prompt is None or planned.duration_seconds is None:
        raise VideoConfigError(f"motion shot is missing prompt or duration: {planned.shot_id}")
    return MotionVideoRequest(
        request_id=planned.request_id,
        run_id=run_id,
        preset=preset.name,
        shot_id=planned.shot_id,
        variation=planned.variation,
        provider=planned.provider,
        model=planned.model,
        image_path=config.root / keyframe.path,
        image_sha256=keyframe.sha256,
        prompt_path=config.root / shot.prompt.path,
        prompt_text=shot.prompt.text,
        prompt_sha256=shot.prompt.sha256,
        ratio=preset.resolution,
        duration_seconds=int(planned.duration_seconds),
        seed=None,
        output_format="mp4",
        timeout_seconds=config.limits.provider_timeout_seconds,
        max_retries=config.limits.max_retries,
    )


def _artifact_evidence(artifact: Any, project_root: Path) -> dict[str, Any]:
    return {
        "video_id": artifact.artifact_id,
        "candidate": artifact.path.name,
        "artifact_id": artifact.artifact_id,
        "kind": artifact.kind,
        "path": artifact.path.relative_to(project_root),
        "sha256": artifact.sha256,
        "size_bytes": artifact.size_bytes,
        "mime_type": artifact.mime_type,
        "duration_seconds": artifact.duration_seconds,
        "width": artifact.width,
        "height": artifact.height,
        "provider_task_id": artifact.provider_task_id,
    }


def _apply_execution_cost_facts(
    cost: dict[str, Any],
    executions: list[ExecutionRecord],
    responsibilities: Mapping[str, str],
) -> None:
    for component in cost.get("components", []):
        category = component.get("category")
        matching = [
            record
            for record in executions
            if responsibilities.get(record.request_id) == category
        ]
        component["attempts"] = sum(record.submission_attempts for record in matching)
        component["successful_outputs"] = sum(len(record.artifacts) for record in matching)
        component["failed_outputs"] = sum(
            1
            for record in matching
            if record.status is not VideoTaskStatus.SUCCEEDED or not record.artifacts
        )


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "yes", "1", "approved", "pass"}
