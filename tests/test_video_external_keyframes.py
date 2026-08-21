from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest
import yaml
from PIL import Image

import lala_workflow.video.keyframe_candidates as keyframe_module
from lala_workflow.hashing import sha256_file
from lala_workflow.video.keyframe_candidates import (
    EXTERNAL_K2_HUMAN_FIELDS,
    EXTERNAL_K2_REVIEW_FIELDS,
    ExternalKeyframeError,
    import_external_keyframe_candidate,
    promote_external_keyframe_candidate,
)


def _image(path: Path, *, fmt: str = "PNG") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (112, 140), (120, 30, 30)).save(path, format=fmt)
    return path


def _import(root: Path, source: Path, *, candidate_id: str = "k2-owner-test-01") -> dict:
    return import_external_keyframe_candidate(
        root,
        source=source,
        candidate_id=candidate_id,
        role="talking_medium_closeup",
        source_reference="Owner-supplied external K2 fixture",
    )


def _review_copy(root: Path, imported: dict, *, fill_pass: bool = True) -> Path:
    source = root / imported["blank_review_path"]
    target = root / "outputs/reviews" / f'{imported["candidate_id"]}-review.csv'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if fill_pass:
        with target.open(newline="", encoding="utf-8") as handle:
            row = next(csv.DictReader(handle))
        for field in EXTERNAL_K2_HUMAN_FIELDS:
            if field not in {"reviewer", "reviewed_at", "notes"}:
                row[field] = "PASS"
        row["reviewer"] = "Project owner"
        row["reviewed_at"] = "2026-08-21T12:00:00+08:00"
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=EXTERNAL_K2_REVIEW_FIELDS)
            writer.writeheader()
            writer.writerow(row)
    return target


def test_import_valid_png_preserves_exact_bytes_hash_and_blank_review(
    video_project_root: Path,
) -> None:
    source = _image(video_project_root / "incoming/k2.png")
    before = source.read_bytes()

    record = _import(video_project_root, source)

    staged = video_project_root / record["staged_path"]
    provenance = json.loads(
        (video_project_root / record["provenance_path"]).read_text(encoding="utf-8")
    )
    assert source.read_bytes() == staged.read_bytes() == before
    assert record["source_sha256"] == record["staged_sha256"] == sha256_file(source)
    assert provenance["source_type"] == "owner_supplied_external_candidate"
    assert provenance["approval_status"] == "PENDING_HUMAN_REVIEW"
    assert provenance["source_identity"] == "k2.png"
    assert not (
        {"provider", "provider_task_id", "model", "prompt_hash", "run_id"}
        & set(provenance)
    )
    with (video_project_root / record["blank_review_path"]).open(
        newline="", encoding="utf-8"
    ) as handle:
        row = next(csv.DictReader(handle))
    assert all(row[field] == "" for field in EXTERNAL_K2_HUMAN_FIELDS)
    assert record["status"] == "READY_FOR_K2_HUMAN_REVIEW"


def test_import_rejects_symlink_traversal_duplicate_and_existing_target(
    video_project_root: Path,
) -> None:
    source = _image(video_project_root / "incoming/k2.png")
    link = video_project_root / "incoming/link.png"
    link.symlink_to(source)
    with pytest.raises(ExternalKeyframeError, match="symlink"):
        _import(video_project_root, link, candidate_id="k2-link")
    with pytest.raises(ExternalKeyframeError, match="candidate ID"):
        _import(video_project_root, source, candidate_id="../escape")
    outside = _image(video_project_root.parent / "outside-k2.png")
    with pytest.raises(ExternalKeyframeError, match="source path traversal"):
        _import(
            video_project_root,
            Path("..") / outside.name,
            candidate_id="k2-source-traversal",
        )

    _import(video_project_root, source)
    with pytest.raises(ExternalKeyframeError, match="already exists"):
        _import(video_project_root, source)

    target_dir = video_project_root / "outputs/keyframes/candidates/k2-existing"
    target_dir.mkdir(parents=True)
    (target_dir / "candidate.png").write_bytes(b"occupied")
    with pytest.raises(ExternalKeyframeError, match="already exists"):
        _import(video_project_root, source, candidate_id="k2-existing")


@pytest.mark.parametrize("kind", ["invalid", "oversized", "extension_mismatch"])
def test_import_rejects_invalid_size_or_mime(
    video_project_root: Path, kind: str
) -> None:
    source = video_project_root / "incoming/k2.png"
    source.parent.mkdir(parents=True)
    if kind == "invalid":
        source.write_bytes(b"not an image")
    elif kind == "oversized":
        source.write_bytes(b"x" * (20 * 1024 * 1024 + 1))
    else:
        source = _image(video_project_root / "incoming/k2.jpg", fmt="PNG")
    with pytest.raises(ExternalKeyframeError):
        _import(video_project_root, source, candidate_id=f"k2-{kind}")


def test_blank_review_and_incomplete_attribution_cannot_promote(
    video_project_root: Path,
) -> None:
    imported = _import(video_project_root, _image(video_project_root / "incoming/k2.png"))
    blank = _review_copy(video_project_root, imported, fill_pass=False)
    with pytest.raises(ExternalKeyframeError, match="required K2 QA"):
        promote_external_keyframe_candidate(
            video_project_root, candidate_id=imported["candidate_id"], review_file=blank
        )

    reviewed = _review_copy(video_project_root, imported)
    with reviewed.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    row["reviewer"] = ""
    with reviewed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXTERNAL_K2_REVIEW_FIELDS)
        writer.writeheader(); writer.writerow(row)
    with pytest.raises(ExternalKeyframeError, match="reviewer"):
        promote_external_keyframe_candidate(
            video_project_root, candidate_id=imported["candidate_id"], review_file=reviewed
        )


def test_promotion_rejects_review_and_staged_symlinks(
    video_project_root: Path,
) -> None:
    imported = _import(video_project_root, _image(video_project_root / "incoming/k2.png"))
    reviewed = _review_copy(video_project_root, imported)
    review_link = video_project_root / "outputs/reviews/k2-review-link.csv"
    review_link.symlink_to(reviewed)

    with pytest.raises(ExternalKeyframeError, match="review file symlink"):
        promote_external_keyframe_candidate(
            video_project_root,
            candidate_id=imported["candidate_id"],
            review_file=review_link,
        )

    staged = video_project_root / imported["staged_path"]
    preserved = staged.with_name("preserved.png")
    staged.rename(preserved)
    staged.symlink_to(preserved)
    with pytest.raises(ExternalKeyframeError, match="staged_path symlink"):
        promote_external_keyframe_candidate(
            video_project_root,
            candidate_id=imported["candidate_id"],
            review_file=reviewed,
        )


def test_promotion_rejects_review_schema_and_staged_hash_drift(
    video_project_root: Path,
) -> None:
    imported = _import(video_project_root, _image(video_project_root / "incoming/k2.png"))
    reviewed = _review_copy(video_project_root, imported)
    with reviewed.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    incomplete_fields = tuple(
        field for field in EXTERNAL_K2_REVIEW_FIELDS if field != "mouth_pass"
    )
    with reviewed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=incomplete_fields)
        writer.writeheader()
        writer.writerow({field: row[field] for field in incomplete_fields})
    with pytest.raises(ExternalKeyframeError, match="schema mismatch"):
        promote_external_keyframe_candidate(
            video_project_root,
            candidate_id=imported["candidate_id"],
            review_file=reviewed,
        )

    drifted = _import(
        video_project_root,
        _image(video_project_root / "incoming/k2-drift.png"),
        candidate_id="k2-owner-drift-01",
    )
    drift_review = _review_copy(video_project_root, drifted)
    (video_project_root / drifted["staged_path"]).write_bytes(b"drifted bytes")
    with pytest.raises(ExternalKeyframeError, match="staged hash drift"):
        promote_external_keyframe_candidate(
            video_project_root,
            candidate_id=drifted["candidate_id"],
            review_file=drift_review,
        )


def test_naive_time_hash_drift_wrong_role_and_candidate_mismatch_reject(
    video_project_root: Path,
) -> None:
    imported = _import(video_project_root, _image(video_project_root / "incoming/k2.png"))
    reviewed = _review_copy(video_project_root, imported)
    with reviewed.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    row["reviewed_at"] = "2026-08-21T12:00:00"
    with reviewed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXTERNAL_K2_REVIEW_FIELDS)
        writer.writeheader(); writer.writerow(row)
    with pytest.raises(ExternalKeyframeError, match="timezone"):
        promote_external_keyframe_candidate(
            video_project_root, candidate_id=imported["candidate_id"], review_file=reviewed
        )

    reviewed = _review_copy(video_project_root, imported)
    with reviewed.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    row["candidate_id"] = "k2-other"
    with reviewed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXTERNAL_K2_REVIEW_FIELDS)
        writer.writeheader(); writer.writerow(row)
    with pytest.raises(ExternalKeyframeError, match="candidate_id"):
        promote_external_keyframe_candidate(
            video_project_root, candidate_id=imported["candidate_id"], review_file=reviewed
        )

    provenance_path = video_project_root / imported["provenance_path"]
    provenance = json.loads(provenance_path.read_text())
    provenance["role"] = "establishing_keyframe"
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    with pytest.raises(ExternalKeyframeError, match="role"):
        promote_external_keyframe_candidate(
            video_project_root,
            candidate_id=imported["candidate_id"],
            review_file=_review_copy(video_project_root, imported),
        )


def test_exact_byte_promotion_registers_k2_and_refuses_duplicate(
    video_project_root: Path,
) -> None:
    manifest_path = video_project_root / "configs/keyframe-manifest.yaml"
    initial_manifest = yaml.safe_load(manifest_path.read_text())
    initial_manifest["keyframes"].pop("talking")
    manifest_path.write_text(
        yaml.safe_dump(initial_manifest, sort_keys=False), encoding="utf-8"
    )
    imported = _import(video_project_root, _image(video_project_root / "incoming/k2.png"))
    reviewed = _review_copy(video_project_root, imported)
    before_manifest = yaml.safe_load(
        manifest_path.read_text()
    )

    promoted = promote_external_keyframe_candidate(
        video_project_root, candidate_id=imported["candidate_id"], review_file=reviewed
    )

    staged = video_project_root / imported["staged_path"]
    approved = video_project_root / promoted["approved_path"]
    assert staged.read_bytes() == approved.read_bytes()
    assert sha256_file(staged) == promoted["approved_sha256"] == sha256_file(approved)
    manifest = yaml.safe_load(
        manifest_path.read_text()
    )
    assert manifest["keyframes"]["hero"] == before_manifest["keyframes"]["hero"]
    assert manifest["keyframes"][imported["candidate_id"]]["roles"] == [
        "talking_medium_closeup"
    ]
    with pytest.raises(ExternalKeyframeError, match="already exists"):
        promote_external_keyframe_candidate(
            video_project_root, candidate_id=imported["candidate_id"], review_file=reviewed
        )


def test_promotion_publication_failure_restores_manifest_and_removes_new_targets(
    video_project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = video_project_root / "configs/keyframe-manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["keyframes"].pop("talking")
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    imported = _import(video_project_root, _image(video_project_root / "incoming/k2.png"))
    reviewed = _review_copy(video_project_root, imported)
    manifest_before = manifest_path.read_bytes()
    approved = (
        video_project_root
        / "assets/approved_keyframes"
        / f'{imported["candidate_id"]}.png'
    )
    promotion = approved.with_suffix(".promotion.json")

    def fail_manifest_publication(*_args, **_kwargs):
        raise OSError("synthetic manifest publication failure")

    monkeypatch.setattr(keyframe_module, "_atomic_write_yaml", fail_manifest_publication)
    with pytest.raises(OSError, match="publication failure"):
        promote_external_keyframe_candidate(
            video_project_root,
            candidate_id=imported["candidate_id"],
            review_file=reviewed,
        )

    assert manifest_path.read_bytes() == manifest_before
    assert not approved.exists()
    assert not promotion.exists()
