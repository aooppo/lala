from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .config import VideoProjectConfig
from .validation import ExternalInputBlocked


@dataclass(frozen=True, slots=True)
class BudgetLimits:
    max_provider_cost_usd: float | None = None
    max_runway_credits: float | None = None
    accept_unknown_provider_cost: bool = False

    def validate(self) -> None:
        if self.max_provider_cost_usd is not None and self.max_provider_cost_usd < 0:
            raise ExternalInputBlocked("max provider cost must be non-negative")
        if self.max_runway_credits is not None and self.max_runway_credits < 0:
            raise ExternalInputBlocked("max Runway credits must be non-negative")


def require_explicit_budget(limits: BudgetLimits, *, provider: str) -> None:
    limits.validate()
    if provider == "runway":
        if limits.max_runway_credits is None:
            raise ExternalInputBlocked(
                "live Runway work requires an explicit --max-runway-credits budget"
            )
    elif limits.max_provider_cost_usd is None:
        raise ExternalInputBlocked(
            "live provider work requires an explicit --max-provider-cost-usd budget"
        )


def check_estimate(
    limits: BudgetLimits,
    *,
    provider: str,
    estimated_usd: float | None,
    estimated_credits: float | None = None,
    operation: str,
) -> None:
    require_explicit_budget(limits, provider=provider)
    if provider == "runway":
        if estimated_credits is None:
            if not limits.accept_unknown_provider_cost:
                raise ExternalInputBlocked(
                    f"{operation} has unknown Runway credits; pass --accept-unknown-provider-cost "
                    "to allow one unknown-cost call"
                )
        elif estimated_credits > float(limits.max_runway_credits):
            raise ExternalInputBlocked(
                f"{operation} estimated Runway credits {estimated_credits:g} exceed "
                f"the {limits.max_runway_credits:g} credit cap"
            )
        return
    if estimated_usd is None:
        if not limits.accept_unknown_provider_cost:
            raise ExternalInputBlocked(
                f"{operation} has unknown provider cost; pass --accept-unknown-provider-cost "
                "to allow one unknown-cost call"
            )
    elif estimated_usd > float(limits.max_provider_cost_usd):
        raise ExternalInputBlocked(
            f"{operation} estimated cost ${estimated_usd:.6f} exceeds "
            f"the ${limits.max_provider_cost_usd:.6f} USD cap"
        )


def check_actual(
    limits: BudgetLimits,
    *,
    provider: str,
    actual_usd: float | None,
    actual_credits: float | None = None,
    operation: str,
) -> None:
    if provider == "runway":
        if actual_credits is not None and limits.max_runway_credits is not None:
            if actual_credits > limits.max_runway_credits:
                raise ExternalInputBlocked(
                    f"{operation} actual Runway credits {actual_credits:g} exceed "
                    f"the {limits.max_runway_credits:g} credit cap"
                )
        return
    if actual_usd is not None and limits.max_provider_cost_usd is not None:
        if actual_usd > limits.max_provider_cost_usd:
            raise ExternalInputBlocked(
                f"{operation} actual provider cost ${actual_usd:.6f} exceeds "
                f"the ${limits.max_provider_cost_usd:.6f} USD cap"
            )


def cost_for_plan(config: VideoProjectConfig, cost: Mapping[str, Any], provider: str) -> tuple[float | None, float | None]:
    """Return known USD/credits for a plan, preserving unknown values as None."""

    if provider == "runway":
        amount = cost.get("motion_video_cost")
        if amount is None:
            return None, None
        credit_usd = float(config.providers["runway"].settings.get("credit_usd") or 0.01)
        return float(amount), float(amount) / credit_usd if credit_usd else None
    amount = cost.get("total_provider_cost")
    return (float(amount), None) if amount is not None else (None, None)
