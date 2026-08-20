from __future__ import annotations

import json

from lala_workflow.cli import main


def test_character_cli_list_show_import_build_preview_and_reject(
    project_root, image_factory, capsys
) -> None:
    assert main(["character", "list", "--project-root", str(project_root)]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["active_character"] == "lala-v1"
    assert main(["character", "show", "lala-v1", "--project-root", str(project_root)]) == 0
    assert json.loads(capsys.readouterr().out)["profile"]["character_id"] == "lala-v1"

    face = image_factory(project_root / "inputs/front.png", color="red")
    body = image_factory(project_root / "inputs/body.png", color="green")
    three = image_factory(project_root / "inputs/three.png", color="blue")
    args = [
        "character",
        "import",
        "--face",
        str(face),
        "--full-body",
        str(body),
        "--three-quarter",
        str(three),
        "--name",
        "CLI Candidate",
        "--project-root",
        str(project_root),
    ]
    assert main(args) == 0
    character_id = json.loads(capsys.readouterr().out)["character_id"]
    assert main(["character", "build", character_id, "--project-root", str(project_root)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "READY_FOR_GENERATION"
    assert main([
        "character", "preview", character_id, "--dry-run", "--project-root", str(project_root)
    ]) == 0
    assert json.loads(capsys.readouterr().out)["technical_checks"]["paid_calls"] == "0"
    assert main(["character", "reject", character_id, "--project-root", str(project_root)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "REJECTED"


def test_character_cli_errors_are_safe_and_live_is_external_blocker(project_root, image_factory, capsys) -> None:
    assert main(["character", "show", "../../bad", "--project-root", str(project_root)]) == 2
    assert "does not exist" in capsys.readouterr().err
    assert main(["character", "activate", "lala-v1", "--project-root", str(project_root)]) == 2
    assert "already active" in capsys.readouterr().err
