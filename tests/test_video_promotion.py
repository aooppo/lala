from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from lala_workflow.hashing import sha256_file
from lala_workflow.video.assembly import assemble_video
from lala_workflow.video.promotion import PromotionError, promote_video
from lala_workflow.video.storage import QA_FIELDS
from tests.test_video_selection import generated_source_run, write_selection


def assembly_run(root: Path, video: Path):
    source = generated_source_run(root, video)
    selection = write_selection(root, source)
    return assemble_video(root, source.run_id, selection, final_edits=1)


def review_copy(root: Path, run_dir: Path) -> Path:
    target = root / "outputs/reviews" / f"{run_dir.name}-review.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run_dir / "review.csv", target)
    return target


def mark_ready(root: Path, run_dir: Path) -> tuple[str, Path]:
    review_path = review_copy(root, run_dir)
    with review_path.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    candidate = row["candidate"]
    row["mtl_review_ready"] = "true"
    row["reviewer"] = "Synthetic MTL reviewer"
    row["reviewed_at"] = "2026-08-19T14:00:00+08:00"
    with review_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    return candidate, review_path


def test_promotion_requires_review_and_copies_with_complete_provenance(
    video_project_root: Path, synthetic_video: Path
) -> None:
    assembly = assembly_run(video_project_root, synthetic_video)
    review_path = assembly.run_dir / "review.csv"
    candidate = next(csv.DictReader(review_path.open(newline="", encoding="utf-8")))["candidate"]
    blank_review = review_copy(video_project_root, assembly.run_dir)
    with pytest.raises(PromotionError, match="MTL readiness"):
        promote_video(
            video_project_root,
            assembly.run_id,
            candidate,
            review_file=blank_review,
        )
    candidate, reviewed_copy = mark_ready(video_project_root, assembly.run_dir)
    source_path = assembly.candidates[0].path
    source_before = source_path.read_bytes()
    review_before = review_path.read_bytes()
    record = promote_video(
        video_project_root,
        assembly.run_id,
        candidate,
        review_file=reviewed_copy,
    )
    assert record["approved_file"] == "lady-lala-product-page-approved-v1.mp4"
    approved = video_project_root / "outputs/approved_videos" / record["approved_file"]
    provenance = approved.with_suffix(".json")
    assert approved.read_bytes() == source_before
    assert source_path.read_bytes() == source_before
    assert review_path.read_bytes() == review_before
    payload = json.loads(provenance.read_text(encoding="utf-8"))
    assert payload["source_run_id"] == assembly.run_id
    assert payload["source_candidate"] == candidate
    assert payload["reviewer"] == "Synthetic MTL reviewer"
    assert payload["script"]["source"] == "MTL"
    assert payload["selected_shots"]
    assert payload["providers"]
    assert payload["review"]["sha256"] == sha256_file(reviewed_copy)

    with pytest.raises(PromotionError, match="already exists"):
        promote_video(
            video_project_root,
            assembly.run_id,
            candidate,
            review_file=reviewed_copy,
            approved_version=1,
        )


def test_approved_naming_allocates_next_version_without_overwrite(
    video_project_root: Path, synthetic_video: Path
) -> None:
    assembly = assembly_run(video_project_root, synthetic_video)
    candidate, reviewed_copy = mark_ready(video_project_root, assembly.run_dir)
    first = promote_video(
        video_project_root, assembly.run_id, candidate, review_file=reviewed_copy
    )
    second = promote_video(
        video_project_root, assembly.run_id, candidate, review_file=reviewed_copy
    )
    assert first["approved_file"].endswith("-v1.mp4")
    assert second["approved_file"].endswith("-v2.mp4")


def test_explicit_approved_version_must_be_the_next_monotonic_version(
    video_project_root: Path, synthetic_video: Path
) -> None:
    assembly = assembly_run(video_project_root, synthetic_video)
    candidate, reviewed_copy = mark_ready(video_project_root, assembly.run_dir)
    with pytest.raises(PromotionError, match="next monotonic"):
        promote_video(
            video_project_root,
            assembly.run_id,
            candidate,
            review_file=reviewed_copy,
            approved_version=2,
        )
    assert list((video_project_root / "outputs/approved_videos").glob("*.mp4")) == []


def test_incomplete_provenance_write_removes_media_and_partial_sidecar(
    video_project_root: Path,
    synthetic_video: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assembly = assembly_run(video_project_root, synthetic_video)
    candidate, reviewed_copy = mark_ready(video_project_root, assembly.run_dir)

    def fail_dump(*_args, **_kwargs):
        raise OSError("synthetic sidecar failure")

    monkeypatch.setattr("lala_workflow.video.promotion.json.dump", fail_dump)
    with pytest.raises(OSError, match="synthetic sidecar"):
        promote_video(
            video_project_root,
            assembly.run_id,
            candidate,
            review_file=reviewed_copy,
        )
    assert list((video_project_root / "outputs/approved_videos").iterdir()) == []
