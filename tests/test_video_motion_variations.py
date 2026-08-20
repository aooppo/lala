from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lala_workflow.video.runner import (
    VideoRunOptions,
    generate_motion_variations,
    preview_motion_variations,
    run_motion_smoke,
)
from lala_workflow.video.storage import QA_FIELDS, VIDEO_RUN_FILES
from lala_workflow.video.validation import ExternalInputBlocked
from tests.fakes_video import FakeMotionProvider


PASS_FIELDS = QA_FIELDS[4:18]


def _motion_fixture(source: Path) -> Path:
    target = source.with_name("motion-smoke-fixture.mp4")
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
            "-t", "5", "-vf", "scale=1280:720", "-c:v", "libx264",
            "-c:a", "aac", "-y", str(target),
        ],
        check=True,
        capture_output=True,
    )
    return target


def _passing_motion_smoke(root: Path, synthetic_video: Path) -> tuple[str, Path]:
    outcome = run_motion_smoke(
        root,
        VideoRunOptions(
            preset="motion",
            action="motion_smoke",
            live=True,
            keyframe_id="hero",
            max_runway_credits=25,
        ),
        provider=FakeMotionProvider(_motion_fixture(synthetic_video)),
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_MOTION_LIVE_SMOKE_TEST": "true",
            "RUNWAYML_API_SECRET": "test-secret",
        },
    )
    review = root / "outputs/reviews" / f"{outcome.run_id}-review.csv"
    review.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(outcome.run_dir / "review.csv", review)
    with review.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    for field in PASS_FIELDS:
        row[field] = "true"
    row.update(
        {
            "mtl_review_ready": "true",
            "technical_export": "true",
            "reviewer": "Motion reviewer",
            "reviewed_at": "2026-08-20T12:00:00+08:00",
        }
    )
    with review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    return outcome.run_id, review


def test_motion_smoke_keeps_strict_bounds(video_project_root: Path, synthetic_video: Path) -> None:
    with pytest.raises(ExternalInputBlocked, match="gen4_turbo"):
        run_motion_smoke(
            video_project_root,
            VideoRunOptions(
                preset="motion", action="motion_smoke", live=True, keyframe_id="hero",
                motion_model="gen4.5", max_runway_credits=25,
            ),
            provider=FakeMotionProvider(_motion_fixture(synthetic_video)),
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "VIDEO_MOTION_LIVE_SMOKE_TEST": "true", "RUNWAYML_API_SECRET": "x"},
        )


def test_motion_variations_require_review_and_match_keyframe(video_project_root: Path, synthetic_video: Path) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    provider = FakeMotionProvider(synthetic_video)
    outcome = generate_motion_variations(
        video_project_root,
        VideoRunOptions(
            preset="motion", action="motion_generate", live=True, keyframe_id="hero",
            smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=3,
            max_runway_credits=75,
        ),
        provider=provider,
        environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "x"},
    )
    assert outcome.status == "SUCCEEDED"
    assert len(provider.submitted) == 3
    assert {path.name for path in outcome.run_dir.iterdir()} == set(VIDEO_RUN_FILES)
    request = json.loads((outcome.run_dir / "request.json").read_text())
    assert request["action"] == "motion_generate"
    assert all(item["prompt_text"] == request["requests"][0]["prompt_text"] for item in request["requests"])

    with pytest.raises(ExternalInputBlocked, match="does not exist"):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion", action="motion_generate", live=True, keyframe_id="other",
                smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=1,
                max_runway_credits=25,
            ),
            provider=FakeMotionProvider(_motion_fixture(synthetic_video)),
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "x"},
        )


def test_motion_variations_guard_budget_limit_and_zero_call_preview(video_project_root: Path, synthetic_video: Path) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    with pytest.raises(ExternalInputBlocked, match="cap exceeded"):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion", action="motion_generate", live=True, keyframe_id="hero",
                smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=2,
                max_runway_credits=5,
            ),
            provider=FakeMotionProvider(synthetic_video),
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "x"},
        )
    with pytest.raises(ExternalInputBlocked, match="explicit"):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion", action="motion_generate", live=True, keyframe_id="hero",
                smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=1,
            ),
            provider=FakeMotionProvider(synthetic_video),
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "x"},
        )
    preview = preview_motion_variations(
        video_project_root,
        VideoRunOptions(
            preset="motion", action="motion_generate", keyframe_id="hero",
            smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=2,
            max_runway_credits=50,
        ),
    )
    assert preview.status == "DRY_RUN_COMPLETE"
    assert preview.submission_count == 0


def test_motion_variations_reject_over_configured_limit(video_project_root: Path, synthetic_video: Path) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    with pytest.raises(ExternalInputBlocked, match="within 1.."):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion", action="motion_generate", live=True, keyframe_id="hero",
                smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=6,
                max_runway_credits=150,
            ),
            provider=FakeMotionProvider(synthetic_video),
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "x"},
        )


def test_legacy_motion_review_schema_is_supported_without_mutating_run(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    run_review = video_project_root / "runs" / smoke_id / "review.csv"
    with run_review.open(newline="", encoding="utf-8") as source:
        current = next(csv.DictReader(source))
    legacy_fields = (
        "run_id", "video_id", "preset", "candidate", "visual_identity",
        "face_stability", "age_stability", "hair_stability", "body_proportions",
        "wardrobe", "jewelry", "eyes", "background", "motion",
        "mtl_review_ready", "reviewer", "reviewed_at",
    )
    legacy_row = {field: current.get(field, "") for field in legacy_fields}
    for field in legacy_fields[4:14]:
        legacy_row[field] = "true"
    legacy_row.update(
        {
            "mtl_review_ready": "true",
            "reviewer": "Legacy motion reviewer",
            "reviewed_at": "2026-08-20T12:00:00+08:00",
        }
    )
    with review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=legacy_fields)
        writer.writeheader()
        writer.writerow(legacy_row)

    preview = preview_motion_variations(
        video_project_root,
        VideoRunOptions(
            preset="motion", action="motion_generate", keyframe_id="hero",
            smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=2,
            max_runway_credits=50,
        ),
    )
    assert preview.status == "DRY_RUN_COMPLETE"
    assert preview.submission_count == 0
    assert {path.name for path in preview.run_dir.iterdir()} == set(VIDEO_RUN_FILES)
    with run_review.open(newline="", encoding="utf-8") as source:
        untouched = next(csv.DictReader(source))
    assert all(untouched[field] == "" for field in QA_FIELDS[4:])


def test_incomplete_review_fails_before_motion_provider_submission(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    with review.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    row["visual_identity"] = ""
    with review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    provider = FakeMotionProvider(synthetic_video)
    with pytest.raises(ExternalInputBlocked, match="incomplete or failing"):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion", action="motion_generate", live=True, keyframe_id="hero",
                smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=1,
                max_runway_credits=25,
            ),
            provider=provider,
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "x"},
        )
    assert provider.submitted == []


def test_prompt_drift_fails_before_motion_provider_submission(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    prompt_path = video_project_root / "prompts/home-broll-v1.txt"
    prompt_path.write_text(prompt_path.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
    provider = FakeMotionProvider(synthetic_video)
    with pytest.raises(ExternalInputBlocked, match="prompt no longer matches"):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion", action="motion_generate", live=True, keyframe_id="hero",
                smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=1,
                max_runway_credits=25,
            ),
            provider=provider,
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "x"},
        )
    assert provider.submitted == []
