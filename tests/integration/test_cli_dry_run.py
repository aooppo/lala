import json
from pathlib import Path
from types import SimpleNamespace

from lala_workflow.cli import main
from lala_workflow.domain import RunStatus


def test_validate_command_reports_anchors_presets_and_versions(
    project_root: Path, capsys
) -> None:
    exit_code = main(["validate", "--project-root", str(project_root)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "baseline_identity" in output
    assert "home_decor" in output
    assert "2024-11-06" in output
    assert "5.15.0" in output


def test_generate_dry_run_cli_creates_request_preview(project_root: Path, capsys) -> None:
    exit_code = main(
        [
            "generate",
            "--project-root",
            str(project_root),
            "--preset",
            "product_page_clean",
            "--count",
            "2",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    cli_payload = json.loads(output)
    assert exit_code == 0
    run_dirs = list((project_root / "runs").iterdir())
    assert len(run_dirs) == 1
    payload = json.loads((run_dirs[0] / "request.json").read_text())
    assert len(payload["requests"]) == 2
    assert cli_payload["mode"] == "dry-run"
    assert cli_payload["requests"] == 2
    assert cli_payload["status"] == "DRY_RUN"


def test_generate_cli_rejects_conflicting_modes(project_root: Path, capsys) -> None:
    exit_code = main(
        [
            "generate",
            "--project-root",
            str(project_root),
            "--preset",
            "baseline_identity",
            "--dry-run",
            "--live",
        ]
    )

    assert exit_code == 2
    assert "mutually exclusive" in capsys.readouterr().err


def test_generate_live_cli_returns_provider_failure_exit_status(
    project_root: Path, monkeypatch, capsys
) -> None:
    outcome = SimpleNamespace(
        run_id="LALA-RUNWAY-20260818-210000-BASELINE-IDENTITY-001",
        run_dir=project_root / "runs/LALA-RUNWAY-20260818-210000-BASELINE-IDENTITY-001",
        result=SimpleNamespace(
            requests=({},),
            status=RunStatus.FAILED,
            outputs=(),
        ),
    )
    monkeypatch.setattr("lala_workflow.cli.run_generation", lambda *_args, **_kwargs: outcome)

    exit_code = main(
        [
            "generate",
            "--project-root",
            str(project_root),
            "--preset",
            "baseline_identity",
            "--count",
            "1",
            "--live",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["mode"] == "live"
    assert payload["status"] == "FAILED"
