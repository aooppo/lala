from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

import pytest

from lala_workflow.providers.runway_video import RunwayMotionProvider
from lala_workflow.video.config import load_video_config
from lala_workflow.video.coffee_table_prompt_preflight import (
    COFFEE_TABLE_PROMPTS,
    CoffeeTablePromptPreflightError,
    format_preflight,
    preflight_coffee_table_prompts,
)
from lala_workflow.video.domain import MotionVideoRequest
from lala_workflow.video.prompts import load_video_prompt, utf16_code_units


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = PROJECT_ROOT / "outputs/reviews/coffee-table-task01-replacement-plan/COFFEE-TABLE-TASK01-REPLACEMENT-20260822-001"


def test_optimized_coffee_table_prompts_pass_utf16_preflight() -> None:
    checks = preflight_coffee_table_prompts(PROJECT_ROOT)
    assert [item.task_id for item in checks] == ["TASK-01", "TASK-02", "TASK-03", "TASK-04"]
    assert all(0 < item.utf16_units <= 850 for item in checks)
    report = format_preflight(checks)
    assert report.count("status: PASS") == 4


def test_utf16_counter_counts_surrogate_pairs() -> None:
    assert utf16_code_units("A😀B") == 4


def test_preflight_rejects_over_provider_limit_before_execution(tmp_path: Path) -> None:
    for relative_path in COFFEE_TABLE_PROMPTS.values():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
    (tmp_path / COFFEE_TABLE_PROMPTS["TASK-02"]).write_text("😀" * 501, encoding="utf-8")
    with pytest.raises(CoffeeTablePromptPreflightError, match="provider UTF-16 limit"):
        preflight_coffee_table_prompts(tmp_path)


def test_review_manifest_binds_prompts_and_continuity_without_live_authority() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "READY_FOR_OWNER_TASK01_REPLACEMENT_LIVE_AUTHORIZATION"
    prompt = manifest["replacement_prompt"]
    prompt_path = PROJECT_ROOT / prompt["path"]
    check = preflight_coffee_table_prompts(PROJECT_ROOT)[0]
    assert prompt["path"] == COFFEE_TABLE_PROMPTS["TASK-01"].as_posix()
    assert prompt["sha256"] == sha256(prompt_path.read_bytes()).hexdigest()
    assert prompt["utf16_units"] == check.utf16_units == 641
    assert manifest["terminal_frame"] == {"approved": False, "selection": None}
    assert manifest["TASK-02"]["status"] == "BLOCKED_ON_ACCEPTED_TASK01_TERMINAL_FRAME"
    assert manifest["authorization"]["replacement_live"] is False
    assert all(value == 0 for value in manifest["accounting"].values())


def test_task01_v4_has_exact_prop_state_and_no_placement_action_cues() -> None:
    text = (PROJECT_ROOT / COFFEE_TABLE_PROMPTS["TASK-01"]).read_text(encoding="utf-8")
    lowered = text.lower()
    assert re.search(r"\b(?:place|placing|release)\b", lowered) is None
    for forbidden in ("lower glass", "reach toward tabletop", "prepare to place", "ready to place"):
        assert forbidden not in lowered
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["wine_glass_state"] == {
        "start": {"hand": 1, "tabletop": 0},
        "during": {"hand": 1, "tabletop": 0},
        "terminal": {"hand": 1, "tabletop": 0},
        "total_required": 1,
    }
    failure = json.loads((PACKAGE / "failure.json").read_text(encoding="utf-8"))
    assert failure["status"] == "REJECTED_HUMAN_QA"
    assert failure["terminal_frame"]["status"] == "NONE_APPROVED"


def test_preflight_count_equals_actual_runway_payload_count(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    keyframe = config.keyframes["hero"]
    source = load_video_prompt(PROJECT_ROOT, COFFEE_TABLE_PROMPTS["TASK-03"])
    copied_prompt = video_project_root / source.path
    copied_prompt.write_bytes((PROJECT_ROOT / source.path).read_bytes())
    request = MotionVideoRequest(
        request_id="coffee-table-task-03", run_id="DRY-TEST", preset="coffee-table",
        shot_id="TASK-03", variation=1, provider="runway", model="gen4_turbo",
        image_path=video_project_root / keyframe.path, image_sha256=keyframe.sha256,
        prompt_path=copied_prompt, prompt_text=source.text, prompt_sha256=sha256(copied_prompt.read_bytes()).hexdigest(),
        ratio="1280:720", duration_seconds=5, seed=None, output_format="mp4",
        timeout_seconds=1800, max_retries=0,
    )
    provider = RunwayMotionProvider(config.providers["runway"], api_key="local-test-secret", client=object())
    payload = provider.translate_request(request)
    check = {item.task_id: item for item in preflight_coffee_table_prompts(PROJECT_ROOT)}["TASK-03"]
    assert payload["prompt_text"].endswith("\n")
    assert check.utf16_units == utf16_code_units(payload["prompt_text"])
