from __future__ import annotations

from collections import defaultdict
from typing import Any

from .domain import CostComponent, ShotPlan, VideoProjectConfig


def estimate_plan_cost(
    plan: ShotPlan,
    config: VideoProjectConfig,
    *,
    talking_duration_seconds: float | None,
    talking_duration_limit_seconds: float | None = None,
) -> dict[str, Any]:
    """Estimate provider cost without treating a future TTS duration as known.

    ``talking_duration_limit_seconds`` is a workflow continuation gate, not a
    provider-enforced TTS limit.  It supports an auditable projection for dry-run and
    provider construction; exact duration-based estimates are emitted only after a WAV
    duration is available in ``talking_duration_seconds``.
    """

    buckets: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "seconds": 0.0,
            "duration_limit_seconds": 0.0,
            "duration_known": True,
            "duration_basis": "planned_request_duration",
            "outputs": 0,
            "price": None,
            "source": None,
            "date": None,
        }
    )
    unknown = False
    if plan.voice_request_count:
        profile = config.voice_profile
        key = ("voice", str(profile.provider or "unknown"), str(profile.model or "unknown"))
        bucket = buckets[key]
        bucket["outputs"] = 1
        if talking_duration_seconds is not None:
            bucket["seconds"] = float(talking_duration_seconds)
            bucket["duration_basis"] = "actual_audio_duration"
        else:
            bucket["duration_known"] = False
            bucket["duration_basis"] = "tts_output_duration"
            if talking_duration_limit_seconds is not None:
                bucket["duration_limit_seconds"] = float(
                    talking_duration_limit_seconds
                )
        price, source, date = _unit_price(
            config, str(profile.provider or "unknown"), str(profile.model or "unknown")
        )
        bucket["price"] = price
        bucket["source"] = source
        bucket["date"] = date
        if price is None or not bucket["duration_known"]:
            unknown = True
    for shot in plan.shots:
        for request in shot.requests:
            key = (request.responsibility, request.provider, request.model)
            bucket = buckets[key]
            if request.responsibility == "talking" and talking_duration_seconds is None:
                bucket["duration_known"] = False
                bucket["duration_basis"] = "tts_output_duration"
                if talking_duration_limit_seconds is not None:
                    bucket["duration_limit_seconds"] += float(
                        talking_duration_limit_seconds
                    )
                seconds = 0.0
            else:
                seconds = (
                    float(talking_duration_seconds or 0)
                    if request.responsibility == "talking"
                    else float(request.duration_seconds or 0)
                )
                bucket["seconds"] += seconds
                if request.responsibility == "talking":
                    bucket["duration_basis"] = "actual_audio_duration"
            bucket["outputs"] += 1
            price, source, date = _unit_price(config, request.provider, request.model)
            bucket["price"] = price
            bucket["source"] = source
            bucket["date"] = date
            if price is None or not bucket["duration_known"]:
                unknown = True

    components: list[dict[str, Any]] = []
    category_totals: dict[str, float | None] = {
        "voice": None,
        "talking": None,
        "motion": None,
    }
    category_duration_limit_projections: dict[str, float | None] = {
        "voice": None,
        "talking": None,
        "motion": None,
    }
    known_provider_cost = 0.0
    projected_total = 0.0
    projection_complete = True
    for (category, provider, model), bucket in sorted(buckets.items()):
        price = bucket["price"]
        amount = (
            round(float(bucket["seconds"]) * float(price), 6)
            if price is not None and bucket["duration_known"]
            else None
        )
        duration_limit_projection = (
            round(float(bucket["duration_limit_seconds"]) * float(price), 6)
            if amount is None
            and price is not None
            and float(bucket["duration_limit_seconds"]) > 0
            else amount
        )
        if amount is None:
            components.append(
                {
                    "category": category,
                    "provider": provider,
                    "model": model,
                    "generated_seconds": (
                        round(float(bucket["seconds"]), 6)
                        if bucket["duration_known"]
                        else None
                    ),
                    "attempts": 0,
                    "successful_outputs": 0,
                    "failed_outputs": 0,
                    "amount": None,
                    "duration_limit_projection_amount": duration_limit_projection,
                    "basis": (
                        "workflow_duration_projection"
                        if duration_limit_projection is not None
                        else "duration_dependent"
                    ),
                    "duration_basis": bucket["duration_basis"],
                    "duration_dependency": "tts_output_duration",
                    "duration_limit_seconds": (
                        round(float(bucket["duration_limit_seconds"]), 6)
                        if float(bucket["duration_limit_seconds"]) > 0
                        else None
                    ),
                    "unit_rate_usd_per_output_second": price,
                    "currency": config.currency,
                    "pricing_source": bucket["source"],
                    "pricing_date": bucket["date"],
                }
            )
            if duration_limit_projection is None:
                projection_complete = False
            else:
                category_duration_limit_projections[category] = round(
                    (category_duration_limit_projections[category] or 0)
                    + duration_limit_projection,
                    6,
                )
                projected_total += duration_limit_projection
            continue
        component = CostComponent(
            category=category,
            provider=provider,
            model=model,
            generated_seconds=round(float(bucket["seconds"]), 6),
            attempts=0,
            successful_outputs=0,
            failed_outputs=0,
            amount=amount,
            basis="estimated",
            currency=config.currency,
            pricing_source=str(bucket["source"]),
            pricing_date=str(bucket["date"]),
        )
        components.append(
            {
                "category": component.category,
                "provider": component.provider,
                "model": component.model,
                "generated_seconds": component.generated_seconds,
                "attempts": component.attempts,
                "successful_outputs": component.successful_outputs,
                "failed_outputs": component.failed_outputs,
                "amount": component.amount,
                "basis": component.basis,
                "duration_limit_projection_amount": component.amount,
                "duration_basis": bucket["duration_basis"],
                "duration_dependency": None,
                "duration_limit_seconds": component.generated_seconds,
                "unit_rate_usd_per_output_second": price,
                "currency": component.currency,
                "pricing_source": component.pricing_source,
                "pricing_date": component.pricing_date,
            }
        )
        category_totals[category] = round((category_totals[category] or 0) + amount, 6)
        category_duration_limit_projections[category] = round(
            (category_duration_limit_projections[category] or 0) + amount, 6
        )
        known_provider_cost += amount
        projected_total += amount
    total = (
        None
        if unknown
        else round(sum(float(item["amount"]) for item in components if item["amount"] is not None), 6)
    )
    return {
        "voice_cost": category_totals["voice"],
        "talking_video_cost": category_totals["talking"],
        "motion_video_cost": category_totals["motion"],
        "voice_cost_at_duration_limit": category_duration_limit_projections["voice"],
        "talking_video_cost_at_duration_limit": category_duration_limit_projections[
            "talking"
        ],
        "motion_video_cost_at_duration_limit": category_duration_limit_projections[
            "motion"
        ],
        "editing_cost": 0,
        "storage_cost": None,
        "total_provider_cost": total,
        "known_provider_cost": round(known_provider_cost, 6),
        "projected_total_at_duration_limit": (
            round(projected_total, 6) if projection_complete else None
        ),
        "budget_state": (
            "TOTAL_ESTIMATE_KNOWN"
            if total is not None
            else (
                "TOTAL_EXACT_UNKNOWN_UNTIL_TTS"
                if projection_complete
                and talking_duration_limit_seconds is not None
                else "TALKING_DURATION_REQUIRED"
            )
        ),
        "talking_duration_seconds": talking_duration_seconds,
        "talking_duration_limit_seconds": talking_duration_limit_seconds,
        "tts_duration_provider_enforced": (
            False if plan.voice_request_count and talking_duration_seconds is None else None
        ),
        "duration_gate_stage": (
            "post_tts_before_talking_or_motion_submission"
            if plan.voice_request_count
            else None
        ),
        "currency": config.currency,
        "components": components,
    }


def _unit_price(
    config: VideoProjectConfig, provider_name: str, model: str
) -> tuple[float | None, str | None, str | None]:
    provider = config.providers.get(provider_name)
    if provider is None:
        return None, None, None
    settings = provider.settings
    if provider_name == "heygen":
        pricing = settings.get("pricing", {})
        record = pricing.get(model) if isinstance(pricing, dict) else None
        if isinstance(record, dict) and record.get("usd_per_unit") is not None:
            return (
                float(record["usd_per_unit"]),
                str(record.get("source") or ""),
                str(record.get("verified_on") or config.verified_on),
            )
    if provider_name == "heygen_voice":
        pricing = settings.get("pricing", {})
        if isinstance(pricing, dict) and pricing.get("usd_per_unit") is not None:
            return (
                float(pricing["usd_per_unit"]),
                str(pricing.get("source") or ""),
                str(pricing.get("verified_on") or config.verified_on),
            )
    if provider_name == "runway":
        models = settings.get("supported_models", {})
        record = models.get(model) if isinstance(models, dict) else None
        if isinstance(record, dict) and record.get("credits_per_second") is not None:
            return (
                float(record["credits_per_second"]) * float(settings.get("credit_usd", 0)),
                str(settings.get("pricing_source") or ""),
                str(settings.get("pricing_verified_on") or config.verified_on),
            )
    return None, None, None
