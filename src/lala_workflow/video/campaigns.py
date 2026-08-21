from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..hashing import sha256_file
from .keyframe_sets import preflight_goal2


class CampaignError(ValueError):
    pass


COFFEE_TABLE_PARENT_PLAN = Path(
    "outputs/campaign-previews/COFFEE-TABLE-DRY-20260821-071433-640204/plan.json"
)
COFFEE_TABLE_PARENT_SHA256 = (
    "ed30e4984dd488cde79188e7e327bc4472ab0c331125a0c600d739a0d388ac5f"
)
COFFEE_TABLE_V1_MANIFEST = Path(
    "outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-074417-152920/execution-manifest.json"
)
COFFEE_TABLE_V1_SHA256 = (
    "69746bff9ee06a4c6c762168d30151a6aab692f245f7a16271607cd716cf9b26"
)
COFFEE_TABLE_V1_REVIEW = Path(
    "outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-074417-152920/owner-review.json"
)
COFFEE_TABLE_V1_REVIEW_SHA256 = (
    "67c71050e690781bb0e990710ccf3aba9603f7f3205811db454a122ede9e5913"
)
COFFEE_TABLE_PRODUCT_SOURCE = Path(
    "outputs/reviews/candidate16-keyframes-v2/references/02.jpg"
)
COFFEE_TABLE_PRODUCT_SHA256 = (
    "4bf6e13b82f9c9c4d4525180aa412ebc22e4ca6c541e6d9c33c905271814b5c5"
)
COFFEE_TABLE_STATUS = "READY_FOR_OWNER_COFFEE_TABLE_EXECUTION_MANIFEST_REVIEW"
COFFEE_TABLE_STORYBOARD = (
    (1, 0, 3, "wide establishing: fireplace, Candidate 16, Coffee Table, sofa"),
    (2, 3, 7, "slow controlled walk from fireplace holding one stable wine glass"),
    (3, 7, 10, "gentle wine-glass placement on the clearly visible Coffee Table"),
    (4, 10, 13, "Coffee Table detail and product emphasis"),
    (5, 13, 17, "controlled natural sit on leather sofa with table prominent"),
    (6, 17, 20, "calm premium product-hero ending"),
)
COFFEE_TABLE_PROMPTS = (
    (
        "prompts/coffee-table-task-01-establish-walk-v1.txt",
        "946fa34f0ac12e0a468a83d620a73c95f581c268a7a4034a24ad6760e8c5f6ab",
    ),
    (
        "prompts/coffee-table-task-02-walk-place-v1.txt",
        "eaa42335a2f6a55029b99f493fa078bffe9c002407331f4bb0935f2e62d2f7b2",
    ),
    (
        "prompts/coffee-table-task-03-product-detail-v2.txt",
        "ce9abc62351bd108e15ff9fff037a3234facdf37f3194a1e7e9fc865a906cf89",
    ),
    (
        "prompts/coffee-table-task-04-sit-hero-v2.txt",
        "92638ab56fd3b3a541e27cc7f9c8464c352dce95c5f24b5a537e1d727042f4ec",
    ),
)
COFFEE_TABLE_KEYFRAME_SHA256 = {
    "K1": "3ad624df44cc31f56309a45ae4ba9577d526693a7332ee97fb7fd9f914a7043c",
    "K2": "78478b171552472227772f5efc092380b69da6b698cc13182880967e3a26bd59",
    "K3": "7281237344ddfc81b7f4635a83410d87b109688b03be4188f648f20dff6fd631",
}


def load_validated_coffee_table_execution_manifest(
    project_root: Path, *, manifest_path: Path, manifest_sha256: str
) -> dict[str, Any]:
    """Load the one approved V2 identity and revalidate every mutable authority input."""

    root = project_root.resolve()
    approved_relative = Path(
        "outputs/campaign-execution-manifests/"
        "COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json"
    )
    approved_sha = "ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea"
    supplied = manifest_path if manifest_path.is_absolute() else root / manifest_path
    expected = root / approved_relative
    if manifest_sha256 != approved_sha:
        raise CampaignError("Coffee Table Live manifest SHA-256 is not Owner-authorized")
    if supplied.is_symlink() or supplied.resolve() != expected.resolve():
        raise CampaignError("Coffee Table Live manifest path is not Owner-authorized")
    if not expected.is_file() or expected.is_symlink() or sha256_file(expected) != approved_sha:
        raise CampaignError("Coffee Table Live manifest hash drift")
    try:
        manifest = json.loads(expected.read_text(encoding="utf-8"))
        plan_path = root / COFFEE_TABLE_PARENT_PLAN
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignError("Coffee Table Live authority evidence is unreadable") from exc
    goal2 = preflight_goal2(root)
    _validate_coffee_table_authority(plan, goal2, root)
    _validate_v1_rejection(root)
    expected_tasks = _coffee_table_execution_tasks(root)
    expected_assembly = _coffee_table_assembly(plan)
    execution = manifest.get("execution", {})
    if (
        manifest.get("schema_version") != "candidate16-coffee-table-execution-manifest/v2"
        or manifest.get("status") != COFFEE_TABLE_STATUS
        or manifest.get("parent_plan", {}).get("sha256") != COFFEE_TABLE_PARENT_SHA256
        or manifest.get("tasks") != expected_tasks
        or manifest.get("assembly") != expected_assembly
        or manifest.get("review")
        != {"reviewer": "", "decision": "", "notes": "", "live_authorized": False}
        or execution.get("provider") != "runway"
        or execution.get("model") != "gen4_turbo"
        or execution.get("task_count") != 4
        or execution.get("max_tasks") != 4
        or execution.get("duration_seconds_per_task") != 5
        or execution.get("generated_seconds") != 20
        or execution.get("max_runway_credits") != 100
        or execution.get("max_provider_cost_usd") != 1.0
        or execution.get("concurrency") != 1
        or execution.get("automatic_paid_retries") != 0
        or execution.get("automatic_replacement_tasks") != 0
        or execution.get("live_authorized") is not False
        or manifest.get("provider_submissions") != 0
        or manifest.get("provider_task_ids") != 0
        or manifest.get("http_requests") != 0
        or manifest.get("paid_calls") != 0
    ):
        raise CampaignError("Coffee Table Live manifest semantics drift")
    return manifest


def preview_coffee_table(
    project_root: Path, *, created_at: datetime | None = None
) -> dict[str, Any]:
    root = project_root.resolve()
    goal2 = preflight_goal2(root)
    if goal2.get("status") != "GOAL2_READY":
        raise CampaignError(str(goal2.get("status") or "BLOCKED_GOAL2_PREFLIGHT"))
    timestamp = (created_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run_id = timestamp.strftime("COFFEE-TABLE-DRY-%Y%m%d-%H%M%S-%f")
    directory = root / "outputs/campaign-previews" / run_id
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise CampaignError(f"Coffee Table preview already exists: {run_id}") from exc
    evidence_path = directory / "plan.json"
    storyboard = [
        {"shot": 1, "time": "0:00-0:03", "duration_seconds": 3, "beat": "wide establishing: fireplace, Candidate 16, Coffee Table, sofa"},
        {"shot": 2, "time": "0:03-0:07", "duration_seconds": 4, "beat": "slow controlled walk from fireplace holding one stable wine glass"},
        {"shot": 3, "time": "0:07-0:10", "duration_seconds": 3, "beat": "gentle wine-glass placement on the clearly visible Coffee Table"},
        {"shot": 4, "time": "0:10-0:13", "duration_seconds": 3, "beat": "Coffee Table detail and product emphasis"},
        {"shot": 5, "time": "0:13-0:17", "duration_seconds": 4, "beat": "controlled natural sit on leather sofa with table prominent"},
        {"shot": 6, "time": "0:17-0:20", "duration_seconds": 3, "beat": "calm premium product-hero ending"},
    ]
    payload: dict[str, Any] = {
        "schema_version": "candidate16-coffee-table-preview/v1",
        "status": "READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION",
        "mode": "DRY_RUN",
        "run_id": run_id,
        "created_at": timestamp.isoformat(),
        "character": {
            "character_id": goal2["active_character"],
            "display_name": goal2["display_name"],
            "wardrobe": "same red dress, hairstyle, jewelry, and overall makeup",
        },
        "keyframe_binding": {
            "set_id": goal2["set_id"],
            "set_manifest_sha256": goal2["set_manifest_sha256"],
            "members": goal2["members"],
        },
        "v7_binding": goal2["v7"],
        "product": {
            "name": "Chunky Chestnut Coffee Table — Solid Mango Wood",
            "sku": "IN3725",
            "pdp": "https://decorolala.com/products/in3725",
            "role": "PRIMARY_PRODUCT",
            "pdp_provenance": "OWNER_SUPPLIED",
        },
        "scene": [
            "stone fireplace",
            "warm wood shelving",
            "warm wooden ceiling and architectural elements",
            "leather sofa",
            "area rug",
            "Chunky Chestnut Coffee Table",
            "warm premium living-room furniture-commercial aesthetic",
        ],
        "performance": {
            "tone": ["calm", "relaxed", "premium lifestyle-commercial", "subtle smile"],
            "required": [
                "slow controlled walking",
                "stable wine-glass wrist",
                "brief natural glance toward product",
                "gentle glass placement",
                "controlled sit-down movement",
            ],
            "forbidden": [
                "overacting", "fast walking", "whip head movement", "large gestures",
                "glass floating", "glass duplication", "glass morphing",
                "hand/glass intersection", "table morphing", "product disappearing",
            ],
        },
        "semantics": {"motion_only": True, "talking": False, "dialogue": False, "tts": False, "lip_sync": False, "heygen": False},
        "storyboard": storyboard,
        "delivery": {
            "master": {"ratio": "16:9", "strategy": "one high-quality composition-safe master"},
            "1:1": {"strategy": "local reframe only after face, body, glass, and Coffee Table safe-area validation", "fallback": "native ratio generation"},
            "9:16": {"strategy": "local reframe only after face, body, glass, and Coffee Table safe-area validation", "fallback": "native ratio generation"},
        },
        "live_options": [
            {
                "name": "Option A",
                "recommended": True,
                "provider": "runway",
                "model": "gen4_turbo",
                "tasks": 4,
                "duration_seconds_per_task": 5,
                "generated_seconds": 20,
                "runway_credits": 100,
                "usd_projection": 1.0,
                "ratio_strategy": "16:9 safe master then guarded local 1:1/9:16 reframes",
            },
            {
                "name": "Option B",
                "recommended": False,
                "provider": "runway",
                "model": "gen4_turbo",
                "tasks": 5,
                "duration_seconds_per_task": 5,
                "generated_seconds": 25,
                "runway_credits": 125,
                "usd_projection": 1.25,
                "ratio_strategy": "native ratio fallback for compositions that fail safe-area checks",
            },
        ],
        "live_execution_plan": {
            "status": "PLAN_ONLY_AWAITING_SEPARATE_OWNER_AUTHORIZATION",
            "selected_option": "Option A",
            "provider": "runway",
            "model": "gen4_turbo",
            "task_count": 4,
            "duration_seconds_per_task": 5,
            "generated_seconds": 20,
            "max_runway_credits": 100,
            "max_provider_cost_usd": 1.0,
            "concurrency": 1,
            "automatic_replacement_tasks": 0,
            "master_ratio": "16:9",
            "delivery": "guarded local 1:1 and 9:16 reframes; native-ratio fallback requires separate authorization",
            "current_cli_live_execution_available": False,
            "requires_separate_owner_authorization": True,
            "live_executed": False,
        },
        "authorization_boundary": "READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION",
        "provider_submissions": 0,
        "paid_calls": 0,
        "automatic_paid_retries": 0,
    }
    try:
        _write_json_exclusive(evidence_path, payload)
    except Exception:
        directory.rmdir()
        raise
    return {
        "status": payload["status"],
        "run_id": run_id,
        "evidence_path": evidence_path.relative_to(root).as_posix(),
        "provider_submissions": 0,
        "paid_calls": 0,
    }


def prepare_coffee_table_execution_manifest(
    project_root: Path,
    *,
    parent_plan: Path,
    parent_plan_sha256: str,
    confirm_owner_authorized_manifest_preparation: bool,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Freeze the exact four-request Coffee Table contract without constructing providers."""

    root = project_root.resolve()
    if not confirm_owner_authorized_manifest_preparation:
        raise CampaignError(
            "Coffee Table execution-manifest preparation requires explicit Owner authorization"
        )
    if parent_plan_sha256 != COFFEE_TABLE_PARENT_SHA256:
        raise CampaignError("Coffee Table parent plan SHA-256 is not the approved identity")
    expected_path = (root / COFFEE_TABLE_PARENT_PLAN).resolve()
    supplied_path = parent_plan if parent_plan.is_absolute() else root / parent_plan
    if supplied_path.is_symlink() or supplied_path.resolve() != expected_path:
        raise CampaignError("Coffee Table parent plan path is not the approved identity")
    if not expected_path.is_file() or expected_path.is_symlink():
        raise CampaignError("Coffee Table parent plan is missing or is not a regular file")
    if sha256_file(expected_path) != COFFEE_TABLE_PARENT_SHA256:
        raise CampaignError("Coffee Table parent plan hash drift")
    try:
        plan = json.loads(expected_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignError("Coffee Table parent plan is unreadable") from exc

    goal2 = preflight_goal2(root)
    _validate_coffee_table_authority(plan, goal2, root)
    _validate_v1_rejection(root)
    tasks = _coffee_table_execution_tasks(root)
    assembly = _coffee_table_assembly(plan)

    timestamp = (created_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run_id = timestamp.strftime("COFFEE-TABLE-EXEC-%Y%m%d-%H%M%S-%f")
    directory = root / "outputs/campaign-execution-manifests" / run_id
    manifest_path = directory / "execution-manifest-v2.json"
    payload: dict[str, Any] = {
        "schema_version": "candidate16-coffee-table-execution-manifest/v2",
        "status": COFFEE_TABLE_STATUS,
        "run_id": run_id,
        "created_at": timestamp.isoformat(),
        "parent_plan": {
            "path": COFFEE_TABLE_PARENT_PLAN.as_posix(),
            "sha256": COFFEE_TABLE_PARENT_SHA256,
            "run_id": plan["run_id"],
            "schema_version": plan["schema_version"],
            "status": plan["status"],
        },
        "supersedes": {
            "manifest_path": COFFEE_TABLE_V1_MANIFEST.as_posix(),
            "manifest_sha256": COFFEE_TABLE_V1_SHA256,
            "owner_review_path": COFFEE_TABLE_V1_REVIEW.as_posix(),
            "owner_review_sha256": COFFEE_TABLE_V1_REVIEW_SHA256,
            "decision": "REJECT_FOR_LIVE",
            "reason_code": "MATERIAL_CONTINUITY_RISK",
        },
        "authority": {
            "character_id": plan["character"]["character_id"],
            "display_name": plan["character"]["display_name"],
            "keyframe_set_id": plan["keyframe_binding"]["set_id"],
            "keyframe_set_sha256": plan["keyframe_binding"]["set_manifest_sha256"],
            "v7_winner": plan["v7_binding"]["selected_candidate_id"],
            "product_sku": plan["product"]["sku"],
        },
        "execution": {
            "provider": "runway",
            "model": "gen4_turbo",
            "api_version": "2024-11-06",
            "task_count": 4,
            "max_tasks": 4,
            "duration_seconds_per_task": 5,
            "generated_seconds": 20,
            "max_runway_credits": 100,
            "max_provider_cost_usd": 1.0,
            "concurrency": 1,
            "automatic_paid_retries": 0,
            "automatic_replacement_tasks": 0,
            "failure_policy": "STOP_ON_FIRST_UNSUCCESSFUL_PROVIDER_TASK",
            "master_aspect_ratio": "16:9",
            "provider_ratio": "1280:720",
            "live_authorized": False,
        },
        "execution_dependencies": [
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
        ],
        "tasks": tasks,
        "assembly": assembly,
        "delivery": {
            "master": {"aspect_ratio": "16:9", "duration_seconds": 20},
            "1:1": {"mode": "GUARDED_LOCAL_REFRAME_ONLY"},
            "9:16": {"mode": "GUARDED_LOCAL_REFRAME_ONLY"},
            "native_ratio_regeneration": "NOT_AUTHORIZED",
        },
        "prohibited": [
            "heygen",
            "tts",
            "dialogue",
            "lip_sync",
            "native_ratio_generation",
            "fifth_provider_task",
            "automatic_paid_retry",
            "automatic_replacement",
            "automatic_approval",
        ],
        "review": {
            "reviewer": "",
            "decision": "",
            "notes": "",
            "live_authorized": False,
        },
        "owner_review_focus": [
            "TASK-01 to TASK-02 body and room continuity across independent approved keyframes",
            "TASK-03 product-only geometry and optical-push stability",
            "TASK-02 terminal frame proves glass on table and empty hands before TASK-04",
            "TASK-04 controlled sit feasibility and identity/body stability",
        ],
        "provider_submissions": 0,
        "provider_task_ids": 0,
        "http_requests": 0,
        "paid_calls": 0,
    }
    try:
        directory.mkdir(parents=True, exist_ok=False)
        _write_json_exclusive(manifest_path, payload)
    except FileExistsError as exc:
        raise CampaignError(f"Coffee Table execution manifest already exists: {run_id}") from exc
    except Exception:
        if manifest_path.exists():
            manifest_path.unlink()
        if directory.exists():
            directory.rmdir()
        raise

    manifest_sha256 = sha256_file(manifest_path)
    return {
        "status": COFFEE_TABLE_STATUS,
        "parent_plan_sha256": COFFEE_TABLE_PARENT_SHA256,
        "execution_manifest_path": manifest_path.relative_to(root).as_posix(),
        "execution_manifest_sha256": manifest_sha256,
        "tasks": [
            {
                "task_id": task["task_id"],
                "source_type": task["source"]["source_type"],
                "source_identity": (
                    task["source"].get("candidate_id")
                    or task["source"].get("product_reference_id")
                    or task["source"].get("source_task_id")
                ),
                "storyboard_beats": task["storyboard_beats"],
            }
            for task in tasks
        ],
        "assembly": {
            "master_duration_seconds": assembly["master_duration_seconds"],
            "segment_count": len(assembly["segments"]),
            "terminal_frame_hold_seconds": 2,
        },
        "provider_submissions": 0,
        "provider_task_ids": 0,
        "http_requests": 0,
        "paid_calls": 0,
    }


def _validate_coffee_table_authority(
    plan: Mapping[str, Any], goal2: Mapping[str, Any], root: Path
) -> None:
    expected_storyboard = [
        {
            "shot": number,
            "time": f"0:{start:02d}-0:{end:02d}",
            "duration_seconds": end - start,
            "beat": beat,
        }
        for number, start, end, beat in COFFEE_TABLE_STORYBOARD
    ]
    required = (
        plan.get("schema_version") == "candidate16-coffee-table-preview/v1"
        and plan.get("status") == "READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION"
        and plan.get("mode") == "DRY_RUN"
        and plan.get("run_id") == "COFFEE-TABLE-DRY-20260821-071433-640204"
        and plan.get("storyboard") == expected_storyboard
        and plan.get("product", {}).get("sku") == "IN3725"
        and plan.get("character", {}).get("character_id") == "character-20260821-001"
        and plan.get("character", {}).get("display_name") == "Candidate 16"
        and plan.get("v7_binding", {}).get("selected_candidate_id")
        == "v7-b-natural-micro-motion"
        and plan.get("semantics")
        == {
            "motion_only": True,
            "talking": False,
            "dialogue": False,
            "tts": False,
            "lip_sync": False,
            "heygen": False,
        }
        and plan.get("provider_submissions") == 0
        and plan.get("paid_calls") == 0
    )
    execution = plan.get("live_execution_plan", {})
    required = required and all(
        (
            execution.get("provider") == "runway",
            execution.get("model") == "gen4_turbo",
            execution.get("task_count") == 4,
            execution.get("duration_seconds_per_task") == 5,
            execution.get("generated_seconds") == 20,
            execution.get("max_runway_credits") == 100,
            execution.get("max_provider_cost_usd") == 1.0,
            execution.get("concurrency") == 1,
            execution.get("automatic_replacement_tasks") == 0,
            plan.get("automatic_paid_retries") == 0,
        )
    )
    if not required:
        raise CampaignError("Coffee Table parent plan semantics drift")
    if goal2.get("status") != "GOAL2_READY":
        raise CampaignError(str(goal2.get("status") or "BLOCKED_GOAL2_PREFLIGHT"))
    if (
        goal2.get("active_character") != plan["character"]["character_id"]
        or goal2.get("set_id") != plan["keyframe_binding"]["set_id"]
        or goal2.get("set_manifest_sha256")
        != plan["keyframe_binding"]["set_manifest_sha256"]
        or goal2.get("v7", {}).get("selected_candidate_id")
        != "v7-b-natural-micro-motion"
    ):
        raise CampaignError("Coffee Table current Goal 2 authority drift")
    expected_ids = {"K1": "K1-V2-002", "K2": "K2-002", "K3": "K3-V2-002"}
    plan_members = plan["keyframe_binding"]["members"]
    goal_members = goal2.get("members", {})
    for role, candidate_id in expected_ids.items():
        member = plan_members.get(role, {})
        if (
            member.get("candidate_id") != candidate_id
            or member.get("sha256") != COFFEE_TABLE_KEYFRAME_SHA256[role]
            or goal_members.get(role, {}).get("candidate_id") != candidate_id
            or goal_members.get(role, {}).get("sha256") != member.get("sha256")
        ):
            raise CampaignError(f"Coffee Table {role} authority drift")
        relative = Path(str(member.get("approved_path") or ""))
        source = (root / relative).resolve()
        approved_root = (root / "assets/approved_keyframes").resolve()
        if (
            not relative.as_posix().startswith("assets/approved_keyframes/")
            or not source.is_relative_to(approved_root)
            or not source.is_file()
            or source.is_symlink()
            or sha256_file(source) != member.get("sha256")
        ):
            raise CampaignError(f"Coffee Table {role} approved keyframe hash drift")


def _validate_v1_rejection(root: Path) -> None:
    manifest = root / COFFEE_TABLE_V1_MANIFEST
    review = root / COFFEE_TABLE_V1_REVIEW
    if (
        not manifest.is_file()
        or manifest.is_symlink()
        or sha256_file(manifest) != COFFEE_TABLE_V1_SHA256
    ):
        raise CampaignError("Coffee Table V1 manifest rejection target hash drift")
    if (
        not review.is_file()
        or review.is_symlink()
        or sha256_file(review) != COFFEE_TABLE_V1_REVIEW_SHA256
    ):
        raise CampaignError("Coffee Table V1 Owner review hash drift")
    try:
        decision = json.loads(review.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignError("Coffee Table V1 Owner review is unreadable") from exc
    if (
        decision.get("manifest_sha256") != COFFEE_TABLE_V1_SHA256
        or decision.get("decision") != "REJECT_FOR_LIVE"
        or decision.get("reason_code") != "MATERIAL_CONTINUITY_RISK"
        or decision.get("live_authorized") is not False
    ):
        raise CampaignError("Coffee Table V1 Owner rejection semantics drift")


def _coffee_table_execution_tasks(root: Path) -> list[dict[str, Any]]:
    prompt_evidence = [
        _coffee_table_prompt_evidence(root, path, digest)
        for path, digest in COFFEE_TABLE_PROMPTS
    ]
    k1_path = "assets/approved_keyframes/K1-V2-002.png"
    k3_path = "assets/approved_keyframes/K3-V2-002.png"
    product_path = COFFEE_TABLE_PRODUCT_SOURCE.as_posix()
    for role, relative in (("K1", k1_path), ("K3", k3_path)):
        if sha256_file(root / relative) != COFFEE_TABLE_KEYFRAME_SHA256[role]:
            raise CampaignError(f"Coffee Table {role} approved keyframe hash drift")
    product_source = root / COFFEE_TABLE_PRODUCT_SOURCE
    if (
        not product_source.is_file()
        or product_source.is_symlink()
        or sha256_file(product_source) != COFFEE_TABLE_PRODUCT_SHA256
    ):
        raise CampaignError("Coffee Table PDP product-only source hash drift")

    task_04_source = {
        "source_type": "UPSTREAM_TASK_FRAME",
        "source_task_id": "TASK-02",
        "required_source_task_status": "SUCCEEDED",
        "source_artifact_filename": "TASK-02.mp4",
        "expected_source_task_sha256": "RUNTIME_BOUND",
        "frame_selector": "LAST_VALID_FRAME",
        "frame_count": {
            "tool": "ffprobe",
            "command_argv_template": [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-count_frames", "-show_entries", "stream=nb_read_frames",
                "-of", "default=nokey=1:noprint_wrappers=1", "{task_02_mp4_path}",
            ],
            "validation": "positive integer frame_count",
            "selected_zero_based_frame_index": "frame_count - 1",
        },
        "extraction": {
            "tool": "ffmpeg",
            "command_argv_template": [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-i", "{task_02_mp4_path}", "-vf",
                "select=eq(n\\,{last_valid_frame_index})", "-frames:v", "1",
                "-c:v", "png", "-n", "{extracted_frame_path}",
            ],
            "output_filename": "TASK-02-last-valid-frame.png",
            "output_mime_type": "image/png",
            "provider_calls": 0,
        },
        "extracted_frame_sha256": "RUNTIME_BOUND",
        "runtime_evidence_path_template": (
            "runs/{live_run_id}/task-04-source-lineage.json"
        ),
        "submission_gate": [
            "source task has durable provider task ID and SUCCEEDED status",
            "downloaded MP4 SHA-256 is recorded and reverified",
            "frame count is a positive integer",
            "exact last decoded frame is extracted locally",
            "extracted PNG validates and its SHA-256 is recorded",
        ],
    }
    task_sources = (
        {
            "source_type": "APPROVED_KEYFRAME",
            "role": "K1",
            "candidate_id": "K1-V2-002",
            "path": k1_path,
            "sha256": COFFEE_TABLE_KEYFRAME_SHA256["K1"],
        },
        {
            "source_type": "APPROVED_KEYFRAME",
            "role": "K3",
            "candidate_id": "K3-V2-002",
            "path": k3_path,
            "sha256": COFFEE_TABLE_KEYFRAME_SHA256["K3"],
        },
        {
            "source_type": "STATIC_PRODUCT_REFERENCE",
            "role": "PRODUCT_ONLY",
            "product_reference_id": "IN3725-PDP-02",
            "path": product_path,
            "sha256": COFFEE_TABLE_PRODUCT_SHA256,
            "mime_type": "image/jpeg",
            "pixel_dimensions": "1280x1280",
            "contains_candidate16": False,
            "contains_wine_glass": False,
        },
        task_04_source,
    )
    task_definitions = (
        ("TASK-01", "ESTABLISH_AND_WALK_START", (1, 2), 0, 5),
        ("TASK-02", "WALK_COMPLETE_AND_GLASS_PLACE", (2, 3), 0, 5),
        ("TASK-03", "COFFEE_TABLE_PRODUCT_DETAIL", (4,), 0, 3),
        ("TASK-04", "CONTROLLED_SIT_AND_HERO", (5, 6), 0, 5),
    )
    tasks: list[dict[str, Any]] = []
    for definition, source, prompt in zip(
        task_definitions, task_sources, prompt_evidence, strict=True
    ):
        task_id, purpose, beats, usable_start, usable_end = definition
        input_path = source.get("path") or "{extracted_frame_path}"
        input_sha256 = source.get("sha256") or "RUNTIME_BOUND"
        tasks.append(
            {
                "task_id": task_id,
                "semantic_purpose": purpose,
                "storyboard_beats": list(beats),
                "source": source,
                "prompt": prompt,
                "request": {
                    "provider": "runway",
                    "model": "gen4_turbo",
                    "api_version": "2024-11-06",
                    "input_image_path": input_path,
                    "input_image_sha256": input_sha256,
                    "ratio": "1280:720",
                    "aspect_ratio": "16:9",
                    "duration_seconds": 5,
                    "seed": None,
                    "output_format": "mp4",
                    "submission_retries": 0,
                    "replacement_tasks": 0,
                },
                "expected_output_filename": f"{task_id}.mp4",
                "expected_usable_interval_seconds": {
                    "start": usable_start,
                    "end": usable_end,
                },
                "projected_runway_credits": 25,
                "projected_cost_usd": 0.25,
            }
        )
    return tasks


def _coffee_table_prompt_evidence(
    root: Path, relative: str, expected_sha256: str
) -> dict[str, Any]:
    prompt = root / relative
    if not prompt.is_file() or prompt.is_symlink():
        raise CampaignError(f"Coffee Table prompt is missing: {relative}")
    text = prompt.read_text(encoding="utf-8")
    units = len(text.encode("utf-16-le")) // 2
    if not text.strip() or units > 1000 or sha256_file(prompt) != expected_sha256:
        raise CampaignError(f"Coffee Table prompt is invalid: {relative}")
    return {
        "path": relative,
        "sha256": expected_sha256,
        "utf16_code_units": units,
        "text": text,
    }


def _coffee_table_assembly(plan: Mapping[str, Any]) -> dict[str, Any]:
    beats = {item["shot"]: item["beat"] for item in plan["storyboard"]}
    segments = [
        _assembly_segment("SEG-01", 1, beats[1], "TASK-01", 0, 3, 0, 3, "TRIM"),
        _assembly_segment("SEG-02", 2, beats[2], "TASK-01", 3, 5, 3, 5, "TRIM_PART_1"),
        _assembly_segment("SEG-03", 2, beats[2], "TASK-02", 0, 2, 5, 7, "TRIM_PART_2"),
        _assembly_segment("SEG-04", 3, beats[3], "TASK-02", 2, 5, 7, 10, "TRIM"),
        _assembly_segment("SEG-05", 4, beats[4], "TASK-03", 0, 3, 10, 13, "TRIM"),
        _assembly_segment("SEG-06", 5, beats[5], "TASK-04", 0, 4, 13, 17, "TRIM"),
        _assembly_segment("SEG-07", 6, beats[6], "TASK-04", 4, 5, 17, 18, "TRIM"),
        {
            "segment_id": "SEG-08",
            "storyboard_beat": 6,
            "beat": beats[6],
            "source_task_id": "TASK-04",
            "source": "TERMINAL_FRAME",
            "frame_selector": "LAST_VALID_FRAME",
            "master_interval_seconds": {"start": 18, "end": 20},
            "operation": "LOCAL_TERMINAL_FRAME_HOLD",
        },
    ]
    return {
        "master_aspect_ratio": "16:9",
        "master_duration_seconds": 20,
        "segments": segments,
        "generated_source_seconds": 20,
        "used_motion_seconds": 18,
        "local_terminal_frame_hold_seconds": 2,
        "task_03_discarded_interval_seconds": {"start": 3, "end": 5},
        "native_generation_required": False,
    }


def _assembly_segment(
    segment_id: str,
    beat_number: int,
    beat: str,
    task_id: str,
    source_start: int,
    source_end: int,
    master_start: int,
    master_end: int,
    operation: str,
) -> dict[str, Any]:
    return {
        "segment_id": segment_id,
        "storyboard_beat": beat_number,
        "beat": beat,
        "source_task_id": task_id,
        "source_interval_seconds": {"start": source_start, "end": source_end},
        "master_interval_seconds": {"start": master_start, "end": master_end},
        "operation": operation,
    }


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
