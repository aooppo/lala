from __future__ import annotations

import csv
import json
from pathlib import Path

from lala_workflow.video.assembly import assemble_video
from lala_workflow.video.storage import QA_FIELDS, VIDEO_RUN_FILES
from tests.test_video_selection import generated_source_run, write_selection


def test_assembly_makes_two_deterministic_candidates_without_provider_calls(
    video_project_root: Path, synthetic_video: Path
) -> None:
    source = generated_source_run(video_project_root, synthetic_video)
    selection = write_selection(video_project_root, source)
    source_results_before = (source.run_dir / "provider-results.json").read_bytes()
    outcome = assemble_video(video_project_root, source.run_id, selection, final_edits=2)
    assert outcome.source_run_id == source.run_id
    assert outcome.submission_count == 0
    assert len(outcome.candidates) == 2
    assert [item.path.name for item in outcome.candidates] == [
        "lady-lala-product-page-candidate-v001.mp4",
        "lady-lala-product-page-candidate-v002.mp4",
    ]
    assert all(item.path.is_file() and len(item.sha256) == 64 for item in outcome.candidates)
    assert {path.name for path in outcome.run_dir.iterdir()} == set(VIDEO_RUN_FILES)
    commands = (outcome.run_dir / "edit-commands.txt").read_text(encoding="utf-8")
    assert commands.count("ffmpeg ") == 2
    assert "xfade=transition=fade" in commands
    with (outcome.run_dir / "review.csv").open(newline="", encoding="utf-8") as source_csv:
        rows = list(csv.DictReader(source_csv))
    assert len(rows) == 2
    assert all(all(row[field] == "" for field in QA_FIELDS[4:]) for row in rows)
    result = json.loads((outcome.run_dir / "provider-results.json").read_text(encoding="utf-8"))
    assert result["submission_count"] == 0
    assert (source.run_dir / "provider-results.json").read_bytes() == source_results_before
