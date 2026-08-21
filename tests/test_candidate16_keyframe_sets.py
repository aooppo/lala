from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from PIL import Image

from lala_workflow.hashing import sha256_file
from lala_workflow.video.keyframe_sets import (
    REVIEW_FIELDS,
    ROLE_REQUIRED_FIELDS,
    KeyframeSetError,
    bind_goal2,
    build_keyframe_set,
    preflight_goal2,
    promote_reviewed_candidate,
    publish_keyframe_set,
    validate_review_package,
)


SELECTED = {
    "pilot_home_context": "K1-V2-002",
    "pilot_talking_medium_closeup": "K2-002",
    "pilot_product_present": "K3-V2-002",
}


def _write_image(path: Path, color: tuple[int, int, int]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (48, 64), color).save(path, format="PNG")
    return sha256_file(path)


def _fixture(root: Path, *, v7_matches: bool = False) -> Path:
    package = root / "outputs/reviews/candidate16-keyframes-v2"
    candidates: dict[str, dict[str, str]] = {}
    definitions = (
        ("K1-V2-001", "pilot_home_context", "K1/K1-V2-001.png"),
        ("K1-V2-002", "pilot_home_context", "K1/K1-V2-002.png"),
        ("K1-V2-003", "pilot_home_context", "K1/K1-V2-003.png"),
        ("K2-002", "pilot_talking_medium_closeup", "K2/K2-002.png"),
        ("K3-V2-001", "pilot_product_present", "K3/K3-V2-001.png"),
        ("K3-V2-002", "pilot_product_present", "K3/K3-V2-002.png"),
        ("K3-V2-003", "pilot_product_present", "K3/K3-V2-003.png"),
    )
    for index, (candidate_id, role, relative) in enumerate(definitions, 1):
        candidates[candidate_id] = {
            "candidate_id": candidate_id,
            "role": role,
            "file": relative,
            "sha256": _write_image(package / relative, (index * 20, 10, 30)),
            "run_id": f"run-{index}",
            "provider_task_id": f"task-{index}",
        }
    manifest = {
        "schema_version": "candidate16-keyframe-review-package/v2",
        "status": "READY_FOR_OWNER_KEYFRAME_REVIEW",
        "character": {
            "character_id": "character-20260821-001",
            "display_name": "Candidate 16",
            "profile_version": 6,
            "profile_sha256": "a" * 64,
            "registry_revision": 5,
            "active": True,
        },
        "provider": "runway",
        "model": "gen4_image",
        "roles": {
            "K1": {"role": "pilot_home_context", "candidates": [candidates[key] for key in ("K1-V2-001", "K1-V2-002", "K1-V2-003")]},
            "K2": {**candidates["K2-002"], "new_submissions": 0},
            "K3": {"role": "pilot_product_present", "candidates": [candidates[key] for key in ("K3-V2-001", "K3-V2-002", "K3-V2-003")]},
        },
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rows = []
    for candidate_id, role, relative in definitions:
        row = {field: "" for field in REVIEW_FIELDS}
        row.update(
            {
                "schema_version": "candidate16-keyframe-review/v2",
                "candidate_id": candidate_id,
                "role": role,
                "candidate_file": relative,
                "candidate_sha256": candidates[candidate_id]["sha256"],
            }
        )
        if candidate_id == SELECTED[role]:
            for field in ROLE_REQUIRED_FIELDS[role]:
                row[field] = "PASS"
            row["reviewer"] = "Project owner (explicit human decision)"
            row["reviewed_at"] = "2026-08-21T14:00:00+08:00"
            row["notes"] = "Owner selected the exact Candidate 16 role authority."
        rows.append(row)
    with (package / "review.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    profile = root / "configs/characters/profiles/character-20260821-001-v006.yaml"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text("character_id: character-20260821-001\nstatus: ACTIVE\n", encoding="utf-8")
    registry = {
        "revision": 5,
        "active_character": "character-20260821-001",
        "characters": {
            "character-20260821-001": {
                "display_name": "Candidate 16",
                "status": "ACTIVE",
                "profile": profile.relative_to(root).as_posix(),
                "profile_sha256": "a" * 64,
            }
        },
    }
    (root / "configs/characters/registry.yaml").write_text(yaml.safe_dump(registry), encoding="utf-8")
    (root / "configs/keyframe-manifest.yaml").write_text(
        yaml.safe_dump({"project": "lady-lala", "status": "approved", "keyframes": {}}, sort_keys=False),
        encoding="utf-8",
    )
    v7 = root / "runs/LALA-VIDEO-20260820-075843-MOTION-V7-001/request.json"
    v7.parent.mkdir(parents=True, exist_ok=True)
    k1_sha = candidates["K1-V2-002"]["sha256"]
    v7.write_text(
        json.dumps({"action": "motion_v7_live", "run_id": v7.parent.name, "requests": [{"image_sha256": k1_sha if v7_matches else "b" * 64}]}),
        encoding="utf-8",
    )
    return package


def _promote_all(root: Path, package: Path) -> None:
    for candidate_id in ("K1-V2-002", "K2-002", "K3-V2-002"):
        result = promote_reviewed_candidate(root, package=package, candidate_id=candidate_id)
        assert result["exact_byte_match"] is True


def test_review_package_requires_exact_one_selection_and_applicable_fields(tmp_path: Path) -> None:
    package = _fixture(tmp_path)
    result = validate_review_package(tmp_path, package)
    assert result["selections"] == SELECTED
    assert result["selected_count"] == 3
    assert result["provider_submissions"] == result["paid_calls"] == 0

    with (package / "review.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["face_identity_pass"] = "PASS"
    with (package / "review.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS); writer.writeheader(); writer.writerows(rows)
    with pytest.raises(KeyframeSetError, match="required role QA"):
        validate_review_package(tmp_path, package)


def test_review_package_rejects_hash_drift_naive_time_and_inapplicable_pass(tmp_path: Path) -> None:
    package = _fixture(tmp_path)
    (package / "K1/K1-V2-002.png").write_bytes(b"drift")
    with pytest.raises(KeyframeSetError, match="BLOCKED_KEYFRAME_INTEGRITY"):
        validate_review_package(tmp_path, package)

    package = _fixture(tmp_path / "time")
    review = package / "review.csv"
    with review.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    next(row for row in rows if row["candidate_id"] == "K2-002")["reviewed_at"] = "2026-08-21T14:00:00"
    with review.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS); writer.writeheader(); writer.writerows(rows)
    with pytest.raises(KeyframeSetError, match="timezone"):
        validate_review_package(tmp_path / "time", package)

    package = _fixture(tmp_path / "applicable")
    review = package / "review.csv"
    with review.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    next(row for row in rows if row["candidate_id"] == "K2-002")["wine_glass_pass"] = "PASS"
    with review.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS); writer.writeheader(); writer.writerows(rows)
    with pytest.raises(KeyframeSetError, match="not applicable"):
        validate_review_package(tmp_path / "applicable", package)


def test_exact_byte_promotions_build_publish_and_bind(tmp_path: Path) -> None:
    package = _fixture(tmp_path, v7_matches=True)
    _promote_all(tmp_path, package)
    manifest = yaml.safe_load((tmp_path / "configs/keyframe-manifest.yaml").read_text())
    for candidate_id in SELECTED.values():
        item = manifest["keyframes"][candidate_id]
        assert sha256_file(tmp_path / item["path"]) == item["sha256"]

    built = build_keyframe_set(tmp_path, set_id="candidate16-keyframe-set-v1", review_package=package)
    assert built["member_count"] == 3
    published = publish_keyframe_set(tmp_path, set_id=built["set_id"])
    assert published["status"] == "PUBLISHED"
    assert published["registry_revision"] == 1
    bound = bind_goal2(tmp_path, set_id=built["set_id"])
    assert bound["active_character"] == "character-20260821-001"
    ready = preflight_goal2(tmp_path)
    assert ready["status"] == "GOAL2_READY"
    assert ready["provider_submissions"] == ready["paid_calls"] == 0


def test_set_and_publish_are_collision_safe_and_v7_is_character_bound(tmp_path: Path) -> None:
    package = _fixture(tmp_path)
    _promote_all(tmp_path, package)
    built = build_keyframe_set(tmp_path, set_id="candidate16-keyframe-set-v1", review_package=package)
    with pytest.raises(KeyframeSetError, match="already exists"):
        build_keyframe_set(tmp_path, set_id="candidate16-keyframe-set-v1", review_package=package)
    publish_keyframe_set(tmp_path, set_id=built["set_id"])
    with pytest.raises(KeyframeSetError, match="already published"):
        publish_keyframe_set(tmp_path, set_id=built["set_id"])
    bind_goal2(tmp_path, set_id=built["set_id"])
    blocked = preflight_goal2(tmp_path)
    assert blocked["status"] == "READY_FOR_OWNER_CANDIDATE16_V7_EXECUTION"
    assert blocked["v7"]["methodology_reusable"] is True
    assert blocked["v7"]["estimated_runway_credits"] == 75


def test_promotion_rejects_duplicate_and_active_character_change(tmp_path: Path) -> None:
    package = _fixture(tmp_path)
    promote_reviewed_candidate(tmp_path, package=package, candidate_id="K1-V2-002")
    with pytest.raises(KeyframeSetError, match="already exists"):
        promote_reviewed_candidate(tmp_path, package=package, candidate_id="K1-V2-002")
    registry_path = tmp_path / "configs/characters/registry.yaml"
    registry = yaml.safe_load(registry_path.read_text())
    registry["active_character"] = "lala-v1"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    with pytest.raises(KeyframeSetError, match="active character"):
        promote_reviewed_candidate(tmp_path, package=package, candidate_id="K2-002")
