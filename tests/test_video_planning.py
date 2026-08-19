from __future__ import annotations

from pathlib import Path

import pytest

from lala_workflow.video.config import load_video_config
from lala_workflow.video.planning import PlanningError, build_shot_plan


@pytest.mark.parametrize(
    ("preset", "shots", "calls"),
    [
        ("product_page", 4, 9),
        ("tooltip", 2, 3),
        ("homepage", 5, 12),
    ],
)
def test_default_plans_are_deterministic_and_bounded(
    video_project_root: Path, preset: str, shots: int, calls: int
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    first = build_shot_plan(config, preset)
    second = build_shot_plan(config, preset)
    assert first == second
    assert len(first.shots) == shots
    assert first.provider_call_count == calls
    assert max(shot.variation_count for shot in first.shots) <= 3
    assert first.final_edit_variations == 2


def test_single_shot_fallback_has_only_talking_requests(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    plan = build_shot_plan(config, "homepage", single_shot=True)
    assert len(plan.shots) == 1
    assert plan.shots[0].kind == "talking"
    assert plan.provider_call_count == 3


def test_talking_smoke_dry_run_supports_three_but_live_first_is_one(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    preview = build_shot_plan(config, "tooltip", mode="talking_smoke")
    live = build_shot_plan(config, "tooltip", mode="talking_smoke", first_live_smoke=True)
    assert preview.provider_call_count == 3
    assert live.provider_call_count == 1


def test_variation_override_cannot_exceed_bound(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    with pytest.raises(PlanningError, match="talking variations"):
        build_shot_plan(config, "tooltip", talking_variations=4)
