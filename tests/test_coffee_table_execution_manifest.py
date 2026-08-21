from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

import lala_workflow.video.campaigns as campaign_module
from lala_workflow.cli import build_parser
from lala_workflow.hashing import sha256_file
from lala_workflow.video.campaigns import (
    COFFEE_TABLE_PARENT_PLAN,
    COFFEE_TABLE_PARENT_SHA256,
    COFFEE_TABLE_PRODUCT_SHA256,
    COFFEE_TABLE_PRODUCT_SOURCE,
    COFFEE_TABLE_STATUS,
    COFFEE_TABLE_V1_MANIFEST,
    COFFEE_TABLE_V1_REVIEW,
    COFFEE_TABLE_V1_SHA256,
    CampaignError,
    prepare_coffee_table_execution_manifest,
)
from lala_workflow.video.runner import handle_video_command


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = datetime(2026, 8, 21, 8, 30, tzinfo=timezone.utc)


def _copy(root: Path, relative: Path | str) -> None:
    source = REPOSITORY_ROOT / relative
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _fixture(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    _copy(root, COFFEE_TABLE_PARENT_PLAN)
    plan = json.loads((root / COFFEE_TABLE_PARENT_PLAN).read_text(encoding="utf-8"))
    for member in plan["keyframe_binding"]["members"].values():
        _copy(root, member["approved_path"])
    _copy(root, COFFEE_TABLE_PRODUCT_SOURCE)
    _copy(root, COFFEE_TABLE_V1_MANIFEST)
    _copy(root, COFFEE_TABLE_V1_REVIEW)
    for relative in (
        "prompts/coffee-table-task-01-establish-walk-v1.txt",
        "prompts/coffee-table-task-02-walk-place-v1.txt",
        "prompts/coffee-table-task-03-product-detail-v2.txt",
        "prompts/coffee-table-task-04-sit-hero-v2.txt",
    ):
        _copy(root, relative)
    ready = {
        "status": "GOAL2_READY",
        "active_character": plan["character"]["character_id"],
        "display_name": plan["character"]["display_name"],
        "set_id": plan["keyframe_binding"]["set_id"],
        "set_manifest_sha256": plan["keyframe_binding"]["set_manifest_sha256"],
        "members": plan["keyframe_binding"]["members"],
        "v7": plan["v7_binding"],
        "provider_submissions": 0,
        "paid_calls": 0,
    }
    monkeypatch.setattr(campaign_module, "preflight_goal2", lambda _root: ready)
    return plan


def _prepare(root: Path) -> dict:
    return prepare_coffee_table_execution_manifest(
        root,
        parent_plan=COFFEE_TABLE_PARENT_PLAN,
        parent_plan_sha256=COFFEE_TABLE_PARENT_SHA256,
        confirm_owner_authorized_manifest_preparation=True,
        created_at=FIXED_TIME,
    )


def _new_execution_directories(root: Path) -> list[Path]:
    parent = root / "outputs/campaign-execution-manifests"
    if not parent.exists():
        return []
    v1_directory = (root / COFFEE_TABLE_V1_MANIFEST).parent
    return [path for path in parent.iterdir() if path != v1_directory]


def test_execution_manifest_freezes_four_requests_and_exact_timeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _fixture(tmp_path, monkeypatch)
    result = _prepare(tmp_path)
    manifest_path = tmp_path / result["execution_manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["status"] == COFFEE_TABLE_STATUS
    assert result["parent_plan_sha256"] == COFFEE_TABLE_PARENT_SHA256
    assert result["execution_manifest_sha256"] == sha256_file(manifest_path)
    assert manifest_path.name == "execution-manifest-v2.json"
    assert manifest["schema_version"] == "candidate16-coffee-table-execution-manifest/v2"
    assert manifest["supersedes"]["manifest_sha256"] == COFFEE_TABLE_V1_SHA256
    assert manifest["supersedes"]["decision"] == "REJECT_FOR_LIVE"
    assert manifest["supersedes"]["reason_code"] == "MATERIAL_CONTINUITY_RISK"
    assert len(manifest["tasks"]) == 4
    assert [task["task_id"] for task in manifest["tasks"]] == [
        "TASK-01", "TASK-02", "TASK-03", "TASK-04"
    ]
    assert [task["source"]["source_type"] for task in manifest["tasks"]] == [
        "APPROVED_KEYFRAME",
        "APPROVED_KEYFRAME",
        "STATIC_PRODUCT_REFERENCE",
        "UPSTREAM_TASK_FRAME",
    ]
    assert all(task["request"]["model"] == "gen4_turbo" for task in manifest["tasks"])
    assert all(task["request"]["ratio"] == "1280:720" for task in manifest["tasks"])
    assert all(task["request"]["duration_seconds"] == 5 for task in manifest["tasks"])
    assert all(
        task["prompt"]["text"]
        == (tmp_path / task["prompt"]["path"]).read_text(encoding="utf-8")
        for task in manifest["tasks"]
    )
    assert sum(task["projected_runway_credits"] for task in manifest["tasks"]) == 100
    assert manifest["execution"]["max_provider_cost_usd"] == 1.0
    assert manifest["execution"]["concurrency"] == 1
    assert manifest["execution"]["automatic_paid_retries"] == 0
    assert manifest["execution"]["automatic_replacement_tasks"] == 0
    task_03 = manifest["tasks"][2]
    assert task_03["source"]["path"] == COFFEE_TABLE_PRODUCT_SOURCE.as_posix()
    assert task_03["source"]["sha256"] == COFFEE_TABLE_PRODUCT_SHA256
    assert task_03["source"]["contains_candidate16"] is False
    assert task_03["source"]["contains_wine_glass"] is False
    assert "No person, hands, wine glass" in task_03["prompt"]["text"]

    task_04 = manifest["tasks"][3]
    assert task_04["source"]["source_task_id"] == "TASK-02"
    assert task_04["source"]["frame_selector"] == "LAST_VALID_FRAME"
    assert task_04["source"]["expected_source_task_sha256"] == "RUNTIME_BOUND"
    assert task_04["source"]["extracted_frame_sha256"] == "RUNTIME_BOUND"
    assert task_04["source"]["frame_count"]["selected_zero_based_frame_index"] == "frame_count - 1"
    assert task_04["source"]["extraction"]["provider_calls"] == 0
    assert task_04["request"]["input_image_sha256"] == "RUNTIME_BOUND"
    assert "hands are empty" in task_04["prompt"]["text"]
    assert "Do not pick up" in task_04["prompt"]["text"]
    assert manifest["execution_dependencies"] == [
        {
            "task_id": "TASK-04",
            "depends_on": ["TASK-02"],
            "required_before_submission": [
                "TASK-02 status is SUCCEEDED",
                "TASK-02 MP4 is downloaded and SHA-256 recorded",
                "TASK-02 LAST_VALID_FRAME PNG is deterministically extracted",
                "extracted PNG validates and its SHA-256 is recorded",
            ],
            "provider_calls_for_dependency_resolution": 0,
        }
    ]

    segments = manifest["assembly"]["segments"]
    assert [segment["master_interval_seconds"]["start"] for segment in segments] == [
        0, 3, 5, 7, 10, 13, 17, 18
    ]
    assert [segment["master_interval_seconds"]["end"] for segment in segments] == [
        3, 5, 7, 10, 13, 17, 18, 20
    ]
    assert [segments[index + 1]["master_interval_seconds"]["start"] for index in range(7)] == [
        segment["master_interval_seconds"]["end"] for segment in segments[:-1]
    ]
    assert [segment["storyboard_beat"] for segment in segments] == [1, 2, 2, 3, 4, 5, 6, 6]
    assert {segment["storyboard_beat"] for segment in segments} == {
        beat["shot"] for beat in plan["storyboard"]
    }
    assert segments[-1]["operation"] == "LOCAL_TERMINAL_FRAME_HOLD"
    assert segments[-1]["frame_selector"] == "LAST_VALID_FRAME"
    assert "source_timestamp_seconds" not in segments[-1]
    assert manifest["assembly"]["task_03_discarded_interval_seconds"] == {"start": 3, "end": 5}
    assert manifest["delivery"]["native_ratio_regeneration"] == "NOT_AUTHORIZED"
    assert manifest["review"] == {
        "reviewer": "", "decision": "", "notes": "", "live_authorized": False
    }
    assert len(manifest["owner_review_focus"]) == 4
    assert result["provider_submissions"] == 0
    assert result["provider_task_ids"] == 0
    assert result["http_requests"] == 0
    assert result["paid_calls"] == 0


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("authorization", "explicit Owner authorization"),
        ("sha", "SHA-256"),
        ("parent", "parent plan hash drift"),
        ("keyframe", "approved keyframe hash drift"),
        ("prompt", "prompt is invalid"),
        ("product", "PDP product-only source hash drift"),
        ("v1_review", "V1 Owner review hash drift"),
        ("goal2", "BLOCKED_EXTERNAL"),
    ],
)
def test_execution_manifest_fails_closed_before_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    message: str,
) -> None:
    plan = _fixture(tmp_path, monkeypatch)
    confirmed = True
    sha = COFFEE_TABLE_PARENT_SHA256
    if mutation == "authorization":
        confirmed = False
    elif mutation == "sha":
        sha = "0" * 64
    elif mutation == "parent":
        (tmp_path / COFFEE_TABLE_PARENT_PLAN).write_text("{}\n", encoding="utf-8")
    elif mutation == "keyframe":
        (tmp_path / plan["keyframe_binding"]["members"]["K1"]["approved_path"]).write_bytes(b"drift")
    elif mutation == "prompt":
        (tmp_path / "prompts/coffee-table-task-01-establish-walk-v1.txt").write_text(
            "drift\n", encoding="utf-8"
        )
    elif mutation == "product":
        (tmp_path / COFFEE_TABLE_PRODUCT_SOURCE).write_bytes(b"drift")
    elif mutation == "v1_review":
        (tmp_path / COFFEE_TABLE_V1_REVIEW).write_text("{}\n", encoding="utf-8")
    elif mutation == "goal2":
        monkeypatch.setattr(
            campaign_module,
            "preflight_goal2",
            lambda _root: {"status": "BLOCKED_EXTERNAL"},
        )

    with pytest.raises(CampaignError, match=message):
        prepare_coffee_table_execution_manifest(
            tmp_path,
            parent_plan=COFFEE_TABLE_PARENT_PLAN,
            parent_plan_sha256=sha,
            confirm_owner_authorized_manifest_preparation=confirmed,
            created_at=FIXED_TIME,
        )
    assert _new_execution_directories(tmp_path) == []


def test_execution_manifest_is_collision_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixture(tmp_path, monkeypatch)
    first = _prepare(tmp_path)
    with pytest.raises(CampaignError, match="already exists"):
        _prepare(tmp_path)
    assert sha256_file(tmp_path / first["execution_manifest_path"]) == first[
        "execution_manifest_sha256"
    ]


def test_execution_manifest_write_failure_leaves_no_partial_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixture(tmp_path, monkeypatch)

    def fail_write(_path: Path, _value: dict) -> None:
        raise OSError("synthetic write failure")

    monkeypatch.setattr(campaign_module, "_write_json_exclusive", fail_write)
    with pytest.raises(OSError, match="synthetic write failure"):
        _prepare(tmp_path)
    assert _new_execution_directories(tmp_path) == []


def test_coffee_table_cli_requires_one_offline_mode_and_parses_contract() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "video",
            "campaign",
            "coffee-table",
            "--prepare-execution-manifest",
            "--parent-plan",
            COFFEE_TABLE_PARENT_PLAN.as_posix(),
            "--parent-plan-sha256",
            COFFEE_TABLE_PARENT_SHA256,
            "--confirm-owner-authorized-manifest-preparation",
        ]
    )
    assert args.prepare_execution_manifest is True
    assert args.dry_run is False
    assert args.parent_plan == COFFEE_TABLE_PARENT_PLAN
    assert args.confirm_owner_authorized_manifest_preparation is True
    with pytest.raises(SystemExit):
        parser.parse_args(["video", "campaign", "coffee-table"])
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["video", "campaign", "coffee-table", "--dry-run", "--prepare-execution-manifest"]
        )


def test_coffee_table_cli_dispatch_returns_review_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixture(tmp_path, monkeypatch)
    args = build_parser().parse_args(
        [
            "video",
            "campaign",
            "coffee-table",
            "--project-root",
            str(tmp_path),
            "--prepare-execution-manifest",
            "--parent-plan",
            COFFEE_TABLE_PARENT_PLAN.as_posix(),
            "--parent-plan-sha256",
            COFFEE_TABLE_PARENT_SHA256,
            "--confirm-owner-authorized-manifest-preparation",
        ]
    )
    code, result = handle_video_command(args)
    assert code == 0
    assert result["status"] == COFFEE_TABLE_STATUS
    assert result["provider_submissions"] == result["paid_calls"] == 0
    assert len(result["tasks"]) == 4
    assert result["tasks"][2]["source_type"] == "STATIC_PRODUCT_REFERENCE"
    assert result["tasks"][3]["source_identity"] == "TASK-02"
