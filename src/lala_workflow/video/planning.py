from __future__ import annotations

from .config import VideoConfigError
from .domain import PlannedRequest, PlannedShot, ShotPlan, VideoProjectConfig
from .prompts import load_video_prompt


class PlanningError(ValueError):
    pass


def build_shot_plan(
    config: VideoProjectConfig,
    preset_name: str,
    *,
    mode: str = "generate",
    single_shot: bool = False,
    talking_variations: int | None = None,
    motion_variations: int | None = None,
    first_live_smoke: bool = False,
) -> ShotPlan:
    if preset_name not in config.presets:
        raise PlanningError(f"unknown video preset: {preset_name}")
    if mode not in {"generate", "talking_smoke"}:
        raise PlanningError(f"unsupported planning mode: {mode}")
    preset = config.presets[preset_name]
    talking_count = _variation(
        talking_variations,
        preset.talking_shot_variations,
        config.limits.max_talking_variations_per_shot,
        "talking variations",
    )
    motion_count = _variation(
        motion_variations,
        preset.broll_variations,
        config.limits.max_motion_variations_per_shot,
        "motion variations",
    )
    templates = list(preset.shots)
    if mode == "talking_smoke" or single_shot:
        if single_shot and not preset.single_shot_fallback:
            raise PlanningError(f"preset {preset_name} does not allow single-shot fallback")
        templates = [next(shot for shot in templates if shot.kind == "talking")]
    if first_live_smoke:
        if mode != "talking_smoke":
            raise PlanningError("first_live_smoke is valid only for a talking smoke plan")
        talking_count = 1

    planned: list[PlannedShot] = []
    for template in templates:
        prompt = (
            load_video_prompt(config.root, template.prompt_file)
            if template.prompt_file is not None
            else None
        )
        if template.kind == "talking":
            count = talking_count
            responsibility = "talking"
            provider = preset.talking_provider
            model = preset.talking_model
        elif template.kind == "motion":
            count = motion_count
            responsibility = "motion"
            provider = preset.motion_provider
            model = preset.motion_model
        else:
            count = 1
            responsibility = "local"
            provider = "local"
            model = "deterministic"
        requests = tuple(
            PlannedRequest(
                request_id=f"{preset_name}-{template.shot_id}-v{variation:03d}",
                shot_id=template.shot_id,
                variation=variation,
                responsibility=responsibility,
                provider=provider,
                model=model,
                duration_seconds=template.duration_seconds,
            )
            for variation in range(1, count + 1)
            if responsibility != "local"
        )
        planned.append(
            PlannedShot(
                shot_id=template.shot_id,
                kind=template.kind,
                source_role=template.source_role,
                prompt=prompt,
                duration_seconds=template.duration_seconds,
                variation_count=count,
                selection_required=len(requests) > 1,
                requests=requests,
                optional=template.optional,
            )
        )
    return ShotPlan(
        preset=preset_name,
        mode=mode,
        script_id=preset.script_id,
        aspect_ratio=preset.aspect_ratio,
        resolution=preset.resolution,
        frame_rate=preset.frame_rate,
        shots=tuple(planned),
        final_edit_variations=preset.final_edit_variations,
        voice_request_count=(
            1
            if config.voice_profile.mode == "cloned_voice"
            and preset.script_id not in config.voice_profile.script_audio
            else 0
        ),
    )


def _variation(value: int | None, default: int, maximum: int, name: str) -> int:
    selected = default if value is None else value
    if isinstance(selected, bool) or not 1 <= selected <= maximum:
        raise PlanningError(f"{name} must be within 1..{maximum}")
    return selected
