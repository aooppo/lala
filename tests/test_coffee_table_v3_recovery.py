from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from lala_workflow.hashing import sha256_file
from lala_workflow.video.coffee_table_v3_recovery import (
    FINAL_MASTER,
    FINAL_MASTER_SHA256,
    FINAL_REVIEW_PACKAGE,
    FINAL_REVIEW_MANIFEST_SHA256,
    READY_FOR_OWNER_COFFEE_TABLE_V3_RECOVERY_REVIEW,
    TASK_01,
    TASK_02,
    TASK_04,
    prepare_coffee_table_v3_recovery,
)


REPOSITORY = Path(__file__).resolve().parents[1]
FIXED_NOW = datetime(2026, 8, 21, 15, 0, 0, tzinfo=timezone.utc)


def _copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _fixture(root: Path) -> Path:
    files = (
        FINAL_REVIEW_PACKAGE / "manifest.json", FINAL_REVIEW_PACKAGE / "evidence.json",
        FINAL_REVIEW_PACKAGE / "review.csv", FINAL_MASTER, TASK_01, TASK_02, TASK_04,
        Path("outputs/broll/COFFEE-TABLE-RECOVERY-20260821-164849-001/LOCAL-TASK-03.mp4"),
        Path("outputs/campaign-recovery-manifests/COFFEE-TABLE-RECOVERY-20260821-204901-001/coffee-table-recovery-manifest-v2.json"),
        Path("outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json"),
        Path("runs/LALA-VIDEO-20260821-082100-COFFEE-TABLE-LIVE-001/provider-results.json"),
        Path("prompts/coffee-table-task-04-sofa-hero-v4.txt"),
    )
    for path in files:
        _copy(REPOSITORY / path, root / path)
    for path in ("assets/approved_anchors", "assets/approved_keyframes", "assets/voice/source", "assets/voice/approved", "assets/scripts"):
        shutil.copytree(REPOSITORY / path, root / path)
    return root


def test_v3_recovery_is_append_only_and_never_selects_or_submits(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    master_before = sha256_file(root / FINAL_MASTER)
    manifest_before = sha256_file(root / FINAL_REVIEW_PACKAGE / "manifest.json")
    outcome = prepare_coffee_table_v3_recovery(root, now=FIXED_NOW)

    assert outcome.status == READY_FOR_OWNER_COFFEE_TABLE_V3_RECOVERY_REVIEW
    assert outcome.provider_calls == outcome.paid_calls == 0
    assert master_before == FINAL_MASTER_SHA256
    assert manifest_before == FINAL_REVIEW_MANIFEST_SHA256
    assert sha256_file(root / FINAL_MASTER) == master_before
    assert sha256_file(root / FINAL_REVIEW_PACKAGE / "manifest.json") == manifest_before

    owner = json.loads(outcome.owner_decision_path.read_text())
    assert owner["decision"] == "REJECT"
    assert owner["reason"] == "SOFA_SEATING_CONTRACT_VIOLATION"
    assert owner["findings"]["wine_glass"] == "Wine glass is correct according to Henry's source requirement."

    frames = json.loads(outcome.source_frame_review_path.read_text())
    assert [row["zero_based_frame_index"] for row in frames["candidates"]] == [92, 96, 100, 104, 108, 112, 116]
    assert frames["owner_selection"]["selected_frame"] is None
    assert frames["owner_selection"]["status"] == "EMPTY_UNAUTHORIZED"

    manifest = json.loads(outcome.manifest_path.read_text())
    assert manifest["task_04_v3_proposal"]["selected_frame"] is None
    assert manifest["task_04_v3_proposal"]["authorization"]["paid_generation"] is False
    assert manifest["task_04_v3_proposal"]["authorization"]["maximum_authorized_credits"] == 0
    assert manifest["reuse_analysis"]["TASK-04"]["decision"] == "REGEN_REQUIRED"
    assert manifest["reuse_analysis"]["TASK-02"]["decision"] == "REUSE_ELIGIBLE"
    assert manifest["historical"]["accounting"]["historical_spent_credits"] == 75
