from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from ..domain import utc_now
from ..hashing import sha256_file
from .naming import approved_filename, next_approved_path
from .review import ReviewError, load_external_review_row
from .storage import VIDEO_RUN_FILES


class PromotionError(ValueError):
    pass


def promote_video(
    project_root: Path,
    run_id: str,
    candidate: str,
    *,
    review_file: Path,
    approved_version: int | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    if not run_id or "/" in run_id or "\\" in run_id:
        raise PromotionError("invalid video run ID")
    run_dir = (root / "runs" / run_id).resolve()
    if (root / "runs").resolve() not in run_dir.parents or not run_dir.is_dir():
        raise PromotionError(f"video run does not exist: {run_id}")
    actual_files = {path.name for path in run_dir.iterdir() if path.is_file()}
    if actual_files != set(VIDEO_RUN_FILES):
        raise PromotionError("video promotion requires an exact thirteen-artifact run")
    request = _read_json(run_dir / "request.json")
    results = _read_json(run_dir / "provider-results.json")
    if (
        results.get("status") == "REVIEW_READY_DRAFT_ASSETS"
        or results.get("contains_draft_brand_assets") is True
        or request.get("contains_draft_brand_assets") is True
    ):
        raise PromotionError(
            "candidates containing draft brand assets cannot be promoted"
        )
    if request.get("action") != "assemble" or results.get("status") != "REVIEW_READY":
        raise PromotionError("only review-ready final assembly candidates can be promoted")
    matches = [
        item
        for item in results.get("results", [])
        if candidate in {item.get("candidate"), item.get("artifact_id"), item.get("video_id")}
    ]
    if len(matches) != 1:
        raise PromotionError(f"candidate must resolve exactly once: {candidate}")
    evidence = matches[0]
    candidate_name = str(evidence.get("candidate") or "")
    try:
        review, review_evidence = load_external_review_row(
            root, run_dir, candidate_name, review_file, require_ready=True
        )
    except ReviewError as exc:
        raise PromotionError(str(exc)) from exc
    relative = Path(str(evidence.get("path") or ""))
    if relative.is_absolute() or ".." in relative.parts:
        raise PromotionError("candidate path is invalid")
    source = (root / relative).resolve()
    allowed = (root / "outputs/final" / run_id).resolve()
    if allowed not in source.parents or not source.is_file():
        raise PromotionError("candidate is missing or outside the assembly output directory")
    source_hash = sha256_file(source)
    if source_hash != evidence.get("sha256"):
        raise PromotionError("candidate hash no longer matches run evidence")
    destination_dir = root / "outputs/approved_videos"
    destination_dir.mkdir(parents=True, exist_ok=True)
    preset = str(request.get("preset") or "")
    next_target = next_approved_path(destination_dir, preset)
    if approved_version is not None:
        if approved_version < 1:
            raise PromotionError("approved version must be positive")
        target = destination_dir / approved_filename(preset, approved_version)
        sidecar = target.with_suffix(".json")
        if target.exists() or sidecar.exists():
            raise PromotionError(f"approved target already exists: {target.name}")
        if target != next_target:
            raise PromotionError(
                f"approved version must be the next monotonic version: {next_target.name}"
            )
    else:
        target = next_target
    sidecar = target.with_suffix(".json")
    if target.exists() or sidecar.exists():
        raise PromotionError(f"approved target already exists: {target.name}")
    script = _read_json(run_dir / "script-hash.json")
    audio = _read_json(run_dir / "audio-hash.json")
    keyframe = _read_json(run_dir / "keyframe-hash.json")
    shot_plan = _read_json(run_dir / "shot-plan.json")
    source_plan = shot_plan.get("source_plan") or {}
    providers = sorted(
        {
            f"{planned.get('provider')}/{planned.get('model')}"
            for shot in source_plan.get("shots", [])
            for planned in shot.get("requests", [])
            if planned.get("provider") and planned.get("model")
        }
    )
    approved_at = utc_now().isoformat()
    record = {
        "approved_file": target.name,
        "approved_path": target.relative_to(root).as_posix(),
        "approved_version": _version_from_name(target.name),
        "approved_at": approved_at,
        "source_run_id": run_id,
        "source_candidate": candidate_name,
        "source_path": relative.as_posix(),
        "source_sha256": source_hash,
        "approved_sha256": source_hash,
        "preset": preset,
        "script": script,
        "audio": audio,
        "keyframe": keyframe,
        "selected_shots": (shot_plan.get("selection") or {}).get("selections", {}),
        "brand_assets": shot_plan.get("graphics", []),
        "providers": providers,
        "reviewer": review["reviewer"],
        "reviewed_at": review["reviewed_at"],
        "mtl_review_ready": review["mtl_review_ready"],
        "review": review_evidence,
    }
    try:
        with source.open("rb") as input_file, target.open("xb") as output_file:
            shutil.copyfileobj(input_file, output_file)
            output_file.flush()
            os.fsync(output_file.fileno())
        if sha256_file(target) != source_hash:
            raise PromotionError("approved copy digest does not match candidate")
        with sidecar.open("x", encoding="utf-8") as output:
            json.dump(record, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        sidecar.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    return record


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionError(f"promotion evidence is unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"promotion evidence must be an object: {path.name}")
    return value


def _version_from_name(name: str) -> int:
    return int(name.rsplit("-v", 1)[1].split(".", 1)[0])
