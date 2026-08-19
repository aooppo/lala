from __future__ import annotations

from collections import defaultdict
from typing import Any

from .domain import CostComponent, ShotPlan, VideoProjectConfig


def estimate_plan_cost(
    plan: ShotPlan,
    config: VideoProjectConfig,
    *,
    talking_duration_seconds: float | None,
) -> dict[str, Any]:
    buckets: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "seconds": 0.0,
            "duration_known": True,
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
        bucket["duration_known"] = False
        bucket["outputs"] = 1
        unknown = True
    for shot in plan.shots:
        for request in shot.requests:
            key = (request.responsibility, request.provider, request.model)
            bucket = buckets[key]
            if request.responsibility == "talking" and talking_duration_seconds is None:
                bucket["duration_known"] = False
                seconds = 0.0
            else:
                seconds = (
                    float(talking_duration_seconds or 0)
                    if request.responsibility == "talking"
                    else float(request.duration_seconds or 0)
                )
                bucket["seconds"] += seconds
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
    for (category, provider, model), bucket in sorted(buckets.items()):
        price = bucket["price"]
        amount = (
            round(float(bucket["seconds"]) * float(price), 6)
            if price is not None and bucket["duration_known"]
            else None
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
                    "basis": "estimated",
                    "currency": config.currency,
                    "pricing_source": bucket["source"],
                    "pricing_date": bucket["date"],
                }
            )
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
                "currency": component.currency,
                "pricing_source": component.pricing_source,
                "pricing_date": component.pricing_date,
            }
        )
        category_totals[category] = round((category_totals[category] or 0) + amount, 6)
    total = (
        None
        if unknown
        else round(sum(float(item["amount"]) for item in components if item["amount"] is not None), 6)
    )
    return {
        "voice_cost": category_totals["voice"],
        "talking_video_cost": category_totals["talking"],
        "motion_video_cost": category_totals["motion"],
        "editing_cost": 0,
        "storage_cost": None,
        "total_provider_cost": total,
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
