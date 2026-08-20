from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..domain import to_primitive, utc_now
from ..hashing import sha256_file
from ..redaction import sanitize
from .domain import CharacterBuild, CharacterProfile, CharacterReference, profile_payload
from .errors import CharacterIntegrityError
from .validation import ValidatedUpload, reference_from_validated, validate_reference_file


class CharacterStorage:
    def __init__(self, project_root: Path, *, secrets: tuple[str, ...] = ()) -> None:
        self.root = project_root.resolve()
        self.config_root = self.root / "configs/characters"
        self.profiles_root = self.config_root / "profiles"
        self.staging_root = self.root / "assets/characters"
        self.approved_root = self.root / "assets/approved_anchors/characters"
        self.outputs_root = self.root / "outputs/characters"
        self.secrets = tuple(item for item in secrets if item)
        for directory in (
            self.config_root,
            self.profiles_root,
            self.staging_root,
            self.approved_root,
            self.outputs_root,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def write_sources(
        self, character_id: str, uploads: Mapping[str, ValidatedUpload]
    ) -> dict[str, CharacterReference]:
        source_root = self.staging_root / character_id / "source"
        source_root.mkdir(parents=True, exist_ok=False)
        result: dict[str, CharacterReference] = {}
        for role, item in uploads.items():
            target = source_root / f"{role.replace('_', '-')}{item.suffix}"
            self._write_bytes_exclusive(target, item.content)
            if sha256_file(target) != item.sha256:
                raise CharacterIntegrityError(f"stored source digest mismatch: {role}")
            relative = target.relative_to(self.root)
            result[role] = reference_from_validated(item, project_relative_path=relative)
        return result

    def write_profile(self, profile: CharacterProfile) -> tuple[CharacterProfile, Path]:
        complete = profile.with_hash()
        path = self.profiles_root / (
            f"{complete.character_id}-v{complete.profile_version:03d}.yaml"
        )
        payload = sanitize(profile_payload(complete), self.secrets)
        text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
        self._write_text_exclusive(path, text)
        return complete, path.relative_to(self.root)

    def load_profile(self, relative: Path, *, verify_hash: bool = True) -> CharacterProfile:
        if relative.is_absolute() or ".." in relative.parts:
            raise CharacterIntegrityError("profile path must be project-relative")
        candidate = self.root / relative
        if candidate.is_symlink():
            raise CharacterIntegrityError("character profile symlinks are not allowed")
        path = candidate.resolve()
        try:
            path.relative_to(self.profiles_root.resolve())
        except ValueError as exc:
            raise CharacterIntegrityError("profile path is outside character profiles") from exc
        if not path.is_file():
            raise CharacterIntegrityError(f"character profile does not exist: {relative}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            raise CharacterIntegrityError(f"character profile is unreadable: {relative}") from exc
        if not isinstance(raw, Mapping):
            raise CharacterIntegrityError("character profile root must be a mapping")
        return CharacterProfile.from_dict(raw, verify_hash=verify_hash)

    def write_build(self, build: CharacterBuild) -> Path:
        build_root = self.outputs_root / build.character_id / "build"
        build_root.mkdir(parents=True, exist_ok=True)
        path = build_root / (
            f"{build.build_id}-{build.status.value.lower()}-{uuid.uuid4().hex[:8]}.json"
        )
        payload = sanitize(to_primitive(build), self.secrets)
        self._write_text_exclusive(
            path, json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        )
        latest = build_root / "latest.json"
        self._atomic_replace_text(
            latest, json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        )
        return path

    def load_latest_build(self, character_id: str) -> CharacterBuild | None:
        path = self.outputs_root / character_id / "build/latest.json"
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CharacterIntegrityError("latest character build is unreadable") from exc
        if not isinstance(raw, Mapping):
            raise CharacterIntegrityError("latest character build must be an object")
        return CharacterBuild.from_dict(raw)

    def append_event(self, character_id: str, event: str, details: Mapping[str, Any]) -> Path:
        root = self.outputs_root / character_id / "provenance"
        root.mkdir(parents=True, exist_ok=True)
        path = root / "events.jsonl"
        payload = sanitize(
            {"timestamp": utc_now().isoformat(), "event": event, "details": dict(details)},
            self.secrets,
        )
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        with os.fdopen(fd, "a", encoding="utf-8") as output:
            output.write(line)
            output.flush()
            os.fsync(output.fileno())
        return path

    def promote_sources(self, profile: CharacterProfile) -> CharacterProfile:
        target_root = self.approved_root / profile.character_id
        target_root.mkdir(parents=True, exist_ok=True)
        references: dict[str, CharacterReference] = {}
        for name, reference in profile.references.items():
            source = validate_reference_file(self.root, reference, allow_staging=True)
            suffix = source.suffix.lower()
            target = target_root / f"{name.replace('_', '-')}{suffix}"
            if target.exists():
                if target.is_symlink() or sha256_file(target) != reference.sha256:
                    raise CharacterIntegrityError(f"approved character source collision: {name}")
            else:
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
                try:
                    with source.open("rb") as input_file, os.fdopen(fd, "wb") as output:
                        shutil.copyfileobj(input_file, output)
                        output.flush()
                        os.fsync(output.fileno())
                except Exception:
                    target.unlink(missing_ok=True)
                    raise
            if sha256_file(target) != reference.sha256:
                raise CharacterIntegrityError(f"approved character source digest mismatch: {name}")
            references[name] = replace(reference, path=target.relative_to(self.root))
        return replace(profile, references=references, profile_sha256="")

    def preview_root(self, character_id: str) -> Path:
        path = self.outputs_root / character_id / "previews"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _write_bytes_exclusive(path: Path, content: bytes) -> None:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _write_text_exclusive(path: Path, text: str) -> None:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as output:
                output.write(text)
                output.flush()
                os.fsync(output.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _atomic_replace_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("x", encoding="utf-8", newline="") as output:
                output.write(text)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
