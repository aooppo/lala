from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .config import VideoConfigError, load_video_config
from .domain import ResolvedPrompt
from .prompts import VideoPromptError, load_video_prompt, utf16_code_units


V7_CANDIDATE_IDS = (
    "v7-a-stability-first",
    "v7-b-natural-micro-motion",
    "v7-c-controlled-upper-bound",
)


class MotionV7Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MotionV7Candidate:
    candidate_id: str
    prompt_file: Path
    experiment_level: str
    motion_intent: str
    provider: str
    model: str
    duration_seconds: int
    ratio: str
    live_allowed: bool
    prompt: ResolvedPrompt
    prompt_utf16_units: int

    def evidence(self, estimated_credits: float | None) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "prompt_file": self.prompt_file.as_posix(),
            "prompt_sha256": self.prompt.sha256,
            "prompt_utf16_units": self.prompt_utf16_units,
            "experiment_level": self.experiment_level,
            "motion_intent": self.motion_intent,
            "provider": self.provider,
            "model": self.model,
            "duration_seconds": self.duration_seconds,
            "ratio": self.ratio,
            "estimated_credits": estimated_credits,
            "live_allowed": self.live_allowed,
            "live_submission": False,
            "provider_task_id": None,
        }


def load_v7_candidates(project_root: Path) -> tuple[MotionV7Candidate, ...]:
    root = project_root.resolve()
    manifest_path = root / "configs/motion-v7.yaml"
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise MotionV7Error("V7 candidate manifest is unreadable") from exc
    if not isinstance(raw, Mapping) or raw.get("version") != "1.0":
        raise MotionV7Error("V7 candidate manifest must declare version 1.0")
    items = raw.get("candidates")
    if not isinstance(items, list) or len(items) != len(V7_CANDIDATE_IDS):
        raise MotionV7Error("V7 requires exactly three candidates")

    config = load_video_config(root, require_inputs=False)
    candidates = tuple(_parse_candidate(root, config.providers, item) for item in items)
    if tuple(item.candidate_id for item in candidates) != V7_CANDIDATE_IDS:
        raise MotionV7Error("V7 candidates must use the canonical A/B/C order")
    return candidates


def build_v7_comparison() -> dict[str, Any]:
    """Return fixed V6 evidence and explicit no-video V7 placeholders.

    This is diagnostic evidence only and deliberately contains no human QA value.
    """

    return {
        "measurement_scope": "color_region_proxy",
        "human_qa_authority": "not_automatic",
        "diagnostic_evidence_only": True,
        "v6": {
            "x_drift_px": -14.0,
            "y_drift_px": 10.0,
            "width_change_pct": -8.641975,
            "height_change_pct": -3.496503,
            "max_scale_change_pct": 13.580247,
            "tracking_success_rate_pct": 100.0,
            "diagnostic_status": "OUTSIDE_THRESHOLD",
        },
        "v7": {"status": "PENDING", "metrics": None},
        "delta": {"status": "PENDING", "metrics": None},
    }


def candidate_credit_estimate(
    candidate: MotionV7Candidate, providers: Mapping[str, Any]
) -> float | None:
    definition = providers.get(candidate.provider)
    settings = getattr(definition, "settings", None)
    models = settings.get("supported_models") if isinstance(settings, Mapping) else None
    capability = models.get(candidate.model) if isinstance(models, Mapping) else None
    if not isinstance(capability, Mapping) or capability.get("credits_per_second") is None:
        return None
    return float(capability["credits_per_second"]) * candidate.duration_seconds


def _parse_candidate(
    root: Path, providers: Mapping[str, Any], raw: Any
) -> MotionV7Candidate:
    if not isinstance(raw, Mapping):
        raise MotionV7Error("each V7 candidate must be a mapping")
    candidate_id = _required(raw, "candidate_id")
    prompt_file = Path(_required(raw, "prompt_file"))
    experiment_level = _required(raw, "experiment_level")
    motion_intent = _required(raw, "motion_intent")
    provider = _required(raw, "provider")
    model = _required(raw, "model")
    ratio = _required(raw, "ratio")
    live_allowed = raw.get("live_allowed")
    if live_allowed is not False:
        raise MotionV7Error("every V7 candidate must set live_allowed=false")
    try:
        duration = int(raw.get("duration_seconds"))
    except (TypeError, ValueError) as exc:
        raise MotionV7Error(f"V7 candidate {candidate_id} duration_seconds is invalid") from exc
    if provider != "runway":
        raise MotionV7Error(f"V7 candidate {candidate_id} provider must be runway")
    try:
        prompt = load_video_prompt(root, prompt_file)
    except VideoPromptError as exc:
        raise MotionV7Error(f"V7 candidate {candidate_id} prompt is invalid: {exc}") from exc
    units = utf16_code_units(prompt.text)
    definition = providers.get(provider)
    settings = getattr(definition, "settings", None)
    models = settings.get("supported_models") if isinstance(settings, Mapping) else None
    capability = models.get(model) if isinstance(models, Mapping) else None
    if not isinstance(capability, Mapping):
        raise MotionV7Error(f"V7 candidate {candidate_id} model is not configured")
    prompt_limit = int(capability.get("prompt_utf16_max") or 1000)
    if units >= prompt_limit:
        raise MotionV7Error(
            f"V7 candidate {candidate_id} prompt exceeds the UTF-16 safety limit "
            f"({units} >= {prompt_limit})"
        )
    if duration not in {int(value) for value in capability.get("durations", ())}:
        raise MotionV7Error(f"V7 candidate {candidate_id} duration is unsupported")
    if ratio not in {str(value) for value in capability.get("ratios", ())}:
        raise MotionV7Error(f"V7 candidate {candidate_id} ratio is unsupported")
    return MotionV7Candidate(
        candidate_id=candidate_id,
        prompt_file=prompt_file,
        experiment_level=experiment_level,
        motion_intent=motion_intent,
        provider=provider,
        model=model,
        duration_seconds=duration,
        ratio=ratio,
        live_allowed=False,
        prompt=prompt,
        prompt_utf16_units=units,
    )


def _required(raw: Mapping[str, Any], field: str) -> str:
    value = str(raw.get(field) or "").strip()
    if not value:
        raise MotionV7Error(f"V7 candidate {field} is required")
    return value
