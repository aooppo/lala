from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest

from lala_workflow.video.review import ReviewError, load_external_review_row, load_review_row
from lala_workflow.video.runner import VideoRunOptions, run_talking_smoke
from lala_workflow.video.storage import QA_FIELDS
from tests.fakes_video import FakeTalkingProvider


def smoke_with_blank_review(root: Path, video: Path):
    return run_talking_smoke(
        root,
        VideoRunOptions(preset="tooltip", action="talking_smoke", live=True),
        provider=FakeTalkingProvider(video),
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_LIVE_SMOKE_TEST": "true",
            "HEYGEN_API_KEY": "test-key",
        },
    )


def test_new_review_has_exact_header_one_row_and_blank_human_fields(
    video_project_root: Path, synthetic_video: Path
) -> None:
    outcome = smoke_with_blank_review(video_project_root, synthetic_video)
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
    assert reader.fieldnames == list(QA_FIELDS)
    assert len(rows) == 1
    assert all(rows[0][field] == "" for field in QA_FIELDS[4:])


def test_review_parser_is_read_only_and_requires_explicit_readiness(
    video_project_root: Path, synthetic_video: Path
) -> None:
    outcome = smoke_with_blank_review(video_project_root, synthetic_video)
    path = outcome.run_dir / "review.csv"
    candidate = next(csv.DictReader(path.open(newline="", encoding="utf-8")))["candidate"]
    before = path.read_bytes()
    with pytest.raises(ReviewError, match="MTL readiness"):
        load_review_row(outcome.run_dir, candidate, require_ready=True)
    assert path.read_bytes() == before


def test_review_parser_rejects_duplicate_candidate_rows(
    video_project_root: Path, synthetic_video: Path
) -> None:
    outcome = smoke_with_blank_review(video_project_root, synthetic_video)
    path = outcome.run_dir / "review.csv"
    content = path.read_text(encoding="utf-8")
    path.write_text(content + content.splitlines()[1] + "\n", encoding="utf-8")
    candidate = content.splitlines()[1].split(",")[3]
    with pytest.raises(ReviewError, match="exactly one"):
        load_review_row(outcome.run_dir, candidate)


def test_external_review_preserves_blank_run_evidence_and_matches_candidate_provenance(
    video_project_root: Path, synthetic_video: Path
) -> None:
    outcome = smoke_with_blank_review(video_project_root, synthetic_video)
    run_review = outcome.run_dir / "review.csv"
    before = run_review.read_bytes()
    reviewed = video_project_root / "outputs/reviews/smoke-review.csv"
    reviewed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run_review, reviewed)
    with reviewed.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    candidate = row["candidate"]
    row["mtl_review_ready"] = "true"
    row["reviewer"] = "Synthetic reviewer"
    row["reviewed_at"] = "2026-08-19T12:30:00+08:00"
    with reviewed.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    loaded, evidence = load_external_review_row(
        video_project_root, outcome.run_dir, candidate, reviewed, require_ready=True
    )
    assert loaded["reviewer"] == "Synthetic reviewer"
    assert evidence["path"] == "outputs/reviews/smoke-review.csv"
    assert run_review.read_bytes() == before


def test_external_review_rejects_a_rewritten_run_qa_sheet(
    video_project_root: Path, synthetic_video: Path
) -> None:
    outcome = smoke_with_blank_review(video_project_root, synthetic_video)
    run_review = outcome.run_dir / "review.csv"
    with run_review.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    candidate = row["candidate"]
    row["reviewer"] = "must not edit run evidence"
    with run_review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    reviewed = video_project_root / "outputs/reviews/review.csv"
    reviewed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run_review, reviewed)
    with pytest.raises(ReviewError, match="must remain blank"):
        load_external_review_row(
            video_project_root, outcome.run_dir, candidate, reviewed, require_ready=True
        )
