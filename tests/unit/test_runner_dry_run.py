import json
from pathlib import Path

import pytest
import yaml

from lala_workflow.runner import RunOptions, run_generation
from lala_workflow.storage import REQUIRED_RUN_FILES


class ExplodingProvider:
    def __getattribute__(self, name: str):
        if name.startswith("_"):
            return super().__getattribute__(name)
        raise AssertionError(f"dry run touched provider method {name}")


def test_dry_run_expands_count_seeds_and_writes_all_artifacts(project_root: Path) -> None:
    outcome = run_generation(
        project_root,
        RunOptions(preset="baseline_identity", count=3, seed=100, live=False),
        provider=ExplodingProvider(),
    )

    request = json.loads((outcome.run_dir / "request.json").read_text())
    result = json.loads((outcome.run_dir / "result.json").read_text())

    assert [item["seed"] for item in request["requests"]] == [100, 101, 102]
    assert len(request["requests"]) == 3
    assert result["status"] == "DRY_RUN"
    assert {path.name for path in outcome.run_dir.iterdir()} == set(REQUIRED_RUN_FILES)
    assert (outcome.run_dir / "review.csv").read_text().count("\n") == 1


def test_default_baseline_dry_run_contains_ten_requests(project_root: Path) -> None:
    outcome = run_generation(project_root, RunOptions(preset="baseline_identity"))

    request = json.loads((outcome.run_dir / "request.json").read_text())

    assert len(request["requests"]) == 10
    assert all(item["output_count"] == 1 for item in request["requests"])


def test_count_above_guardrail_is_rejected_before_run_creation(project_root: Path) -> None:
    with pytest.raises(ValueError, match="max_outputs_per_run"):
        run_generation(project_root, RunOptions(preset="baseline_identity", count=11))

    assert list((project_root / "runs").iterdir()) == []


def test_zero_concurrency_and_timeout_are_rejected(project_root: Path) -> None:
    with pytest.raises(ValueError, match="concurrency"):
        run_generation(
            project_root,
            RunOptions(preset="baseline_identity", concurrency=0),
        )
    with pytest.raises(ValueError, match="timeouts"):
        run_generation(
            project_root,
            RunOptions(preset="baseline_identity", poll_timeout_seconds=0),
        )


def test_explicitly_selected_qa_reference_can_be_used_by_future_preset(
    project_root: Path,
) -> None:
    preset_path = project_root / "configs/look-presets.yaml"
    preset_data = yaml.safe_load(preset_path.read_text())
    preset_data["presets"]["baseline_identity"]["references"].append("character_sheet")
    preset_path.write_text(yaml.safe_dump(preset_data, sort_keys=False))
    prompt_path = project_root / "prompts/baseline-identity-v1.txt"
    prompt_path.write_text(prompt_path.read_text() + " Use @qa_sheet as an additional reference.")

    outcome = run_generation(
        project_root,
        RunOptions(preset="baseline_identity", count=1),
    )

    payload = json.loads((outcome.run_dir / "request.json").read_text())
    assert [item["name"] for item in payload["requests"][0]["references"]] == [
        "face",
        "full_body",
        "character_sheet",
    ]
