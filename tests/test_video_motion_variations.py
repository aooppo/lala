from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import lala_workflow.video.runner as runner_module

from lala_workflow.video.runner import (
    VideoRunOptions,
    generate_motion_variations,
    preview_motion_variations,
    run_motion_smoke,
    run_motion_v7_live,
)
from lala_workflow.video.storage import QA_FIELDS, VIDEO_RUN_FILES
from lala_workflow.video.validation import ExternalInputBlocked
from tests.fakes_video import FakeMotionProvider


PASS_FIELDS = QA_FIELDS[4:18]
V7_PASS_FIELDS = (
    "visual_identity",
    "face_stability",
    "age_stability",
    "hair_stability",
    "body_proportions",
    "wardrobe",
    "jewelry",
    "mouth",
    "eyes",
    "background",
    "motion",
    "technical_export",
)


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


def _reviewed_v7_parent(
    root: Path, synthetic_video: Path
) -> tuple[str, Path]:
    outcome = run_motion_v7_live(
        root,
        keyframe_id="hero",
        execute_live=True,
        confirm_v7_batch=True,
        max_runway_credits=75,
        provider=FakeMotionProvider(_motion_fixture(synthetic_video)),
        environ={
            "VIDEO_ALLOW_LIVE_CALLS": "true",
            "RUNWAYML_API_SECRET": "fixture-only",
        },
    )
    review = root / "outputs/reviews" / f"{outcome.run_id}-review.csv"
    review.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(outcome.run_dir / "review.csv", review)
    with review.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        row.update(
            {
                "mtl_review_ready": "false",
                "reviewer": "Fixture human reviewer",
                "reviewed_at": "2026-08-20T16:43:46+08:00",
                "notes": "Explicit human FAIL",
            }
        )
    for field in V7_PASS_FIELDS:
        rows[0][field] = "true"
    rows[0].update(
        {
            "mtl_review_ready": "true",
            "notes": "Explicit human PASS; selected V7-A",
        }
    )
    with review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
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


def test_p1_2_prompt_candidates_are_versioned_and_within_utf16_limit(
    video_project_root: Path,
) -> None:
    expected = {
        "motion-variation-v1.txt": 959,
        "motion-variation-v2.txt": 985,
        "motion-variation-v3.txt": 997,
    }
    for filename, units in expected.items():
        text = (video_project_root / "prompts" / filename).read_text(encoding="utf-8")
        assert len(text.encode("utf-16-le")) // 2 == units
        assert units <= 1000


def test_v7_prompt_provenance_rebinds_across_worktrees(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_id, review = _reviewed_v7_parent(video_project_root, synthetic_video)
    request_path = video_project_root / "runs" / smoke_id / "request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    for item in request["requests"]:
        prompt_name = Path(item["prompt_path"]).name
        item["prompt_path"] = str(
            Path("/previous/worktree/prompts") / prompt_name
        )
    request_path.write_text(
        json.dumps(request, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    outcome = preview_motion_variations(
        video_project_root,
        VideoRunOptions(
            preset="motion",
            action="motion_generate",
            keyframe_id="hero",
            smoke_run_id=smoke_id,
            smoke_review_file=review,
            motion_variations=3,
            max_runway_credits=75,
        ),
    )

    assert outcome.status == "DRY_RUN_COMPLETE"
    assert outcome.submission_count == 0


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


def test_owner_attestation_is_dry_run_only_and_preserves_blank_review(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    shutil.copyfile(video_project_root / "runs" / smoke_id / "review.csv", review)
    preview = preview_motion_variations(
        video_project_root,
        VideoRunOptions(
            preset="motion",
            action="motion_generate",
            keyframe_id="hero",
            smoke_run_id=smoke_id,
            smoke_review_file=review,
            motion_variations=3,
            max_runway_credits=75,
            motion_smoke_qa_attested=True,
        ),
    )
    assert preview.status == "DRY_RUN_COMPLETE"
    assert preview.submission_count == 0
    with review.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    assert all(row[field] == "" for field in QA_FIELDS[4:])
    provider = FakeMotionProvider(synthetic_video)
    with pytest.raises(ExternalInputBlocked, match="planning-only"):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion",
                action="motion_generate",
                live=True,
                keyframe_id="hero",
                smoke_run_id=smoke_id,
                smoke_review_file=review,
                motion_variations=1,
                max_runway_credits=25,
                motion_smoke_qa_attested=True,
            ),
            provider=provider,
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "x"},
        )
    assert provider.submitted == []


def test_prompt_drift_fails_before_motion_provider_submission(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    prompt_path = video_project_root / "prompts/home-broll-v3.txt"
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


def test_p1_2_dry_run_allowed_when_p1_1_failed(
    video_project_root: Path, synthetic_video: Path
) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    with review.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    row.update({"eyes": "false", "motion": "false", "mtl_review_ready": "false"})
    with review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)

    outcome = preview_motion_variations(
        video_project_root,
        VideoRunOptions(
            preset="motion", action="motion_generate", keyframe_id="hero",
            smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=3,
            max_runway_credits=75,
        ),
    )
    request = json.loads((outcome.run_dir / "request.json").read_text())
    results = json.loads((outcome.run_dir / "provider-results.json").read_text())
    assert outcome.status == "DRY_RUN_COMPLETE"
    assert outcome.provider_call_count == 3
    assert outcome.submission_count == 0
    assert request["motion_smoke_review"]["status"] == "HUMAN_QA_FAILED"
    assert request["motion_smoke_review"]["live_authorized"] is False
    assert results["submission_count"] == 0
    assert results["results"] == []
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 3
    assert all(all(row[field] == "" for field in QA_FIELDS[4:]) for row in rows)


def test_p1_2_live_blocked_when_p1_1_failed_before_provider_construction(
    video_project_root: Path, synthetic_video: Path, monkeypatch
) -> None:
    smoke_id, review = _passing_motion_smoke(video_project_root, synthetic_video)
    with review.open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    row.update({"eyes": "false", "motion": "false", "mtl_review_ready": "false"})
    with review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    constructions = []
    monkeypatch.setattr(runner_module, "_create_motion_provider", lambda *_args, **_kwargs: constructions.append(True))

    with pytest.raises(ExternalInputBlocked, match="incomplete or failing|explicitly approved"):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion", action="motion_generate", live=True, keyframe_id="hero",
                smoke_run_id=smoke_id, smoke_review_file=review, motion_variations=3,
                max_runway_credits=75,
            ),
            environ={"VIDEO_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture-only"},
        )
    assert constructions == []


def test_p1_2_v7_parent_selects_unique_passing_candidate_offline(
    video_project_root: Path, synthetic_video: Path
) -> None:
    run_id, review = _reviewed_v7_parent(video_project_root, synthetic_video)

    outcome = preview_motion_variations(
        video_project_root,
        VideoRunOptions(
            preset="motion",
            action="motion_generate",
            keyframe_id="hero",
            smoke_run_id=run_id,
            smoke_review_file=review,
            motion_variations=3,
            max_runway_credits=75,
        ),
    )

    request = json.loads((outcome.run_dir / "request.json").read_text())
    results = json.loads((outcome.run_dir / "provider-results.json").read_text())
    assert outcome.status == "DRY_RUN_COMPLETE"
    assert outcome.submission_count == 0
    assert request["motion_smoke_review"]["status"] == "P1_2_LIVE_READY"
    assert request["motion_smoke_review"]["selected_candidate_id"] == (
        "v7-a-stability-first"
    )
    assert request["requests"][0]["prompt_sha256"] == (
        "1d60886bdbc31d2d161ecd652d6f57bdc9d5b836da58c4a026386a8206c1b1ca"
    )
    assert results["submission_count"] == 0
    assert results["results"] == []


def test_p1_2_v7_parent_rejects_ambiguous_human_pass_before_provider_construction(
    video_project_root: Path, synthetic_video: Path, monkeypatch
) -> None:
    run_id, review = _reviewed_v7_parent(video_project_root, synthetic_video)
    with review.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    for field in V7_PASS_FIELDS:
        rows[1][field] = "true"
    rows[1]["mtl_review_ready"] = "true"
    with review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    constructions: list[bool] = []
    monkeypatch.setattr(
        runner_module,
        "_create_motion_provider",
        lambda *_args, **_kwargs: constructions.append(True),
    )

    with pytest.raises(ExternalInputBlocked, match="exactly one|unique"):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion",
                action="motion_generate",
                live=True,
                keyframe_id="hero",
                smoke_run_id=run_id,
                smoke_review_file=review,
                motion_variations=1,
                max_runway_credits=25,
            ),
            environ={
                "VIDEO_ALLOW_LIVE_CALLS": "true",
                "RUNWAYML_API_SECRET": "fixture-only",
            },
        )
    assert constructions == []


def test_p1_2_v7_parent_rejects_review_provenance_mismatch(
    video_project_root: Path, synthetic_video: Path
) -> None:
    run_id, review = _reviewed_v7_parent(video_project_root, synthetic_video)
    with review.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    rows[0]["candidate"] = "not-the-parent-candidate.mp4"
    with review.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=QA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ExternalInputBlocked, match="provenance|candidate"):
        preview_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion",
                action="motion_generate",
                keyframe_id="hero",
                smoke_run_id=run_id,
                smoke_review_file=review,
                motion_variations=1,
                max_runway_credits=25,
            ),
        )


def test_p1_2_v7_parent_rejects_selected_media_hash_drift_before_provider_construction(
    video_project_root: Path, synthetic_video: Path, monkeypatch
) -> None:
    run_id, review = _reviewed_v7_parent(video_project_root, synthetic_video)
    results = json.loads(
        (video_project_root / "runs" / run_id / "provider-results.json").read_text()
    )
    selected = video_project_root / results["results"][0]["artifacts"][0]["path"]
    selected.write_bytes(selected.read_bytes() + b"drift")
    constructions: list[bool] = []
    monkeypatch.setattr(
        runner_module,
        "_create_motion_provider",
        lambda *_args, **_kwargs: constructions.append(True),
    )

    with pytest.raises(ExternalInputBlocked, match="hash"):
        generate_motion_variations(
            video_project_root,
            VideoRunOptions(
                preset="motion",
                action="motion_generate",
                live=True,
                keyframe_id="hero",
                smoke_run_id=run_id,
                smoke_review_file=review,
                motion_variations=1,
                max_runway_credits=25,
            ),
            environ={
                "VIDEO_ALLOW_LIVE_CALLS": "true",
                "RUNWAYML_API_SECRET": "fixture-only",
            },
        )
    assert constructions == []
