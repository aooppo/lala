import json
from pathlib import Path
import pytest

from lala_workflow.providers.runway import RunwayImageProvider
from lala_workflow.runner import LiveCallBlocked, RunOptions, run_generation


def test_mocked_runway_live_path_persists_outputs_and_redacts_secret(
    project_root: Path, runway_capabilities, fake_runway_client, fake_png_downloader
) -> None:
    provider = RunwayImageProvider(
        runway_capabilities,
        api_key="integration-secret-sentinel",
        client=fake_runway_client,
        downloader=fake_png_downloader,
    )
    outcome = run_generation(
        project_root,
        RunOptions(preset="home_decor", count=2, live=True),
        provider=provider,
        environment={
            "RUNWAY_ALLOW_LIVE_CALLS": "true",
            "RUNWAYML_API_SECRET": "integration-secret-sentinel",
        },
    )

    assert len(fake_runway_client.text_to_image.requests) == 2
    assert all(
        len(item["reference_images"]) == 3
        for item in fake_runway_client.text_to_image.requests
    )
    assert len(outcome.result.outputs) == 2
    run_text = "\n".join(path.read_text(errors="ignore") for path in outcome.run_dir.iterdir())
    assert "integration-secret-sentinel" not in run_text
    assert json.loads((outcome.run_dir / "result.json").read_text())["status"] == "SUCCEEDED"


def test_live_guard_fails_before_run_or_provider_call(project_root: Path) -> None:
    class Provider:
        def __getattribute__(self, name: str):
            if name.startswith("_"):
                return super().__getattribute__(name)
            raise AssertionError("provider must not be touched")

    outcome = None
    try:
        run_generation(
            project_root,
            RunOptions(preset="baseline_identity", count=1, live=True),
            provider=Provider(),
            environment={},
        )
    except Exception as exc:
        assert "credentials and explicit paid-call permission" in str(exc)
    else:
        raise AssertionError(f"expected blocked live call, got {outcome}")

    assert list((project_root / "runs").iterdir()) == []


def test_smoke_test_cap_and_unknown_credit_estimate_fail_closed(project_root: Path) -> None:
    environment = {
        "RUNWAY_ALLOW_LIVE_CALLS": "true",
        "RUNWAYML_API_SECRET": "test-secret",
        "RUNWAY_LIVE_SMOKE_TEST": "true",
    }
    with pytest.raises(LiveCallBlocked, match="exactly one output"):
        run_generation(
            project_root,
            RunOptions(preset="baseline_identity", count=2, live=True),
            environment=environment,
        )

    environment["RUNWAY_LIVE_SMOKE_TEST"] = "false"
    with pytest.raises(LiveCallBlocked, match="estimate.*unavailable"):
        run_generation(
            project_root,
            RunOptions(
                preset="baseline_identity",
                count=1,
                live=True,
                max_estimated_credits=10,
            ),
            environment=environment,
        )

    assert list((project_root / "runs").iterdir()) == []
