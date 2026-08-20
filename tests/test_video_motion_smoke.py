from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from lala_workflow.video.runner import (
    VideoRunOptions,
    _validate_passing_motion_smoke,
    run_motion_smoke,
)
from lala_workflow.video.prompts import VideoPromptError
from lala_workflow.video.storage import QA_FIELDS, VIDEO_RUN_FILES
from tests.fakes_video import FakeMotionProvider


def _motion_fixture(source: Path) -> Path:
    target = source.with_name("motion-smoke-fixture.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-t",
            "5",
            "-vf",
            "scale=1280:720",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-y",
            str(target),
        ],
        check=True,
        capture_output=True,
    )
    return target


def test_motion_smoke_is_voice_independent_and_writes_media_evidence(
    video_project_root: Path, synthetic_video: Path
) -> None:
    profile_path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update({"mode": "pending", "approval_status": "pending", "script_audio": {}})
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    provider = FakeMotionProvider(_motion_fixture(synthetic_video))

    outcome = run_motion_smoke(
        video_project_root,
        VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id="hero",
            motion_variations=1,
            live=True,
            max_runway_credits=25,
        ),
        provider=provider,
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_MOTION_LIVE_SMOKE_TEST": "true",
            "RUNWAYML_API_SECRET": "synthetic-secret",
        },
    )

    assert outcome.status == "SUCCEEDED"
    assert outcome.submission_count == 1
    assert len(provider.submitted) == 1
    assert {path.name for path in outcome.run_dir.iterdir()} == set(VIDEO_RUN_FILES)
    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    artifact = results["results"][0]["artifacts"][0]
    technical = artifact["technical_evidence"]
    assert technical["media"]["video_codec"] == "h264"
    assert technical["media"]["audio_stream_present"] is True
    assert all((video_project_root / item["path"]).is_file() for item in technical["frames"].values())
    assert (video_project_root / technical["contact_sheet"]["path"]).is_file()
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    assert all(row[field] == "" for field in QA_FIELDS[4:])


def test_motion_smoke_dry_run_has_zero_submissions_and_explicit_budget(
    video_project_root: Path,
) -> None:
    outcome = run_motion_smoke(
        video_project_root,
        VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id="hero",
            motion_variations=1,
            max_runway_credits=25,
        ),
    )
    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    assert outcome.status == "DRY_RUN_COMPLETE"
    assert outcome.submission_count == 0
    assert request["budget"]["max_runway_credits"] == 25
    assert request["budget"]["estimated_runway_credits"] == 25
    assert request["requests"][0]["prompt_path"].endswith("prompts/home-broll-v1.txt")


def test_motion_smoke_prompt_override_records_exact_v2_provenance(
    video_project_root: Path,
) -> None:
    prompt_path = video_project_root / "prompts/home-broll-v2.txt"
    prompt_text = prompt_path.read_text(encoding="utf-8")
    outcome = run_motion_smoke(
        video_project_root,
        VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id="hero",
            motion_variations=1,
            motion_prompt="prompts/home-broll-v2.txt",
            max_runway_credits=25,
        ),
    )
    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    item = request["requests"][0]
    assert item["prompt_path"].endswith("prompts/home-broll-v2.txt")
    assert item["prompt_text"] == prompt_text
    assert item["prompt_sha256"] == hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    plan = json.loads((outcome.run_dir / "shot-plan.json").read_text(encoding="utf-8"))
    assert plan["shots"][0]["prompt"]["sha256"] == item["prompt_sha256"]


def test_motion_smoke_rejects_unversioned_or_outside_prompt(
    video_project_root: Path,
) -> None:
    (video_project_root / "prompts/home-broll.txt").write_text("prompt\n", encoding="utf-8")
    (video_project_root / "outside-v1.txt").write_text("prompt\n", encoding="utf-8")
    for selected, message in (
        ("prompts/home-broll.txt", "versioned"),
        ("outside-v1.txt", "under prompts"),
    ):
        with pytest.raises(VideoPromptError, match=message):
            run_motion_smoke(
                video_project_root,
                VideoRunOptions(
                    preset="motion_smoke",
                    action="motion_smoke",
                    keyframe_id="hero",
                    motion_prompt=selected,
                ),
            )


def test_reviewed_motion_smoke_copy_is_hash_and_keyframe_gated(
    video_project_root: Path, synthetic_video: Path
) -> None:
    outcome = run_motion_smoke(
        video_project_root,
        VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id="hero",
            motion_variations=1,
            live=True,
            max_runway_credits=25,
        ),
        provider=FakeMotionProvider(_motion_fixture(synthetic_video)),
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_MOTION_LIVE_SMOKE_TEST": "true",
            "RUNWAYML_API_SECRET": "synthetic-secret",
        },
    )
    review = video_project_root / "outputs/reviews/motion-review.csv"
    review.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(outcome.run_dir / "review.csv", review)
    with review.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    for field in QA_FIELDS[4:18]:
        row[field] = "true"
    row.update(
        {
            "reviewer": "Motion reviewer",
            "reviewed_at": "2026-08-19T15:00:00+08:00",
        }
    )
    with review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    import json as _json

    keyframe_hash = _json.loads(
        (outcome.run_dir / "keyframe-hash.json").read_text(encoding="utf-8")
    )["sha256"]
    evidence = _validate_passing_motion_smoke(
        video_project_root,
        outcome.run_id,
        review,
        keyframe_sha256=keyframe_hash,
    )
    assert evidence["path"] == "outputs/reviews/motion-review.csv"
