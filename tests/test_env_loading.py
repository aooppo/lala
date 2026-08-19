from __future__ import annotations

from pathlib import Path

import pytest

from lala_workflow.env import (
    EnvironmentConfigError,
    load_project_env,
    migrate_legacy_voice_env,
    require_canonical_voice_env,
)


def test_missing_project_env_is_harmless_and_reports_only_status(tmp_path: Path) -> None:
    environ: dict[str, str] = {}
    status = load_project_env(tmp_path, environ=environ, enabled=True)
    assert status["HEYGEN_API_KEY"] == {"status": "missing", "length": 0}
    assert environ == {}
    assert ".env" not in str(status)


def test_project_env_loads_without_overriding_process_values(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "HEYGEN_API_KEY=file-secret\nHEYGEN_VOICE_ID=from-file\n", encoding="utf-8"
    )
    environ = {"HEYGEN_API_KEY": "process-secret"}
    status = load_project_env(tmp_path, environ=environ, enabled=True)
    assert environ["HEYGEN_API_KEY"] == "process-secret"
    assert environ["HEYGEN_VOICE_ID"] == "from-file"
    assert status["HEYGEN_API_KEY"] == {
        "status": "configured",
        "length": len("process-secret"),
    }
    assert "process-secret" not in str(status)
    assert "file-secret" not in str(status)


def test_test_process_skips_real_project_env_by_default(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("HEYGEN_API_KEY=must-not-load\n", encoding="utf-8")
    environ = {"PYTEST_CURRENT_TEST": "tests/test_env_loading.py::test"}
    load_project_env(tmp_path, environ=environ)
    assert "HEYGEN_API_KEY" not in environ


def test_legacy_voice_id_requires_explicit_migration(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentConfigError, match="init-env"):
        require_canonical_voice_env({"voice_id": "legacy-id"})
    (tmp_path / ".env").write_text("voice_id=legacy-id\n", encoding="utf-8")
    result = migrate_legacy_voice_env(tmp_path)
    assert result == {"status": "migrated", "variable": "HEYGEN_VOICE_ID"}
    raw = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "HEYGEN_VOICE_ID=legacy-id" in raw


def test_migration_refuses_to_replace_canonical_variable(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "voice_id=legacy-id\nHEYGEN_VOICE_ID=canonical-id\n", encoding="utf-8"
    )
    before = (tmp_path / ".env").read_bytes()
    with pytest.raises(EnvironmentConfigError, match="already configured"):
        migrate_legacy_voice_env(tmp_path)
    assert (tmp_path / ".env").read_bytes() == before
