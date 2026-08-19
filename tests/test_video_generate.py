from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest
import yaml

from lala_workflow.hashing import sha256_file
from lala_workflow.video.domain import MediaArtifact, VideoTaskResult, VideoTaskStatus
from lala_workflow.video.runner import VideoRunOptions, generate_video, run_talking_smoke
from lala_workflow.video.storage import QA_FIELDS, VIDEO_RUN_FILES
from lala_workflow.video.validation import ExternalInputBlocked
from tests.fakes_video import FakeMotionProvider, FakeTalkingProvider


PASS_FIELDS = QA_FIELDS[4:18]


def approved_smoke_run(root: Path, synthetic_video: Path) -> str:
    outcome = run_talking_smoke(
        root,
        VideoRunOptions(preset="tooltip", action="talking_smoke", live=True),
        provider=FakeTalkingProvider(synthetic_video),
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_LIVE_SMOKE_TEST": "true",
            "HEYGEN_API_KEY": "test-key",
        },
    )
    source_review = outcome.run_dir / "review.csv"
    review_path = root / "outputs/reviews" / f"{outcome.run_id}-review.csv"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_review, review_path)
    with review_path.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    for field in PASS_FIELDS:
        row[field] = "true"
    row["mtl_review_ready"] = "true"
    row["reviewer"] = "Synthetic reviewer"
    row["reviewed_at"] = "2026-08-19T12:30:00+08:00"
    with review_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    return outcome.run_id


def approved_smoke_review(root: Path, run_id: str) -> Path:
    return root / "outputs/reviews" / f"{run_id}-review.csv"


@pytest.mark.parametrize(
    ("preset", "expected_calls", "expected_shots"),
    [("product_page", 9, 4), ("tooltip", 3, 2), ("homepage", 12, 5)],
)
def test_three_pilot_workflows_generate_bounded_shot_alternatives(
    video_project_root: Path,
    synthetic_video: Path,
    preset: str,
    expected_calls: int,
    expected_shots: int,
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    talking = FakeTalkingProvider(synthetic_video)
    motion = FakeMotionProvider(synthetic_video)
    outcome = generate_video(
        video_project_root,
        VideoRunOptions(
            preset=preset,
            action="generate",
            live=True,
            smoke_run_id=smoke_run_id,
            smoke_review_file=approved_smoke_review(video_project_root, smoke_run_id),
        ),
        providers={"heygen": talking, "runway": motion},
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "HEYGEN_API_KEY": "test-key",
            "RUNWAYML_API_SECRET": "test-secret",
        },
    )
    assert outcome.status == "AWAITING_SELECTION"
    assert outcome.provider_call_count == expected_calls
    assert outcome.submission_count == expected_calls
    assert len(outcome.plan.shots) == expected_shots
    assert len(talking.submitted) == 3
    assert len(motion.submitted) == expected_calls - 3
    assert {path.name for path in outcome.run_dir.iterdir()} == set(VIDEO_RUN_FILES)
    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    assert request["smoke_review"]["sha256"] == sha256_file(
        approved_smoke_review(video_project_root, smoke_run_id)
    )
    assert (outcome.run_dir / "script.txt").read_bytes() == (
        video_project_root / f"assets/scripts/{'product-page' if preset == 'product_page' else preset}.txt"
    ).read_bytes()
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == expected_calls
    assert all(all(row[field] == "" for field in QA_FIELDS[4:]) for row in rows)


class OneFailureMotionProvider(FakeMotionProvider):
    def wait(self, task_id: str, timeout_seconds: float) -> VideoTaskResult:
        if "reward_visual" in task_id:
            return VideoTaskResult(task_id, VideoTaskStatus.FAILED, error_code="synthetic_failure")
        return super().wait(task_id, timeout_seconds)


def test_partial_provider_failure_is_recorded_without_unbounded_recovery(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    motion = OneFailureMotionProvider(synthetic_video)
    outcome = generate_video(
        video_project_root,
        VideoRunOptions(
            preset="product_page",
            action="generate",
            live=True,
            smoke_run_id=smoke_run_id,
            smoke_review_file=approved_smoke_review(video_project_root, smoke_run_id),
        ),
        providers={"heygen": FakeTalkingProvider(synthetic_video), "runway": motion},
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "HEYGEN_API_KEY": "test-key",
            "RUNWAYML_API_SECRET": "test-secret",
        },
    )
    assert outcome.status == "PARTIAL"
    results = json.loads((outcome.run_dir / "provider-results.json").read_text(encoding="utf-8"))
    assert results["failed_outputs"] == 3
    assert outcome.submission_count == 9


def test_full_generation_rejects_unreviewed_smoke_before_provider_calls(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke = run_talking_smoke(
        video_project_root,
        VideoRunOptions(preset="tooltip", action="talking_smoke", live=True),
        provider=FakeTalkingProvider(synthetic_video),
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_LIVE_SMOKE_TEST": "true",
            "HEYGEN_API_KEY": "test-key",
        },
    )
    talking = FakeTalkingProvider(synthetic_video)
    motion = FakeMotionProvider(synthetic_video)
    smoke_review = video_project_root / "outputs/reviews/unreviewed-smoke.csv"
    smoke_review.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(smoke.run_dir / "review.csv", smoke_review)
    with pytest.raises(ExternalInputBlocked, match="QA decisions"):
        generate_video(
            video_project_root,
            VideoRunOptions(
                preset="homepage",
                action="generate",
                live=True,
                smoke_run_id=smoke.run_id,
                smoke_review_file=smoke_review,
            ),
            providers={"heygen": talking, "runway": motion},
            environ={
                "VIDEO_ALLOW_LIVE_CALLS": "true",
                "HEYGEN_API_KEY": "test-key",
                "RUNWAYML_API_SECRET": "test-secret",
            },
        )
    assert talking.submitted == []
    assert motion.submitted == []


class WritingVoiceProvider:
    def __init__(self, source: Path) -> None:
        self.source = source
        self.requests = []

    def synthesize(self, request) -> MediaArtifact:
        self.requests.append(request)
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.source, request.output_path)
        return MediaArtifact(
            artifact_id=f"voice-{request.preset}",
            kind="audio",
            path=request.output_path,
            sha256=sha256_file(request.output_path),
            size_bytes=request.output_path.stat().st_size,
            mime_type="audio/wav",
        )


def test_cloned_voice_full_generation_counts_and_records_voice_provider_call(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    profile_path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "mode": "cloned_voice",
            "provider": "heygen_voice",
            "model": "starfish",
            "voice_id": "approved-voice-id",
            "script_audio": {},
        }
    )
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    voice = WritingVoiceProvider(
        video_project_root / "assets/voice/approved/tooltip.wav"
    )
    outcome = generate_video(
        video_project_root,
        VideoRunOptions(
            preset="tooltip",
            action="generate",
            live=True,
            smoke_run_id=smoke_run_id,
            smoke_review_file=approved_smoke_review(video_project_root, smoke_run_id),
        ),
        providers={
            "heygen_voice": voice,
            "heygen": FakeTalkingProvider(synthetic_video),
            "runway": FakeMotionProvider(synthetic_video),
        },
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "HEYGEN_API_KEY": "test-key",
            "RUNWAYML_API_SECRET": "test-secret",
        },
    )
    assert len(voice.requests) == 1
    assert outcome.provider_call_count == 4
    assert outcome.submission_count == 4
    results = json.loads((outcome.run_dir / "provider-results.json").read_text(encoding="utf-8"))
    assert results["submission_count"] == 4
    assert results["results"][0]["artifacts"][0]["kind"] == "audio"


class FailingVoiceProvider:
    def synthesize(self, _request):
        raise RuntimeError("synthetic voice failure")


def test_voice_failure_after_run_allocation_writes_complete_failure_evidence(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    profile_path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "mode": "cloned_voice",
            "provider": "heygen_voice",
            "model": "starfish",
            "voice_id": "approved-voice-id",
            "script_audio": {},
        }
    )
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    before = set((video_project_root / "runs").iterdir())
    with pytest.raises(RuntimeError, match="synthetic voice failure"):
        generate_video(
            video_project_root,
            VideoRunOptions(
                preset="tooltip",
                action="generate",
                live=True,
                smoke_run_id=smoke_run_id,
                smoke_review_file=approved_smoke_review(video_project_root, smoke_run_id),
            ),
            providers={"heygen_voice": FailingVoiceProvider()},
            environ={
                "VIDEO_ALLOW_LIVE_CALLS": "true",
                "HEYGEN_API_KEY": "test-key",
            },
        )
    created = set((video_project_root / "runs").iterdir()) - before
    assert len(created) == 1
    failure_run = created.pop()
    assert {path.name for path in failure_run.iterdir()} == set(VIDEO_RUN_FILES)
    results = json.loads((failure_run / "provider-results.json").read_text(encoding="utf-8"))
    assert results["status"] == "FAILED"
