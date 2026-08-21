from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest
import yaml

import lala_workflow.video.runner as runner_module
from lala_workflow.hashing import sha256_file
from lala_workflow.video.config import load_video_config
from lala_workflow.video.costing import estimate_plan_cost
from lala_workflow.video.domain import MediaArtifact
from lala_workflow.video.planning import build_shot_plan
from lala_workflow.video.runner import (
    VideoRunOptions,
    generate_video,
    preview_video,
    run_talking_smoke,
)
from lala_workflow.video.storage import QA_FIELDS
from lala_workflow.video.validation import ExternalInputBlocked
from tests.fakes_video import FakeMotionProvider, FakeTalkingProvider
from tests.test_video_generate import approved_smoke_review, approved_smoke_run
from tests.test_video_motion_variations import (
    V7_PASS_FIELDS,
    _passing_motion_smoke,
    _reviewed_v7_parent,
)


def _cloned_voice_config(root: Path):
    profile_path = root / "configs/voice-profile.yaml"
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
    config = load_video_config(root, require_inputs=True)
    plan = build_shot_plan(
        config,
        "product_page",
        talking_variations=1,
        motion_variations=1,
    )
    return config, plan


def _enable_talking_role(root: Path) -> None:
    path = root / "configs/keyframe-manifest.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["keyframes"]["hero"]["roles"] = ["hero", "talking_medium_closeup"]
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")


class WritingVoiceProvider:
    def __init__(self, source: Path) -> None:
        self.source = source
        self.requests: list[object] = []

    def synthesize(self, request) -> MediaArtifact:
        self.requests.append(request)
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.source, request.output_path)
        return MediaArtifact(
            artifact_id="synthetic-voice",
            kind="audio",
            path=request.output_path,
            sha256=sha256_file(request.output_path),
            size_bytes=request.output_path.stat().st_size,
            mime_type="audio/wav",
        )


def test_cost_model_calculates_known_duration_and_preserves_runway_exactly(
    video_project_root: Path,
) -> None:
    config, plan = _cloned_voice_config(video_project_root)

    cost = estimate_plan_cost(plan, config, talking_duration_seconds=10.0)

    assert cost["voice_cost"] == 0.00667
    assert cost["talking_video_cost"] == 0.5
    assert cost["motion_video_cost"] == 0.4
    assert cost["total_provider_cost"] == 0.90667
    assert cost["budget_state"] == "TOTAL_ESTIMATE_KNOWN"
    assert {item["duration_basis"] for item in cost["components"]} == {
        "actual_audio_duration",
        "planned_request_duration",
    }


def test_cost_model_exposes_unknown_tts_dependency_without_fake_amount(
    video_project_root: Path,
) -> None:
    config, plan = _cloned_voice_config(video_project_root)

    cost = estimate_plan_cost(plan, config, talking_duration_seconds=None)

    assert cost["voice_cost"] is None
    assert cost["talking_video_cost"] is None
    assert cost["total_provider_cost"] is None
    assert cost["projected_total_at_duration_limit"] is None
    assert cost["budget_state"] == "TALKING_DURATION_REQUIRED"
    dependent = [
        item for item in cost["components"] if item["category"] in {"voice", "talking"}
    ]
    assert {item["unit_rate_usd_per_output_second"] for item in dependent} == {
        0.000667,
        0.05,
    }
    assert all(item["duration_dependency"] == "tts_output_duration" for item in dependent)


def test_cost_model_records_auditable_duration_projection_not_actual(
    video_project_root: Path,
) -> None:
    config, plan = _cloned_voice_config(video_project_root)

    cost = estimate_plan_cost(
        plan,
        config,
        talking_duration_seconds=None,
        talking_duration_limit_seconds=45.0,
    )

    assert cost["voice_cost"] is None
    assert cost["talking_video_cost"] is None
    assert cost["voice_cost_at_duration_limit"] == 0.030015
    assert cost["talking_video_cost_at_duration_limit"] == 2.25
    assert cost["motion_video_cost"] == 0.4
    assert cost["projected_total_at_duration_limit"] == 2.680015
    assert cost["budget_state"] == "TOTAL_EXACT_UNKNOWN_UNTIL_TTS"
    assert cost["tts_duration_provider_enforced"] is False
    assert all(
        item["amount"] is None and item["basis"] == "workflow_duration_projection"
        for item in cost["components"]
        if item["category"] in {"voice", "talking"}
    )


def test_product_dry_run_records_v7_and_staged_budget_without_unknown_bypass(
    video_project_root: Path,
    synthetic_video: Path,
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    v7_run_id, v7_review = _reviewed_v7_parent(video_project_root, synthetic_video)
    _cloned_voice_config(video_project_root)

    outcome = preview_video(
        video_project_root,
        VideoRunOptions(
            preset="product_page",
            action="generate",
            smoke_run_id=smoke_run_id,
            smoke_review_file=approved_smoke_review(video_project_root, smoke_run_id),
            motion_smoke_run_id=v7_run_id,
            motion_smoke_review_file=v7_review,
            talking_variations=1,
            motion_variations=1,
            max_provider_cost_usd=3.0,
            max_runway_credits=40,
            max_talking_duration_seconds=45.0,
        ),
    )

    request = json.loads((outcome.run_dir / "request.json").read_text())
    results = json.loads((outcome.run_dir / "provider-results.json").read_text())
    cost = json.loads((outcome.run_dir / "cost.json").read_text())
    assert outcome.status == "DRY_RUN_COMPLETE"
    assert request["motion_smoke_review"]["selected_candidate_id"] == (
        "v7-a-stability-first"
    )
    assert request["budget"]["budget_state"] == "TOTAL_EXACT_UNKNOWN_UNTIL_TTS"
    assert request["budget"]["accept_unknown_provider_cost"] is False
    assert request["budget"]["projected_total_at_duration_limit_usd"] == 2.680015
    assert cost["total_provider_cost"] is None
    assert cost["projected_total_at_duration_limit"] == 2.680015
    assert results["submission_count"] == 0


def test_post_tts_duration_gate_blocks_all_video_submissions(
    video_project_root: Path,
    synthetic_video: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    motion_run_id, motion_review = _passing_motion_smoke(
        video_project_root, synthetic_video
    )
    _enable_talking_role(video_project_root)
    _cloned_voice_config(video_project_root)
    voice = WritingVoiceProvider(
        video_project_root / "assets/voice/approved/tooltip.wav"
    )
    talking = FakeTalkingProvider(synthetic_video)
    motion = FakeMotionProvider(synthetic_video)
    monkeypatch.setattr(
        runner_module,
        "_create_generation_providers",
        lambda *_args, **_kwargs: {
            "heygen_voice": voice,
            "heygen": talking,
            "runway": motion,
        },
    )
    before_runs = set((video_project_root / "runs").iterdir())

    with pytest.raises(ExternalInputBlocked, match="post-TTS audio duration"):
        generate_video(
            video_project_root,
            VideoRunOptions(
                preset="product_page",
                action="generate",
                live=True,
                smoke_run_id=smoke_run_id,
                smoke_review_file=approved_smoke_review(
                    video_project_root, smoke_run_id
                ),
                motion_smoke_run_id=motion_run_id,
                motion_smoke_review_file=motion_review,
                talking_variations=1,
                motion_variations=1,
                max_provider_cost_usd=3.0,
                max_runway_credits=40,
                max_talking_duration_seconds=5.0,
            ),
            environ={
                "VIDEO_ALLOW_LIVE_CALLS": "true",
                "VIDEO_FULL_PILOT_LIVE": "true",
                "HEYGEN_API_KEY": "fixture-only",
                "RUNWAYML_API_SECRET": "fixture-only",
            },
        )

    assert len(voice.requests) == 1
    assert talking.submitted == []
    assert motion.submitted == []
    created_runs = set((video_project_root / "runs").iterdir()) - before_runs
    assert len(created_runs) == 1
    failure_request = json.loads((created_runs.pop() / "request.json").read_text())
    assert failure_request["post_tts_budget"]["post_tts_actual_duration_seconds"] == 10.0
    assert failure_request["post_tts_budget"]["post_tts_total_estimate_usd"] == 0.90667


def test_post_tts_actual_duration_recalculates_cost_before_video_submission(
    video_project_root: Path,
    synthetic_video: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    motion_run_id, motion_review = _passing_motion_smoke(
        video_project_root, synthetic_video
    )
    _enable_talking_role(video_project_root)
    _cloned_voice_config(video_project_root)
    voice = WritingVoiceProvider(
        video_project_root / "assets/voice/approved/tooltip.wav"
    )
    talking = FakeTalkingProvider(synthetic_video)
    motion = FakeMotionProvider(synthetic_video)
    monkeypatch.setattr(
        runner_module,
        "_create_generation_providers",
        lambda *_args, **_kwargs: {
            "heygen_voice": voice,
            "heygen": talking,
            "runway": motion,
        },
    )
    monkeypatch.setattr(
        runner_module, "_validate_talking_media_output", lambda *_args: None
    )

    outcome = generate_video(
        video_project_root,
        VideoRunOptions(
            preset="product_page",
            action="generate",
            live=True,
            smoke_run_id=smoke_run_id,
            smoke_review_file=approved_smoke_review(video_project_root, smoke_run_id),
            motion_smoke_run_id=motion_run_id,
            motion_smoke_review_file=motion_review,
            talking_variations=1,
            motion_variations=1,
            max_provider_cost_usd=3.0,
            max_runway_credits=40,
            max_talking_duration_seconds=12.0,
        ),
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_FULL_PILOT_LIVE": "true",
            "HEYGEN_API_KEY": "fixture-only",
            "RUNWAYML_API_SECRET": "fixture-only",
        },
    )

    request = json.loads((outcome.run_dir / "request.json").read_text())
    cost = json.loads((outcome.run_dir / "cost.json").read_text())
    assert outcome.status == "AWAITING_SELECTION"
    assert len(voice.requests) == 1
    assert len(talking.submitted) == 1
    assert len(motion.submitted) == 2
    assert cost["voice_cost"] == 0.00667
    assert cost["talking_video_cost"] == 0.5
    assert cost["motion_video_cost"] == 0.4
    assert cost["total_provider_cost"] == 0.90667
    assert request["budget"]["budget_state"] == "TOTAL_ESTIMATE_KNOWN"
    assert request["budget"]["post_tts_actual_duration_seconds"] == 10.0
    assert request["budget"]["remaining_provider_budget_usd"] == 2.09333


def test_duration_projection_over_owner_cap_blocks_before_provider_factory(
    video_project_root: Path,
    synthetic_video: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    motion_run_id, motion_review = _passing_motion_smoke(
        video_project_root, synthetic_video
    )
    _enable_talking_role(video_project_root)
    _cloned_voice_config(video_project_root)
    constructions: list[bool] = []
    monkeypatch.setattr(
        runner_module,
        "_create_generation_providers",
        lambda *_args, **_kwargs: constructions.append(True),
    )

    with pytest.raises(ExternalInputBlocked, match="exceeds"):
        generate_video(
            video_project_root,
            VideoRunOptions(
                preset="product_page",
                action="generate",
                live=True,
                smoke_run_id=smoke_run_id,
                smoke_review_file=approved_smoke_review(
                    video_project_root, smoke_run_id
                ),
                motion_smoke_run_id=motion_run_id,
                motion_smoke_review_file=motion_review,
                talking_variations=1,
                motion_variations=1,
                max_provider_cost_usd=3.0,
                max_runway_credits=40,
                max_talking_duration_seconds=60.0,
            ),
            environ={
                "VIDEO_ALLOW_LIVE_CALLS": "true",
                "VIDEO_FULL_PILOT_LIVE": "true",
                "HEYGEN_API_KEY": "fixture-only",
                "RUNWAYML_API_SECRET": "fixture-only",
            },
        )

    assert constructions == []


def test_product_live_preflight_accepts_reviewed_v7_a(
    video_project_root: Path,
    synthetic_video: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    v7_run_id, v7_review = _reviewed_v7_parent(video_project_root, synthetic_video)
    _enable_talking_role(video_project_root)
    talking = FakeTalkingProvider(synthetic_video)
    motion = FakeMotionProvider(synthetic_video)
    monkeypatch.setattr(
        runner_module,
        "_create_generation_providers",
        lambda *_args, **_kwargs: {"heygen": talking, "runway": motion},
    )
    monkeypatch.setattr(
        runner_module, "_validate_talking_media_output", lambda *_args: None
    )

    outcome = generate_video(
        video_project_root,
        VideoRunOptions(
            preset="product_page",
            action="generate",
            live=True,
            smoke_run_id=smoke_run_id,
            smoke_review_file=approved_smoke_review(video_project_root, smoke_run_id),
            motion_smoke_run_id=v7_run_id,
            motion_smoke_review_file=v7_review,
            talking_variations=1,
            motion_variations=1,
            max_provider_cost_usd=3.0,
            max_runway_credits=40,
        ),
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_FULL_PILOT_LIVE": "true",
            "HEYGEN_API_KEY": "fixture-only",
            "RUNWAYML_API_SECRET": "fixture-only",
        },
    )

    request = json.loads((outcome.run_dir / "request.json").read_text())
    assert outcome.status == "AWAITING_SELECTION"
    assert request["motion_smoke_review"]["selected_candidate_id"] == (
        "v7-a-stability-first"
    )
    assert len(talking.submitted) == 1
    assert len(motion.submitted) == 2


def test_ambiguous_v7_blocks_before_provider_factory(
    video_project_root: Path,
    synthetic_video: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_run_id = approved_smoke_run(video_project_root, synthetic_video)
    v7_run_id, v7_review = _reviewed_v7_parent(video_project_root, synthetic_video)
    with v7_review.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    for field in V7_PASS_FIELDS:
        rows[1][field] = "true"
    rows[1]["mtl_review_ready"] = "true"
    with v7_review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    constructions: list[bool] = []
    monkeypatch.setattr(
        runner_module,
        "_create_generation_providers",
        lambda *_args, **_kwargs: constructions.append(True),
    )

    with pytest.raises(ExternalInputBlocked, match="exactly one unique"):
        generate_video(
            video_project_root,
            VideoRunOptions(
                preset="product_page",
                action="generate",
                live=True,
                smoke_run_id=smoke_run_id,
                smoke_review_file=approved_smoke_review(
                    video_project_root, smoke_run_id
                ),
                motion_smoke_run_id=v7_run_id,
                motion_smoke_review_file=v7_review,
                talking_variations=1,
                motion_variations=1,
                max_provider_cost_usd=3.0,
                max_runway_credits=40,
            ),
            environ={
                "VIDEO_ALLOW_LIVE_CALLS": "true",
                "VIDEO_FULL_PILOT_LIVE": "true",
                "HEYGEN_API_KEY": "fixture-only",
                "RUNWAYML_API_SECRET": "fixture-only",
            },
        )

    assert constructions == []


def test_v7_wrong_keyframe_blocks_before_provider_factory(
    video_project_root: Path,
    synthetic_video: Path,
    image_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    v7_run_id, v7_review = _reviewed_v7_parent(video_project_root, synthetic_video)
    other = image_factory(
        video_project_root / "assets/approved_keyframes/other.png",
        size=(128, 72),
        color=(20, 80, 140),
    )
    other_sha = sha256_file(other)
    promotion = other.with_suffix(".json")
    promotion.write_text(
        json.dumps(
            {
                "source_run_id": "synthetic-other-run",
                "source_output_id": "synthetic-other-output",
                "sha256": other_sha,
                "reviewer": "Synthetic test reviewer",
                "approved_at": "2026-08-21T10:00:00+08:00",
            }
        ),
        encoding="utf-8",
    )
    manifest_path = video_project_root / "configs/keyframe-manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["keyframes"]["other"] = {
        "path": "assets/approved_keyframes/other.png",
        "sha256": other_sha,
        "source_run_id": "synthetic-other-run",
        "source_output_id": "synthetic-other-output",
        "promotion_record": "assets/approved_keyframes/other.json",
        "reviewer": "Synthetic test reviewer",
        "approved_at": "2026-08-21T10:00:00+08:00",
        "roles": ["hero", "talking_medium_closeup"],
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    smoke = run_talking_smoke(
        video_project_root,
        VideoRunOptions(
            preset="tooltip", action="talking_smoke", live=True, keyframe_id="other"
        ),
        provider=FakeTalkingProvider(synthetic_video),
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "VIDEO_LIVE_SMOKE_TEST": "true",
            "HEYGEN_API_KEY": "fixture-only",
        },
    )
    smoke_review = (
        video_project_root / "outputs/reviews" / f"{smoke.run_id}-review.csv"
    )
    shutil.copyfile(smoke.run_dir / "review.csv", smoke_review)
    with smoke_review.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    for field in QA_FIELDS[4:18]:
        row[field] = "true"
    row.update(
        {
            "mtl_review_ready": "true",
            "reviewer": "Synthetic human reviewer",
            "reviewed_at": "2026-08-21T10:00:00+08:00",
        }
    )
    with smoke_review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    constructions: list[bool] = []
    monkeypatch.setattr(
        runner_module,
        "_create_generation_providers",
        lambda *_args, **_kwargs: constructions.append(True),
    )

    with pytest.raises(ExternalInputBlocked, match="different approved keyframe"):
        generate_video(
            video_project_root,
            VideoRunOptions(
                preset="product_page",
                action="generate",
                live=True,
                keyframe_id="other",
                smoke_run_id=smoke.run_id,
                smoke_review_file=smoke_review,
                motion_smoke_run_id=v7_run_id,
                motion_smoke_review_file=v7_review,
                talking_variations=1,
                motion_variations=1,
                max_provider_cost_usd=3.0,
                max_runway_credits=40,
            ),
            environ={
                "VIDEO_ALLOW_LIVE_CALLS": "true",
                "VIDEO_FULL_PILOT_LIVE": "true",
                "HEYGEN_API_KEY": "fixture-only",
                "RUNWAYML_API_SECRET": "fixture-only",
            },
        )

    assert constructions == []
