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
    preview_motion_smoke,
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
    assert request["requests"][0]["prompt_path"].endswith("prompts/home-broll-v3.txt")


def test_motion_smoke_prompt_override_records_exact_v3_provenance(
    video_project_root: Path,
) -> None:
    prompt_path = video_project_root / "prompts/home-broll-v3.txt"
    prompt_text = prompt_path.read_text(encoding="utf-8")
    outcome = run_motion_smoke(
        video_project_root,
        VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id="hero",
            motion_variations=1,
            motion_prompt="prompts/home-broll-v3.txt",
            max_runway_credits=25,
        ),
    )
    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    item = request["requests"][0]
    assert item["prompt_path"].endswith("prompts/home-broll-v3.txt")
    assert item["prompt_text"] == prompt_text
    assert item["prompt_sha256"] == hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    plan = json.loads((outcome.run_dir / "shot-plan.json").read_text(encoding="utf-8"))
    assert plan["shots"][0]["prompt"]["sha256"] == item["prompt_sha256"]


def test_motion_smoke_v3_prompt_is_within_runway_utf16_limit(
    video_project_root: Path,
) -> None:
    prompt_path = video_project_root / "prompts/home-broll-v3.txt"
    prompt_text = prompt_path.read_text(encoding="utf-8")
    assert len(prompt_text.encode("utf-16-le")) // 2 <= 1000
    outcome = preview_motion_smoke(
        video_project_root,
        VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id="hero",
            motion_prompt="prompts/home-broll-v3.txt",
        ),
    )
    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    assert request["requests"][0]["prompt_path"].endswith("prompts/home-broll-v3.txt")


def test_motion_smoke_v4_camera_lock_dry_run_records_exact_provenance(
    video_project_root: Path,
) -> None:
    v3_path = video_project_root / "prompts/home-broll-v3.txt"
    v4_path = video_project_root / "prompts/home-broll-v4.txt"
    v4_bytes = v4_path.read_bytes()
    v4_text = v4_bytes.decode("utf-8")

    assert hashlib.sha256(v3_path.read_bytes()).hexdigest() == (
        "897c00baabbf51304268c842d811bec1927fafc4e0042ad11bf63867933e69b5"
    )
    assert len(v3_path.read_text(encoding="utf-8").encode("utf-16-le")) // 2 == 892
    assert v4_bytes.endswith(b"\n")
    assert len(v4_text.encode("utf-16-le")) // 2 == 845
    assert hashlib.sha256(v4_bytes).hexdigest() == (
        "b3460aaa0de7738e53de6163d1dc53875cd5306d05f71dbe7d3e2e27117b666c"
    )

    outcome = run_motion_smoke(
        video_project_root,
        VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id="hero",
            motion_variations=1,
            motion_prompt="prompts/home-broll-v4.txt",
            max_runway_credits=25,
        ),
    )

    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    cost = json.loads((outcome.run_dir / "cost.json").read_text(encoding="utf-8"))
    item = request["requests"][0]
    assert outcome.status == "DRY_RUN_COMPLETE"
    assert outcome.submission_count == 0
    assert request["provider_call_count"] == 1
    assert item["prompt_path"].endswith("prompts/home-broll-v4.txt")
    assert item["prompt_text"] == v4_text
    assert item["prompt_sha256"] == hashlib.sha256(v4_bytes).hexdigest()
    assert results["submission_count"] == 0
    assert results["results"] == []
    assert cost["estimated_runway_credits"] == 25
    assert cost["actual_runway_credits"] is None


def test_motion_smoke_v5_eye_mouth_lock_dry_run_records_exact_provenance(
    video_project_root: Path,
) -> None:
    v3_path = video_project_root / "prompts/home-broll-v3.txt"
    v4_path = video_project_root / "prompts/home-broll-v4.txt"
    v5_path = video_project_root / "prompts/home-broll-v5.txt"
    v5_bytes = v5_path.read_bytes()
    v5_text = v5_bytes.decode("utf-8")

    assert hashlib.sha256(v3_path.read_bytes()).hexdigest() == (
        "897c00baabbf51304268c842d811bec1927fafc4e0042ad11bf63867933e69b5"
    )
    assert hashlib.sha256(v4_path.read_bytes()).hexdigest() == (
        "b3460aaa0de7738e53de6163d1dc53875cd5306d05f71dbe7d3e2e27117b666c"
    )
    assert v5_bytes.endswith(b"\n")
    assert len(v5_text.encode("utf-16-le")) // 2 == 837
    assert hashlib.sha256(v5_bytes).hexdigest() == (
        "b27caa4269db46dd7d9ad5b700080418df7067e194a60af38b9cf5c99b7fae22"
    )

    outcome = run_motion_smoke(
        video_project_root,
        VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id="hero",
            motion_variations=1,
            motion_prompt="prompts/home-broll-v5.txt",
            max_runway_credits=25,
        ),
    )

    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    cost = json.loads((outcome.run_dir / "cost.json").read_text(encoding="utf-8"))
    item = request["requests"][0]
    assert outcome.status == "DRY_RUN_COMPLETE"
    assert outcome.submission_count == 0
    assert request["provider_call_count"] == 1
    assert item["prompt_path"].endswith("prompts/home-broll-v5.txt")
    assert item["prompt_text"] == v5_text
    assert item["prompt_sha256"] == hashlib.sha256(v5_bytes).hexdigest()
    assert results["submission_count"] == 0
    assert results["results"] == []
    assert cost["estimated_runway_credits"] == 25
    assert cost["actual_runway_credits"] is None


def test_motion_smoke_v6_combined_lock_dry_run_records_exact_provenance(
    video_project_root: Path,
) -> None:
    v4_path = video_project_root / "prompts/home-broll-v4.txt"
    v5_path = video_project_root / "prompts/home-broll-v5.txt"
    v6_path = video_project_root / "prompts/home-broll-v6.txt"
    v6_bytes = v6_path.read_bytes()
    v6_text = v6_bytes.decode("utf-8")

    assert hashlib.sha256(v4_path.read_bytes()).hexdigest() == (
        "b3460aaa0de7738e53de6163d1dc53875cd5306d05f71dbe7d3e2e27117b666c"
    )
    assert hashlib.sha256(v5_path.read_bytes()).hexdigest() == (
        "b27caa4269db46dd7d9ad5b700080418df7067e194a60af38b9cf5c99b7fae22"
    )
    assert v6_bytes.endswith(b"\n")
    assert len(v6_text.encode("utf-16-le")) // 2 == 874
    assert len(v6_text.encode("utf-16-le")) // 2 <= 1000
    assert hashlib.sha256(v6_bytes).hexdigest() == (
        "6f63f1d89d925b1a8faa6e205fe35f110f6d6986210d9a919d04949919b2e8c6"
    )

    outcome = run_motion_smoke(
        video_project_root,
        VideoRunOptions(
            preset="motion_smoke",
            action="motion_smoke",
            keyframe_id="hero",
            motion_variations=1,
            motion_prompt="prompts/home-broll-v6.txt",
            max_runway_credits=25,
        ),
    )

    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    cost = json.loads((outcome.run_dir / "cost.json").read_text(encoding="utf-8"))
    item = request["requests"][0]
    assert outcome.status == "DRY_RUN_COMPLETE"
    assert outcome.submission_count == 0
    assert request["provider_call_count"] == 1
    assert item["prompt_path"].endswith("prompts/home-broll-v6.txt")
    assert item["prompt_text"] == v6_text
    assert item["prompt_sha256"] == hashlib.sha256(v6_bytes).hexdigest()
    assert results["submission_count"] == 0
    assert results["results"] == []
    assert cost["estimated_runway_credits"] == 25
    assert cost["actual_runway_credits"] is None


def test_motion_smoke_rejects_overlong_prompt_before_run_creation(
    video_project_root: Path,
) -> None:
    with pytest.raises(ValueError, match=r"1001 > 1000"):
        preview_motion_smoke(
            video_project_root,
            VideoRunOptions(
                preset="motion_smoke",
                action="motion_smoke",
                keyframe_id="hero",
                motion_prompt="prompts/home-broll-v2.txt",
            ),
        )


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
