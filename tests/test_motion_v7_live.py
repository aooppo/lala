from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import yaml

import lala_workflow.video.runner as runner_module
from lala_workflow.cli import build_parser
from lala_workflow.providers.base import ProviderSubmissionError
from lala_workflow.video.motion_v7 import V7_CANDIDATE_IDS
from lala_workflow.video.runner import recover_motion_v7_live, run_motion_v7_live
from lala_workflow.hashing import sha256_file
from lala_workflow.video.storage import QA_FIELDS, VIDEO_RUN_FILES
from lala_workflow.video.validation import ExternalInputBlocked
from tests.fakes_video import FakeMotionProvider


LIVE_ENV = {
    "VIDEO_ALLOW_LIVE_CALLS": "true",
    "RUNWAYML_API_SECRET": "fixture-only",
}


class EvidenceCheckingMotionProvider(FakeMotionProvider):
    def __init__(self, root: Path, fixture_video: Path) -> None:
        super().__init__(fixture_video)
        self.root = root
        self.http_request_count = 0
        self.plan_verified_before_submit: list[bool] = []

    def submit(self, request) -> str:
        run_dir = self.root / "runs" / request.run_id
        required = {
            "request.json",
            "resolved-config.yaml",
            "keyframe-hash.json",
            "shot-plan.json",
            "review.csv",
            "cost.json",
        }
        events = (run_dir / "task-events.jsonl").read_text(encoding="utf-8")
        self.plan_verified_before_submit.append(
            required.issubset({path.name for path in run_dir.iterdir()})
            and "preflight_evidence_verified" in events
            and len(self.validated) >= 3
        )
        self.http_request_count += 1
        return super().submit(request)

    def wait(self, task_id: str, timeout_seconds: float):
        self.http_request_count += 1
        return super().wait(task_id, timeout_seconds)


class FailSecondSubmissionProvider(EvidenceCheckingMotionProvider):
    def submit(self, request) -> str:
        if len(self.submitted) == 1:
            self.plan_verified_before_submit.append(True)
            self.submitted.append(request)
            self.http_request_count += 1
            raise ProviderSubmissionError("synthetic B submission failure")
        return super().submit(request)


class FailNthSubmissionProvider(EvidenceCheckingMotionProvider):
    def __init__(self, root: Path, fixture_video: Path, fail_number: int) -> None:
        super().__init__(root, fixture_video)
        self.fail_number = fail_number

    def submit(self, request) -> str:
        if len(self.submitted) + 1 == self.fail_number:
            self.plan_verified_before_submit.append(True)
            self.submitted.append(request)
            self.http_request_count += 1
            raise ProviderSubmissionError(
                f"synthetic submission {self.fail_number} failure"
            )
        return super().submit(request)


class CreditFailSecondSubmissionProvider(EvidenceCheckingMotionProvider):
    def submit(self, request) -> str:
        if len(self.submitted) == 1:
            self.plan_verified_before_submit.append(True)
            self.submitted.append(request)
            self.http_request_count += 1
            raise ProviderSubmissionError("synthetic insufficient credits")
        return super().submit(request)


def _run(root: Path, provider, **overrides):
    values = {
        "keyframe_id": "hero",
        "execute_live": True,
        "confirm_v7_batch": True,
        "max_runway_credits": 75,
        "provider": provider,
        "environ": LIVE_ENV,
    }
    values.update(overrides)
    return run_motion_v7_live(root, **values)


def _submission_count(provider) -> int:
    return len(provider.submitted)


def _recover(root: Path, parent_run_id: str, provider, **overrides):
    values = {
        "parent_run_id": parent_run_id,
        "execute_live": True,
        "confirm_missing_bc": True,
        "max_runway_credits": 50,
        "provider": provider,
        "environ": LIVE_ENV,
    }
    values.update(overrides)
    return recover_motion_v7_live(root, **values)


def _candidate16_fixture_constants(root: Path, monkeypatch) -> None:
    monkeypatch.setattr(runner_module, "CANDIDATE16_V7_KEYFRAME_ID", "hero")
    monkeypatch.setattr(
        runner_module,
        "CANDIDATE16_V7_KEYFRAME_SHA256",
        sha256_file(root / "assets/approved_keyframes/hero.png"),
    )


def test_v7_live_cli_is_fixed_and_requires_runtime_confirmations() -> None:
    parser = build_parser()
    parsed = parser.parse_args(
        [
            "video",
            "motion-v7-live",
            "--keyframe",
            "hero",
            "--execute-live",
            "--confirm-v7-batch",
            "--max-runway-credits",
            "75",
        ]
    )
    assert parsed.video_command == "motion-v7-live"
    assert parsed.execute_live is True
    assert parsed.confirm_v7_batch is True
    assert parsed.max_runway_credits == 75
    for forbidden in ("candidate", "only_a", "only_b", "only_c", "skip", "range"):
        assert not hasattr(parsed, forbidden)


def test_authorized_fake_v7_live_submits_exact_a_b_c_after_plan_evidence(
    video_project_root: Path, synthetic_video: Path, monkeypatch
) -> None:
    provider = EvidenceCheckingMotionProvider(video_project_root, synthetic_video)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("V7 live must not construct another provider or downstream stage")

    monkeypatch.setattr(runner_module, "_create_motion_provider", forbidden)
    monkeypatch.setattr(runner_module, "_create_talking_provider", forbidden)
    monkeypatch.setattr(runner_module, "_create_voice_provider", forbidden)

    outcome = _run(video_project_root, provider)

    assert outcome.status == "SUCCEEDED"
    assert outcome.provider_call_count == 3
    assert outcome.submission_count == 3
    assert [request.shot_id for request in provider.submitted] == list(V7_CANDIDATE_IDS)
    assert [request.prompt_sha256 for request in provider.submitted] == [
        "1d60886bdbc31d2d161ecd652d6f57bdc9d5b836da58c4a026386a8206c1b1ca",
        "b44906b8a786564406e42d740ebb7a4e68390b88c490697b5b54de8ca11ebb67",
        "5dbaa0f0fd8c2f9ca5e83c8f661aeb598dc4e831be5e77cae34cb3a4649f0f32",
    ]
    assert provider.plan_verified_before_submit == [True, True, True]
    assert len(provider.submitted) == 3
    assert {path.name for path in outcome.run_dir.iterdir()} == set(VIDEO_RUN_FILES)

    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    assert results["submission_attempts"] == 3
    assert results["submission_count"] == 3
    assert results["provider_task_ids"] == [
        f"fake-talking-{request.request_id}" for request in provider.submitted
    ]
    assert [item["candidate_id"] for item in results["results"]] == list(V7_CANDIDATE_IDS)
    assert [item["submission_state"] for item in results["results"]] == [
        "submitted",
        "submitted",
        "submitted",
    ]
    assert results["http_request_count"] == 6
    assert results["http_request_count_known"] is True
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 3
    assert all(all(row[field] == "" for field in QA_FIELDS[4:]) for row in rows)


@pytest.mark.parametrize("candidate", ("a", "b"))
def test_v7_live_oversized_prompt_blocks_all_submissions(
    video_project_root: Path, synthetic_video: Path, candidate: str
) -> None:
    prompt = video_project_root / f"prompts/p1-1-motion-v7-{candidate}-v1.txt"
    prompt.write_text("x" * 1000, encoding="utf-8")
    provider = EvidenceCheckingMotionProvider(video_project_root, synthetic_video)
    with pytest.raises(Exception, match="UTF-16|hash"):
        _run(video_project_root, provider)
    assert _submission_count(provider) == 0


def test_v7_live_missing_c_prompt_blocks_all_submissions(
    video_project_root: Path, synthetic_video: Path
) -> None:
    (video_project_root / "prompts/p1-1-motion-v7-c-v1.txt").unlink()
    provider = EvidenceCheckingMotionProvider(video_project_root, synthetic_video)
    with pytest.raises(Exception, match="prompt"):
        _run(video_project_root, provider)
    assert _submission_count(provider) == 0


def test_v7_live_wrong_candidate_count_blocks_all_submissions(
    video_project_root: Path, synthetic_video: Path
) -> None:
    path = video_project_root / "configs/motion-v7.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["candidates"].pop()
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    provider = EvidenceCheckingMotionProvider(video_project_root, synthetic_video)
    with pytest.raises(Exception, match="exactly three"):
        _run(video_project_root, provider)
    assert _submission_count(provider) == 0


def test_v7_live_wrong_order_blocks_all_submissions(
    video_project_root: Path, synthetic_video: Path
) -> None:
    path = video_project_root / "configs/motion-v7.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["candidates"][0], data["candidates"][1] = data["candidates"][1], data["candidates"][0]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    provider = EvidenceCheckingMotionProvider(video_project_root, synthetic_video)
    with pytest.raises(Exception, match="order"):
        _run(video_project_root, provider)
    assert _submission_count(provider) == 0


def test_v7_live_wrong_prompt_mapping_blocks_all_submissions(
    video_project_root: Path, synthetic_video: Path
) -> None:
    path = video_project_root / "configs/motion-v7.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["candidates"][1]["prompt_file"] = "prompts/p1-1-motion-v7-a-v1.txt"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    provider = EvidenceCheckingMotionProvider(video_project_root, synthetic_video)
    with pytest.raises(Exception, match="mapping|duplicate"):
        _run(video_project_root, provider)
    assert _submission_count(provider) == 0


@pytest.mark.parametrize(
    ("override", "match"),
    (
        ({"execute_live": False}, "execute-live"),
        ({"confirm_v7_batch": False}, "confirm-v7-batch"),
        ({"environ": {}}, "VIDEO_ALLOW_LIVE_CALLS"),
    ),
)
def test_v7_live_missing_authorization_blocks_all_submissions(
    video_project_root: Path, synthetic_video: Path, override: dict, match: str
) -> None:
    provider = EvidenceCheckingMotionProvider(video_project_root, synthetic_video)
    with pytest.raises(ExternalInputBlocked, match=match):
        _run(video_project_root, provider, **override)
    assert _submission_count(provider) == 0


def test_v7_live_invalid_source_blocks_all_submissions(
    video_project_root: Path, synthetic_video: Path
) -> None:
    (video_project_root / "assets/approved_keyframes/hero.png").unlink()
    provider = EvidenceCheckingMotionProvider(video_project_root, synthetic_video)
    with pytest.raises(Exception, match="keyframe|source|hash|exist"):
        _run(video_project_root, provider)
    assert _submission_count(provider) == 0


def test_v7_live_unknown_credit_estimate_blocks_all_submissions(
    video_project_root: Path, synthetic_video: Path
) -> None:
    path = video_project_root / "configs/providers.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data["providers"]["runway"]["supported_models"]["gen4_turbo"]["credits_per_second"]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    provider = EvidenceCheckingMotionProvider(video_project_root, synthetic_video)
    with pytest.raises(ExternalInputBlocked, match="estimate"):
        _run(video_project_root, provider)
    assert _submission_count(provider) == 0


def test_v7_live_a_success_b_submission_error_stops_without_retry(
    video_project_root: Path, synthetic_video: Path
) -> None:
    provider = FailSecondSubmissionProvider(video_project_root, synthetic_video)
    outcome = _run(video_project_root, provider)

    assert outcome.status == "PARTIAL"
    assert outcome.submission_count == 1
    assert [request.shot_id for request in provider.submitted] == list(V7_CANDIDATE_IDS[:2])
    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    assert results["submission_attempts"] == 2
    assert results["submission_count"] == 1
    assert len(results["provider_task_ids"]) == 1
    assert [item["submission_state"] for item in results["results"]] == [
        "submitted",
        "failed",
        "not_submitted",
    ]
    assert results["results"][0]["provider_task_id"]
    assert results["results"][1]["provider_task_id"] is None
    assert results["results"][2]["submission_attempts"] == 0
    assert results["automatic_retries"] == 0
    assert results["replacement_tasks"] == 0
    assert {path.name for path in outcome.run_dir.iterdir()} == set(VIDEO_RUN_FILES)


@pytest.mark.parametrize(
    ("fail_number", "expected_status", "expected_states", "expected_task_ids"),
    (
        (1, "FAILED", ["failed", "not_submitted", "not_submitted"], 0),
        (3, "PARTIAL", ["submitted", "submitted", "failed"], 2),
    ),
)
def test_v7_live_fail_stop_covers_a_and_c_submission_errors(
    video_project_root: Path,
    synthetic_video: Path,
    fail_number: int,
    expected_status: str,
    expected_states: list[str],
    expected_task_ids: int,
) -> None:
    provider = FailNthSubmissionProvider(
        video_project_root, synthetic_video, fail_number
    )
    outcome = _run(video_project_root, provider)
    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    assert outcome.status == expected_status
    assert len(provider.submitted) == fail_number
    assert results["submission_attempts"] == fail_number
    assert len(results["provider_task_ids"]) == expected_task_ids
    assert [item["submission_state"] for item in results["results"]] == expected_states
    assert results["automatic_retries"] == 0
    assert results["replacement_tasks"] == 0


def test_v7_recovery_submits_only_b_c_and_stages_blank_owner_review(
    video_project_root: Path, synthetic_video: Path, monkeypatch
) -> None:
    _candidate16_fixture_constants(video_project_root, monkeypatch)
    parent_provider = CreditFailSecondSubmissionProvider(video_project_root, synthetic_video)
    parent = _run(video_project_root, parent_provider)
    provider = FakeMotionProvider(synthetic_video)

    outcome = _recover(video_project_root, parent.run_id, provider)

    assert outcome.status == "SUCCEEDED"
    assert outcome.provider_call_count == 2
    assert outcome.submission_count == 2
    assert [request.shot_id for request in provider.submitted] == list(V7_CANDIDATE_IDS[1:])
    assert all(request.max_retries == 0 for request in provider.submitted)
    results = json.loads(
        (outcome.run_dir / "provider-results.json").read_text(encoding="utf-8")
    )
    assert [item["candidate_id"] for item in results["results"]] == list(V7_CANDIDATE_IDS)
    assert results["results"][0]["evidence_source_run_id"] == parent.run_id
    assert results["automatic_retries"] == 0
    assert results["replacement_tasks"] == 0
    assert results["combined_confirmed_actual_runway_credits"] is None
    package = video_project_root / "outputs/reviews/candidate16-v7"
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "READY_FOR_OWNER_CANDIDATE16_V7_REVIEW"
    assert manifest["winner"] is None
    assert manifest["coffee_table_executed"] is False
    assert len(manifest["media"]) == 3
    comparison = video_project_root / manifest["comparison"]["path"]
    assert comparison.is_file()
    assert manifest["comparison"]["sha256"] == sha256_file(comparison)
    assert manifest["comparison"]["layout"] == "left=A, center=B, right=C"
    with (package / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 3
    assert all(all(row[field] == "" for field in QA_FIELDS[4:]) for row in rows)


def test_v7_recovery_exact_cap_and_duplicate_evidence_block_before_submission(
    video_project_root: Path, synthetic_video: Path, monkeypatch
) -> None:
    _candidate16_fixture_constants(video_project_root, monkeypatch)
    parent = _run(
        video_project_root,
        CreditFailSecondSubmissionProvider(video_project_root, synthetic_video),
    )
    blocked_provider = FakeMotionProvider(synthetic_video)
    with pytest.raises(ExternalInputBlocked, match="exact.*50"):
        _recover(
            video_project_root,
            parent.run_id,
            blocked_provider,
            max_runway_credits=75,
        )
    assert blocked_provider.submitted == []

    first_provider = FakeMotionProvider(synthetic_video)
    _recover(video_project_root, parent.run_id, first_provider)
    duplicate_provider = FakeMotionProvider(synthetic_video)
    with pytest.raises(ExternalInputBlocked, match="already exists"):
        _recover(video_project_root, parent.run_id, duplicate_provider)
    assert duplicate_provider.submitted == []


def test_v7_recovery_parent_a_hash_tamper_blocks_all_submissions(
    video_project_root: Path, synthetic_video: Path, monkeypatch
) -> None:
    _candidate16_fixture_constants(video_project_root, monkeypatch)
    parent = _run(
        video_project_root,
        CreditFailSecondSubmissionProvider(video_project_root, synthetic_video),
    )
    results = json.loads((parent.run_dir / "provider-results.json").read_text(encoding="utf-8"))
    a_path = video_project_root / results["results"][0]["artifacts"][0]["path"]
    a_path.write_bytes(b"tampered")
    provider = FakeMotionProvider(synthetic_video)
    with pytest.raises(ExternalInputBlocked, match="hash-mismatched"):
        _recover(video_project_root, parent.run_id, provider)
    assert provider.submitted == []
