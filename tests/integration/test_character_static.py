from __future__ import annotations

import json

from lala_workflow.characters.service import CharacterService
from lala_workflow.runner import RunOptions, run_generation


def test_static_dry_run_records_character_provenance_and_eight_artifacts(
    project_root, character_uploads
) -> None:
    service = CharacterService(project_root)
    candidate = service.import_character(character_uploads, created_by="test")
    service.build(candidate.character_id)
    outcome = run_generation(
        project_root,
        RunOptions(
            preset="baseline_identity",
            count=1,
            character_id=candidate.character_id,
            allow_staging_character=True,
        ),
    )
    assert len(list(outcome.run_dir.iterdir())) == 8
    request = json.loads((outcome.run_dir / "request.json").read_text())
    item = request["requests"][0]
    assert item["character_id"] == candidate.character_id
    assert item["character_profile_sha256"]
    assert set(item["character_source_hashes"]) == {"face", "full_body", "three_quarter"}
    hashes = json.loads((outcome.run_dir / "anchor-hashes.json").read_text())
    assert hashes["character"]["character_id"] == candidate.character_id
    assert hashes["character"]["selection_source"] == "explicit"
    assert [ref["name"] for ref in item["references"]] == ["face", "full_body"]


def test_default_static_run_uses_active_legacy_without_provider_contract_change(project_root) -> None:
    outcome = run_generation(project_root, RunOptions(preset="baseline_identity", count=1))
    request = json.loads((outcome.run_dir / "request.json").read_text())["requests"][0]
    assert request["character_id"] == "lala-v1"
    assert request["character_profile_sha256"]
    assert [(item["name"], item["tag"]) for item in request["references"]] == [
        ("face", "lala_face"),
        ("full_body", "lala_look"),
    ]
