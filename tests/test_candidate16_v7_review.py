from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from lala_workflow.hashing import sha256_file
from lala_workflow.video.candidate16_v7 import (
    Candidate16V7Error,
    load_candidate16_v7_registration,
    register_candidate16_v7_review,
)
from lala_workflow.video.keyframe_sets import _classify_v7
from lala_workflow.video.storage import QA_FIELDS


IDS = (
    "v7-a-stability-first",
    "v7-b-natural-micro-motion",
    "v7-c-controlled-upper-bound",
)
PASS_FIELDS = (
    "visual_identity",
    "face_stability",
    "age_stability",
    "hair_stability",
    "body_proportions",
    "wardrobe",
    "jewelry",
    "mouth",
    "teeth",
    "eyes",
    "background",
    "motion",
    "technical_export",
)


def _json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _review(path: Path, run_id: str, *, reviewed: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for candidate_id in IDS:
        row = {field: "" for field in QA_FIELDS}
        row.update(
            {
                "run_id": run_id,
                "video_id": candidate_id,
                "preset": "motion-v7",
                "candidate": f"{candidate_id}.mp4",
            }
        )
        if reviewed:
            row["reviewer"] = "Project owner (explicit human decision)"
            row["reviewed_at"] = "2026-08-21T15:10:00+08:00"
            if candidate_id == IDS[1]:
                for field in PASS_FIELDS:
                    row[field] = "true"
                row["mtl_review_ready"] = "true"
                row["notes"] = "APPROVE v7-b-natural-micro-motion as Candidate 16 V7 winner."
            elif candidate_id == IDS[0]:
                row["mtl_review_ready"] = "false"
                row["notes"] = "NOT SELECTED — excessive subject position/scale movement for the stability baseline."
            else:
                row["mtl_review_ready"] = "false"
                row["notes"] = "NOT SELECTED — acceptable stability fallback, but B provides a better balance of natural micro-motion and framing stability."
        rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(root: Path) -> Path:
    parent = "LALA-VIDEO-20260821-063716-MOTION-V7-001"
    recovery = "LALA-VIDEO-20260821-064916-MOTION-V7-RECOVERY-001"
    keyframe = root / "assets/approved_keyframes/K1-V2-002.png"
    keyframe.parent.mkdir(parents=True, exist_ok=True)
    keyframe.write_bytes(b"candidate16-k1")
    keyframe_sha = sha256_file(keyframe)

    prompts = {}
    for candidate_id in IDS:
        prompt = root / f"prompts/{candidate_id}.txt"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text(candidate_id, encoding="utf-8")
        prompts[candidate_id] = (prompt.relative_to(root).as_posix(), sha256_file(prompt))

    combined = []
    manifest_media = []
    for index, candidate_id in enumerate(IDS):
        source_run = parent if index == 0 else recovery
        source = root / f"outputs/broll/{source_run}/{candidate_id}.mp4"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(f"media-{candidate_id}".encode())
        digest = sha256_file(source)
        task_id = f"task-{index + 1}"
        artifact = {
            "artifact_id": f"artifact-{candidate_id}",
            "video_id": f"artifact-{candidate_id}",
            "candidate": f"artifact-{candidate_id}.mp4",
            "path": source.relative_to(root).as_posix(),
            "sha256": digest,
            "provider_task_id": task_id,
        }
        combined.append(
            {
                "candidate_id": candidate_id,
                "provider_status": "SUCCEEDED",
                "provider_task_id": task_id,
                "prompt_path": prompts[candidate_id][0],
                "prompt_sha256": prompts[candidate_id][1],
                "evidence_source_run_id": source_run,
                "artifacts": [artifact],
            }
        )
        package_media = root / f"outputs/reviews/candidate16-v7/{candidate_id}.mp4"
        package_media.parent.mkdir(parents=True, exist_ok=True)
        package_media.write_bytes(source.read_bytes())
        manifest_media.append(
            {
                "candidate_id": candidate_id,
                "path": package_media.relative_to(root).as_posix(),
                "sha256": digest,
                "size_bytes": package_media.stat().st_size,
            }
        )

    requests = [
        {
            "shot_id": candidate_id,
            "image_sha256": keyframe_sha,
            "prompt_path": prompts[candidate_id][0],
            "prompt_sha256": prompts[candidate_id][1],
        }
        for candidate_id in IDS
    ]
    _json(root / f"runs/{parent}/request.json", {"action": "motion_v7_live", "run_id": parent, "requests": requests})
    _json(root / f"runs/{parent}/provider-results.json", {"status": "PARTIAL", "results": [combined[0], {"candidate_id": IDS[1]}, {"candidate_id": IDS[2]}]})
    _json(root / f"runs/{parent}/keyframe-hash.json", {"keyframe_id": "K1-V2-002", "sha256": keyframe_sha})
    _review(root / f"runs/{parent}/review.csv", parent, reviewed=False)

    _json(root / f"runs/{recovery}/request.json", {"action": "motion_v7_recovery", "run_id": recovery, "parent_run_id": parent, "requests": requests[1:]})
    _json(root / f"runs/{recovery}/provider-results.json", {"status": "SUCCEEDED", "parent_run_id": parent, "results": combined})
    _json(root / f"runs/{recovery}/keyframe-hash.json", {"keyframe_id": "K1-V2-002", "sha256": keyframe_sha})
    _review(root / f"runs/{recovery}/review.csv", recovery, reviewed=False)

    package = root / "outputs/reviews/candidate16-v7"
    _json(
        package / "manifest.json",
        {
            "character_id": "character-20260821-001",
            "keyframe_id": "K1-V2-002",
            "keyframe_sha256": keyframe_sha,
            "parent_run_id": parent,
            "recovery_run_id": recovery,
            "state": "READY_FOR_OWNER_CANDIDATE16_V7_REVIEW",
            "winner": None,
            "human_review_required": True,
            "coffee_table_executed": False,
            "media": manifest_media,
        },
    )
    _review(package / "review.csv", recovery, reviewed=True)
    return package


def test_registers_unique_v7_b_and_goal2_classification(tmp_path: Path) -> None:
    package = _fixture(tmp_path)
    result = register_candidate16_v7_review(tmp_path, package=package)
    assert result["status"] == "CANDIDATE16_V7_HUMAN_QA_PASS"
    assert result["winner"] == IDS[1]
    assert result["provider_submissions"] == result["paid_calls"] == 0

    loaded = load_candidate16_v7_registration(
        tmp_path, candidate16_k1_sha256=result["keyframe_sha256"]
    )
    assert loaded["selected_candidate_id"] == IDS[1]
    classified = _classify_v7(tmp_path, result["keyframe_sha256"])
    assert classified["status"] == "CANDIDATE16_V7_MATCH"
    assert classified["selected_candidate_id"] == IDS[1]


def test_registration_rejects_second_pass_and_media_drift_without_evidence(
    tmp_path: Path,
) -> None:
    package = _fixture(tmp_path)
    review = package / "review.csv"
    with review.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for field in PASS_FIELDS:
        rows[0][field] = "true"
    rows[0]["mtl_review_ready"] = "true"
    with review.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(Candidate16V7Error, match="exactly one|V7-B"):
        register_candidate16_v7_review(tmp_path, package=package)
    assert not (package / "registration.json").exists()

    package = _fixture(tmp_path / "drift")
    (package / f"{IDS[1]}.mp4").write_bytes(b"changed")
    with pytest.raises(Candidate16V7Error, match="media.*SHA-256"):
        register_candidate16_v7_review(tmp_path / "drift", package=package)
    assert not (package / "registration.json").exists()


def test_registration_is_collision_safe_and_revalidates_current_bytes(tmp_path: Path) -> None:
    package = _fixture(tmp_path)
    result = register_candidate16_v7_review(tmp_path, package=package)
    with pytest.raises(Candidate16V7Error, match="already exists"):
        register_candidate16_v7_review(tmp_path, package=package)
    selected = tmp_path / result["selected_media_path"]
    selected.write_bytes(b"mutated")
    with pytest.raises(Candidate16V7Error, match="media.*SHA-256"):
        load_candidate16_v7_registration(
            tmp_path, candidate16_k1_sha256=result["keyframe_sha256"]
        )


def test_registration_rejects_tampered_human_authority(tmp_path: Path) -> None:
    package = _fixture(tmp_path)
    result = register_candidate16_v7_review(tmp_path, package=package)
    registration = package / "registration.json"
    payload = json.loads(registration.read_text(encoding="utf-8"))
    payload["authority"] = "AUTOMATIC"
    payload["automatic_human_qa"] = True
    registration.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Candidate16V7Error, match="authority|automatic_human_qa"):
        load_candidate16_v7_registration(
            tmp_path, candidate16_k1_sha256=result["keyframe_sha256"]
        )
