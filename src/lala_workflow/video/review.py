from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from ..hashing import sha256_file
from .storage import QA_FIELDS


class ReviewError(ValueError):
    pass


def load_review_row(
    run_dir: Path, candidate: str, *, require_ready: bool = False
) -> dict[str, str]:
    row = _load_review_path(run_dir / "review.csv", candidate)
    if require_ready:
        _require_ready(row)
    return row


def load_external_review_row(
    project_root: Path,
    run_dir: Path,
    candidate: str,
    review_file: Path,
    *,
    require_ready: bool = False,
) -> tuple[dict[str, str], dict[str, str]]:
    root = project_root.resolve()
    path = review_file if review_file.is_absolute() else root / review_file
    path = path.resolve()
    reviews_root = (root / "outputs/reviews").resolve()
    if reviews_root not in path.parents or not path.is_file():
        raise ReviewError("review file must be an existing copy under outputs/reviews")
    baseline = load_review_row(run_dir, candidate)
    if any(str(baseline.get(field) or "").strip() for field in QA_FIELDS[4:]):
        raise ReviewError("run review human fields must remain blank append-only evidence")
    row = _load_review_path(path, candidate)
    mismatches = [field for field in QA_FIELDS[:4] if row.get(field) != baseline.get(field)]
    if mismatches:
        raise ReviewError(
            "external review candidate provenance mismatch: " + ", ".join(mismatches)
        )
    if require_ready:
        _require_ready(row)
    return row, {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
    }


def _load_review_path(path: Path, candidate: str) -> dict[str, str]:
    try:
        with path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != list(QA_FIELDS):
                raise ReviewError("review.csv header does not match the exact video QA schema")
            rows = [dict(row) for row in reader if row.get("candidate") == candidate]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ReviewError("review.csv is unreadable") from exc
    if len(rows) != 1:
        raise ReviewError(f"candidate must have exactly one review row: {candidate}")
    return rows[0]


def _require_ready(row: dict[str, str]) -> None:
    if not _truthy(row.get("mtl_review_ready")):
        raise ReviewError("explicit MTL readiness is required for promotion")
    if not str(row.get("reviewer") or "").strip():
        raise ReviewError("reviewer is required for promotion")
    raw_time = str(row.get("reviewed_at") or "").strip()
    try:
        reviewed_at = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewError("reviewed_at must be a valid ISO 8601 timestamp") from exc
    if reviewed_at.tzinfo is None:
        raise ReviewError("reviewed_at must include a timezone")


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "yes", "1", "approved", "pass"}
