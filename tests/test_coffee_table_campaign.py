from __future__ import annotations

import json
from pathlib import Path

import pytest

import lala_workflow.video.campaigns as campaign_module
from lala_workflow.video.campaigns import CampaignError, preview_coffee_table


def _ready() -> dict:
    return {
        "status": "GOAL2_READY",
        "active_character": "character-20260821-001",
        "display_name": "Candidate 16",
        "set_id": "candidate16-keyframe-set-v1",
        "set_manifest_sha256": "a" * 64,
        "members": {
            "K1": {"candidate_id": "K1-V2-002", "sha256": "1" * 64},
            "K2": {"candidate_id": "K2-002", "sha256": "2" * 64},
            "K3": {"candidate_id": "K3-V2-002", "sha256": "3" * 64},
        },
        "v7": {
            "status": "CANDIDATE16_V7_MATCH",
            "selected_candidate_id": "v7-b-natural-micro-motion",
            "selected_media_sha256": "4" * 64,
            "selected_prompt_sha256": "5" * 64,
        },
        "provider_submissions": 0,
        "paid_calls": 0,
    }


def test_coffee_table_preview_is_motion_only_bounded_and_zero_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(campaign_module, "preflight_goal2", lambda _root: _ready())
    result = preview_coffee_table(tmp_path)
    evidence = json.loads((tmp_path / result["evidence_path"]).read_text())
    assert result["status"] == "READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION"
    assert result["provider_submissions"] == result["paid_calls"] == 0
    assert evidence["product"]["sku"] == "IN3725"
    assert evidence["semantics"]["talking"] is False
    assert evidence["semantics"]["tts"] is False
    assert evidence["semantics"]["lip_sync"] is False
    assert len(evidence["storyboard"]) == 6
    assert sum(beat["duration_seconds"] for beat in evidence["storyboard"]) == 20
    assert set(evidence["delivery"]) == {"master", "1:1", "9:16"}
    assert evidence["live_options"][0]["recommended"] is True
    assert evidence["live_options"][0]["tasks"] <= 5
    assert evidence["live_options"][0]["runway_credits"] <= 125
    assert evidence["v7_binding"]["selected_candidate_id"] == "v7-b-natural-micro-motion"
    assert evidence["live_execution_plan"]["selected_option"] == "Option A"
    assert evidence["live_execution_plan"]["task_count"] == 4
    assert evidence["live_execution_plan"]["max_runway_credits"] == 100
    assert evidence["live_execution_plan"]["max_provider_cost_usd"] == 1.0
    assert evidence["live_execution_plan"]["current_cli_live_execution_available"] is False
    assert evidence["live_execution_plan"]["live_executed"] is False


def test_coffee_table_preview_refuses_blocker_without_creating_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked = _ready() | {"status": "READY_FOR_OWNER_CANDIDATE16_V7_EXECUTION"}
    monkeypatch.setattr(campaign_module, "preflight_goal2", lambda _root: blocked)
    with pytest.raises(CampaignError, match="READY_FOR_OWNER_CANDIDATE16_V7_EXECUTION"):
        preview_coffee_table(tmp_path)
    assert not (tmp_path / "outputs/campaign-previews").exists()
