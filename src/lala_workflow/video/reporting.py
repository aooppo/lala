from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Any, Mapping, Sequence

from .storage import QA_FIELDS, VIDEO_RUN_FILES, VideoRunContext, VideoRunStorage


def blank_review_rows(
    run_id: str, preset: str, candidates: Sequence[Mapping[str, Any]]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for candidate in candidates:
        row = {field: "" for field in QA_FIELDS}
        row.update(
            {
                "run_id": run_id,
                "video_id": str(candidate.get("video_id") or candidate.get("candidate") or ""),
                "preset": preset,
                "candidate": str(candidate.get("candidate") or ""),
            }
        )
        rows.append(row)
    return rows


def summary_markdown(
    *,
    run_id: str,
    preset: str,
    status: str,
    provider_call_count: int,
    output_count: int,
    total_provider_cost: float | None,
    blocker: str | None = None,
) -> str:
    cost = "unknown" if total_provider_cost is None else f"USD {total_provider_cost:.6f}"
    lines = [
        f"# Video Run {run_id}",
        "",
        f"- Preset: `{preset}`",
        f"- Status: `{status}`",
        f"- Planned provider calls: {provider_call_count}",
        f"- Outputs: {output_count}",
        f"- Estimated/actual provider cost: {cost}",
    ]
    if blocker:
        lines.append(f"- Blocker: `{blocker}`")
    return "\n".join(lines) + "\n"


def read_video_summary(project_root: Path, run_id: str) -> str:
    if not run_id or "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise ValueError("invalid video run ID")
    path = (project_root.resolve() / "runs" / run_id / "summary.md").resolve()
    runs_root = (project_root.resolve() / "runs").resolve()
    if runs_root not in path.parents:
        raise ValueError("video run path escapes runs directory")
    return path.read_text(encoding="utf-8")


def build_video_report(project_root: Path, run_id: str) -> dict[str, Any]:
    if not run_id or "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise ValueError("invalid video run ID")
    root = project_root.resolve()
    run_dir = (root / "runs" / run_id).resolve()
    if (root / "runs").resolve() not in run_dir.parents or not run_dir.is_dir():
        raise ValueError(f"video run does not exist: {run_id}")
    actual = {path.name for path in run_dir.iterdir() if path.is_file()}
    if actual != set(VIDEO_RUN_FILES):
        raise ValueError("video run does not contain the exact thirteen-artifact bundle")
    request = _read_json(run_dir / "request.json")
    results = _read_json(run_dir / "provider-results.json")
    cost = _read_json(run_dir / "cost.json")
    try:
        with (run_dir / "review.csv").open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != list(QA_FIELDS):
                raise ValueError("review.csv header does not match the video QA schema")
            review_rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ValueError("review.csv is unreadable") from exc
    requests = request.get("requests") or []
    providers = sorted(
        {
            f"{item.get('provider')}/{item.get('model')}"
            for item in requests
            if item.get("provider") and item.get("model")
        }
    )
    return {
        "run_id": run_id,
        "mode": request.get("mode"),
        "action": request.get("action"),
        "preset": request.get("preset"),
        "status": results.get("status"),
        "planned_provider_calls": request.get("provider_call_count", 0),
        "provider_submissions": results.get("submission_count", 0),
        "candidate_count": results.get("successful_outputs", 0),
        "failed_outputs": results.get("failed_outputs", 0),
        "review_rows": len(review_rows),
        "providers": providers,
        "cost": cost,
        "summary": (run_dir / "summary.md").read_text(encoding="utf-8"),
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"run artifact is unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"run artifact must be an object: {path.name}")
    return value
