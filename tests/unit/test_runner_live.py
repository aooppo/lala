from __future__ import annotations

import hashlib
from pathlib import Path

from lala_workflow.hashing import sha256_file
from lala_workflow.runner import RunOptions, run_generation


LIVE_ENV = {"RUNWAY_ALLOW_LIVE_CALLS": "true", "RUNWAYML_API_SECRET": "test-secret"}


def test_submission_retries_are_bounded_and_output_is_hashed(
    project_root: Path, fake_image_provider_factory
) -> None:
    provider = fake_image_provider_factory(submission_failures=2)

    outcome = run_generation(
        project_root,
        RunOptions(preset="baseline_identity", count=1, live=True, max_retries=2),
        provider=provider,
        environment=LIVE_ENV,
    )

    assert provider.submit_calls == 3
    assert outcome.result.status.value == "SUCCEEDED"
    assert len(outcome.result.outputs) == 1
    output = outcome.result.outputs[0]
    assert output.sha256 == sha256_file(project_root / output.file)
    events = (outcome.run_dir / "task-events.jsonl").read_text()
    assert "live_execution_authorized" in events


def test_terminal_task_failure_is_not_resubmitted_and_yields_partial(
    project_root: Path, fake_image_provider_factory
) -> None:
    provider = fake_image_provider_factory(failed_outputs={"output-002"})

    outcome = run_generation(
        project_root,
        RunOptions(preset="baseline_identity", count=2, live=True),
        provider=provider,
        environment=LIVE_ENV,
    )

    assert provider.submit_calls == 2
    assert outcome.result.status.value == "PARTIAL"
    assert len(outcome.result.outputs) == 1
    assert outcome.result.errors[0]["output_id"] == "output-002"
