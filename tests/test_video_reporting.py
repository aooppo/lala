from __future__ import annotations

import json
from pathlib import Path

import yaml

from lala_workflow.video.reporting import build_video_report
from lala_workflow.video.runner import VideoRunOptions, preview_video


def test_report_reconciles_run_status_outputs_cost_and_review(video_project_root: Path) -> None:
    outcome = preview_video(
        video_project_root, VideoRunOptions(preset="homepage", action="generate")
    )
    report = build_video_report(video_project_root, outcome.run_id)
    assert report["status"] == "DRY_RUN"
    assert report["preset"] == "homepage"
    assert report["planned_provider_calls"] == 12
    assert report["provider_submissions"] == 0
    assert report["candidate_count"] == 0
    assert report["review_rows"] == 0
    assert report["cost"]["total_provider_cost"] is not None


def test_missing_pricing_stays_null_in_cost_and_report(video_project_root: Path) -> None:
    path = video_project_root / "configs/providers.yaml"
    providers = yaml.safe_load(path.read_text(encoding="utf-8"))
    del providers["providers"]["heygen"]["pricing"]
    path.write_text(yaml.safe_dump(providers, sort_keys=False), encoding="utf-8")
    outcome = preview_video(
        video_project_root, VideoRunOptions(preset="tooltip", action="generate")
    )
    report = build_video_report(video_project_root, outcome.run_id)
    assert report["cost"]["talking_video_cost"] is None
    assert report["cost"]["total_provider_cost"] is None
    assert report["cost"]["components"][0]["amount"] is None
    assert report["cost"]["components"][0]["pricing_source"] is None
