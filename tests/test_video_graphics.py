from __future__ import annotations

import json
from pathlib import Path

import pytest

from lala_workflow.video.assembly import assemble_video
from lala_workflow.video.graphics import DRAFT_NOTICE, resolve_brand_graphic
from lala_workflow.video.promotion import PromotionError, promote_video
from tests.test_video_selection import generated_source_run, write_selection


def test_missing_brand_source_creates_deterministic_review_only_draft(
    video_project_root: Path,
) -> None:
    script = (video_project_root / "assets/scripts/tooltip.txt").read_bytes()
    first = resolve_brand_graphic(
        video_project_root,
        run_id="GRAPHIC-TEST-1",
        asset_id="five_lala_likes",
        exact_caption=script.decode("utf-8"),
        script_sha256="a" * 64,
    )
    assert first.draft is True
    assert first.approval_status == "draft"
    assert first.path.is_file()
    assert (video_project_root / "assets/brand/approved") not in first.path.parents
    sidecar = json.loads(first.path.with_suffix(".json").read_text(encoding="utf-8"))
    assert sidecar["notice"] == DRAFT_NOTICE
    assert sidecar["exact_caption"] == script.decode("utf-8")


def test_tooltip_assembly_overlays_graphic_and_draft_blocks_promotion(
    video_project_root: Path, synthetic_video: Path
) -> None:
    source = generated_source_run(video_project_root, synthetic_video, preset="tooltip")
    selection = write_selection(video_project_root, source)
    outcome = assemble_video(video_project_root, source.run_id, selection, final_edits=1)
    assert outcome.status == "REVIEW_READY_DRAFT_ASSETS"
    command = (outcome.run_dir / "edit-commands.txt").read_text(encoding="utf-8")
    assert "overlay=" in command
    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    assert results["contains_draft_brand_assets"] is True
    assert results["graphics"][0]["draft"] is True
    candidate = results["results"][0]["candidate"]
    with pytest.raises(PromotionError, match="draft brand assets"):
        promote_video(
            video_project_root,
            outcome.run_id,
            candidate,
            review_file=outcome.run_dir / "review.csv",
        )
