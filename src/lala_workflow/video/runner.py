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
)
from .execution import (
    ExecutionRecord,
    execute_provider_request,
    validate_live_provider_guard,
    validate_live_smoke_guards,
)
from .planning import build_shot_plan
from .prompts import load_video_prompt
from .reporting import blank_review_rows, read_video_summary, summary_markdown
from .review import ReviewError, load_external_review_row
from .storage import QA_FIELDS, VideoRunContext, VideoRunStorage
from .validation import ExternalInputBlocked
from .downloads import generate_video_evidence
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
    motion_smoke_run_id: str | None = None
    motion_smoke_review_file: Path | None = None
    provider_name: str | None = None
    max_provider_cost_usd: float | None = None
    max_runway_credits: float | None = None
    accept_unknown_provider_cost: bool = False


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
    prompt = load_video_prompt(config.root, Path("prompts/home-broll-v1.txt"))
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
    if args.video_command == "motion-smoke-test":
        options = VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            motion_variations=args.variations,
            keyframe_id=args.keyframe,
            live=bool(args.live),
            provider_name="runway",
            max_provider_cost_usd=args.max_provider_cost_usd,
            max_runway_credits=args.max_runway_credits,
            accept_unknown_provider_cost=bool(args.accept_unknown_provider_cost),
        )
        outcome = run_motion_smoke(
            args.project_root,
            options,
            model=args.model,
            duration_seconds=args.duration,
            ratio=args.ratio,
        )
        return (0 if outcome.status in {"DRY_RUN_COMPLETE", "SUCCEEDED"} else 3), {
            "run_id": outcome.run_id,
            "run_dir": str(outcome.run_dir),
            "status": outcome.status,
            "planned_provider_calls": outcome.provider_call_count,
            "paid_calls": outcome.submission_count,
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
