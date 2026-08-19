from __future__ import annotations

import csv
import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from ..domain import make_run_id, to_primitive, utc_now
from ..redaction import sanitize


VIDEO_RUN_FILES = (
    "request.json",
    "resolved-config.yaml",
    "script.txt",
    "script-hash.json",
    "audio-hash.json",
    "keyframe-hash.json",
    "shot-plan.json",
    "task-events.jsonl",
    "provider-results.json",
    "edit-commands.txt",
    "review.csv",
    "cost.json",
    "summary.md",
)

QA_FIELDS = (
    "run_id",
    "video_id",
    "preset",
    "candidate",
    "visual_identity",
    "face_stability",
    "age_stability",
    "hair_stability",
    "body_proportions",
    "wardrobe",
    "jewelry",
    "lip_sync",
    "mouth",
    "teeth",
    "eyes",
    "background",
    "motion",
    "audio_identity",
    "pronunciation",
    "script_match",
    "audio_video_sync",
    "technical_export",
    "mtl_review_ready",
    "reviewer",
    "reviewed_at",
    "notes",
)


@dataclass(frozen=True, slots=True)
class VideoRunContext:
    run_id: str
    path: Path


class VideoRunStorage:
    def __init__(self, project_root: Path, *, secrets: Sequence[str] = ()) -> None:
        self.root = project_root.resolve()
        self.runs_root = self.root / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.secrets = tuple(secret for secret in secrets if secret)
        self._event_lock = threading.Lock()

    def create_run(self, preset: str, *, now: datetime | None = None) -> VideoRunContext:
        current = now or utc_now()
        for sequence in range(1, 1000):
            run_id = make_run_id("video", preset, current, sequence)
            path = self.runs_root / run_id
            try:
                path.mkdir(exist_ok=False)
            except FileExistsError:
                continue
            (path / "task-events.jsonl").touch(exist_ok=False)
            return VideoRunContext(run_id, path)
        raise RuntimeError("could not allocate a unique video run ID")

    def append_event(
        self, run: VideoRunContext, event: str, details: Mapping[str, Any] | None = None
    ) -> None:
        payload = {
            "timestamp": utc_now().isoformat(),
            "event": event,
            "details": sanitize(dict(details or {}), self.secrets),
        }
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
        with self._event_lock:
            with (run.path / "task-events.jsonl").open("a", encoding="utf-8") as output:
                output.write(line)
                output.flush()
                os.fsync(output.fileno())

    def write_json_new(self, run: VideoRunContext, filename: str, value: Any) -> Path:
        payload = sanitize(to_primitive(value), self.secrets)
        return self._write_text_new(
            run.path / filename,
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        )

    def write_yaml_new(self, run: VideoRunContext, filename: str, value: Any) -> Path:
        payload = sanitize(to_primitive(value), self.secrets)
        return self._write_text_new(
            run.path / filename,
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        )

    def write_text_new(self, run: VideoRunContext, filename: str, text: str) -> Path:
        payload = sanitize(text, self.secrets)
        if not isinstance(payload, str):
            raise TypeError("text sanitizer returned non-string")
        return self._write_text_new(run.path / filename, payload)

    def write_bytes_new(self, run: VideoRunContext, filename: str, content: bytes) -> Path:
        path = run.path / filename
        with path.open("xb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        return path

    def write_review_new(
        self, run: VideoRunContext, rows: Sequence[Mapping[str, Any]]
    ) -> Path:
        path = run.path / "review.csv"
        with path.open("x", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=QA_FIELDS, extrasaction="raise")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in QA_FIELDS})
            output.flush()
            os.fsync(output.fileno())
        return path

    def assert_complete(self, run: VideoRunContext) -> None:
        actual = {path.name for path in run.path.iterdir() if path.is_file()}
        expected = set(VIDEO_RUN_FILES)
        if actual != expected:
            raise RuntimeError(
                f"video run artifact mismatch: missing={sorted(expected - actual)}, "
                f"extra={sorted(actual - expected)}"
            )

    @staticmethod
    def _write_text_new(path: Path, text: str) -> Path:
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("x", encoding="utf-8", newline="") as output:
                output.write(text)
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(temp, path)
            except FileExistsError:
                raise
            temp.unlink()
        finally:
            temp.unlink(missing_ok=True)
        return path
