import json
from datetime import UTC, datetime
from pathlib import Path

from lala_workflow.storage import REQUIRED_RUN_FILES, RunStorage


def test_run_id_allocation_is_collision_safe(tmp_path: Path) -> None:
    storage = RunStorage(tmp_path)
    now = datetime(2026, 8, 18, 21, 0, 0, tzinfo=UTC)

    first = storage.create_run("runway", "baseline_identity", now=now)
    second = storage.create_run("runway", "baseline_identity", now=now)

    assert first.run_id.endswith("-001")
    assert second.run_id.endswith("-002")
    assert first.path != second.path


def test_storage_initializes_and_writes_required_artifacts(tmp_path: Path) -> None:
    storage = RunStorage(tmp_path)
    run = storage.create_run("runway", "baseline_identity")

    storage.write_json(run, "request.json", {"secret": "safe-value"})
    storage.write_yaml(run, "resolved-config.yaml", {"count": 1})
    storage.write_text(run, "resolved-prompt.txt", "prompt")
    storage.write_json(run, "anchor-hashes.json", {"face": "a" * 64})
    storage.append_event(run, "validated", {"count": 1})
    storage.write_json(run, "result.json", {"status": "DRY_RUN"})
    storage.write_text(run, "review.csv", "run_id\n")
    storage.write_text(run, "summary.md", "# Summary\n")

    assert set(REQUIRED_RUN_FILES) == {path.name for path in run.path.iterdir()}
    assert json.loads((run.path / "request.json").read_text()) == {"secret": "[REDACTED]"}
    assert json.loads((run.path / "task-events.jsonl").read_text().splitlines()[0])["event"] == (
        "validated"
    )
