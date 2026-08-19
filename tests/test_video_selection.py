from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from lala_workflow.video.runner import VideoRunOptions, generate_video
from lala_workflow.video.selection import SelectionError, load_shot_selection
from tests.fakes_video import FakeMotionProvider, FakeTalkingProvider
from tests.test_video_generate import approved_smoke_review, approved_smoke_run


def generated_source_run(root: Path, video: Path, preset: str = "product_page"):
    smoke = approved_smoke_run(root, video)
    return generate_video(
        root,
        VideoRunOptions(
            preset=preset,
            action="generate",
            live=True,
            smoke_run_id=smoke,
            smoke_review_file=approved_smoke_review(root, smoke),
        ),
        providers={"heygen": FakeTalkingProvider(video), "runway": FakeMotionProvider(video)},
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "HEYGEN_API_KEY": "test-key",
            "RUNWAYML_API_SECRET": "test-secret",
        },
    )


def write_selection(root: Path, outcome, *, mutate=None) -> Path:
    plan = json.loads((outcome.run_dir / "shot-plan.json").read_text(encoding="utf-8"))
    results = json.loads((outcome.run_dir / "provider-results.json").read_text(encoding="utf-8"))
    by_request = {item["request_id"]: item for item in results["results"]}
    selections = {}
    for shot in plan["shots"]:
        requests = shot["requests"]
        if requests:
            first = by_request[requests[0]["request_id"]]
            selections[shot["shot_id"]] = first["artifacts"][0]["artifact_id"]
    payload = {
        "source_run_id": outcome.run_id,
        "reviewer": "Synthetic shot reviewer",
        "selected_at": "2026-08-19T13:00:00+08:00",
        "selections": selections,
    }
    if mutate:
        mutate(payload)
    path = root / "selection.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_selection_resolves_one_existing_artifact_per_provider_shot(
    video_project_root: Path, synthetic_video: Path
) -> None:
    outcome = generated_source_run(video_project_root, synthetic_video)
    selection = load_shot_selection(
        video_project_root, outcome.run_id, write_selection(video_project_root, outcome)
    )
    assert set(selection.selections) == {
        "talking_performance",
        "product_interaction",
        "reward_visual",
    }
    assert all(item.path.is_file() for item in selection.selections.values())


@pytest.mark.parametrize("case", ["missing", "duplicate", "cross_run", "unknown"])
def test_selection_rejects_missing_duplicate_cross_run_or_unknown_artifacts(
    video_project_root: Path, synthetic_video: Path, case: str
) -> None:
    outcome = generated_source_run(video_project_root, synthetic_video)

    def mutate(payload):
        keys = list(payload["selections"])
        if case == "missing":
            payload["selections"].pop(keys[0])
        elif case == "duplicate":
            payload["selections"][keys[1]] = payload["selections"][keys[0]]
        elif case == "cross_run":
            payload["source_run_id"] = "LALA-VIDEO-OTHER"
        else:
            payload["selections"][keys[0]] = "not-an-artifact"

    path = write_selection(video_project_root, outcome, mutate=mutate)
    with pytest.raises(SelectionError):
        load_shot_selection(video_project_root, outcome.run_id, path)
