from __future__ import annotations

import shutil
from types import SimpleNamespace

import pytest
from PIL import Image

from lala_workflow.characters.domain import CharacterStatus
from lala_workflow.characters.preview import GeneratedPreview, StaticRunnerPreviewOperation
from lala_workflow.characters.errors import PreviewUnavailableError
from lala_workflow.characters.service import CharacterService


class FakeStatic:
    def generate(self, profile, build, destination):
        Image.new("RGB", (128, 192), "purple").save(destination)
        return GeneratedPreview(
            destination,
            source_run_id="fake-static-run",
            provider_task_id="fake-static-task",
            provenance={"simulated_test_fixture": True},
        )


class FakeMotion:
    def __init__(self, video):
        self.video = video

    def generate(self, profile, build, static_preview, destination):
        shutil.copyfile(self.video, destination)
        return GeneratedPreview(
            destination,
            source_run_id="fake-motion-run",
            provider_task_id="fake-motion-task",
            provenance={"static_preview_sha256": static_preview.sha256, "simulated_test_fixture": True},
            subject_lock={"status": "WITHIN_THRESHOLD", "measurement_scope": "test_fixture"},
        )


def test_offline_preview_plans_zero_calls_and_cannot_activate(project_root, character_uploads) -> None:
    service = CharacterService(project_root)
    profile = service.import_character(character_uploads, created_by="test")
    service.build(profile.character_id)
    result = service.preview(profile.character_id)
    assert result.status is CharacterStatus.READY_FOR_GENERATION
    assert result.static_preview is None and result.motion_preview is None
    assert result.technical_checks["paid_calls"] == "0"
    assert service.list_characters().active_character == "lala-v1"


def test_default_live_preview_preflights_all_gates_before_any_call(
    project_root, character_uploads, monkeypatch
) -> None:
    for name in (
        "RUNWAY_ALLOW_LIVE_CALLS",
        "RUNWAYML_API_SECRET",
        "VIDEO_ALLOW_LIVE_CALLS",
        "VIDEO_MOTION_LIVE_SMOKE_TEST",
    ):
        monkeypatch.delenv(name, raising=False)
    service = CharacterService(project_root)
    profile = service.import_character(character_uploads, created_by="test")
    service.build(profile.character_id)
    with pytest.raises(PreviewUnavailableError):
        service.preview(profile.character_id, live=True)
    assert list((project_root / "runs").glob("LALA-*")) == []
    assert service.list_characters().active_character == "lala-v1"


def test_fake_static_and_motion_create_verified_preview_only_evidence(
    project_root, character_uploads, synthetic_video
) -> None:
    service = CharacterService(
        project_root,
        static_preview_operation=FakeStatic(),
        motion_preview_operation=FakeMotion(synthetic_video),
    )
    profile = service.import_character(character_uploads, created_by="test")
    service.build(profile.character_id)
    result = service.preview(profile.character_id, live=True)
    assert result.status is CharacterStatus.READY_FOR_APPROVAL
    assert result.static_preview and result.motion_preview
    assert result.static_preview.provenance["production_approved"] is False
    assert result.motion_preview.provenance["preview_only"] is True
    assert result.motion_preview.path.name.endswith("-motion.mp4")
    assert result.static_preview.path.name.endswith("-static.png")
    assert result.subject_lock["authority"] == "diagnostic_only_not_automatic_approval"
    assert service.show(profile.character_id).profile.status is CharacterStatus.READY_FOR_APPROVAL
    assert service.list_characters().active_character == "lala-v1"


def test_partial_failure_preserves_static_preview(project_root, character_uploads) -> None:
    class FailedMotion:
        def generate(self, *_args, **_kwargs):
            raise RuntimeError("simulated motion failure")

    service = CharacterService(
        project_root,
        static_preview_operation=FakeStatic(),
        motion_preview_operation=FailedMotion(),
    )
    profile = service.import_character(character_uploads, created_by="test")
    service.build(profile.character_id)
    result = service.preview(profile.character_id, live=True)
    assert result.status is CharacterStatus.FAILED
    assert result.static_preview is not None
    assert result.motion_preview is None
    assert service.list_characters().active_character == "lala-v1"
    first_path = result.static_preview.path
    retried = service.preview(profile.character_id, live=True)
    assert retried.static_preview is not None
    assert retried.static_preview.path != first_path
    assert (project_root / first_path).is_file()


def test_static_preview_cost_is_explicitly_unknown_when_provider_exposes_no_billing(
    project_root, character_uploads, monkeypatch
) -> None:
    service = CharacterService(project_root)
    profile = service.import_character(character_uploads, created_by="test")
    build = service.build(profile.character_id)
    output = project_root / "static-provider-output.png"
    Image.new("RGB", (128, 192), "purple").save(output)
    outcome = SimpleNamespace(
        run_id="STATIC-RUN",
        result=SimpleNamespace(
            outputs=(SimpleNamespace(file=output.relative_to(project_root)),),
            tasks=({"provider_task_id": "static-task"},),
            requests=({"prompt": {"sha256": "a" * 64}, "references": ()},),
            status=SimpleNamespace(value="SUCCEEDED"),
        ),
    )
    monkeypatch.setattr("lala_workflow.runner.run_generation", lambda *_a, **_k: outcome)
    generated = StaticRunnerPreviewOperation(
        project_root,
        environment={"RUNWAY_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "fixture"},
    ).generate(profile, build, project_root / "unused.png")
    assert generated.provenance["cost_status"] == "UNKNOWN_NOT_EXPOSED_BY_PROVIDER"
    assert generated.provenance["estimated_credits"] is None
    assert generated.provenance["estimated_usd"] is None
