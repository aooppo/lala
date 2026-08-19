from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..hashing import sha256_file
from .domain import MediaArtifact, ShotSelection


class SelectionError(ValueError):
    pass


def load_shot_selection(
    project_root: Path, source_run_id: str, selection_file: Path
) -> ShotSelection:
    root = project_root.resolve()
    if not source_run_id or "/" in source_run_id or "\\" in source_run_id:
        raise SelectionError("invalid source run ID")
    run_dir = (root / "runs" / source_run_id).resolve()
    if (root / "runs").resolve() not in run_dir.parents or not run_dir.is_dir():
        raise SelectionError(f"source run does not exist: {source_run_id}")
    try:
        raw = yaml.safe_load(selection_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise SelectionError(f"selection file is unreadable: {selection_file}") from exc
    if not isinstance(raw, Mapping):
        raise SelectionError("selection file root must be a mapping")
    if raw.get("source_run_id") != source_run_id:
        raise SelectionError("selection source_run_id does not match requested run")
    reviewer = str(raw.get("reviewer") or "").strip()
    selected_at_raw = str(raw.get("selected_at") or "").strip()
    if not reviewer:
        raise SelectionError("selection reviewer is required")
    try:
        selected_at = datetime.fromisoformat(selected_at_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SelectionError("selection selected_at is invalid") from exc
    if selected_at.tzinfo is None:
        raise SelectionError("selection selected_at must include a timezone")
    selections = raw.get("selections")
    if not isinstance(selections, Mapping):
        raise SelectionError("selections must be a mapping")
    try:
        plan = json.loads((run_dir / "shot-plan.json").read_text(encoding="utf-8"))
        provider_results = json.loads(
            (run_dir / "provider-results.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise SelectionError("source run plan/results are unreadable") from exc
    if provider_results.get("status") not in {"AWAITING_SELECTION", "PARTIAL"}:
        raise SelectionError("source run is not awaiting shot selection")
    expected_shots = {
        str(shot["shot_id"]): {str(request["request_id"]) for request in shot.get("requests", [])}
        for shot in plan.get("shots", [])
        if shot.get("requests")
    }
    if set(selections) != set(expected_shots):
        missing = sorted(set(expected_shots) - set(selections))
        extra = sorted(set(selections) - set(expected_shots))
        raise SelectionError(f"selection shot mismatch: missing={missing}, extra={extra}")

    artifacts: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for result in provider_results.get("results", []):
        request_id = str(result.get("request_id") or "")
        for artifact in result.get("artifacts", []) or []:
            artifact_id = str(artifact.get("artifact_id") or "")
            if artifact_id:
                artifacts[artifact_id] = (request_id, artifact)
    selected: dict[str, MediaArtifact] = {}
    selected_ids: set[str] = set()
    for shot_id, artifact_value in selections.items():
        artifact_id = str(artifact_value)
        if artifact_id in selected_ids:
            raise SelectionError(f"artifact selected more than once: {artifact_id}")
        record = artifacts.get(artifact_id)
        if record is None:
            raise SelectionError(f"selected artifact does not exist in source run: {artifact_id}")
        request_id, artifact = record
        if request_id not in expected_shots[str(shot_id)]:
            raise SelectionError(f"artifact {artifact_id} does not belong to shot {shot_id}")
        relative = Path(str(artifact.get("path") or ""))
        if relative.is_absolute() or ".." in relative.parts:
            raise SelectionError(f"artifact path is invalid: {artifact_id}")
        path = (root / relative).resolve()
        allowed_roots = (
            (root / "outputs/talking_shots").resolve(),
            (root / "outputs/broll").resolve(),
        )
        if not any(allowed in path.parents for allowed in allowed_roots) or not path.is_file():
            raise SelectionError(f"artifact is missing or outside source output roots: {artifact_id}")
        actual_hash = sha256_file(path)
        if actual_hash != artifact.get("sha256"):
            raise SelectionError(f"artifact digest mismatch: {artifact_id}")
        selected[str(shot_id)] = MediaArtifact(
            artifact_id=artifact_id,
            kind=str(artifact.get("kind") or ""),
            path=path,
            sha256=actual_hash,
            size_bytes=path.stat().st_size,
            mime_type=str(artifact.get("mime_type") or "video/mp4"),
            duration_seconds=_optional_float(artifact.get("duration_seconds")),
            width=_optional_int(artifact.get("width")),
            height=_optional_int(artifact.get("height")),
            provider_task_id=str(artifact.get("provider_task_id") or "") or None,
        )
        selected_ids.add(artifact_id)
    return ShotSelection(
        source_run_id=source_run_id,
        reviewer=reviewer,
        selected_at=selected_at.isoformat(),
        selection_file=selection_file.resolve(),
        selections=selected,
    )


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None
