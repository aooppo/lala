from __future__ import annotations

import csv
import hashlib
import json

import pytest

from lala_workflow.video.motion_v7 import MotionV7Error, build_v7_comparison, load_v7_candidates
from lala_workflow.video.runner import preview_motion_v7
from lala_workflow.video.storage import QA_FIELDS, VIDEO_RUN_FILES
from lala_workflow.cli import build_parser


def test_v7_candidates_are_ordered_versioned_and_live_disabled(video_project_root) -> None:
    candidates = load_v7_candidates(video_project_root)

    assert [candidate.candidate_id for candidate in candidates] == [
        "v7-a-stability-first",
        "v7-b-natural-micro-motion",
        "v7-c-controlled-upper-bound",
    ]
    assert [candidate.prompt_file.name for candidate in candidates] == [
        "p1-1-motion-v7-a-v1.txt",
        "p1-1-motion-v7-b-v1.txt",
        "p1-1-motion-v7-c-v1.txt",
    ]
    assert all(candidate.provider == "runway" for candidate in candidates)
    assert all(candidate.live_allowed is False for candidate in candidates)
    assert all(candidate.prompt_utf16_units < 1000 for candidate in candidates)
    assert all(candidate.prompt_utf16_units > 0 for candidate in candidates)


def test_v7_rejects_live_enabled_candidate_configuration(video_project_root) -> None:
    path = video_project_root / "configs/motion-v7.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("live_allowed: false", "live_allowed: true", 1), encoding="utf-8")

    with pytest.raises(MotionV7Error, match="live_allowed=false"):
        load_v7_candidates(video_project_root)


def test_v7_comparison_keeps_v6_and_marks_v7_pending() -> None:
    comparison = build_v7_comparison()

    assert comparison["measurement_scope"] == "color_region_proxy"
    assert comparison["human_qa_authority"] == "not_automatic"
    assert comparison["v6"] == {
        "x_drift_px": -14.0,
        "y_drift_px": 10.0,
        "width_change_pct": -8.641975,
        "height_change_pct": -3.496503,
        "max_scale_change_pct": 13.580247,
        "tracking_success_rate_pct": 100.0,
        "diagnostic_status": "OUTSIDE_THRESHOLD",
    }
    assert comparison["v7"] == {"status": "PENDING", "metrics": None}
    assert comparison["delta"] == {"status": "PENDING", "metrics": None}


def test_v7_dry_run_writes_three_candidates_and_blank_human_qa(video_project_root) -> None:
    legacy_v2 = video_project_root / "prompts/home-broll-v2.txt"
    legacy_v3 = video_project_root / "prompts/home-broll-v3.txt"
    legacy_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (legacy_v2, legacy_v3)
    }

    outcome = preview_motion_v7(video_project_root, keyframe_id="hero")

    assert outcome.status == "DRY_RUN_COMPLETE"
    assert outcome.provider_call_count == 3
    assert outcome.submission_count == 0
    assert {path.name for path in outcome.run_dir.iterdir()} == set(VIDEO_RUN_FILES)
    assert legacy_hashes == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (legacy_v2, legacy_v3)
    }

    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    results = json.loads((outcome.run_dir / "provider-results.json").read_text(encoding="utf-8"))
    cost = json.loads((outcome.run_dir / "cost.json").read_text(encoding="utf-8"))
    assert request["action"] == "motion_v7_dry_run"
    assert request["mode"] == "DRY_RUN"
    assert request["provider_call_count"] == 3
    assert request["submission_count"] == 0
    assert [item["candidate_id"] for item in request["candidate_metadata"]] == [
        "v7-a-stability-first",
        "v7-b-natural-micro-motion",
        "v7-c-controlled-upper-bound",
    ]
    assert all(item["live_allowed"] is False for item in request["candidate_metadata"])
    assert all(item["live_submission"] is False for item in request["candidate_metadata"])
    assert all(item["provider_task_id"] is None for item in request["candidate_metadata"])
    assert all(item["estimated_credits"] == 25 for item in request["candidate_metadata"])
    assert request["subject_lock_comparison"]["v7"]["status"] == "PENDING"
    assert request["subject_lock_comparison"]["delta"]["status"] == "PENDING"
    assert results == {
        "provider": "runway",
        "results": [],
        "status": "DRY_RUN",
        "submission_count": 0,
    }
    assert cost["estimated_runway_credits"] == 75
    assert cost["actual_runway_credits"] is None

    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 3
    assert all(row["candidate"] for row in rows)
    assert all(all(row[field] == "" for field in QA_FIELDS[4:]) for row in rows)


def test_v7_invalid_prompt_fails_before_run_creation(video_project_root) -> None:
    prompt = video_project_root / "prompts/p1-1-motion-v7-b-v1.txt"
    prompt.write_text("x" * 1000, encoding="utf-8")

    before = {path.name for path in (video_project_root / "runs").iterdir()}
    with pytest.raises(MotionV7Error, match="UTF-16"):
        preview_motion_v7(video_project_root, keyframe_id="hero")
    after = {path.name for path in (video_project_root / "runs").iterdir()}
    assert after == before


def test_v7_cli_has_no_live_option() -> None:
    parser = build_parser()
    parsed = parser.parse_args(["video", "motion-v7-dry-run", "--keyframe", "hero"])
    assert parsed.video_command == "motion-v7-dry-run"
    with pytest.raises(SystemExit):
        parser.parse_args(["video", "motion-v7-dry-run", "--keyframe", "hero", "--live"])
