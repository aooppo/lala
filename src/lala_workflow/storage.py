from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import yaml

from .domain import make_run_id, to_primitive, utc_now
from .redaction import sanitize


REQUIRED_RUN_FILES = (
    "request.json",
    "resolved-config.yaml",
    "resolved-prompt.txt",
    "anchor-hashes.json",
    "task-events.jsonl",
    "result.json",
    "review.csv",
    "summary.md",
)


@dataclass(frozen=True, slots=True)
class RunContext:
    run_id: str
    path: Path


class RunStorage:
    def __init__(self, project_root: Path, *, secrets: tuple[str, ...] = ()) -> None:
        self.project_root = project_root.resolve()
        self.runs_root = self.project_root / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.secrets = secrets
        self._event_lock = threading.Lock()

    def create_run(
        self,
        provider: str,
        preset: str,
        *,
        now: datetime | None = None,
    ) -> RunContext:
        current = now or utc_now()
        for sequence in range(1, 1000):
            run_id = make_run_id(provider, preset, current, sequence)
            path = self.runs_root / run_id
            try:
                path.mkdir(parents=False, exist_ok=False)
            except FileExistsError:
                continue
            (path / "task-events.jsonl").touch(exist_ok=False)
            return RunContext(run_id, path)
        raise RuntimeError("could not allocate a unique run ID")

    def write_json(self, run: RunContext, filename: str, value: Any) -> Path:
        payload = sanitize(to_primitive(value), self.secrets)
        return self._atomic_write(
            run.path / filename,
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        )

    def write_yaml(self, run: RunContext, filename: str, value: Any) -> Path:
        payload = sanitize(to_primitive(value), self.secrets)
        return self._atomic_write(
            run.path / filename,
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        )

    def write_text(self, run: RunContext, filename: str, text: str) -> Path:
        sanitized = sanitize(text, self.secrets)
        if not isinstance(sanitized, str):
            raise TypeError("text sanitizer returned non-string")
        return self._atomic_write(run.path / filename, sanitized)

    def append_event(
        self,
        run: RunContext,
        event: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        payload = {
            "timestamp": utc_now().isoformat(),
            "event": event,
            "details": sanitize(dict(details or {}), self.secrets),
        }
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
        with self._event_lock:
            with (run.path / "task-events.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()

    @staticmethod
    def _atomic_write(path: Path, text: str) -> Path:
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("x", encoding="utf-8", newline="") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        return path
