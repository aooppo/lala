from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import pytest

from lala_workflow.cli import main
from lala_workflow.video.runner import VideoRunOptions, preview_video
from lala_workflow.video.storage import QA_FIELDS, VIDEO_RUN_FILES, VideoRunStorage
from lala_workflow.video.validation import ExternalInputBlocked


def test_dry_run_writes_exact_evidence_and_makes_zero_submissions(
    video_project_root: Path,
) -> None:
    before = set((video_project_root / "runs").iterdir())
    outcome = preview_video(
        video_project_root,
        VideoRunOptions(preset="tooltip", action="generate"),
    )
    after = set((video_project_root / "runs").iterdir())
    assert after - before == {outcome.run_dir}
    assert {path.name for path in outcome.run_dir.iterdir()} == set(VIDEO_RUN_FILES)
    assert outcome.provider_call_count == 3
    assert outcome.submission_count == 0
    assert (outcome.run_dir / "script.txt").read_bytes() == (
        video_project_root / "assets/scripts/tooltip.txt"
    ).read_bytes()
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.reader(source))
    assert rows == [list(QA_FIELDS)]
    cost = json.loads((outcome.run_dir / "cost.json").read_text(encoding="utf-8"))
    assert cost["talking_video_cost"] == 1.5
    assert cost["editing_cost"] == 0


def test_run_artifacts_refuse_rewrite(video_project_root: Path) -> None:
    outcome = preview_video(
        video_project_root,
        VideoRunOptions(preset="tooltip", action="generate"),
    )
    storage = VideoRunStorage(video_project_root)
    with pytest.raises(FileExistsError):
        storage.write_json_new(outcome.context, "cost.json", {})


def test_missing_production_inputs_create_no_run() -> None:
    root = Path(__file__).resolve().parents[1]
    before = set((root / "runs").iterdir())
    with pytest.raises(ExternalInputBlocked):
        preview_video(root, VideoRunOptions(preset="tooltip", action="generate"))
    assert set((root / "runs").iterdir()) == before


def test_video_cli_validate_and_preview_exit_contract(
    video_project_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["video", "validate", "--project-root", str(video_project_root)]) == 0
    assert '"status": "valid"' in capsys.readouterr().out
    assert (
        main(
            [
                "video",
                "generate",
                "--project-root",
                str(video_project_root),
                "--preset",
                "homepage",
                "--single-shot",
                "--dry-run",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert '"paid_calls": 0' in output
    assert '"planned_provider_calls": 3' in output


def test_video_cli_missing_inputs_returns_external_blocker(
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).resolve().parents[1]
    assert main(["video", "validate", "--project-root", str(root)]) == 4
    assert "BLOCKED_EXTERNAL:" in capsys.readouterr().err


def test_all_three_preview_plans_complete_within_sixty_seconds(
    video_project_root: Path,
) -> None:
    started = time.monotonic()
    outcomes = [
        preview_video(
            video_project_root, VideoRunOptions(preset=preset, action="generate")
        )
        for preset in ("product_page", "tooltip", "homepage")
    ]
    assert time.monotonic() - started < 60
    assert [outcome.provider_call_count for outcome in outcomes] == [9, 3, 12]
    assert all(outcome.submission_count == 0 for outcome in outcomes)
