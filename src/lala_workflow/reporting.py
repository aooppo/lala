from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .hashing import assert_within_directory, sha256_file

from .domain import GenerationResult, OutputArtifact, ResolvedRunConfig


REVIEW_FIELDS = (
    "run_id",
    "output_id",
    "output_file",
    "provider",
    "provider_task_id",
    "model",
    "seed",
    "face_identity_pass",
    "age_pass",
    "hair_pass",
    "body_proportions_pass",
    "wardrobe_pass",
    "jewelry_pass",
    "hands_pass",
    "scene_pass",
    "no_extra_people_pass",
    "no_text_logo_pass",
    "video_keyframe_ready",
    "mtl_review_ready",
    "reviewer",
    "reviewed_at",
    "notes",
)

SUBJECTIVE_REVIEW_FIELDS = REVIEW_FIELDS[7:]
RUN_ID_RE = re.compile(r"^LALA-[A-Z0-9-]+-\d{8}-\d{6}-[A-Z0-9-]+-\d{3}$")
OUTPUT_ID_RE = re.compile(r"^output-\d{3}(?:-\d{2})?$")
TRUTHY_REVIEW_VALUES = {"1", "true", "yes", "y", "approved", "pass"}


def review_csv_text(
    result: GenerationResult,
    requests_by_output: Mapping[str, Mapping[str, Any]],
) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=REVIEW_FIELDS, lineterminator="\n")
    writer.writeheader()
    for output in result.outputs:
        request = requests_by_output.get(output.output_id, {})
        row = {
            "run_id": result.run_id,
            "output_id": output.output_id,
            "output_file": output.file.as_posix(),
            "provider": result.provider,
            "provider_task_id": output.provider_task_id,
            "model": result.model,
            "seed": "" if request.get("seed") is None else request.get("seed"),
        }
        row.update({field: "" for field in SUBJECTIVE_REVIEW_FIELDS})
        writer.writerow(row)
    return buffer.getvalue()


def summary_markdown(
    config: ResolvedRunConfig,
    result: GenerationResult,
    *,
    paid_calls: int,
) -> str:
    character_line = (
        f"- Character: `{config.character_id}` v{config.character_profile_version} "
        f"(`{config.character_profile_sha256}`)\n"
        if config.character_id
        else ""
    )
    return (
        f"# Run Summary: {result.run_id}\n\n"
        f"- Status: `{result.status.value}`\n"
        f"- Mode: `{'live' if config.live else 'dry-run'}`\n"
        f"- Preset: `{config.preset}`\n"
        f"- Provider/model: `{config.provider}` / `{config.model}`\n"
        f"{character_line}"
        f"- Resolution: `{config.resolution}`\n"
        f"- Requested candidates: {config.count}\n"
        f"- Downloaded outputs: {len(result.outputs)}\n"
        f"- Errors: {len(result.errors)}\n"
        f"- Paid calls made: {paid_calls}\n"
        f"- Started: {result.started_at.isoformat()}\n"
        f"- Completed: {result.completed_at.isoformat()}\n"
        f"- Duration seconds: {result.duration_seconds:.3f}\n"
    )


def read_run_summary(project_root: Path, run_id: str) -> str:
    run_dir = _resolve_run_dir(project_root, run_id)
    summary = run_dir / "summary.md"
    if not summary.is_file():
        raise ValueError(f"run summary does not exist: {run_id}")
    return summary.read_text(encoding="utf-8")


def promote_keyframe(project_root: Path, run_id: str, output_id: str) -> dict[str, Any]:
    root = project_root.resolve()
    run_dir = _resolve_run_dir(root, run_id)
    if not OUTPUT_ID_RE.fullmatch(output_id):
        raise ValueError(f"invalid output ID: {output_id}")
    review_path = run_dir / "review.csv"
    result_path = run_dir / "result.json"
    config_path = run_dir / "resolved-config.yaml"
    for path in (review_path, result_path, config_path):
        if not path.is_file():
            raise ValueError(f"required run artifact does not exist: {path.name}")

    with review_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REVIEW_FIELDS:
            raise ValueError("review.csv header does not match the required schema")
        matches = [row for row in reader if row.get("output_id") == output_id]
    if len(matches) != 1:
        raise ValueError(f"review.csv must contain exactly one row for {output_id}")
    review = matches[0]
    if review.get("video_keyframe_ready", "").strip().casefold() not in TRUTHY_REVIEW_VALUES:
        raise ValueError(f"output {output_id} is not marked video-keyframe-ready")
    reviewer = review.get("reviewer", "").strip()
    if not reviewer:
        raise ValueError("reviewer is required for keyframe promotion")
    reviewed_at = review.get("reviewed_at", "").strip()
    try:
        approval_time = datetime.fromisoformat(reviewed_at)
    except ValueError as exc:
        raise ValueError("reviewed_at must be ISO 8601") from exc
    if approval_time.tzinfo is None or approval_time.utcoffset() is None:
        raise ValueError("reviewed_at must include a timezone")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(result, dict) or not isinstance(config, dict):
        raise ValueError("run result/config must be mappings")
    outputs = [item for item in result.get("outputs", []) if item.get("output_id") == output_id]
    if len(outputs) != 1:
        raise ValueError(f"result.json must contain exactly one output for {output_id}")
    output = outputs[0]
    source_relative = Path(str(output.get("file", "")))
    if source_relative.is_absolute():
        raise ValueError("result output path must be project-relative")
    source = assert_within_directory(root / source_relative, root / "outputs")
    if not source.is_file():
        raise ValueError(f"source output does not exist: {source_relative}")
    if review.get("output_file", "") != source_relative.as_posix():
        raise ValueError("review output_file does not match result output path")
    actual_hash = sha256_file(source)
    expected_hash = str(output.get("sha256", ""))
    if actual_hash != expected_hash:
        raise ValueError("source image hash does not match result.json")

    requests = [item for item in result.get("requests", []) if item.get("output_id") == output_id]
    if len(requests) != 1:
        raise ValueError(f"result.json must contain exactly one request for {output_id}")
    prompt = requests[0].get("prompt")
    if not isinstance(prompt, dict) or not prompt.get("version"):
        raise ValueError("request prompt version is missing")

    approved_dir = root / "outputs/approved_keyframes"
    approved_dir.mkdir(parents=True, exist_ok=True)
    target = approved_dir / f"{run_id}-{output_id}{source.suffix.lower()}"
    metadata = target.with_suffix(target.suffix + ".json")
    if target.exists() or metadata.exists():
        raise ValueError(f"approved keyframe already exists: {target.name}")
    record = {
        "source_run_id": run_id,
        "source_output_id": output_id,
        "source_image": source_relative.as_posix(),
        "image_sha256": actual_hash,
        "approved_anchor_version": str(config.get("anchor_set_version", "")),
        "prompt_version": str(prompt["version"]),
        "provider": str(result.get("provider", config.get("provider", ""))),
        "model": str(result.get("model", config.get("model", ""))),
        "reviewer": reviewer,
        "approval_date": reviewed_at,
        "approved_keyframe": target.relative_to(root).as_posix(),
    }
    created_target = False
    created_metadata = False
    try:
        target_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        created_target = True
        with source.open("rb") as source_handle, os.fdopen(target_fd, "wb") as target_handle:
            shutil.copyfileobj(source_handle, target_handle)
            target_handle.flush()
            os.fsync(target_handle.fileno())
        if sha256_file(target) != actual_hash:
            raise ValueError("promoted keyframe hash does not match source")
        metadata_fd = os.open(metadata, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        created_metadata = True
        with os.fdopen(metadata_fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if created_metadata:
            metadata.unlink(missing_ok=True)
        if created_target:
            target.unlink(missing_ok=True)
        raise
    return record


def _resolve_run_dir(project_root: Path, run_id: str) -> Path:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError(f"invalid run ID: {run_id}")
    runs_root = (project_root / "runs").resolve()
    run_dir = (runs_root / run_id).resolve()
    try:
        run_dir.relative_to(runs_root)
    except ValueError as exc:
        raise ValueError(f"invalid run ID: {run_id}") from exc
    if not run_dir.is_dir():
        raise ValueError(f"run does not exist: {run_id}")
    return run_dir
