import json
from pathlib import Path

from lala_workflow.cli import main
from lala_workflow.storage import RunStorage


def test_report_command_is_read_only_and_prints_existing_summary(
    project_root: Path, dry_run_outcome, capsys
) -> None:
    before = {path.name: path.stat().st_mtime_ns for path in dry_run_outcome.run_dir.iterdir()}

    exit_code = main(
        [
            "report",
            "--project-root",
            str(project_root),
            "--run-id",
            dry_run_outcome.run_id,
        ]
    )

    after = {path.name: path.stat().st_mtime_ns for path in dry_run_outcome.run_dir.iterdir()}
    assert exit_code == 0
    assert dry_run_outcome.run_id in capsys.readouterr().out
    assert before == after


def test_report_rejects_path_traversal(project_root: Path, capsys) -> None:
    exit_code = main(
        ["report", "--project-root", str(project_root), "--run-id", "../outside"]
    )

    assert exit_code == 2
    assert "invalid run ID" in capsys.readouterr().err


def test_storage_redacts_secret_from_result_and_events(project_root: Path) -> None:
    secret = "result-secret-sentinel"
    storage = RunStorage(project_root, secrets=(secret,))
    run = storage.create_run("runway", "baseline_identity")

    storage.write_json(
        run,
        "result.json",
        {"status": "FAILED", "error": f"Bearer {secret}", "authorization": secret},
    )
    storage.append_event(run, "failed", {"message": secret})

    text = (run.path / "result.json").read_text() + (run.path / "task-events.jsonl").read_text()
    assert secret not in text
    assert "[REDACTED]" in text
    assert json.loads((run.path / "result.json").read_text())["authorization"] == "[REDACTED]"
