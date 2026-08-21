from __future__ import annotations

import hashlib
import json
import struct
import wave
from pathlib import Path

import pytest
from PIL import Image

from lala_workflow.audio.validation import AudioValidationError, inspect_wav
from lala_workflow.video.validation import SourceValidationError, validate_approved_keyframe


def write_wav(path: Path, *, seconds: float = 0.1, silent: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 8_000
    sample_count = int(sample_rate * seconds)
    samples = b"".join(
        struct.pack("<h", 0 if silent else (500 if index % 2 else -500))
        for index in range(sample_count)
    )
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(samples)
    return path


def test_inspect_wav_reports_content_metadata(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "voice.wav", seconds=0.25)
    info = inspect_wav(path)
    assert info.duration_seconds == pytest.approx(0.25)
    assert info.sample_rate == 8_000
    assert info.channels == 1
    assert info.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("kind", ["silent", "empty", "not_wav"])
def test_inspect_wav_rejects_unusable_audio(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "voice.wav"
    if kind == "silent":
        write_wav(path, silent=True)
    elif kind == "empty":
        path.write_bytes(b"")
    else:
        path.write_bytes(b"not a wave")
    with pytest.raises(AudioValidationError):
        inspect_wav(path)


def test_validate_keyframe_requires_containment_hash_and_promotion(tmp_path: Path) -> None:
    path = tmp_path / "assets/approved_keyframes/hero.png"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (24, 32), "red").save(path)
    promotion = path.with_suffix(".json")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    promotion.write_text(
        "{"
        '"source_run_id":"goal1-run",'
        '"source_output_id":"output-001",'
        f'"image_sha256":"{digest}",'
        '"reviewer":"MTL reviewer",'
        '"approval_date":"2026-08-19T12:00:00+08:00"'
        "}",
        encoding="utf-8",
    )
    raw = {
        "path": "assets/approved_keyframes/hero.png",
        "sha256": digest,
        "source_run_id": "goal1-run",
        "source_output_id": "output-001",
        "promotion_record": "assets/approved_keyframes/hero.json",
        "reviewer": "MTL reviewer",
        "approved_at": "2026-08-19T12:00:00+08:00",
    }
    record = validate_approved_keyframe("hero", raw, tmp_path)
    assert record.width == 24
    assert record.height == 32
    assert record.sha256 == digest

    raw["sha256"] = "0" * 64
    with pytest.raises(SourceValidationError, match="digest"):
        validate_approved_keyframe("hero", raw, tmp_path)

    raw["sha256"] = digest
    raw.pop("reviewer")
    with pytest.raises(SourceValidationError, match="reviewer"):
        validate_approved_keyframe("hero", raw, tmp_path)


def test_validate_owner_supplied_legacy_keyframe_has_distinct_audited_provenance(
    tmp_path: Path,
) -> None:
    path = tmp_path / "assets/approved_keyframes/legacy.png"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (48, 32), "red").save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    package_hash = "a" * 64
    provenance = path.with_suffix(".provenance.json")
    raw = {
        "path": "assets/approved_keyframes/legacy.png",
        "sha256": digest,
        "provenance_type": "owner_supplied_legacy_asset",
        "provenance_record": "assets/approved_keyframes/legacy.provenance.json",
        "source_package": "owner-inputs.zip",
        "source_package_sha256": package_hash,
        "source_path": "01_keyframe/video_keyframe_candidate/legacy.png",
        "owner_approval_reference": "current user request section 1.2",
    }
    provenance.write_text(
        json.dumps(
            {
                **raw,
                "asset_path": raw["path"],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    record = validate_approved_keyframe("legacy", raw, tmp_path)

    assert record.provenance_type == "owner_supplied_legacy_asset"
    assert record.provenance_record == Path(
        "assets/approved_keyframes/legacy.provenance.json"
    )
    assert record.source_package == "owner-inputs.zip"
    assert record.source_package_sha256 == package_hash
    assert record.source_run_id is None
    assert record.reviewer is None


@pytest.mark.parametrize(
    "mutation,match",
    [
        ({"owner_approval_reference": None}, "owner_approval_reference"),
        ({"source_package_sha256": "not-a-hash"}, "source_package_sha256"),
        ({"source_run_id": "fabricated-run"}, "generated provenance"),
    ],
)
def test_validate_owner_supplied_legacy_keyframe_rejects_incomplete_or_fabricated_claims(
    tmp_path: Path, mutation: dict[str, str | None], match: str
) -> None:
    path = tmp_path / "assets/approved_keyframes/legacy.png"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (48, 32), "red").save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    raw: dict[str, str | None] = {
        "path": "assets/approved_keyframes/legacy.png",
        "sha256": digest,
        "provenance_type": "owner_supplied_legacy_asset",
        "provenance_record": "assets/approved_keyframes/legacy.provenance.json",
        "source_package": "owner-inputs.zip",
        "source_package_sha256": "a" * 64,
        "source_path": "01_keyframe/video_keyframe_candidate/legacy.png",
        "owner_approval_reference": "current user request section 1.2",
    }
    raw.update(mutation)
    provenance = path.with_suffix(".provenance.json")
    provenance.write_text(
        json.dumps({**raw, "asset_path": raw["path"]}, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(SourceValidationError, match=match):
        validate_approved_keyframe("legacy", raw, tmp_path)


def test_validate_external_promotion_accepts_truthful_exact_byte_provenance(
    tmp_path: Path,
) -> None:
    path = tmp_path / "assets/approved_keyframes/k2-owner-test-01.png"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (72, 90), "red").save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    review_digest = "b" * 64
    promotion = path.with_suffix(".promotion.json")
    payload = {
        "schema_version": "external-keyframe-promotion/v1",
        "provenance_type": "owner_supplied_external_promotion",
        "candidate_id": "k2-owner-test-01",
        "role": "talking_medium_closeup",
        "source_type": "owner_supplied_external_candidate",
        "source_reference": "Owner-supplied external K2 fixture",
        "source_identity": "k2.png",
        "source_sha256": digest,
        "staged_path": "outputs/keyframes/candidates/k2-owner-test-01/candidate.png",
        "staged_sha256": digest,
        "review_file": "outputs/reviews/k2-owner-test-01-review.csv",
        "review_sha256": review_digest,
        "reviewer": "Project owner",
        "approved_at": "2026-08-21T12:00:00+08:00",
        "approved_path": "assets/approved_keyframes/k2-owner-test-01.png",
        "approved_sha256": digest,
    }
    promotion.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    raw = {
        "path": payload["approved_path"],
        "sha256": digest,
        "provenance_type": payload["provenance_type"],
        "promotion_record": "assets/approved_keyframes/k2-owner-test-01.promotion.json",
        "source_candidate_id": payload["candidate_id"],
        "source_candidate_sha256": digest,
        "source_reference": payload["source_reference"],
        "review_file_sha256": review_digest,
        "reviewer": payload["reviewer"],
        "approved_at": payload["approved_at"],
        "roles": ["talking_medium_closeup"],
    }

    record = validate_approved_keyframe("k2-owner-test-01", raw, tmp_path)

    assert record.provenance_type == "owner_supplied_external_promotion"
    assert record.source_candidate_sha256 == digest
    assert record.review_file_sha256 == review_digest
    assert record.roles == ("talking_medium_closeup",)

    raw["provider"] = "runway"
    with pytest.raises(SourceValidationError, match="fabricated"):
        validate_approved_keyframe("k2-owner-test-01", raw, tmp_path)
    raw.pop("provider")

    payload["provider_task_id"] = "fabricated-task"
    promotion.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(SourceValidationError, match="fabricated"):
        validate_approved_keyframe("k2-owner-test-01", raw, tmp_path)
