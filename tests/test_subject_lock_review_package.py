from __future__ import annotations

import csv
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from lala_workflow.hashing import sha256_file
from lala_workflow.video.qa.review_package import (
    finalize_subject_lock_package,
    scan_review_package_secrets,
    verify_review_package,
)
from lala_workflow.video.reporting import build_video_report
from lala_workflow.video.runner import VideoRunOptions, run_motion_smoke
from lala_workflow.video.storage import QA_FIELDS
from tests.fakes_video import FakeMotionProvider


def _fixture(source: Path) -> Path:
    target = source.with_name("subject-lock-motion.mp4")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source), "-t", "5", "-vf", "scale=1280:720", "-c:v", "libx264", "-c:a", "aac", "-y", str(target)], check=True, capture_output=True)
    return target


def _package(video_project_root: Path, synthetic_video: Path):
    outcome = run_motion_smoke(
        video_project_root,
        VideoRunOptions(preset="motion", action="motion_smoke", live=True, keyframe_id="hero", max_runway_credits=25),
        provider=FakeMotionProvider(_fixture(synthetic_video)),
        environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "VIDEO_MOTION_LIVE_SMOKE_TEST": "true", "RUNWAYML_API_SECRET": "fixture-only"},
    )
    results = json.loads((outcome.run_dir / "provider-results.json").read_text())
    source_video = video_project_root / results["results"][0]["artifacts"][0]["path"]
    package = video_project_root / "outputs/review-packages" / "fixture-package"
    package.mkdir(parents=True)
    shutil.copyfile(source_video, package / "video.mp4")
    shutil.copyfile(outcome.run_dir / "review.csv", package / "review.csv")
    return outcome, package


def test_subject_lock_review_package_artifacts_and_sha256_manifest(video_project_root: Path, synthetic_video: Path) -> None:
    outcome, package = _package(video_project_root, synthetic_video)
    run_review_before = (outcome.run_dir / "review.csv").read_bytes()
    package_review_before = (package / "review.csv").read_bytes()
    result = finalize_subject_lock_package(video_project_root, outcome.run_id, package)
    assert result["provider_calls"] == 0
    assert result["human_review_modified"] is False
    for name in ("subject-lock.json", "subject-trajectory.csv", "subject-overlay.png"):
        assert (package / name).is_file()
        assert name in (package / "SHA256SUMS.txt").read_text()
    assert verify_review_package(package)["passed"] is True
    with zipfile.ZipFile(package.with_suffix(".zip")) as archive:
        names = archive.namelist()
    assert all(f"{package.name}/{name}" in names for name in ("subject-lock.json", "subject-trajectory.csv", "subject-overlay.png"))
    assert (outcome.run_dir / "review.csv").read_bytes() == run_review_before
    assert (package / "review.csv").read_bytes() == package_review_before
    with (package / "review.csv").open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    assert all(row[field] == "" for field in QA_FIELDS[4:])
    assert scan_review_package_secrets(package)["passed"] is True


def test_subject_lock_report_is_diagnostic_not_human_qa(video_project_root: Path, synthetic_video: Path) -> None:
    outcome, package = _package(video_project_root, synthetic_video)
    finalize_subject_lock_package(video_project_root, outcome.run_id, package)
    report = build_video_report(video_project_root, outcome.run_id)
    assert report["human_qa_status"] == "NOT_SET"
    assert report["subject_lock_diagnostic"]["human_qa_authority"] == "not_automatic"
    assert report["subject_lock_diagnostic"]["diagnostic_status"] in {"WITHIN_THRESHOLD", "OUTSIDE_THRESHOLD", "INSUFFICIENT_EVIDENCE"}
