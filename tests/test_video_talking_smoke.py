from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest
import yaml

from lala_workflow.hashing import sha256_file
from lala_workflow.providers.base import ProviderSubmissionError
from lala_workflow.video.domain import MediaArtifact
from lala_workflow.video.runner import VideoRunOptions, run_talking_smoke
from lala_workflow.video.storage import QA_FIELDS, VIDEO_RUN_FILES
from tests.fakes_video import FakeTalkingProvider
from tests.test_video_generate import approved_smoke_review, approved_smoke_run


def test_mocked_live_talking_smoke_produces_one_reviewable_result(
    video_project_root: Path, synthetic_video: Path
) -> None:
    provider = FakeTalkingProvider(synthetic_video)
    secret = "local-test-secret-value"
    outcome = run_talking_smoke(
        video_project_root,
        VideoRunOptions(preset="tooltip", action="talking_smoke", live=True),
        provider=provider,
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_LIVE_SMOKE_TEST": "true",
            "HEYGEN_API_KEY": secret,
        },
    )
    assert outcome.provider_call_count == 1
    assert outcome.submission_count == 1
    assert len(provider.submitted) == 1
    assert {path.name for path in outcome.run_dir.iterdir()} == set(VIDEO_RUN_FILES)
    results = json.loads((outcome.run_dir / "provider-results.json").read_text(encoding="utf-8"))
    assert results["successful_outputs"] == 1
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 1
    assert list(rows[0]) == list(QA_FIELDS)
    assert rows[0]["candidate"].endswith(".mp4")
    assert all(rows[0][field] == "" for field in QA_FIELDS[4:])
    serialized = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore") for path in outcome.run_dir.iterdir()
    )
    assert secret not in serialized


class WritingVoiceProvider:
    def __init__(self, source: Path) -> None:
        self.source = source
        self.requests = []

    def synthesize(self, request) -> MediaArtifact:
        self.requests.append(request)
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.source, request.output_path)
        return MediaArtifact(
            artifact_id="voice-smoke",
            kind="audio",
            path=request.output_path,
            sha256=sha256_file(request.output_path),
            size_bytes=request.output_path.stat().st_size,
            mime_type="audio/wav",
            provider_task_id=None,
            provenance={
                "provider_request_id": None,
                "provider_request_id_present": True,
                "submission_policy": "single_submit_no_automatic_replay",
            },
        )


def test_cloned_voice_smoke_synthesizes_once_then_requests_one_talking_result(
    video_project_root: Path, synthetic_video: Path
) -> None:
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
    talking = FakeTalkingProvider(synthetic_video)
    outcome = run_talking_smoke(
        video_project_root,
        VideoRunOptions(preset="tooltip", action="talking_smoke", live=True),
        provider=talking,
        voice_provider=voice,
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_LIVE_SMOKE_TEST": "true",
            "HEYGEN_API_KEY": "test-key",
        },
    )
    assert len(voice.requests) == 1
    assert len(talking.submitted) == 1
    assert outcome.provider_call_count == 2
    assert outcome.submission_count == 2
    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    voice_result = results["results"][0]
    assert voice_result["provider_task_id"] is None
    assert voice_result["artifacts"][0]["provider_task_id"] is None
    assert voice_result["artifacts"][0]["provenance"]["provider_request_id"] is None


class AmbiguousTalkingProvider(FakeTalkingProvider):
    def submit(self, request):
        self.submitted.append(request)
        raise ProviderSubmissionError("synthetic ambiguous submission")


class AmbiguousSecondTalkingProvider(FakeTalkingProvider):
    def submit(self, request):
        if len(self.submitted) == 1:
            self.submitted.append(request)
            raise ProviderSubmissionError("synthetic ambiguous second submission")
        return super().submit(request)


def test_smoke_execution_exception_still_writes_thirteen_failure_artifacts(
    video_project_root: Path, synthetic_video: Path
) -> None:
    before = set((video_project_root / "runs").iterdir())
    with pytest.raises(ProviderSubmissionError, match="synthetic ambiguous"):
        run_talking_smoke(
            video_project_root,
            VideoRunOptions(preset="tooltip", action="talking_smoke", live=True),
            provider=AmbiguousTalkingProvider(synthetic_video),
            environ={
                "VIDEO_ALLOW_LIVE_CALLS": "true",
                "VIDEO_LIVE_SMOKE_TEST": "true",
                "HEYGEN_API_KEY": "test-key",
            },
        )
    created = set((video_project_root / "runs").iterdir()) - before
    assert len(created) == 1
    failure_run = created.pop()
    assert {path.name for path in failure_run.iterdir()} == set(VIDEO_RUN_FILES)
    results = json.loads((failure_run / "provider-results.json").read_text(encoding="utf-8"))
    assert results["status"] == "FAILED"


def test_reviewed_first_smoke_unlocks_three_talking_only_alternatives(
    video_project_root: Path, synthetic_video: Path
) -> None:
    first_run_id = approved_smoke_run(video_project_root, synthetic_video)
    provider = FakeTalkingProvider(synthetic_video)
    outcome = run_talking_smoke(
        video_project_root,
        VideoRunOptions(
            preset="tooltip",
            action="talking_smoke",
            live=True,
            talking_variations=3,
            smoke_run_id=first_run_id,
            smoke_review_file=approved_smoke_review(video_project_root, first_run_id),
        ),
        provider=provider,
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "HEYGEN_API_KEY": "test-key",
        },
    )
    assert outcome.status == "SUCCEEDED"
    assert outcome.provider_call_count == 3
    assert outcome.submission_count == 3
    assert len(provider.submitted) == 3
    request = json.loads((outcome.run_dir / "request.json").read_text(encoding="utf-8"))
    assert request["prior_smoke_run_id"] == first_run_id
    assert request["prior_smoke_review"]["sha256"]
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 3
    assert all(all(row[field] == "" for field in QA_FIELDS[4:]) for row in rows)


def test_expanded_validation_stops_after_ambiguous_submission(
    video_project_root: Path, synthetic_video: Path
) -> None:
    first_run_id = approved_smoke_run(video_project_root, synthetic_video)
    provider = AmbiguousSecondTalkingProvider(synthetic_video)
    outcome = run_talking_smoke(
        video_project_root,
        VideoRunOptions(
            preset="tooltip",
            action="talking_smoke",
            live=True,
            talking_variations=3,
            smoke_run_id=first_run_id,
            smoke_review_file=approved_smoke_review(video_project_root, first_run_id),
        ),
        provider=provider,
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "HEYGEN_API_KEY": "test-key",
        },
    )

    assert outcome.status == "PARTIAL"
    assert len(provider.submitted) == 2
    results = json.loads((outcome.run_dir / "provider-results.json").read_text(encoding="utf-8"))
    assert results["successful_outputs"] == 1
    assert results["failed_outputs"] == 1
    assert results["not_attempted_requests"] == 1
    assert results["submission_count_known"] is False
