from __future__ import annotations

import os
import json
import math
import csv
import shutil
import subprocess
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from ..domain import to_primitive
from ..hashing import sha256_file
from .config import VideoConfigError, load_video_config
from .costing import estimate_plan_cost
from .budget import BudgetLimits, check_actual, check_estimate, require_explicit_budget
from .domain import (
    ApprovedAudio,
    ApprovedKeyframe,
    MotionVideoRequest,
    PlannedRequest,
    PlannedShot,
    ResolvedPrompt,
    ScriptRecord,
    ShotPlan,
    TalkingVideoRequest,
    VideoProjectConfig,
    VideoTaskStatus,
    PlannedRequest,
    PlannedShot,
    ResolvedPrompt,
)
from .execution import (
    ExecutionRecord,
    execute_provider_request,
    validate_live_provider_guard,
    validate_live_smoke_guards,
)
from .planning import build_shot_plan
from .prompts import VideoPromptError, load_video_prompt, utf16_code_units
from .motion_v7 import (
    V7_CANDIDATE_IDS,
    candidate_credit_estimate,
    build_v7_comparison,
    load_v7_candidates,
)
from .reporting import blank_review_rows, read_video_summary, summary_markdown
from .review import ReviewError, load_external_review_row
from .storage import QA_FIELDS, VideoRunContext, VideoRunStorage
from .validation import ExternalInputBlocked
from .downloads import generate_video_evidence, validate_media_artifact
from .voice import resolve_approved_audio, resolve_or_synthesize_audio


@dataclass(frozen=True, slots=True)
class VideoRunOptions:
    preset: str = "motion"
    action: str = "generate"
    single_shot: bool = False
    talking_variations: int | None = None
    motion_variations: int | None = None
    keyframe_id: str | None = None
    audio_override: Path | None = None
    live: bool = False
    smoke_run_id: str | None = None
    smoke_review_file: Path | None = None
    motion_smoke_run_id: str | None = None
    motion_smoke_review_file: Path | None = None
    motion_smoke_qa_attested: bool = False
    provider_name: str | None = None
    max_provider_cost_usd: float | None = None
    max_runway_credits: float | None = None
    accept_unknown_provider_cost: bool = False
    motion_model: str | None = None
    motion_duration: int | None = None
    motion_ratio: str | None = None
    motion_prompt: str | None = None


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
        plan = build_shot_plan(config, preset.name)
        _validate_motion_plan_prompts(config, plan)
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
    _validate_motion_plan_prompts(config, plan)
    cost = estimate_plan_cost(
        plan,
        config,
        talking_duration_seconds=audio.duration_seconds if audio is not None else None,
    )
    preview_budgets = _budget_limits(options)
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
            "budget": _budget_evidence(
                preview_budgets,
                cost.get("total_provider_cost"),
                _estimate_motion_credits(config, plan),
            ),
            "requests": requests,
        },
    )
    storage.write_yaml_new(
        run,
        "resolved-config.yaml",
        {
            **_resolved_config(config, options, plan),
            "budget": _budget_evidence(
                preview_budgets,
                cost.get("total_provider_cost"),
                _estimate_motion_credits(config, plan),
            ),
        },
    )
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


def run_motion_smoke(
    project_root: Path,
    options: VideoRunOptions,
    *,
    model: str = "gen4_turbo",
    duration_seconds: int = 5,
    ratio: str = "1280:720",
    provider: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> VideoRunOutcome:
    """Preview or execute the independent one-result Runway motion smoke stage."""

    if options.action != "motion_smoke":
        raise ValueError("run_motion_smoke requires action=motion_smoke")
    environment = os.environ if environ is None else environ
    config = load_video_config(project_root, require_inputs=False)
    model = options.motion_model or model
    duration_seconds = (
        options.motion_duration if options.motion_duration is not None else duration_seconds
    )
    ratio = options.motion_ratio or ratio
    if options.live and model != "gen4_turbo":
        raise ExternalInputBlocked(
            "the first live motion smoke must use one gen4_turbo result of exactly 5 seconds"
        )
    keyframe = _keyframe(config, options.keyframe_id)
    definition = config.providers.get("runway")
    if definition is None or definition.responsibility != "motion":
        raise VideoConfigError("Runway motion provider is not configured")
    capabilities = definition.settings.get("supported_models") or {}
    capability = capabilities.get(model) if isinstance(capabilities, Mapping) else None
    if not isinstance(capability, Mapping):
        raise VideoConfigError(f"unsupported Runway motion model: {model}")
    if ratio not in {str(item) for item in capability.get("ratios", ())}:
        raise VideoConfigError(f"unsupported Runway motion ratio: {ratio}")
    if duration_seconds not in {int(item) for item in capability.get("durations", ())}:
        raise VideoConfigError(f"unsupported Runway motion duration: {duration_seconds}")
    variations = options.motion_variations if options.motion_variations is not None else 1
    if not 1 <= variations <= config.limits.max_motion_variations_per_shot:
        raise VideoConfigError(
            f"motion variations must be within 1..{config.limits.max_motion_variations_per_shot}"
        )
    prompt = _resolve_motion_prompt(config, options.motion_prompt)
    _validate_motion_provider_settings(
        config, model, duration_seconds, ratio, prompt
    )
    planned_requests = tuple(
        PlannedRequest(
            request_id=f"motion-smoke-pilot-v{index:03d}",
            shot_id="motion_smoke",
            variation=index,
            responsibility="motion",
            provider="runway",
            model=model,
            duration_seconds=float(duration_seconds),
        )
        for index in range(1, variations + 1)
    )
    plan = ShotPlan(
        preset="motion_smoke",
        mode="motion_smoke",
        script_id="not_applicable",
        aspect_ratio="16:9",
        resolution=ratio,
        frame_rate=30,
        shots=(
            PlannedShot(
                shot_id="motion_smoke",
                kind="motion",
                source_role=keyframe.keyframe_id,
                prompt=prompt,
                duration_seconds=float(duration_seconds),
                variation_count=variations,
                selection_required=variations > 1,
                requests=planned_requests,
            ),
        ),
        final_edit_variations=0,
        voice_request_count=0,
    )
    credits_per_second = float(capability.get("credits_per_second") or 0)
    estimated_credits = credits_per_second * duration_seconds * variations or None
    credit_usd = float(definition.settings.get("credit_usd") or 0.01)
    estimated_usd = (
        estimated_credits * credit_usd if estimated_credits is not None else None
    )
    budgets = _budget_limits(options)
    if options.live:
        if environment.get("VIDEO_ALLOW_LIVE_CALLS") != "true":
            raise ExternalInputBlocked(
                "live video calls require exact VIDEO_ALLOW_LIVE_CALLS=true"
            )
        if environment.get("VIDEO_MOTION_LIVE_SMOKE_TEST") != "true":
            raise ExternalInputBlocked(
                "first motion smoke requires exact VIDEO_MOTION_LIVE_SMOKE_TEST=true"
            )
        if not str(environment.get("RUNWAYML_API_SECRET") or "").strip():
            raise ExternalInputBlocked(
                "live provider credential is missing: RUNWAYML_API_SECRET"
            )
        if variations != 1 or model != "gen4_turbo" or duration_seconds != 5:
            raise ExternalInputBlocked(
                "the first live motion smoke must use one gen4_turbo result of exactly 5 seconds"
            )
        if budgets.max_runway_credits is None or budgets.max_runway_credits > 25:
            raise ExternalInputBlocked(
                "the first live motion smoke requires an explicit cap no greater than 25 Runway credits"
            )
        # This is deliberately before construction of the real SDK client.
        check_estimate(
            budgets,
            provider="runway",
            estimated_usd=estimated_usd,
            estimated_credits=estimated_credits,
            operation="motion smoke",
        )
        if provider is None:
            from ..providers.runway_video import RunwayMotionProvider

            provider = RunwayMotionProvider(
                definition, api_key=str(environment["RUNWAYML_API_SECRET"])
            )

    storage = VideoRunStorage(
        config.root,
        secrets=tuple(
            value
            for key, value in environment.items()
            if (key.endswith("_API_KEY") or key.endswith("_API_SECRET")) and value
        ),
    )
    run = storage.create_run("motion-smoke")
    request = MotionVideoRequest(
        request_id=planned_requests[0].request_id,
        run_id=run.run_id,
        preset="motion_smoke",
        shot_id="motion_smoke",
        variation=1,
        provider="runway",
        model=model,
        image_path=config.root / keyframe.path,
        image_sha256=keyframe.sha256,
        prompt_path=config.root / prompt.path,
        prompt_text=prompt.text,
        prompt_sha256=prompt.sha256,
        ratio=ratio,
        duration_seconds=duration_seconds,
        seed=None,
        output_format="mp4",
        timeout_seconds=config.limits.provider_timeout_seconds,
        max_retries=config.limits.max_retries,
    )
    budget_evidence = _budget_evidence(budgets, estimated_usd, estimated_credits)
    base_request = {
        "run_id": run.run_id,
        "mode": "LIVE" if options.live else "DRY_RUN",
        "action": "motion_smoke",
        "preset": "motion_smoke",
        "provider_call_count": variations,
        "budget": budget_evidence,
        "requests": [to_primitive(request)],
    }
    base_config = {
        "preset": "motion_smoke",
        "live": options.live,
        "keyframe_id": keyframe.keyframe_id,
        "model": model,
        "duration_seconds": duration_seconds,
        "ratio": ratio,
        "variations": variations,
        "budget": budget_evidence,
        "providers_verified_on": config.verified_on,
    }
    if not options.live:
        storage.append_event(
            run,
            "validated",
            {"mode": "DRY_RUN", "provider_call_count": variations},
        )
        _write_motion_smoke_bundle(
            config,
            storage,
            run,
            request=base_request,
            resolved=base_config,
            plan=plan,
            keyframe=keyframe,
            status="DRY_RUN_COMPLETE",
            results={
                "status": "DRY_RUN",
                "submission_count": 0,
                "successful_outputs": 0,
                "failed_outputs": 0,
                "results": [],
            },
            candidates=(),
            cost=_motion_smoke_cost(
                config, model, duration_seconds, variations, estimated_credits, None
            ),
            edit_commands="",
        )
        storage.append_event(run, "dry_run_completed", {"submission_count": 0})
        storage.assert_complete(run)
        return VideoRunOutcome(
            run.run_id, run.path, run, plan, variations, 0, "DRY_RUN_COMPLETE"
        )

    storage.append_event(
        run,
        "live_authorized",
        {
            "stage": "motion_smoke",
            "provider": "runway",
            "provider_call_count": 1,
            "budget": budget_evidence,
        },
    )
    execution: ExecutionRecord | None = None
    try:
        # Re-check immediately before the paid submission/upload boundary.
        check_estimate(
            budgets,
            provider="runway",
            estimated_usd=estimated_usd,
            estimated_credits=estimated_credits,
            operation="Runway submission",
        )
        execution = execute_provider_request(
            request,
            provider,
            storage,
            run,
            config.root / "outputs/broll" / run.run_id,
        )
        if execution.status is not VideoTaskStatus.SUCCEEDED or len(execution.artifacts) != 1:
            raise ExternalInputBlocked(
                f"motion smoke provider task did not succeed: {execution.status.value}"
            )
        artifact = execution.artifacts[0]
        try:
            expected_width, expected_height = (int(value) for value in ratio.split(":", 1))
        except (TypeError, ValueError) as exc:
            raise VideoConfigError("motion smoke ratio is invalid") from exc
        if artifact.width != expected_width or artifact.height != expected_height:
            raise ExternalInputBlocked(
                "motion smoke output resolution does not match the requested ratio"
            )
        if artifact.duration_seconds is None or abs(artifact.duration_seconds - duration_seconds) > 0.5:
            raise ExternalInputBlocked(
                "motion smoke output duration is outside the requested tolerance"
            )
        technical = generate_video_evidence(
            artifact.path,
            artifact.path.parent / "evidence",
            prefix=artifact.path.stem,
            timeout_seconds=min(config.limits.provider_timeout_seconds, 120),
        )
        for frame in technical["frames"].values():
            frame["path"] = Path(frame["path"]).relative_to(config.root)
        technical["contact_sheet"]["path"] = Path(
            technical["contact_sheet"]["path"]
        ).relative_to(config.root)
        check_actual(
            budgets,
            provider="runway",
            actual_usd=(
                execution.actual_credits * credit_usd
                if execution.actual_credits is not None
                else None
            ),
            actual_credits=execution.actual_credits,
            operation="motion smoke",
        )
    except Exception as exc:
        _write_motion_smoke_bundle(
            config,
            storage,
            run,
            request=base_request,
            resolved={**base_config, "failure_stage": "motion_smoke"},
            plan=plan,
            keyframe=keyframe,
            status="FAILED",
            results={
                "status": "FAILED",
                "submission_count": (
                    1 if execution is not None and execution.provider_task_id else 0
                ),
                "submission_count_known": execution is not None,
                "successful_outputs": 0,
                "failed_outputs": 1,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "results": (
                    [
                        {
                            "request_id": execution.request_id,
                            "provider_task_id": execution.provider_task_id,
                            "status": execution.status.value,
                            "submission_attempts": execution.submission_attempts,
                            "error_code": execution.error_code,
                            "error_message": execution.error_message,
                            "estimated_credits": execution.estimated_credits,
                            "actual_credits": execution.actual_credits,
                            "artifacts": [],
                        }
                    ]
                    if execution is not None
                    else []
                ),
            },
            candidates=(),
            cost=_motion_smoke_cost(
                config, model, duration_seconds, variations, estimated_credits, None
            ),
            edit_commands="",
        )
        storage.append_event(
            run,
            "workflow_failed",
            {"stage": "motion_smoke", "error_type": type(exc).__name__, "error": str(exc)},
        )
        storage.assert_complete(run)
        raise
    candidate = _artifact_evidence(artifact, config.root)
    candidate["technical_evidence"] = technical
    result_evidence = {
        "request_id": request.request_id,
        "provider_task_id": execution.provider_task_id,
        "status": execution.status.value,
        "submission_attempts": execution.submission_attempts,
        "estimated_credits": execution.estimated_credits,
        "actual_credits": execution.actual_credits,
        "error_code": execution.error_code,
        "error_message": execution.error_message,
        "artifacts": [candidate],
    }
    edit_commands = "\n".join(
        " ".join(str(item) for item in command) for command in technical["commands"]
    ) + "\n"
    _write_motion_smoke_bundle(
        config,
        storage,
        run,
        request=base_request,
        resolved=base_config,
        plan=plan,
        keyframe=keyframe,
        status="SUCCEEDED",
        results={
            "status": "SUCCEEDED",
            "submission_count": 1,
            "successful_outputs": 1,
            "failed_outputs": 0,
            "results": [result_evidence],
        },
        candidates=(candidate,),
        cost=_motion_smoke_cost(
            config,
            model,
            duration_seconds,
            variations,
            execution.estimated_credits or estimated_credits,
            execution.actual_credits,
        ),
        edit_commands=edit_commands,
    )
    storage.append_event(
        run,
        "motion_smoke_completed",
        {"status": "SUCCEEDED", "provider_task_id": execution.provider_task_id},
    )
    storage.assert_complete(run)
    return VideoRunOutcome(run.run_id, run.path, run, plan, 1, 1, "SUCCEEDED")


def _write_motion_smoke_bundle(
    config: VideoProjectConfig,
    storage: VideoRunStorage,
    run: VideoRunContext,
    *,
    request: Mapping[str, Any],
    resolved: Mapping[str, Any],
    plan: ShotPlan,
    keyframe: ApprovedKeyframe,
    status: str,
    results: Mapping[str, Any],
    candidates: tuple[Mapping[str, Any], ...],
    cost: Mapping[str, Any],
    edit_commands: str,
) -> None:
    storage.write_json_new(run, "request.json", request)
    storage.write_yaml_new(run, "resolved-config.yaml", resolved)
    storage.write_bytes_new(run, "script.txt", b"")
    storage.write_json_new(
        run,
        "script-hash.json",
        {"status": "NOT_APPLICABLE", "reason": "independent motion smoke has no MTL script"},
    )
    storage.write_json_new(
        run,
        "audio-hash.json",
        {"status": "NOT_APPLICABLE", "reason": "independent motion smoke has no voice/audio"},
    )
    storage.write_json_new(run, "keyframe-hash.json", _keyframe_evidence(keyframe, config))
    storage.write_json_new(run, "shot-plan.json", to_primitive(plan))
    storage.write_json_new(run, "provider-results.json", results)
    storage.write_text_new(run, "edit-commands.txt", edit_commands)
    storage.write_review_new(
        run, blank_review_rows(run.run_id, "motion_smoke", candidates)
    )
    storage.write_json_new(run, "cost.json", cost)
    storage.write_text_new(
        run,
        "summary.md",
        summary_markdown(
            run_id=run.run_id,
            preset="motion_smoke",
            status=status,
            provider_call_count=int(request.get("provider_call_count") or 0),
            output_count=len(candidates),
            total_provider_cost=cost.get("total_provider_cost"),
        ),
    )


def _motion_smoke_cost(
    config: VideoProjectConfig,
    model: str,
    duration_seconds: int,
    variations: int,
    estimated_credits: float | None,
    actual_credits: float | None,
) -> dict[str, Any]:
    credit_usd = float(config.providers["runway"].settings.get("credit_usd") or 0.01)
    effective_credits = actual_credits if actual_credits is not None else estimated_credits
    amount = effective_credits * credit_usd if effective_credits is not None else None
    return {
        "voice_cost": None,
        "talking_video_cost": None,
        "motion_video_cost": amount,
        "estimated_runway_credits": estimated_credits,
        "actual_runway_credits": actual_credits,
        "editing_cost": 0,
        "storage_cost": None,
        "total_provider_cost": amount,
        "currency": config.currency,
        "components": [
            {
                "category": "motion",
                "provider": "runway",
                "model": model,
                "generated_seconds": duration_seconds * variations,
                "attempts": variations if actual_credits is not None else 0,
                "successful_outputs": variations if actual_credits is not None else 0,
                "failed_outputs": 0,
                "amount": amount,
                "basis": "actual" if actual_credits is not None else "estimated",
                "currency": config.currency,
                "estimated_credits": estimated_credits,
                "actual_credits": actual_credits,
                "pricing_source": config.providers["runway"].settings.get("pricing_source"),
                "pricing_date": config.providers["runway"].settings.get(
                    "pricing_verified_on"
                ),
            }
        ],
    }


def _budget_limits(options: VideoRunOptions) -> BudgetLimits:
    return BudgetLimits(
        max_provider_cost_usd=options.max_provider_cost_usd,
        max_runway_credits=options.max_runway_credits,
        accept_unknown_provider_cost=options.accept_unknown_provider_cost,
    )


def _budget_evidence(
    limits: BudgetLimits, estimated_usd: float | None, estimated_credits: float | None
) -> dict[str, Any]:
    return {
        "max_provider_cost_usd": limits.max_provider_cost_usd,
        "max_runway_credits": limits.max_runway_credits,
        "accept_unknown_provider_cost": limits.accept_unknown_provider_cost,
        "estimated_provider_cost_usd": estimated_usd,
        "estimated_runway_credits": estimated_credits,
    }


def _estimate_talking_stage_usd(
    config: VideoProjectConfig,
    *,
    provider_name: str,
    talking_results: int,
    duration_seconds: float,
    include_voice: bool,
) -> float | None:
    provider = config.providers.get(provider_name)
    if provider is None:
        return None
    price: float | None = None
    pricing = provider.settings.get("pricing")
    if isinstance(pricing, Mapping):
        model = provider.settings.get("model")
        record = pricing.get(model) if isinstance(pricing.get(model), Mapping) else None
        if isinstance(record, Mapping) and record.get("usd_per_unit") is not None:
            price = float(record["usd_per_unit"])
    if price is None:
        return None
    amount = duration_seconds * talking_results * price
    if include_voice:
        voice = config.providers.get(str(config.voice_profile.provider or ""))
        voice_pricing = voice.settings.get("pricing") if voice is not None else None
        if not isinstance(voice_pricing, Mapping) or voice_pricing.get("usd_per_unit") is None:
            return None
        amount += duration_seconds * float(voice_pricing["usd_per_unit"])
    return round(amount, 6)


def _estimate_motion_credits(
    config: VideoProjectConfig, plan: ShotPlan
) -> float | None:
    total = 0.0
    found = False
    for shot in plan.shots:
        for request in shot.requests:
            if request.responsibility != "motion":
                continue
            provider = config.providers.get(request.provider)
            models = provider.settings.get("supported_models") if provider else None
            capability = models.get(request.model) if isinstance(models, Mapping) else None
            if not isinstance(capability, Mapping) or capability.get("credits_per_second") is None:
                return None
            if request.duration_seconds is None:
                return None
            total += float(capability["credits_per_second"]) * float(
                request.duration_seconds
            )
            found = True
    return total if found else None


def _resolve_calibrated_smoke_audio(
    config: VideoProjectConfig,
    script: ScriptRecord,
    *,
    run_id: str,
    provider: Any,
    budget_limits: BudgetLimits,
    estimated_stage_usd: float | None,
    enforce_budget: bool,
    attempts: list[dict[str, Any]],
) -> ApprovedAudio:
    """Synthesize at most three exact-script candidates without rewriting the script."""

    speeds = (0.9, 1.0, 1.1)
    for index, speed in enumerate(speeds, start=1):
        if enforce_budget:
            check_estimate(
                budget_limits,
                provider="heygen",
                estimated_usd=estimated_stage_usd,
                operation=f"HeyGen speech submission {index}",
            )
        audio = resolve_or_synthesize_audio(
            config,
            script,
            run_id=run_id,
            provider=provider,
            speed_override=speed,
        )
        record = {
            "attempt": index,
            "speed": speed,
            "provider_request_id": audio.provider_task_id,
            "path": audio.path,
            "sha256": audio.sha256,
            "duration_seconds": audio.duration_seconds,
            "within_smoke_range": 8 <= audio.duration_seconds <= 12,
        }
        attempts.append(record)
        if record["within_smoke_range"]:
            return audio
        # Preserve every paid result as derived evidence while freeing the
        # canonical per-run output name for the next bounded calibration call.
        current = config.root / audio.path
        calibrated = current.with_name(
            f"{current.stem}-speed-{str(speed).replace('.', 'p')}{current.suffix}"
        )
        if calibrated.exists():
            raise VideoConfigError(f"voice calibration output already exists: {calibrated}")
        os.replace(current, calibrated)
        record["path"] = calibrated.relative_to(config.root)
    raise ExternalInputBlocked(
        "Tooltip speech remained outside 8..12 seconds after bounded speeds 0.9, 1.0, and 1.1; "
        "manual audio selection is required"
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
    voice_provider_needed = False
    if plan.voice_request_count:
        voice_name = str(config.voice_profile.provider or "")
        credential = _credential_name(voice_name)
        if not str(environment.get(credential) or "").strip():
            raise ExternalInputBlocked(f"live provider credential is missing: {credential}")
        voice_provider_needed = voice_provider is None
        if options.audio_override is not None:
            raise VideoConfigError("audio override is unavailable when voice synthesis is required")
        audio: ApprovedAudio | None = None
    else:
        audio = resolve_approved_audio(config, script, override=options.audio_override)
        _validate_talking_validation_audio(
            provider_name, audio.duration_seconds, environment, first_live_smoke
        )
    estimated_talking_usd = _estimate_talking_stage_usd(
        config,
        provider_name=provider_name,
        talking_results=len(plan.shots[0].requests),
        duration_seconds=(audio.duration_seconds if audio is not None else 12.0),
        include_voice=bool(plan.voice_request_count),
    )
    budget_limits = _budget_limits(options)
    if provider is None or voice_provider_needed:
        # Enforce before construction of either real provider client.
        check_estimate(
            budget_limits,
            provider=provider_name,
            estimated_usd=estimated_talking_usd,
            operation="talking smoke provider construction",
        )
    real_talking_provider = provider is None
    if voice_provider_needed:
        voice_provider = _create_voice_provider(config, voice_name, environment)
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
            "budget": _budget_evidence(
                budget_limits, estimated_talking_usd, None
            ),
        },
    )
    voice_called = 0
    voice_calibration_attempts: list[dict[str, Any]] = []
    requests: list[TalkingVideoRequest] = []
    executions: list[ExecutionRecord] = []
    try:
        if plan.voice_request_count:
            audio = _resolve_calibrated_smoke_audio(
                config,
                script,
                run_id=run.run_id,
                provider=voice_provider,
                budget_limits=budget_limits,
                estimated_stage_usd=estimated_talking_usd,
                enforce_budget=(
                    options.max_provider_cost_usd is not None
                    or options.accept_unknown_provider_cost
                ),
                attempts=voice_calibration_attempts,
            )
            voice_called = len(voice_calibration_attempts)
            storage.append_event(
                run,
                "voice_synthesized",
                {
                    "provider": config.voice_profile.provider,
                    "model": config.voice_profile.model,
                    "audio_sha256": audio.sha256,
                    "calibration_attempts": voice_calibration_attempts,
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
                if provider is not None and (
                    options.max_provider_cost_usd is not None
                    or options.accept_unknown_provider_cost
                ):
                    check_estimate(
                        budget_limits,
                        provider=provider_name,
                        estimated_usd=estimated_talking_usd,
                        operation="HeyGen talking submission",
                    )
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
            if real_talking_provider and execution.status is VideoTaskStatus.SUCCEEDED:
                for artifact in execution.artifacts:
                    _validate_talking_media_output(artifact, preset.resolution, audio.duration_seconds)
            if execution.status is not VideoTaskStatus.SUCCEEDED:
                break
    except Exception as exc:
        voice_called = max(voice_called, len(voice_calibration_attempts))
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
            "budget": _budget_evidence(
                budget_limits, estimated_talking_usd, None
            ),
            "voice_calibration_attempts": voice_calibration_attempts,
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
            "budget": _budget_evidence(
                budget_limits, estimated_talking_usd, None
            ),
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


def preview_motion_smoke(project_root: Path, options: VideoRunOptions) -> VideoRunOutcome:
    """Resolve the motion smoke without constructing a provider or making a paid call."""
    if options.live or options.action != "motion_smoke":
        raise ValueError("preview_motion_smoke requires a dry-run motion_smoke option")
    config = load_video_config(project_root, require_inputs=False)
    keyframe = _keyframe(config, options.keyframe_id)
    model = options.motion_model or "gen4_turbo"
    duration = options.motion_duration if options.motion_duration is not None else 5
    ratio = options.motion_ratio or "1280:720"
    prompt = _resolve_motion_prompt(config, options.motion_prompt)
    _validate_motion_provider_settings(config, model, duration, ratio, prompt)
    if options.max_runway_credits is not None:
        _validate_motion_credit_cap(config, model, duration, 1, options.max_runway_credits)
    plan = _motion_plan("motion_smoke", prompt, model, duration, ratio, 1)
    cost = estimate_plan_cost(plan, config, talking_duration_seconds=None)
    cost.update({"runway_credit_cap": options.max_runway_credits, "estimated_runway_credits": _motion_credit_estimate(config, model, duration, 1)})
    storage = VideoRunStorage(config.root)
    run = storage.create_run("motion-smoke")
    requests = [_motion_request_from_plan(run.run_id, config, keyframe, prompt, item, ratio) for item in plan.shots[0].requests]
    storage.append_event(run, "validated", {"mode": "DRY_RUN", "action": "motion_smoke", "provider_call_count": 1})
    _write_motion_bundle(config, options, plan, keyframe, prompt, storage, run, requests, (), cost, status="DRY_RUN_COMPLETE", smoke_context=None)
    storage.append_event(run, "dry_run_completed", {"submission_count": 0})
    storage.assert_complete(run)
    return VideoRunOutcome(run.run_id, run.path, run, plan, 1, 0, "DRY_RUN_COMPLETE")


def preview_motion_v7(project_root: Path, *, keyframe_id: str | None) -> VideoRunOutcome:
    """Write one local-only V7 A/B/C planning run without a live counterpart."""

    config = load_video_config(project_root, require_inputs=False)
    keyframe = _keyframe(config, keyframe_id)
    candidates = load_v7_candidates(config.root)
    planned_shots: list[PlannedShot] = []
    requests: list[MotionVideoRequest] = []
    candidate_metadata: list[dict[str, Any]] = []
    estimated_credits = 0.0
    estimate_known = True
    for index, candidate in enumerate(candidates, start=1):
        _validate_motion_provider_settings(
            config,
            candidate.model,
            candidate.duration_seconds,
            candidate.ratio,
            candidate.prompt,
        )
        request_id = f"motion-v7-{candidate.candidate_id}"
        planned = PlannedRequest(
            request_id=request_id,
            shot_id=candidate.candidate_id,
            variation=index,
            responsibility="motion",
            provider=candidate.provider,
            model=candidate.model,
            duration_seconds=float(candidate.duration_seconds),
        )
        planned_shots.append(
            PlannedShot(
                shot_id=candidate.candidate_id,
                kind="motion",
                source_role=keyframe.keyframe_id,
                prompt=candidate.prompt,
                duration_seconds=float(candidate.duration_seconds),
                variation_count=1,
                selection_required=True,
                requests=(planned,),
            )
        )
        estimate = candidate_credit_estimate(candidate, config.providers)
        if estimate is None:
            estimate_known = False
        else:
            estimated_credits += estimate
        candidate_metadata.append(candidate.evidence(estimate))
    plan = ShotPlan(
        preset="motion-v7",
        mode="motion_v7_dry_run",
        script_id="not_applicable",
        aspect_ratio="16:9",
        resolution="1280:720",
        frame_rate=30,
        shots=tuple(planned_shots),
        final_edit_variations=0,
    )
    if plan.provider_call_count != 3:
        raise VideoConfigError("V7 dry-run must contain exactly three planned requests")

    storage = VideoRunStorage(config.root)
    run = storage.create_run("motion-v7")
    for candidate, shot in zip(candidates, planned_shots, strict=True):
        planned = shot.requests[0]
        requests.append(
            MotionVideoRequest(
                request_id=f"{run.run_id}-{planned.request_id}",
                run_id=run.run_id,
                preset="motion-v7",
                shot_id=candidate.candidate_id,
                variation=planned.variation,
                provider=candidate.provider,
                model=candidate.model,
                image_path=config.root / keyframe.path,
                image_sha256=keyframe.sha256,
                prompt_path=config.root / candidate.prompt.path,
                prompt_text=candidate.prompt.text,
                prompt_sha256=candidate.prompt.sha256,
                ratio=candidate.ratio,
                duration_seconds=candidate.duration_seconds,
                seed=None,
                output_format="mp4",
                timeout_seconds=config.limits.provider_timeout_seconds,
                max_retries=config.limits.max_retries,
            )
        )
    cost = estimate_plan_cost(plan, config, talking_duration_seconds=None)
    cost.update(
        {
            "estimated_runway_credits": estimated_credits if estimate_known else None,
            "actual_runway_credits": None,
            "paid_calls": 0,
        }
    )
    comparison = build_v7_comparison()
    storage.append_event(
        run,
        "validated",
        {
            "mode": "DRY_RUN",
            "action": "motion_v7_dry_run",
            "provider_call_count": plan.provider_call_count,
            "submission_count": 0,
        },
    )
    storage.write_json_new(
        run,
        "request.json",
        {
            "run_id": run.run_id,
            "mode": "DRY_RUN",
            "action": "motion_v7_dry_run",
            "preset": "motion-v7",
            "provider": "runway",
            "provider_call_count": plan.provider_call_count,
            "submission_count": 0,
            "paid_calls": 0,
            "requests": [to_primitive(request) for request in requests],
            "candidate_metadata": candidate_metadata,
            "subject_lock_comparison": comparison,
        },
    )
    storage.write_yaml_new(
        run,
        "resolved-config.yaml",
        {
            "action": "motion_v7_dry_run",
            "live": False,
            "keyframe_id": keyframe.keyframe_id,
            "candidate_metadata": candidate_metadata,
            "subject_lock_comparison": comparison,
            "p1_2_live_gate": "BLOCKED_PENDING_P1_1_HUMAN_PASS",
        },
    )
    storage.write_bytes_new(run, "script.txt", b"")
    storage.write_json_new(run, "script-hash.json", {"status": "not_applicable", "sha256": None})
    storage.write_json_new(run, "audio-hash.json", {"status": "not_applicable", "sha256": None})
    storage.write_json_new(run, "keyframe-hash.json", _keyframe_evidence(keyframe, config))
    storage.write_json_new(
        run,
        "shot-plan.json",
        {
            **to_primitive(plan),
            "candidate_metadata": candidate_metadata,
            "subject_lock_comparison": comparison,
        },
    )
    storage.write_json_new(
        run,
        "provider-results.json",
        {
            "status": "DRY_RUN",
            "provider": "runway",
            "submission_count": 0,
            "results": [],
        },
    )
    storage.write_text_new(run, "edit-commands.txt", "")
    storage.write_review_new(
        run,
        blank_review_rows(
            run.run_id,
            "motion-v7",
            [
                {
                    "video_id": item["candidate_id"],
                    "candidate": f'{item["candidate_id"]}-planned.mp4',
                }
                for item in candidate_metadata
            ],
        ),
    )
    storage.write_json_new(run, "cost.json", cost)
    storage.write_text_new(
        run,
        "summary.md",
        summary_markdown(
            run_id=run.run_id,
            preset="motion-v7",
            status="DRY_RUN_COMPLETE",
            provider_call_count=plan.provider_call_count,
            output_count=0,
            total_provider_cost=cost.get("total_provider_cost"),
        ),
    )
    storage.append_event(run, "dry_run_completed", {"submission_count": 0, "paid_calls": 0})
    storage.assert_complete(run)
    return VideoRunOutcome(
        run.run_id, run.path, run, plan, plan.provider_call_count, 0, "DRY_RUN_COMPLETE"
    )


def run_motion_v7_live(
    project_root: Path,
    *,
    keyframe_id: str | None,
    execute_live: bool,
    confirm_v7_batch: bool,
    max_runway_credits: float | None,
    provider: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> VideoRunOutcome:
    """Execute the fixed V7 A/B/C batch after one full evidence-first preflight."""

    environment = os.environ if environ is None else environ
    if not execute_live:
        raise ExternalInputBlocked("motion-v7-live requires explicit --execute-live")
    if not confirm_v7_batch:
        raise ExternalInputBlocked("motion-v7-live requires explicit --confirm-v7-batch")
    validate_live_provider_guard("runway", environment)

    config = load_video_config(project_root, require_inputs=False)
    if config.limits.max_concurrency != 1:
        raise VideoConfigError("V7 live batch requires configured concurrency one")
    keyframe = _keyframe(config, keyframe_id)
    source_path = config.root / keyframe.path
    provenance_path = config.root / keyframe.provenance_record
    if not source_path.is_file() or sha256_file(source_path) != keyframe.sha256:
        raise ExternalInputBlocked("approved V7 keyframe source is missing or hash-mismatched")
    if not provenance_path.is_file():
        raise ExternalInputBlocked("approved V7 keyframe provenance is missing")

    candidates = load_v7_candidates(config.root)
    if len(candidates) != 3:
        raise VideoConfigError("V7 live batch requires exactly three candidates")
    estimates: list[float] = []
    for candidate in candidates:
        _validate_motion_provider_settings(
            config,
            candidate.model,
            candidate.duration_seconds,
            candidate.ratio,
            candidate.prompt,
        )
        estimate = candidate_credit_estimate(candidate, config.providers)
        if estimate is None or not math.isfinite(estimate) or estimate <= 0:
            raise ExternalInputBlocked("V7 live Runway credit estimate is unavailable")
        estimates.append(estimate)
    estimated_credits = sum(estimates)
    if (
        max_runway_credits is None
        or not math.isfinite(max_runway_credits)
        or max_runway_credits <= 0
    ):
        raise ExternalInputBlocked(
            "motion-v7-live requires a finite positive --max-runway-credits cap"
        )
    if estimated_credits > max_runway_credits:
        raise ExternalInputBlocked(
            f"V7 live Runway credit cap exceeded: estimated {estimated_credits:g} "
            f"> cap {max_runway_credits:g}"
        )

    plan = _v7_live_plan(candidates, keyframe)
    if plan.provider_call_count != 3:
        raise VideoConfigError("V7 live batch must plan exactly three submissions")
    code_commit = _authoritative_code_commit()
    storage = VideoRunStorage(
        config.root,
        secrets=(str(environment.get("RUNWAYML_API_SECRET") or ""),),
    )

    if provider is None:
        provider = _create_motion_provider(config, environment)

    # Validate a complete request batch before allocating the parent evidence run.
    provisional = _v7_live_requests(
        "video-motion-v7-preflight", config, keyframe, candidates, plan
    )
    for request in provisional:
        provider.validate_request(request)

    run = storage.create_run("motion-v7")
    requests = _v7_live_requests(run.run_id, config, keyframe, candidates, plan)
    for request in requests:
        provider.validate_request(request)

    candidate_metadata = [
        {
            **candidate.evidence(estimate),
            "submission_state": "planned",
            "submission_attempts": 0,
        }
        for candidate, estimate in zip(candidates, estimates, strict=True)
    ]
    started_at = datetime.now().astimezone().isoformat()
    _write_v7_live_preflight_bundle(
        config=config,
        storage=storage,
        run=run,
        plan=plan,
        keyframe=keyframe,
        requests=requests,
        candidate_metadata=candidate_metadata,
        estimated_credits=estimated_credits,
        max_runway_credits=max_runway_credits,
        code_commit=code_commit,
        started_at=started_at,
    )
    _verify_v7_live_preflight_evidence(
        config=config,
        run=run,
        keyframe=keyframe,
        candidate_metadata=candidate_metadata,
        estimated_credits=estimated_credits,
    )
    storage.append_event(
        run,
        "preflight_evidence_verified",
        {
            "candidate_count": 3,
            "planned_submissions": 3,
            "estimated_runway_credits": estimated_credits,
        },
    )

    executions: list[ExecutionRecord] = []
    for request, estimate in zip(requests, estimates, strict=True):
        record = _execute_v7_request_once(
            request,
            provider,
            storage,
            run,
            config.root / "outputs/broll" / run.run_id,
            estimate,
        )
        executions.append(record)
        if record.status is not VideoTaskStatus.SUCCEEDED or not record.artifacts:
            break

    successful_count = sum(
        1
        for record in executions
        if record.status is VideoTaskStatus.SUCCEEDED and record.artifacts
    )
    status = (
        "SUCCEEDED"
        if successful_count == 3
        else ("PARTIAL" if successful_count else "FAILED")
    )
    _complete_v7_live_bundle(
        config=config,
        storage=storage,
        run=run,
        plan=plan,
        candidates=candidates,
        requests=requests,
        executions=executions,
        provider=provider,
        status=status,
        estimated_credits=estimated_credits,
        max_runway_credits=max_runway_credits,
        started_at=started_at,
    )
    storage.append_event(
        run,
        "motion_v7_live_completed",
        {
            "status": status,
            "submission_attempts": sum(item.submission_attempts for item in executions),
            "task_submission_count": sum(
                1 for item in executions if item.provider_task_id
            ),
        },
    )
    storage.assert_complete(run)
    return VideoRunOutcome(
        run.run_id,
        run.path,
        run,
        plan,
        3,
        sum(1 for item in executions if item.provider_task_id),
        status,
    )


def _v7_live_plan(candidates: tuple[Any, ...], keyframe: ApprovedKeyframe) -> ShotPlan:
    shots = tuple(
        PlannedShot(
            shot_id=candidate.candidate_id,
            kind="motion",
            source_role=keyframe.keyframe_id,
            prompt=candidate.prompt,
            duration_seconds=float(candidate.duration_seconds),
            variation_count=1,
            selection_required=True,
            requests=(
                PlannedRequest(
                    request_id=f"motion-v7-{candidate.candidate_id}",
                    shot_id=candidate.candidate_id,
                    variation=index,
                    responsibility="motion",
                    provider="runway",
                    model=candidate.model,
                    duration_seconds=float(candidate.duration_seconds),
                ),
            ),
        )
        for index, candidate in enumerate(candidates, start=1)
    )
    return ShotPlan(
        preset="motion-v7",
        mode="motion_v7_live",
        script_id="not_applicable",
        aspect_ratio="16:9",
        resolution="1280:720",
        frame_rate=30,
        shots=shots,
        final_edit_variations=0,
    )


def _v7_live_requests(
    run_id: str,
    config: VideoProjectConfig,
    keyframe: ApprovedKeyframe,
    candidates: tuple[Any, ...],
    plan: ShotPlan,
) -> list[MotionVideoRequest]:
    result: list[MotionVideoRequest] = []
    for candidate, shot in zip(candidates, plan.shots, strict=True):
        planned = shot.requests[0]
        result.append(
            MotionVideoRequest(
                request_id=f"{run_id}-{planned.request_id}",
                run_id=run_id,
                preset="motion-v7",
                shot_id=candidate.candidate_id,
                variation=planned.variation,
                provider="runway",
                model=candidate.model,
                image_path=config.root / keyframe.path,
                image_sha256=keyframe.sha256,
                prompt_path=config.root / candidate.prompt.path,
                prompt_text=candidate.prompt.text,
                prompt_sha256=candidate.prompt.sha256,
                ratio=candidate.ratio,
                duration_seconds=candidate.duration_seconds,
                seed=None,
                output_format="mp4",
                timeout_seconds=config.limits.provider_timeout_seconds,
                max_retries=0,
            )
        )
    return result


def _write_v7_live_preflight_bundle(
    *,
    config: VideoProjectConfig,
    storage: VideoRunStorage,
    run: VideoRunContext,
    plan: ShotPlan,
    keyframe: ApprovedKeyframe,
    requests: list[MotionVideoRequest],
    candidate_metadata: list[dict[str, Any]],
    estimated_credits: float,
    max_runway_credits: float,
    code_commit: str,
    started_at: str,
) -> None:
    comparison = build_v7_comparison()
    storage.append_event(
        run,
        "live_authorized",
        {
            "stage": "motion_v7_live",
            "provider": "runway",
            "candidate_count": 3,
            "planned_submissions": 3,
        },
    )
    storage.write_json_new(
        run,
        "request.json",
        {
            "run_id": run.run_id,
            "run_type": "P1-1 Motion V7",
            "mode": "LIVE",
            "action": "motion_v7_live",
            "preset": "motion-v7",
            "authoritative_code_commit": code_commit,
            "provider": "runway",
            "started_at": started_at,
            "candidate_count": 3,
            "planned_submissions": 3,
            "estimated_runway_credits": estimated_credits,
            "max_runway_credits": max_runway_credits,
            "live_authorization": {
                "execute_live": True,
                "confirm_v7_batch": True,
                "video_allow_live_calls": True,
                "credential_present": True,
            },
            "requests": [to_primitive(item) for item in requests],
            "candidate_metadata": candidate_metadata,
            "subject_lock_comparison": comparison,
        },
    )
    storage.write_yaml_new(
        run,
        "resolved-config.yaml",
        {
            "action": "motion_v7_live",
            "live": True,
            "canonical_live_allowed": False,
            "provider": "runway",
            "keyframe_id": keyframe.keyframe_id,
            "candidate_count": 3,
            "planned_submissions": 3,
            "estimated_runway_credits": estimated_credits,
            "max_runway_credits": max_runway_credits,
            "automatic_submission_retries": 0,
            "failure_policy": "fail_stop",
            "candidate_metadata": candidate_metadata,
            "subject_lock_comparison": comparison,
            "p1_2_state": "P1_2_LIVE_BLOCKED_PENDING_P1_1_HUMAN_PASS",
        },
    )
    storage.write_bytes_new(run, "script.txt", b"")
    storage.write_json_new(
        run, "script-hash.json", {"status": "not_applicable", "sha256": None}
    )
    storage.write_json_new(
        run, "audio-hash.json", {"status": "not_applicable", "sha256": None}
    )
    storage.write_json_new(run, "keyframe-hash.json", _keyframe_evidence(keyframe, config))
    storage.write_json_new(
        run,
        "shot-plan.json",
        {
            **to_primitive(plan),
            "candidate_metadata": candidate_metadata,
            "subject_lock_comparison": comparison,
            "preflight_state": "VALIDATED_AWAITING_SUBMISSION",
        },
    )
    storage.write_text_new(run, "edit-commands.txt", "")
    storage.write_review_new(
        run,
        blank_review_rows(
            run.run_id,
            "motion-v7",
            [
                {
                    "video_id": item["candidate_id"],
                    "candidate": f'{item["candidate_id"]}.mp4',
                }
                for item in candidate_metadata
            ],
        ),
    )
    cost = estimate_plan_cost(plan, config, talking_duration_seconds=None)
    cost.update(
        {
            "estimated_runway_credits": estimated_credits,
            "max_runway_credits": max_runway_credits,
            "actual_runway_credits": None,
            "paid_calls": None,
            "state": "PREFLIGHT_ESTIMATE",
        }
    )
    storage.write_json_new(run, "cost.json", cost)


def _verify_v7_live_preflight_evidence(
    *,
    config: VideoProjectConfig,
    run: VideoRunContext,
    keyframe: ApprovedKeyframe,
    candidate_metadata: list[dict[str, Any]],
    estimated_credits: float,
) -> None:
    try:
        request = json.loads((run.path / "request.json").read_text(encoding="utf-8"))
        plan = json.loads((run.path / "shot-plan.json").read_text(encoding="utf-8"))
        source = json.loads((run.path / "keyframe-hash.json").read_text(encoding="utf-8"))
        cost = json.loads((run.path / "cost.json").read_text(encoding="utf-8"))
        with (run.path / "review.csv").open(newline="", encoding="utf-8") as handle:
            review_rows = list(csv.DictReader(handle))
    except (OSError, json.JSONDecodeError, csv.Error) as exc:
        raise VideoConfigError("V7 live preflight evidence is unreadable") from exc
    expected_ids = [item["candidate_id"] for item in candidate_metadata]
    expected_hashes = [item["prompt_sha256"] for item in candidate_metadata]
    if request.get("candidate_count") != 3 or request.get("planned_submissions") != 3:
        raise VideoConfigError("V7 live request evidence count verification failed")
    if [item.get("candidate_id") for item in request.get("candidate_metadata", [])] != expected_ids:
        raise VideoConfigError("V7 live request evidence order verification failed")
    if [item.get("prompt_sha256") for item in plan.get("candidate_metadata", [])] != expected_hashes:
        raise VideoConfigError("V7 live plan prompt verification failed")
    if source.get("sha256") != keyframe.sha256 or sha256_file(config.root / keyframe.path) != keyframe.sha256:
        raise VideoConfigError("V7 live source evidence verification failed")
    if cost.get("estimated_runway_credits") != estimated_credits:
        raise VideoConfigError("V7 live credit evidence verification failed")
    if len(review_rows) != 3 or any(
        str(row.get(field) or "").strip()
        for row in review_rows
        for field in QA_FIELDS[4:]
    ):
        raise VideoConfigError("V7 live Human QA evidence must contain three blank rows")


def _execute_v7_request_once(
    request: MotionVideoRequest,
    provider: Any,
    storage: VideoRunStorage,
    run: VideoRunContext,
    output_dir: Path,
    estimated_credits: float,
) -> ExecutionRecord:
    storage.append_event(
        run,
        "submission_attempt",
        {"request_id": request.request_id, "attempt": 1},
    )
    try:
        task_id = provider.submit(request)
    except Exception as exc:
        storage.append_event(
            run,
            "submission_failed",
            {"request_id": request.request_id, "error": str(exc)},
        )
        return ExecutionRecord(
            request.request_id,
            None,
            VideoTaskStatus.FAILED,
            1,
            (),
            getattr(exc, "code", "provider_submission_error"),
            str(exc),
            estimated_credits,
            None,
        )
    if not task_id:
        return ExecutionRecord(
            request.request_id,
            None,
            VideoTaskStatus.FAILED,
            1,
            (),
            "provider_submission_error",
            "provider submission returned no durable task ID",
            estimated_credits,
            None,
        )
    storage.append_event(
        run,
        "task_submitted",
        {"request_id": request.request_id, "provider_task_id": task_id},
    )
    try:
        result = provider.wait(task_id, request.timeout_seconds)
    except Exception as exc:
        return ExecutionRecord(
            request.request_id,
            task_id,
            VideoTaskStatus.FAILED,
            1,
            (),
            getattr(exc, "code", "provider_poll_error"),
            str(exc),
            estimated_credits,
            None,
        )
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
            1,
            (),
            result.error_code,
            result.error_message,
            result.estimated_credits or estimated_credits,
            result.actual_credits,
        )
    try:
        artifacts = provider.download_results(
            result,
            output_dir,
            request.request_id,
            request.timeout_seconds,
            0,
        )
        validated = tuple(validate_media_artifact(item) for item in artifacts)
    except Exception as exc:
        return ExecutionRecord(
            request.request_id,
            task_id,
            VideoTaskStatus.FAILED,
            1,
            (),
            getattr(exc, "code", "provider_download_error"),
            str(exc),
            result.estimated_credits or estimated_credits,
            result.actual_credits,
        )
    storage.append_event(
        run,
        "outputs_validated",
        {
            "request_id": request.request_id,
            "provider_task_id": task_id,
            "artifacts": [item.artifact_id for item in validated],
        },
    )
    return ExecutionRecord(
        request.request_id,
        task_id,
        VideoTaskStatus.SUCCEEDED,
        1,
        validated,
        estimated_credits=result.estimated_credits or estimated_credits,
        actual_credits=result.actual_credits,
    )


def _complete_v7_live_bundle(
    *,
    config: VideoProjectConfig,
    storage: VideoRunStorage,
    run: VideoRunContext,
    plan: ShotPlan,
    candidates: tuple[Any, ...],
    requests: list[MotionVideoRequest],
    executions: list[ExecutionRecord],
    provider: Any,
    status: str,
    estimated_credits: float,
    max_runway_credits: float,
    started_at: str,
) -> None:
    by_request = {item.request_id: item for item in executions}
    result_rows: list[dict[str, Any]] = []
    for candidate, request in zip(candidates, requests, strict=True):
        execution = by_request.get(request.request_id)
        if execution is None:
            result_rows.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "experiment_level": candidate.experiment_level,
                    "prompt_path": candidate.prompt.path,
                    "prompt_sha256": candidate.prompt.sha256,
                    "prompt_utf16_units": candidate.prompt_utf16_units,
                    "estimated_credits": candidate_credit_estimate(candidate, config.providers),
                    "submission_state": "not_submitted",
                    "submission_attempts": 0,
                    "provider_task_id": None,
                    "provider_status": None,
                    "error_code": None,
                    "error_message": None,
                    "artifacts": [],
                }
            )
            continue
        result_rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "experiment_level": candidate.experiment_level,
                "prompt_path": candidate.prompt.path,
                "prompt_sha256": candidate.prompt.sha256,
                "prompt_utf16_units": candidate.prompt_utf16_units,
                "estimated_credits": candidate_credit_estimate(candidate, config.providers),
                "submission_state": (
                    "submitted" if execution.provider_task_id else "failed"
                ),
                "submission_attempts": execution.submission_attempts,
                "provider_task_id": execution.provider_task_id,
                "provider_status": execution.status.value,
                "error_code": execution.error_code,
                "error_message": execution.error_message,
                "provider_estimated_credits": execution.estimated_credits,
                "provider_actual_credits": execution.actual_credits,
                "artifacts": [
                    _artifact_evidence(item, config.root) for item in execution.artifacts
                ],
            }
        )
    task_ids = [item.provider_task_id for item in executions if item.provider_task_id]
    http_count = getattr(provider, "http_request_count", None)
    http_known = isinstance(http_count, int) and not isinstance(http_count, bool) and http_count >= 0
    completed_at = datetime.now().astimezone().isoformat()
    storage.write_json_new(
        run,
        "provider-results.json",
        {
            "status": status,
            "provider": "runway",
            "started_at": started_at,
            "completed_at": completed_at,
            "planned_submissions": 3,
            "submission_attempts": sum(item.submission_attempts for item in executions),
            "submission_count": len(task_ids),
            "provider_task_ids": task_ids,
            "http_request_count": http_count if http_known else None,
            "http_request_count_known": http_known,
            "http_request_count_scope": "runway_api_submit_and_poll",
            "output_download_http_request_count": None,
            "output_download_http_request_count_known": False,
            "automatic_retries": 0,
            "replacement_tasks": 0,
            "results": result_rows,
        },
    )
    cost = json.loads((run.path / "cost.json").read_text(encoding="utf-8"))
    # `cost.json` is immutable plan evidence. Actual per-task cost facts are kept in
    # provider-results instead of rewriting it after live execution.
    actual_values = [item.actual_credits for item in executions if item.actual_credits is not None]
    actual_credits_text = f"{sum(actual_values):g}" if actual_values else "unknown"
    summary = summary_markdown(
        run_id=run.run_id,
        preset="motion-v7",
        status=status,
        provider_call_count=3,
        output_count=sum(len(item.artifacts) for item in executions),
        total_provider_cost=cost.get("total_provider_cost"),
    )
    summary += (
        "\n"
        f"- Planned Runway credits: {estimated_credits:g}\n"
        f"- Runway credit cap: {max_runway_credits:g}\n"
        f"- Actual Runway credits: {actual_credits_text}\n"
    )
    storage.write_text_new(run, "summary.md", summary)


def _authoritative_code_commit() -> str:
    repository = Path(__file__).resolve().parents[3]
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ExternalInputBlocked(
            "V7 live requires an authoritative repository code commit"
        ) from exc
    commit = completed.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ExternalInputBlocked("V7 live authoritative code commit is invalid")
    return commit


def generate_motion_variations(
    project_root: Path,
    options: VideoRunOptions,
    *,
    provider: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> VideoRunOutcome:
    """Generate 1..N Runway-only variations unlocked by a reviewed motion smoke."""
    if options.action != "motion_generate":
        raise ValueError("generate_motion_variations requires a motion_generate option")
    if options.motion_smoke_qa_attested:
        raise ExternalInputBlocked(
            "--motion-smoke-qa-attested is planning-only and cannot authorize Live generation"
        )
    environment = os.environ if environ is None else environ
    config = load_video_config(project_root, require_inputs=False)
    keyframe = _keyframe(config, options.keyframe_id)
    variations = options.motion_variations if options.motion_variations is not None else 1
    if isinstance(variations, bool) or not 1 <= variations <= config.limits.max_motion_variations_per_shot:
        raise ExternalInputBlocked(
            "motion variations must be within 1.."
            f"{config.limits.max_motion_variations_per_shot}"
        )
    model = options.motion_model or "gen4_turbo"
    duration = options.motion_duration if options.motion_duration is not None else 5
    ratio = options.motion_ratio or "1280:720"
    smoke, review_evidence = _validate_passing_motion_variation_smoke(
        config.root, options.smoke_run_id, options.smoke_review_file,
        allow_owner_attestation=False,
    )
    smoke_request = _first_motion_request(smoke)
    if (smoke_request.get("keyframe_sha256") or smoke_request.get("image_sha256")) != keyframe.sha256:
        raise ExternalInputBlocked("motion smoke used a different approved keyframe digest")
    prompt_path = Path(str(smoke_request.get("prompt_path") or ""))
    if not prompt_path.as_posix():
        raise ExternalInputBlocked("motion smoke prompt provenance is missing")
    if prompt_path.is_absolute():
        try:
            prompt_path = prompt_path.relative_to(config.root)
        except ValueError as exc:
            raise ExternalInputBlocked("motion smoke prompt provenance escapes project root") from exc
    try:
        prompt = load_video_prompt(config.root, prompt_path)
    except VideoPromptError as exc:
        raise ExternalInputBlocked("motion smoke prompt provenance is invalid") from exc
    if prompt.sha256 != smoke_request.get("prompt_sha256") or prompt.text != smoke_request.get("prompt_text"):
        raise ExternalInputBlocked("motion smoke prompt no longer matches its recorded provenance")
    _validate_motion_provider_settings(config, model, duration, ratio, prompt)
    cap = options.max_runway_credits
    _validate_motion_credit_cap(config, model, duration, variations, cap)
    if options.live:
        validate_live_provider_guard("runway", environment)
    if provider is None:
        if not options.live:
            raise ValueError("motion variation preview must use preview_motion_variations")
        provider = _create_motion_provider(config, environment)
    return _execute_motion_run(
        config,
        options,
        keyframe=keyframe,
        prompt=prompt,
        model=model,
        duration=duration,
        ratio=ratio,
        variations=variations,
        action="motion_generate",
        provider=provider,
        smoke_context={
            "motion_smoke_run_id": options.smoke_run_id,
            "motion_smoke_review": review_evidence,
        },
        credit_cap=cap,
        environ=environment,
    )


def preview_motion_variations(
    project_root: Path, options: VideoRunOptions
) -> VideoRunOutcome:
    """Create a zero-call motion variation preview after validating smoke provenance."""
    if options.live or options.action != "motion_generate":
        raise ValueError("preview_motion_variations requires a dry-run motion_generate option")
    # Smoke and review are validated for dry-run too; only the live environment/credential
    # gate is skipped. This keeps previews useful while preserving the same evidence contract.
    config = load_video_config(project_root, require_inputs=False)
    keyframe = _keyframe(config, options.keyframe_id)
    variations = options.motion_variations if options.motion_variations is not None else 1
    if isinstance(variations, bool) or not 1 <= variations <= config.limits.max_motion_variations_per_shot:
        raise ExternalInputBlocked(
            "motion variations must be within 1.."
            f"{config.limits.max_motion_variations_per_shot}"
        )
    smoke, review_evidence = _validate_passing_motion_variation_smoke(
        config.root, options.smoke_run_id, options.smoke_review_file,
        # Dry-run validates immutable review provenance and records its state, but
        # human PASS is a live-only authorization boundary.
        allow_owner_attestation=True,
    )
    smoke_request = _first_motion_request(smoke)
    if (smoke_request.get("keyframe_sha256") or smoke_request.get("image_sha256")) != keyframe.sha256:
        raise ExternalInputBlocked("motion smoke used a different approved keyframe digest")
    prompt_path = Path(str(smoke_request.get("prompt_path") or ""))
    if prompt_path.is_absolute():
        try:
            prompt_path = prompt_path.relative_to(config.root)
        except ValueError as exc:
            raise ExternalInputBlocked("motion smoke prompt provenance escapes project root") from exc
    try:
        prompt = load_video_prompt(config.root, prompt_path)
    except VideoPromptError as exc:
        raise ExternalInputBlocked("motion smoke prompt provenance is invalid") from exc
    if prompt.sha256 != smoke_request.get("prompt_sha256") or prompt.text != smoke_request.get("prompt_text"):
        raise ExternalInputBlocked("motion smoke prompt no longer matches its recorded provenance")
    model = options.motion_model or str(smoke_request.get("model") or "gen4_turbo")
    duration = options.motion_duration if options.motion_duration is not None else int(smoke_request.get("duration_seconds") or 5)
    ratio = options.motion_ratio or str(smoke_request.get("ratio") or "1280:720")
    _validate_motion_provider_settings(config, model, duration, ratio, prompt)
    if options.max_runway_credits is not None:
        _validate_motion_credit_cap(config, model, duration, variations, options.max_runway_credits)
    plan = _motion_plan("motion_generate", prompt, model, duration, ratio, variations)
    cost = estimate_plan_cost(plan, config, talking_duration_seconds=None)
    cost.update({"runway_credit_cap": options.max_runway_credits, "estimated_runway_credits": _motion_credit_estimate(config, model, duration, variations)})
    storage = VideoRunStorage(config.root)
    run = storage.create_run("motion-generate")
    requests = [_motion_request_from_plan(run.run_id, config, keyframe, prompt, item, ratio) for item in plan.shots[0].requests]
    storage.append_event(run, "validated", {"mode": "DRY_RUN", "action": "motion_generate", "provider_call_count": variations})
    _write_motion_bundle(
        config, options, plan, keyframe, prompt, storage, run, requests, (), cost,
        status="DRY_RUN_COMPLETE", smoke_context={"motion_smoke_run_id": options.smoke_run_id, "motion_smoke_review": review_evidence},
    )
    storage.append_event(run, "dry_run_completed", {"submission_count": 0})
    storage.assert_complete(run)
    return VideoRunOutcome(run.run_id, run.path, run, plan, variations, 0, "DRY_RUN_COMPLETE")


def _motion_plan(mode: str, prompt: ResolvedPrompt, model: str, duration: int, ratio: str, variations: int) -> ShotPlan:
    requests = tuple(
        PlannedRequest(
            request_id=f"motion-{mode.replace('_', '-')}-v{index:03d}",
            shot_id="motion_variation",
            variation=index,
            responsibility="motion",
            provider="runway",
            model=model,
            duration_seconds=float(duration),
        )
        for index in range(1, variations + 1)
    )
    return ShotPlan(
        preset="motion-generate" if mode == "motion_generate" else "motion-smoke",
        mode=mode,
        script_id="",
        aspect_ratio=ratio,
        resolution=ratio,
        frame_rate=30,
        shots=(PlannedShot("motion_variation", "motion", "hero", prompt, float(duration), variations, variations > 1, requests),),
        final_edit_variations=1,
        voice_request_count=0,
    )


def _motion_request_from_plan(run_id: str, config: VideoProjectConfig, keyframe: ApprovedKeyframe, prompt: ResolvedPrompt, planned: PlannedRequest, ratio: str | None = None) -> MotionVideoRequest:
    return MotionVideoRequest(
        request_id=f"{run_id}-{planned.request_id}", run_id=run_id, preset="motion-generate",
        shot_id=planned.shot_id, variation=planned.variation, provider="runway", model=planned.model,
        image_path=config.root / keyframe.path, image_sha256=keyframe.sha256,
        prompt_path=config.root / prompt.path, prompt_text=prompt.text, prompt_sha256=prompt.sha256,
        ratio=ratio or "1280:720",
        duration_seconds=int(planned.duration_seconds or 0), seed=None, output_format="mp4",
        timeout_seconds=config.limits.provider_timeout_seconds, max_retries=config.limits.max_retries,
    )


def _execute_motion_run(config: VideoProjectConfig, options: VideoRunOptions, *, keyframe: ApprovedKeyframe, prompt: ResolvedPrompt, model: str, duration: int, ratio: str, variations: int, action: str, provider: Any, smoke_context: Mapping[str, Any] | None, credit_cap: float | None, environ: Mapping[str, str] | None = None) -> VideoRunOutcome:
    plan = _motion_plan(action, prompt, model, duration, ratio, variations)
    secret_environment = environ if options.live and environ is not None else {}
    storage = VideoRunStorage(config.root, secrets=tuple(value for key, value in secret_environment.items() if key.endswith(("_API_KEY", "_API_SECRET")) and value))
    run = storage.create_run("motion-smoke" if action == "motion_smoke" else "motion-generate")
    storage.append_event(run, "live_authorized", {"stage": action, "provider": "runway", "provider_call_count": variations, **dict(smoke_context or {})})
    requests = [_motion_request_from_plan(run.run_id, config, keyframe, prompt, item, ratio) for item in plan.shots[0].requests]
    executions: list[ExecutionRecord] = []
    try:
        for request in requests:
            try:
                executions.append(execute_provider_request(request, provider, storage, run, config.root / "outputs/broll" / run.run_id))
            except Exception as exc:
                storage.append_event(run, "request_failed", {"request_id": request.request_id, "error": str(exc)})
                executions.append(ExecutionRecord(request.request_id, None, VideoTaskStatus.FAILED, 1, (), getattr(exc, "code", "submission_or_download_error"), str(exc)))
    except Exception as exc:
        _write_motion_failure_bundle(config, options, plan, keyframe, prompt, storage, run, requests, executions, exc, smoke_context, credit_cap)
        raise
    artifacts = tuple(artifact for execution in executions for artifact in execution.artifacts)
    successful = sum(1 for execution in executions if execution.status is VideoTaskStatus.SUCCEEDED and execution.artifacts)
    status = "SUCCEEDED" if successful == variations else ("PARTIAL" if successful else "FAILED")
    cost = estimate_plan_cost(plan, config, talking_duration_seconds=None)
    cost.update({"runway_credit_cap": credit_cap, "estimated_runway_credits": _motion_credit_estimate(config, model, duration, variations)})
    _apply_execution_cost_facts(cost, executions, {request.request_id: "motion" for request in requests})
    _write_motion_bundle(config, options, plan, keyframe, prompt, storage, run, requests, executions, cost, status=status, smoke_context=smoke_context)
    storage.append_event(run, "motion_generation_completed", {"status": status, "successful_outputs": len(artifacts)})
    storage.assert_complete(run)
    return VideoRunOutcome(run.run_id, run.path, run, plan, variations, sum(1 for execution in executions if execution.provider_task_id), status)


def _write_motion_bundle(config: VideoProjectConfig, options: VideoRunOptions, plan: ShotPlan, keyframe: ApprovedKeyframe, prompt: ResolvedPrompt, storage: VideoRunStorage, run: VideoRunContext, requests: list[MotionVideoRequest], executions: tuple[ExecutionRecord, ...] | list[ExecutionRecord] | tuple[Any, ...], cost: Mapping[str, Any], *, status: str, smoke_context: Mapping[str, Any] | None) -> None:
    artifacts = tuple(artifact for execution in executions for artifact in execution.artifacts)
    request_evidence = [to_primitive(request) for request in requests]
    result_rows = [{"request_id": execution.request_id, "provider_task_id": execution.provider_task_id, "status": execution.status.value, "submission_attempts": execution.submission_attempts, "error_code": execution.error_code, "error_message": execution.error_message, "artifacts": [_artifact_evidence(artifact, config.root) for artifact in execution.artifacts]} for execution in executions]
    storage.write_json_new(run, "request.json", {"run_id": run.run_id, "mode": "LIVE" if options.live else "DRY_RUN", "action": options.action, "preset": "motion", "provider": "runway", "provider_call_count": plan.provider_call_count, "max_runway_credits": cost.get("runway_credit_cap"), "estimated_runway_credits": cost.get("estimated_runway_credits"), "requests": request_evidence, **dict(smoke_context or {})})
    storage.write_yaml_new(run, "resolved-config.yaml", {"action": options.action, "model": plan.shots[0].requests[0].model if plan.shots[0].requests else None, "duration_seconds": plan.shots[0].duration_seconds, "ratio": plan.aspect_ratio, "variations": plan.shots[0].variation_count, "credit_cap": cost.get("runway_credit_cap"), "estimated_runway_credits": cost.get("estimated_runway_credits"), "limits": to_primitive(config.limits), "live": options.live, **dict(smoke_context or {})})
    storage.write_bytes_new(run, "script.txt", b"")
    storage.write_json_new(run, "script-hash.json", {"status": "not_applicable", "sha256": None})
    storage.write_json_new(run, "audio-hash.json", {"status": "not_applicable", "sha256": None})
    storage.write_json_new(run, "keyframe-hash.json", _keyframe_evidence(keyframe, config))
    storage.write_json_new(run, "shot-plan.json", {**to_primitive(plan), "prompt": to_primitive(prompt)})
    storage.write_json_new(run, "provider-results.json", {"status": status, "provider": "runway", "submission_count": sum(1 for execution in executions if execution.provider_task_id), "submission_attempts": sum(execution.submission_attempts for execution in executions), "successful_outputs": len(artifacts), "failed_outputs": len(requests) - len(artifacts), "results": result_rows})
    storage.write_text_new(run, "edit-commands.txt", "")
    review_candidates = [_artifact_evidence(artifact, config.root) for artifact in artifacts]
    if not review_candidates and status == "DRY_RUN_COMPLETE":
        review_candidates = [
            {
                "video_id": request.request_id,
                "candidate": f"{request.shot_id}-planned-v{request.variation:03d}.mp4",
            }
            for request in requests
        ]
    storage.write_review_new(run, blank_review_rows(run.run_id, "motion", review_candidates))
    storage.write_json_new(run, "cost.json", cost)
    storage.write_text_new(run, "summary.md", summary_markdown(run_id=run.run_id, preset="motion", status=status, provider_call_count=plan.provider_call_count, output_count=len(artifacts), total_provider_cost=cost.get("total_provider_cost")))


def _write_motion_failure_bundle(config: VideoProjectConfig, options: VideoRunOptions, plan: ShotPlan, keyframe: ApprovedKeyframe, prompt: ResolvedPrompt, storage: VideoRunStorage, run: VideoRunContext, requests: list[MotionVideoRequest], executions: list[ExecutionRecord], error: Exception, smoke_context: Mapping[str, Any] | None, credit_cap: float | None) -> None:
    storage.append_event(run, "workflow_failed", {"stage": options.action, "error_type": type(error).__name__, "error": str(error)})
    cost = estimate_plan_cost(plan, config, talking_duration_seconds=None)
    cost.update({"runway_credit_cap": credit_cap, "estimated_runway_credits": _motion_credit_estimate(config, plan.shots[0].requests[0].model, int(plan.shots[0].duration_seconds or 0), plan.shots[0].variation_count)})
    _write_motion_bundle(config, options, plan, keyframe, prompt, storage, run, requests, tuple(executions), cost, status="FAILED", smoke_context=smoke_context)
    storage.assert_complete(run)


def _resolve_motion_prompt(config: VideoProjectConfig, selected: str | None) -> ResolvedPrompt:
    # Motion Smoke has a stable default independent of any preset's current
    # creative prompt. Variations never call this fallback: they read the
    # reviewed smoke's recorded prompt provenance instead.
    return load_video_prompt(
        config.root,
        Path(selected) if selected else Path("prompts/home-broll-v3.txt"),
    )


def _validate_motion_provider_settings(config: VideoProjectConfig, model: str, duration: int, ratio: str, prompt: ResolvedPrompt) -> None:
    definition = config.providers.get("runway")
    if definition is None:
        raise VideoConfigError("Runway motion provider is not configured")
    settings = definition.settings
    capability = (settings.get("supported_models") or {}).get(model)
    if not isinstance(capability, Mapping):
        raise VideoConfigError(f"unsupported Runway motion model: {model}")
    if duration not in tuple(int(value) for value in capability.get("durations", ())):
        raise VideoConfigError(f"unsupported Runway motion duration: {duration}")
    if ratio not in tuple(str(value) for value in capability.get("ratios", ())):
        raise VideoConfigError(f"unsupported Runway motion ratio: {ratio}")
    if capability.get("prompt_required") is True and not prompt.text.strip():
        raise VideoConfigError(f"Runway model {model} requires a prompt")
    prompt_limit = int(
        capability.get("prompt_utf16_max")
        or settings.get("prompt_utf16_max")
        or 1000
    )
    prompt_units = utf16_code_units(prompt.text)
    if prompt_units > prompt_limit:
        raise VideoConfigError(
            "Runway motion prompt exceeds the UTF-16 character limit "
            f"({prompt_units} > {prompt_limit})"
        )


def _validate_motion_plan_prompts(config: VideoProjectConfig, plan: ShotPlan) -> None:
    """Validate planned Runway prompts before constructing any provider client."""

    for shot in plan.shots:
        if shot.kind != "motion" or shot.prompt is None:
            continue
        for planned in shot.requests:
            if planned.responsibility != "motion" or planned.duration_seconds is None:
                continue
            _validate_motion_provider_settings(
                config,
                planned.model,
                int(planned.duration_seconds),
                plan.resolution,
                shot.prompt,
            )


def _motion_credit_estimate(config: VideoProjectConfig, model: str, duration: int, variations: int) -> float | None:
    settings = config.providers["runway"].settings
    capability = (settings.get("supported_models") or {}).get(model)
    if not isinstance(capability, Mapping) or capability.get("credits_per_second") is None:
        return None
    return float(capability["credits_per_second"]) * duration * variations


def _validate_motion_credit_cap(config: VideoProjectConfig, model: str, duration: int, variations: int, cap: float | None, *, require_cap: bool = True) -> None:
    if cap is not None and (not math.isfinite(cap) or cap <= 0):
        raise ExternalInputBlocked("max Runway credits must be a finite positive number")
    if cap is None and require_cap:
        raise ExternalInputBlocked("live motion generation requires an explicit --max-runway-credits cap")
    if cap is None:
        return
    estimate = _motion_credit_estimate(config, model, duration, variations)
    if estimate is None:
        raise ExternalInputBlocked("Runway credit estimate is unavailable; refusing live generation")
    if estimate > cap:
        raise ExternalInputBlocked(f"Runway credit cap exceeded: estimated {estimate:g} > cap {cap:g}")


def _validate_motion_smoke_guards(model: str, duration: int, ratio: str, cap: float | None, environment: Mapping[str, str], config: VideoProjectConfig) -> None:
    validate_live_provider_guard("runway", environment)
    if model != "gen4_turbo":
        raise ExternalInputBlocked("motion smoke model is strictly gen4_turbo")
    if duration != 5:
        raise ExternalInputBlocked("motion smoke duration is strictly 5 seconds")
    _validate_motion_credit_cap(config, model, duration, 1, cap)
    if cap is not None and cap > 25:
        raise ExternalInputBlocked("motion smoke credit cap must not exceed 25 Runway credits")
    if _motion_credit_estimate(config, model, duration, 1) > 25:
        raise ExternalInputBlocked("motion smoke maximum is 25 Runway credits")
    if ratio not in tuple(str(value) for value in config.providers["runway"].settings["supported_models"][model].get("ratios", ())):
        raise ExternalInputBlocked(f"unsupported Runway motion ratio: {ratio}")


def _create_motion_provider(config: VideoProjectConfig, environment: Mapping[str, str]) -> Any:
    from ..providers.runway_video import RunwayMotionProvider

    return RunwayMotionProvider(config.providers["runway"], api_key=str(environment["RUNWAYML_API_SECRET"]))


def _validate_passing_motion_variation_smoke(
    project_root: Path,
    run_id: str | None,
    review_file: Path | None,
    *,
    allow_owner_attestation: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not run_id or "/" in run_id or "\\" in run_id:
        raise ExternalInputBlocked("motion generation requires a reviewed passing --motion-smoke-run-id")
    run_dir = (project_root / "runs" / run_id).resolve()
    runs_root = (project_root / "runs").resolve()
    if runs_root not in run_dir.parents or not run_dir.is_dir():
        raise ExternalInputBlocked(f"motion smoke run does not exist: {run_id}")
    try:
        request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
        results = json.loads((run_dir / "provider-results.json").read_text(encoding="utf-8"))
        keyframe_evidence = json.loads((run_dir / "keyframe-hash.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalInputBlocked(f"motion smoke run evidence is incomplete: {run_id}") from exc
    if request.get("action") == "motion_v7_live":
        return _validate_passing_v7_parent(
            project_root,
            run_dir,
            request,
            results,
            keyframe_evidence,
            review_file,
        )
    if request.get("action") != "motion_smoke" or results.get("status") != "SUCCEEDED":
        raise ExternalInputBlocked("motion smoke run is not a successful Runway motion result")
    request_items = request.get("requests") or []
    recorded_keyframe_sha256 = next(
        (
            item.get("image_sha256") or item.get("keyframe_sha256")
            for item in request_items
            if isinstance(item, dict)
        ),
        None,
    )
    if not recorded_keyframe_sha256 or keyframe_evidence.get("sha256") != recorded_keyframe_sha256:
        raise ExternalInputBlocked("motion smoke keyframe provenance is inconsistent")
    result_items = results.get("results") or []
    if len(result_items) != 1 or len(result_items[0].get("artifacts") or []) != 1:
        raise ExternalInputBlocked("motion smoke must contain exactly one output")
    artifact = result_items[0]["artifacts"][0]
    candidate = str(artifact.get("candidate") or artifact.get("video_id") or "")
    if not candidate:
        raise ExternalInputBlocked("motion smoke output provenance is missing")
    if review_file is None:
        raise ExternalInputBlocked("motion generation requires an immutable --motion-smoke-review-file")
    if allow_owner_attestation:
        evidence = _validate_owner_motion_qa_attestation(
            project_root, run_dir, candidate, review_file
        )
    else:
        try:
            row, evidence = _load_motion_review_copy(project_root, run_dir, candidate, review_file)
        except ReviewError as exc:
            raise ExternalInputBlocked(str(exc)) from exc
        required = ("visual_identity_pass", "face_stability_pass", "hair_pass", "wardrobe_pass", "jewelry_pass", "eye_motion_pass", "background_pass", "motion_quality_pass")
        if _truthy(row.get("legacy_motion_schema")):
            required += ("age_stability_pass", "body_proportions_pass")
        else:
            required += ("technical_export_pass",)
        if any(not _truthy(row.get(field)) for field in required):
            raise ExternalInputBlocked("motion smoke manual QA review has incomplete or failing decisions")
        if not _truthy(row.get("mtl_review_ready")) or not str(row.get("reviewer") or "").strip():
            raise ExternalInputBlocked("motion smoke review must be explicitly approved by a reviewer")
        try:
            reviewed_at = datetime.fromisoformat(str(row.get("reviewed_at") or "").replace("Z", "+00:00"))
        except ValueError as exc:
            raise ExternalInputBlocked("motion smoke review reviewed_at is invalid") from exc
        if reviewed_at.tzinfo is None:
            raise ExternalInputBlocked("motion smoke review reviewed_at must include a timezone")
    source_path = (project_root / str(artifact.get("path") or "")).resolve()
    outputs_root = (project_root / "outputs/broll").resolve()
    if outputs_root not in source_path.parents or not source_path.is_file():
        raise ExternalInputBlocked("motion smoke output is missing or outside broll outputs")
    if sha256_file(source_path) != artifact.get("sha256"):
        raise ExternalInputBlocked("motion smoke output hash no longer matches evidence")
    return request, evidence


_V7_REQUIRED_PASS_FIELDS = (
    "visual_identity",
    "face_stability",
    "age_stability",
    "hair_stability",
    "body_proportions",
    "wardrobe",
    "jewelry",
    "mouth",
    "eyes",
    "background",
    "motion",
    "technical_export",
)


def _validate_passing_v7_parent(
    project_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    results: dict[str, Any],
    keyframe_evidence: dict[str, Any],
    review_file: Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if results.get("status") != "SUCCEEDED":
        raise ExternalInputBlocked("V7 parent run is not a successful Runway motion result")
    request_items = request.get("requests") or []
    result_items = results.get("results") or []
    expected_ids = list(V7_CANDIDATE_IDS)
    if (
        len(request_items) != len(expected_ids)
        or [item.get("shot_id") for item in request_items] != expected_ids
        or len(result_items) != len(expected_ids)
        or [item.get("candidate_id") for item in result_items] != expected_ids
    ):
        raise ExternalInputBlocked("V7 parent candidate provenance is not canonical A/B/C")
    recorded_keyframes = {
        item.get("image_sha256") or item.get("keyframe_sha256")
        for item in request_items
        if isinstance(item, dict)
    }
    if (
        len(recorded_keyframes) != 1
        or None in recorded_keyframes
        or keyframe_evidence.get("sha256") not in recorded_keyframes
    ):
        raise ExternalInputBlocked("V7 parent keyframe provenance is inconsistent")
    if review_file is None:
        raise ExternalInputBlocked("motion generation requires an immutable --motion-smoke-review-file")

    root = project_root.resolve()
    review_path = review_file if review_file.is_absolute() else root / review_file
    review_path = review_path.resolve()
    try:
        with review_path.open(newline="", encoding="utf-8") as source:
            review_reader = csv.DictReader(source)
            review_rows = list(review_reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ExternalInputBlocked("V7 review CSV is unreadable") from exc
    if review_reader.fieldnames != list(QA_FIELDS):
        raise ExternalInputBlocked("V7 review CSV does not match the exact video QA schema")
    if (
        len(review_rows) != len(expected_ids)
        or [row.get("video_id") for row in review_rows] != expected_ids
        or [row.get("candidate") for row in review_rows]
        != [f"{candidate_id}.mp4" for candidate_id in expected_ids]
    ):
        raise ExternalInputBlocked("V7 review candidate provenance is not canonical A/B/C")

    rows: dict[str, dict[str, str]] = {}
    review_evidence: dict[str, str] | None = None
    for candidate_id in expected_ids:
        try:
            row, evidence = load_external_review_row(
                root,
                run_dir,
                f"{candidate_id}.mp4",
                review_path,
                require_ready=False,
            )
        except ReviewError as exc:
            raise ExternalInputBlocked(str(exc)) from exc
        rows[candidate_id] = row
        review_evidence = evidence

    passing_ids = [
        candidate_id
        for candidate_id, row in rows.items()
        if all(_truthy(row.get(field)) for field in _V7_REQUIRED_PASS_FIELDS)
        and _truthy(row.get("mtl_review_ready"))
    ]
    if len(passing_ids) != 1:
        raise ExternalInputBlocked("V7 review must contain exactly one unique passing candidate")
    selected_id = passing_ids[0]
    for candidate_id, row in rows.items():
        _validate_review_attribution(row, candidate_id)
        if candidate_id != selected_id and str(row.get("mtl_review_ready") or "").strip().lower() not in {
            "false",
            "no",
            "0",
            "fail",
            "failed",
        }:
            raise ExternalInputBlocked(
                "V7 non-selected candidates require an explicit overall human FAIL"
            )

    selected_request: dict[str, Any] | None = None
    outputs_root = (root / "outputs/broll" / run_dir.name).resolve()
    for candidate_id, request_item, result_item in zip(
        expected_ids, request_items, result_items, strict=True
    ):
        artifacts = result_item.get("artifacts") or []
        if (
            len(artifacts) != 1
            or not result_item.get("provider_task_id")
            or artifacts[0].get("provider_task_id") != result_item.get("provider_task_id")
        ):
            raise ExternalInputBlocked("V7 candidate task/output provenance is incomplete")
        artifact = artifacts[0]
        if (
            result_item.get("candidate_id") != candidate_id
            or request_item.get("shot_id") != candidate_id
            or artifact.get("artifact_id") != request_item.get("request_id")
            or artifact.get("video_id") != request_item.get("request_id")
            or artifact.get("candidate") != f'{request_item.get("request_id")}.mp4'
        ):
            raise ExternalInputBlocked("V7 candidate task/output provenance is inconsistent")
        source_path = (root / str(artifact.get("path") or "")).resolve()
        if outputs_root not in source_path.parents or not source_path.is_file():
            raise ExternalInputBlocked("V7 candidate media is missing or outside its broll run")
        if sha256_file(source_path) != artifact.get("sha256"):
            raise ExternalInputBlocked("V7 candidate media hash no longer matches evidence")
        if candidate_id == selected_id:
            selected_request = dict(request_item)
    if selected_request is None:
        raise ExternalInputBlocked("V7 selected candidate request provenance is missing")

    selected_parent = dict(request)
    selected_parent["requests"] = [selected_request]
    selected_parent["selected_candidate_id"] = selected_id
    return selected_parent, {
        **dict(review_evidence or {}),
        "status": "P1_2_LIVE_READY",
        "live_authorized": True,
        "selected_candidate_id": selected_id,
        "human_qa_authority": "HUMAN",
        "automatic_human_qa": False,
        "source_review_copy_unchanged": True,
    }


def _validate_review_attribution(row: Mapping[str, Any], candidate_id: str) -> None:
    if not str(row.get("reviewer") or "").strip():
        raise ExternalInputBlocked(f"V7 candidate reviewer is required: {candidate_id}")
    raw_time = str(row.get("reviewed_at") or "").strip()
    try:
        reviewed_at = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExternalInputBlocked(
            f"V7 candidate reviewed_at is invalid: {candidate_id}"
        ) from exc
    if reviewed_at.tzinfo is None:
        raise ExternalInputBlocked(
            f"V7 candidate reviewed_at must include a timezone: {candidate_id}"
        )


def _validate_owner_motion_qa_attestation(
    project_root: Path,
    run_dir: Path,
    candidate: str,
    review_file: Path | None,
) -> dict[str, Any]:
    """Validate a planning-only review copy without treating it as authorization."""
    if review_file is None:
        raise ExternalInputBlocked("motion planning requires an immutable --motion-smoke-review-file")
    try:
        row, evidence = _load_motion_review_copy(
            project_root, run_dir, candidate, review_file
        )
    except ReviewError as exc:
        raise ExternalInputBlocked(str(exc)) from exc
    reviewed_fields = (
        "visual_identity_pass", "face_stability_pass", "hair_pass", "wardrobe_pass",
        "jewelry_pass", "eye_motion_pass", "background_pass", "motion_quality_pass",
        "technical_export_pass", "age_stability_pass", "body_proportions_pass",
        "mtl_review_ready", "reviewer", "reviewed_at",
    )
    reviewed_values = [str(row.get(field) or "").strip() for field in reviewed_fields]
    if not any(reviewed_values):
        review_status = "NOT_SET"
    elif str(row.get("mtl_review_ready") or "").strip().lower() in {"false", "no", "0", "fail", "failed"}:
        review_status = "HUMAN_QA_FAILED"
    else:
        review_status = "HUMAN_REVIEW_PRESENT_NOT_AUTHORIZING_DRY_RUN"
    return {
        **evidence,
        "status": review_status,
        "live_authorized": False,
        "source_review_copy_unchanged": True,
    }


def _load_motion_review_copy(project_root: Path, run_dir: Path, candidate: str, review_file: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Read modern video QA rows and the legacy motion-smoke QA schema immutably.

    Existing real motion smoke runs predate the unified video QA header. Supporting their
    equivalent, motion-only fields lets operators continue from that approved evidence without
    rewriting the run or weakening the stricter talking/pilot review parser.
    """
    root = project_root.resolve()
    path = review_file if review_file.is_absolute() else root / review_file
    path = path.resolve()
    reviews_root = (root / "outputs/reviews").resolve()
    if reviews_root not in path.parents or not path.is_file():
        raise ReviewError("review file must be an existing copy under outputs/reviews")
    baseline_path = run_dir / "review.csv"
    try:
        with baseline_path.open(newline="", encoding="utf-8") as source:
            baseline_reader = csv.DictReader(source)
            baseline_fields = baseline_reader.fieldnames or []
            baseline_rows = [dict(row) for row in baseline_reader if row.get("candidate") == candidate]
        with path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            fields = reader.fieldnames or []
            rows = [dict(row) for row in reader if row.get("candidate") == candidate]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ReviewError("motion review CSV is unreadable") from exc
    if len(baseline_rows) != 1 or len(rows) != 1:
        raise ReviewError(f"candidate must have exactly one motion review row: {candidate}")
    if fields == list(QA_FIELDS):
        row, evidence = load_external_review_row(root, run_dir, candidate, path, require_ready=False)
        normalized = dict(row)
        normalized.update(
            {
                "visual_identity_pass": row.get("visual_identity", ""),
                "face_stability_pass": row.get("face_stability", ""),
                "hair_pass": row.get("hair_stability", ""),
                "wardrobe_pass": row.get("wardrobe", ""),
                "jewelry_pass": row.get("jewelry", ""),
                "eye_motion_pass": row.get("eyes", ""),
                "background_pass": row.get("background", ""),
                "motion_quality_pass": row.get("motion", ""),
                "technical_export_pass": row.get("technical_export", ""),
                "age_stability_pass": row.get("age_stability", ""),
                "body_proportions_pass": row.get("body_proportions", ""),
            }
        )
        return normalized, evidence
    legacy_required = {"run_id", "video_id", "preset", "candidate", "mtl_review_ready", "reviewer", "reviewed_at"}
    if not legacy_required.issubset(fields) or not {"run_id", "video_id", "preset", "candidate"}.issubset(baseline_fields):
        raise ReviewError("motion review.csv header does not match a supported QA schema")
    baseline = baseline_rows[0]
    row = rows[0]
    for field in ("run_id", "video_id", "preset", "candidate"):
        if row.get(field) != baseline.get(field):
            raise ReviewError(f"external motion review candidate provenance mismatch: {field}")
    human_fields = [field for field in baseline_fields if field not in {"run_id", "video_id", "preset", "candidate"}]
    if any(str(baseline.get(field) or "").strip() for field in human_fields):
        raise ReviewError("run motion review human fields must remain blank append-only evidence")
    normalized = {
        "visual_identity_pass": row.get("visual_identity", ""),
        "face_stability_pass": row.get("face_stability", ""),
        "hair_pass": row.get("hair_stability", ""),
        "wardrobe_pass": row.get("wardrobe", ""),
        "jewelry_pass": row.get("jewelry", ""),
        "eye_motion_pass": row.get("eyes", ""),
        "background_pass": row.get("background", ""),
        "motion_quality_pass": row.get("motion", ""),
        "technical_export_pass": row.get("technical_export", ""),
        "age_stability_pass": row.get("age_stability", ""),
        "body_proportions_pass": row.get("body_proportions", ""),
        "legacy_motion_schema": "true",
        "mtl_review_ready": row.get("mtl_review_ready", ""),
        "reviewer": row.get("reviewer", ""),
        "reviewed_at": row.get("reviewed_at", ""),
    }
    return normalized, {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}


def _first_motion_request(request_evidence: Mapping[str, Any]) -> dict[str, Any]:
    for item in request_evidence.get("requests") or []:
        if isinstance(item, dict) and (item.get("image_sha256") or item.get("keyframe_sha256")):
            return item
    raise ExternalInputBlocked("motion smoke request provenance is missing")


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
    _validate_motion_plan_prompts(config, plan)
    smoke, smoke_review_evidence = _validate_passing_smoke(
        config.root, options.smoke_run_id, options.smoke_review_file
    )
    smoke_request = _first_talking_request(smoke)
    if smoke_request.get("keyframe_sha256") != keyframe.sha256:
        raise ExternalInputBlocked("passing smoke run used a different approved keyframe digest")
    if smoke_request.get("provider") != preset.talking_provider:
        raise ExternalInputBlocked("passing smoke run used a different talking provider")
    motion_smoke_review_evidence: dict[str, str] | None = None
    if providers is None:
        motion_smoke_review_evidence = _validate_passing_motion_smoke(
            config.root,
            options.motion_smoke_run_id,
            options.motion_smoke_review_file,
            keyframe_sha256=keyframe.sha256,
        )
    _validate_full_live_guards(config, plan, environment)

    if (
        providers is None
        and options.preset in {"product_page", "homepage"}
        and "talking_medium_closeup" not in keyframe.roles
    ):
        raise ExternalInputBlocked(
            f"{options.preset} live generation requires an approved talking_medium_closeup "
            "keyframe role; derive-talking-crop creates only an unapproved candidate"
        )

    budget_limits = _budget_limits(options)
    estimated_motion_credits = _estimate_motion_credits(config, plan)
    talking_requests = sum(
        len(shot.requests) for shot in plan.shots if shot.kind == "talking"
    )
    estimated_talking_usd = _estimate_talking_stage_usd(
        config,
        provider_name=preset.talking_provider,
        talking_results=talking_requests,
        duration_seconds=12.0,
        include_voice=bool(plan.voice_request_count),
    )
    if providers is None:
        if environment.get("VIDEO_FULL_PILOT_LIVE") != "true":
            raise ExternalInputBlocked(
                "full live pilot requires exact VIDEO_FULL_PILOT_LIVE=true"
            )
        if talking_requests or plan.voice_request_count:
            check_estimate(
                budget_limits,
                provider=preset.talking_provider,
                estimated_usd=estimated_talking_usd,
                operation="pilot provider construction",
            )
        if estimated_motion_credits is not None:
            check_estimate(
                budget_limits,
                provider="runway",
                estimated_usd=(
                    estimated_motion_credits
                    * float(config.providers["runway"].settings.get("credit_usd") or 0.01)
                ),
                estimated_credits=estimated_motion_credits,
                operation="pilot Runway provider construction",
            )

    selected_providers = dict(providers or {})
    real_generation_providers = providers is None
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
        if providers is None and plan.voice_request_count:
            check_estimate(
                budget_limits,
                provider=preset.talking_provider,
                estimated_usd=estimated_talking_usd,
                operation="HeyGen speech submission",
            )
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
            "motion_smoke_run_id": options.motion_smoke_run_id,
            "motion_smoke_review": motion_smoke_review_evidence,
            "provider_call_count": plan.provider_call_count,
            "concurrency": 1,
            "budget": _budget_evidence(
                budget_limits, estimated_talking_usd, estimated_motion_credits
            ),
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
                if providers is None:
                    if planned.responsibility == "motion":
                        check_estimate(
                            budget_limits,
                            provider="runway",
                            estimated_usd=(
                                estimated_motion_credits
                                * float(
                                    config.providers["runway"].settings.get("credit_usd")
                                    or 0.01
                                )
                                if estimated_motion_credits is not None
                                else None
                            ),
                            estimated_credits=estimated_motion_credits,
                            operation="Runway submission",
                        )
                    else:
                        check_estimate(
                            budget_limits,
                            provider=preset.talking_provider,
                            estimated_usd=estimated_talking_usd,
                            operation="HeyGen video submission",
                        )
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
            if real_generation_providers and execution.status is VideoTaskStatus.SUCCEEDED:
                for artifact in execution.artifacts:
                    if planned.responsibility == "talking":
                        _validate_talking_media_output(
                            artifact, preset.resolution, audio.duration_seconds
                        )

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
            "motion_smoke_run_id": options.motion_smoke_run_id,
            "motion_smoke_review": motion_smoke_review_evidence,
            "provider_call_count": plan.provider_call_count,
            "budget": _budget_evidence(
                budget_limits, estimated_talking_usd, estimated_motion_credits
            ),
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
            "budget": _budget_evidence(
                budget_limits, estimated_talking_usd, estimated_motion_credits
            ),
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
    if args.video_command == "voice":
        if args.voice_command == "verify":
            from .voice_verification import verify_owner_voice

            return 0, verify_owner_voice(
                args.project_root,
                voice_id=getattr(args, "voice_id", None),
                voice_id_env=getattr(args, "voice_id_env", None),
            )
        if args.voice_command == "download-preview":
            from .voice_verification import download_owner_voice_preview

            return 0, download_owner_voice_preview(
                args.project_root,
                voice_id=args.voice_id,
            )
        if args.voice_command == "init-env":
            from ..env import migrate_legacy_voice_env

            return 0, migrate_legacy_voice_env(args.project_root)
        raise ValueError(f"voice command is not implemented: {args.voice_command}")
    if args.video_command == "keyframe":
        if args.keyframe_command == "derive-talking-crop":
            from .keyframes import derive_talking_crop

            return 0, derive_talking_crop(args.project_root, args.source)
        raise ValueError(f"keyframe command is not implemented: {args.keyframe_command}")
    if args.video_command == "motion-v7-dry-run":
        outcome = preview_motion_v7(args.project_root, keyframe_id=args.keyframe)
        return 0, {
            "run_id": outcome.run_id,
            "run_dir": str(outcome.run_dir),
            "status": outcome.status,
            "planned_provider_calls": outcome.provider_call_count,
            "paid_calls": 0,
        }
    if args.video_command == "motion-v7-live":
        outcome = run_motion_v7_live(
            args.project_root,
            keyframe_id=args.keyframe,
            execute_live=bool(args.execute_live),
            confirm_v7_batch=bool(args.confirm_v7_batch),
            max_runway_credits=args.max_runway_credits,
        )
        return (0 if outcome.status == "SUCCEEDED" else 3), {
            "run_id": outcome.run_id,
            "run_dir": str(outcome.run_dir),
            "status": outcome.status,
            "planned_provider_calls": outcome.provider_call_count,
            "task_submission_count": outcome.submission_count,
        }
    if args.video_command == "motion-smoke-test":
        options = VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id=args.keyframe,
            live=bool(args.live),
            provider_name="runway",
            motion_model=args.model,
            motion_duration=args.duration,
            motion_ratio=args.ratio,
            motion_variations=args.variations,
            motion_prompt=args.prompt,
            max_provider_cost_usd=args.max_provider_cost_usd,
            max_runway_credits=args.max_runway_credits,
            accept_unknown_provider_cost=bool(args.accept_unknown_provider_cost),
        )
        outcome = run_motion_smoke(
            args.project_root,
            options,
        )
        return (0 if outcome.status in {"DRY_RUN_COMPLETE", "SUCCEEDED"} else 3), {
            "run_id": outcome.run_id,
            "run_dir": str(outcome.run_dir),
            "status": outcome.status,
            "planned_provider_calls": outcome.provider_call_count,
            "paid_calls": outcome.submission_count,
            "prompt_path": str(outcome.plan.shots[0].prompt.path)
            if outcome.plan.shots and outcome.plan.shots[0].prompt
            else None,
        }
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
            motion_smoke_run_id=getattr(args, "motion_smoke_run_id", None),
            motion_smoke_review_file=(
                Path(args.motion_smoke_review_file)
                if getattr(args, "motion_smoke_review_file", None)
                else None
            ),
            provider_name=getattr(args, "provider", None),
            max_provider_cost_usd=getattr(args, "max_provider_cost_usd", None),
            max_runway_credits=getattr(args, "max_runway_credits", None),
            accept_unknown_provider_cost=bool(
                getattr(args, "accept_unknown_provider_cost", False)
            ),
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
    if args.video_command == "motion-generate":
        options = VideoRunOptions(
            preset="motion",
            action="motion_generate",
            keyframe_id=args.keyframe,
            live=bool(args.live),
            motion_model=args.model,
            motion_duration=args.duration,
            motion_ratio=args.ratio,
            motion_variations=args.variations,
            max_runway_credits=args.max_runway_credits,
            motion_prompt=getattr(args, "prompt", None),
            smoke_run_id=getattr(args, "motion_smoke_run_id", None),
            smoke_review_file=(Path(args.motion_smoke_review_file) if getattr(args, "motion_smoke_review_file", None) else None),
            motion_smoke_qa_attested=bool(getattr(args, "motion_smoke_qa_attested", False)),
        )
        if args.live:
            outcome = generate_motion_variations(args.project_root, options)
        else:
            outcome = preview_motion_variations(args.project_root, options)
        return (0 if outcome.status in {"SUCCEEDED", "DRY_RUN_COMPLETE"} else 3), {
            "run_id": outcome.run_id,
            "run_dir": str(outcome.run_dir),
            "status": outcome.status,
            "planned_provider_calls": outcome.provider_call_count,
            "paid_calls": outcome.submission_count,
        }
    if args.video_command == "report":
        from .reporting import build_video_report

        return 0, build_video_report(args.project_root, args.run_id)
    if args.video_command == "subject-lock":
        from .qa.review_package import finalize_subject_lock_package

        return 0, finalize_subject_lock_package(
            args.project_root, args.run_id, Path(args.package_dir)
        )
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
            selected_path = Path(selected)
            for candidate in config.keyframes.values():
                if (
                    selected_path.as_posix() == candidate.path.as_posix()
                    or selected_path.as_posix() == (config.root / candidate.path).as_posix()
                ):
                    return candidate
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


def _validate_passing_motion_smoke(
    project_root: Path,
    run_id: str | None,
    review_file: Path | None,
    *,
    keyframe_sha256: str,
) -> dict[str, str]:
    if not run_id or "/" in run_id or "\\" in run_id:
        raise ExternalInputBlocked(
            "complete generation requires a human-reviewed motion smoke run"
        )
    run_dir = (project_root / "runs" / run_id).resolve()
    runs_root = (project_root / "runs").resolve()
    if runs_root not in run_dir.parents or not run_dir.is_dir():
        raise ExternalInputBlocked(f"motion smoke run does not exist: {run_id}")
    try:
        request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
        results = json.loads((run_dir / "provider-results.json").read_text(encoding="utf-8"))
        keyframe = json.loads((run_dir / "keyframe-hash.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalInputBlocked(f"motion smoke evidence is incomplete: {run_id}") from exc
    if request.get("action") != "motion_smoke" or results.get("status") != "SUCCEEDED":
        raise ExternalInputBlocked("motion smoke is not a successful one-result run")
    if keyframe.get("sha256") != keyframe_sha256:
        raise ExternalInputBlocked("motion smoke used a different approved keyframe digest")
    result_items = results.get("results") or []
    artifacts = result_items[0].get("artifacts") if len(result_items) == 1 else []
    if len(artifacts or []) != 1:
        raise ExternalInputBlocked("motion smoke output provenance is missing")
    artifact = artifacts[0]
    candidate = str(artifact.get("candidate") or artifact.get("artifact_id") or "")
    if not candidate or not artifact.get("provider_task_id"):
        raise ExternalInputBlocked("motion smoke task/output identity is missing")
    source_path = (project_root / str(artifact.get("path") or "")).resolve()
    outputs_root = (project_root / "outputs/broll").resolve()
    if outputs_root not in source_path.parents or not source_path.is_file():
        raise ExternalInputBlocked("motion smoke output is missing or outside broll outputs")
    if sha256_file(source_path) != artifact.get("sha256"):
        raise ExternalInputBlocked("motion smoke output hash no longer matches evidence")
    if review_file is None:
        raise ExternalInputBlocked(
            "complete generation requires --motion-smoke-review-file under outputs/reviews"
        )
    try:
        row, review_evidence = load_external_review_row(
            project_root, run_dir, candidate, review_file, require_ready=False
        )
    except ReviewError as exc:
        raise ExternalInputBlocked(str(exc)) from exc
    required_passes = QA_FIELDS[4:18]
    if any(not _truthy(row.get(field)) for field in required_passes):
        raise ExternalInputBlocked("motion smoke review has incomplete or failing QA decisions")
    if not str(row.get("reviewer") or "").strip():
        raise ExternalInputBlocked("motion smoke reviewer is required")
    try:
        reviewed_at = datetime.fromisoformat(
            str(row.get("reviewed_at") or "").replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ExternalInputBlocked("motion smoke reviewed_at is invalid") from exc
    if reviewed_at.tzinfo is None:
        raise ExternalInputBlocked("motion smoke reviewed_at must include a timezone")
    return review_evidence


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
        "source_url_redacted": artifact.source_url_redacted,
        "container": artifact.container,
        "video_codec": artifact.video_codec,
        "pixel_format": artifact.pixel_format,
        "average_frame_rate": artifact.average_frame_rate,
        "audio_stream_present": artifact.audio_stream_present,
        "audio_codec": artifact.audio_codec,
        "sample_rate": artifact.sample_rate,
        "channel_count": artifact.channel_count,
        "bit_rate": artifact.bit_rate,
        "provenance": artifact.provenance,
    }


def _validate_talking_media_output(
    artifact: Any, resolution: str, expected_duration: float
) -> None:
    try:
        width, height = (int(value) for value in resolution.split(":", 1))
    except (TypeError, ValueError) as exc:
        raise VideoConfigError("talking output resolution is invalid") from exc
    if artifact.width != width or artifact.height != height:
        raise ExternalInputBlocked("talking output resolution does not match the requested format")
    if not artifact.audio_stream_present:
        raise ExternalInputBlocked("talking output has no audio stream")
    if artifact.duration_seconds is None or abs(artifact.duration_seconds - expected_duration) > 0.75:
        raise ExternalInputBlocked("talking output duration does not match the approved audio")


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
        component["estimated_credits"] = sum(
            record.estimated_credits or 0 for record in matching
        ) if any(record.estimated_credits is not None for record in matching) else None
        component["actual_credits"] = sum(
            record.actual_credits or 0 for record in matching
        ) if any(record.actual_credits is not None for record in matching) else None


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "yes", "1", "approved", "pass"}
