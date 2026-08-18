import csv
import json
from pathlib import Path

import pytest
import yaml
from PIL import Image

from lala_workflow.hashing import sha256_file
from lala_workflow.reporting import REVIEW_FIELDS, promote_keyframe
from lala_workflow.storage import RunStorage


def make_reviewed_run(
    project_root: Path,
    *,
    ready: str = "true",
    reviewer: str = "MTL Reviewer",
    reviewed_at: str = "2026-08-18T22:00:00+08:00",
) -> tuple[str, Path]:
    storage = RunStorage(project_root)
    run = storage.create_run("runway", "baseline_identity")
    output_dir = project_root / "outputs" / run.run_id
    output_dir.mkdir(parents=True)
    source = output_dir / "output-001.png"
    Image.new("RGB", (20, 20), "red").save(source)
    relative = source.relative_to(project_root)
    storage.write_json(
        run,
        "result.json",
        {
            "run_id": run.run_id,
            "provider": "runway",
            "model": "gen4_image",
            "requests": [
                {"output_id": "output-001", "prompt": {"version": "v1"}, "seed": 42}
            ],
            "outputs": [
                {
                    "output_id": "output-001",
                    "provider_task_id": "task-1",
                    "file": relative.as_posix(),
                    "sha256": sha256_file(source),
                    "size_bytes": source.stat().st_size,
                }
            ],
        },
    )
    storage.write_yaml(
        run,
        "resolved-config.yaml",
        {"anchor_set_version": "1.0", "provider": "runway", "model": "gen4_image"},
    )
    row = {field: "" for field in REVIEW_FIELDS}
    row.update(
        {
            "run_id": run.run_id,
            "output_id": "output-001",
            "output_file": relative.as_posix(),
            "provider": "runway",
            "provider_task_id": "task-1",
            "model": "gen4_image",
            "seed": "42",
            "video_keyframe_ready": ready,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
        }
    )
    with (run.path / "review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    return run.run_id, source


def test_promotion_copies_source_and_records_complete_metadata(project_root: Path) -> None:
    run_id, source = make_reviewed_run(project_root)
    original_hash = sha256_file(source)

    record = promote_keyframe(project_root, run_id, "output-001")

    promoted = project_root / record["approved_keyframe"]
    metadata = promoted.with_suffix(promoted.suffix + ".json")
    assert source.is_file()
    assert sha256_file(source) == original_hash
    assert sha256_file(promoted) == original_hash
    assert metadata.is_file()
    assert json.loads(metadata.read_text()) == record
    assert record["source_run_id"] == run_id
    assert record["image_sha256"] == original_hash
    assert record["approved_anchor_version"] == "1.0"
    assert record["prompt_version"] == "v1"
    assert record["provider"] == "runway"
    assert record["model"] == "gen4_image"
    assert record["reviewer"] == "MTL Reviewer"
    assert record["approval_date"] == "2026-08-18T22:00:00+08:00"


@pytest.mark.parametrize(
    ("ready", "reviewer", "reviewed_at", "message"),
    [
        ("", "Reviewer", "2026-08-18T22:00:00+08:00", "not marked video-keyframe-ready"),
        ("true", "", "2026-08-18T22:00:00+08:00", "reviewer is required"),
        ("true", "Reviewer", "not-a-date", "reviewed_at must be ISO 8601"),
        ("true", "Reviewer", "2026-08-18T22:00:00", "timezone"),
    ],
)
def test_promotion_rejects_missing_human_approval(
    project_root: Path, ready: str, reviewer: str, reviewed_at: str, message: str
) -> None:
    run_id, _source = make_reviewed_run(
        project_root,
        ready=ready,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
    )

    with pytest.raises(ValueError, match=message):
        promote_keyframe(project_root, run_id, "output-001")


def test_promotion_rejects_hash_mismatch_and_collision(project_root: Path) -> None:
    run_id, source = make_reviewed_run(project_root)
    source.write_bytes(b"changed")

    with pytest.raises(ValueError, match="hash does not match"):
        promote_keyframe(project_root, run_id, "output-001")

    run_id, _source = make_reviewed_run(project_root)
    record = promote_keyframe(project_root, run_id, "output-001")
    assert (project_root / record["approved_keyframe"]).is_file()
    with pytest.raises(ValueError, match="already exists"):
        promote_keyframe(project_root, run_id, "output-001")
