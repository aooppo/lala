from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from lala_workflow.video.scripts import ScriptIntegrityError, capture_script, load_script_record


def metadata(path: str, content: bytes) -> dict[str, str]:
    return {
        "path": path,
        "version": "mtl-2026-08-19",
        "sha256": hashlib.sha256(content).hexdigest(),
        "source_reference": "Synthetic MTL source fixture",
    }


def test_script_record_preserves_exact_utf8_bytes(tmp_path: Path) -> None:
    content = "Exact MTL punctuation!\r\nSecond line.\n".encode()
    path = tmp_path / "assets/scripts/tooltip.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(content)

    record = load_script_record(
        "tooltip",
        metadata("assets/scripts/tooltip.txt", content),
        tmp_path,
        source="MTL",
        modification_policy="immutable",
    )

    assert record.content == content
    assert record.text == content.decode("utf-8")
    assert record.sha256 == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("version", None, "version"),
        ("source_reference", None, "source_reference"),
        ("sha256", None, "sha256"),
        ("sha256", "0" * 64, "digest"),
    ],
)
def test_script_record_rejects_missing_or_changed_metadata(
    tmp_path: Path, field: str, value: str | None, message: str
) -> None:
    content = b"MTL exact text\n"
    path = tmp_path / "assets/scripts/homepage.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    raw = metadata("assets/scripts/homepage.txt", content)
    raw[field] = value

    with pytest.raises(ScriptIntegrityError, match=message):
        load_script_record(
            "homepage", raw, tmp_path, source="MTL", modification_policy="immutable"
        )


def test_script_record_rejects_wrong_attribution_or_path_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"copy")
    raw = metadata("outside.txt", b"copy")
    with pytest.raises(ScriptIntegrityError, match="MTL"):
        load_script_record("tooltip", raw, tmp_path, source="author", modification_policy="immutable")
    with pytest.raises(ScriptIntegrityError, match="assets/scripts"):
        load_script_record("tooltip", raw, tmp_path, source="MTL", modification_policy="immutable")


def test_capture_script_is_exclusive_and_byte_exact(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    target = tmp_path / "run/script.txt"
    source.write_bytes(b"line one\r\nline two\n")
    capture_script(source, target)
    assert target.read_bytes() == source.read_bytes()
    with pytest.raises(FileExistsError):
        capture_script(source, target)
