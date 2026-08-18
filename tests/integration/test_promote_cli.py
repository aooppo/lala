import json
from pathlib import Path

from lala_workflow.cli import main
from tests.unit.test_promotion import make_reviewed_run


def test_promote_cli_prints_metadata_and_preserves_source(project_root: Path, capsys) -> None:
    run_id, source = make_reviewed_run(project_root)

    exit_code = main(
        [
            "promote",
            "--project-root",
            str(project_root),
            "--run-id",
            run_id,
            "--output-id",
            "output-001",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert source.is_file()
    assert (project_root / payload["approved_keyframe"]).is_file()


def test_promote_cli_rejects_unreviewed_output(project_root: Path, capsys) -> None:
    run_id, _source = make_reviewed_run(project_root, ready="")

    exit_code = main(
        [
            "promote",
            "--project-root",
            str(project_root),
            "--run-id",
            run_id,
            "--output-id",
            "output-001",
        ]
    )

    assert exit_code == 2
    assert "not marked video-keyframe-ready" in capsys.readouterr().err
