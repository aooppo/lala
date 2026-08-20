from __future__ import annotations

import fcntl
import os
import uuid
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Callable, Iterator, Mapping

import yaml

from ..domain import to_primitive, utc_now
from .domain import (
    CharacterProfile,
    CharacterRegistry,
    CharacterRegistryEntry,
    CharacterStatus,
)
from .errors import CharacterIntegrityError, CharacterStateError, RegistryConflictError
from .storage import CharacterStorage
from .validation import validate_reference_file


class CharacterRegistryStore:
    def __init__(self, project_root: Path, *, storage: CharacterStorage | None = None) -> None:
        self.root = project_root.resolve()
        self.storage = storage or CharacterStorage(self.root)
        self.registry_path = self.root / "configs/characters/registry.yaml"
        self.lock_path = self.root / "configs/characters/.registry.lock"
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.registry_path.is_file()

    def load(self, *, validate_profiles: bool = True) -> CharacterRegistry:
        with self._locked(exclusive=False):
            registry = self._read_unlocked()
        if validate_profiles:
            self.validate_profiles(registry)
        return registry

    def initialize(self, registry: CharacterRegistry) -> CharacterRegistry:
        with self._locked(exclusive=True):
            if self.registry_path.exists():
                current = self._read_unlocked()
                self.validate_profiles(current)
                return current
            self.validate_profiles(registry)
            self._write_unlocked(registry)
        return registry

    def validate_profiles(self, registry: CharacterRegistry) -> None:
        for character_id, entry in registry.characters.items():
            profile = self.storage.load_profile(entry.profile)
            if profile.character_id != character_id:
                raise CharacterIntegrityError(
                    f"registry/profile character mismatch: {character_id}"
                )
            if profile.profile_sha256 != entry.profile_sha256:
                raise CharacterIntegrityError(
                    f"registry/profile digest mismatch: {character_id}"
                )
            if profile.status is not entry.status:
                raise CharacterIntegrityError(
                    f"registry/profile status mismatch: {character_id}"
                )
            for reference in profile.references.values():
                validate_reference_file(self.root, reference, allow_staging=True)
                parts = reference.path.parts
                if character_id == "lala-v1":
                    if parts[:2] != ("assets", "approved_anchors"):
                        raise CharacterIntegrityError("legacy profile must use approved anchors")
                elif profile.status in {CharacterStatus.ACTIVE, CharacterStatus.INACTIVE}:
                    expected = ("assets", "approved_anchors", "characters", character_id)
                    if parts[:4] != expected:
                        raise CharacterIntegrityError(
                            f"active character source is outside its authority root: {character_id}"
                        )
                else:
                    expected = ("assets", "characters", character_id, "source")
                    if parts[:4] != expected:
                        raise CharacterIntegrityError(
                            f"staging character source is outside its isolated root: {character_id}"
                        )

    def register(
        self,
        profile: CharacterProfile,
        profile_path: Path,
        *,
        expected_revision: int | None = None,
    ) -> CharacterRegistry:
        def transform(current: CharacterRegistry) -> CharacterRegistry:
            if profile.character_id in current.characters:
                raise RegistryConflictError(f"character already exists: {profile.character_id}")
            now = utc_now().isoformat()
            entry = CharacterRegistryEntry(
                profile.character_id,
                profile.display_name,
                profile.status,
                profile_path,
                profile.profile_sha256,
                now,
            )
            return replace(
                current,
                revision=current.revision + 1,
                characters={**dict(current.characters), profile.character_id: entry},
                last_event={
                    "type": "created",
                    "character_id": profile.character_id,
                    "profile_sha256": profile.profile_sha256,
                    "at": now,
                },
            )

        return self.mutate(transform, expected_revision=expected_revision)

    def update_profile(
        self,
        profile: CharacterProfile,
        profile_path: Path,
        *,
        event_type: str,
        expected_revision: int | None = None,
        expected_active: str | None = None,
    ) -> CharacterRegistry:
        def transform(current: CharacterRegistry) -> CharacterRegistry:
            if profile.character_id not in current.characters:
                raise CharacterStateError(f"character does not exist: {profile.character_id}")
            if profile.status is CharacterStatus.ACTIVE:
                raise CharacterStateError("use activate for ACTIVE profile transitions")
            now = utc_now().isoformat()
            entry = CharacterRegistryEntry(
                profile.character_id,
                profile.display_name,
                profile.status,
                profile_path,
                profile.profile_sha256,
                now,
            )
            characters = dict(current.characters)
            characters[profile.character_id] = entry
            return replace(
                current,
                revision=current.revision + 1,
                characters=characters,
                last_event={
                    "type": event_type,
                    "character_id": profile.character_id,
                    "profile_sha256": profile.profile_sha256,
                    "at": now,
                },
            )

        return self.mutate(
            transform,
            expected_revision=expected_revision,
            expected_active=expected_active,
        )

    def activate(
        self,
        *,
        new_profile: CharacterProfile,
        new_profile_path: Path,
        old_profile: CharacterProfile,
        old_profile_path: Path,
        expected_revision: int,
        expected_active: str,
        event_type: str = "approved_and_activated",
    ) -> CharacterRegistry:
        if new_profile.status is not CharacterStatus.ACTIVE:
            raise CharacterStateError("new activation profile must be ACTIVE")
        if old_profile.status is not CharacterStatus.INACTIVE:
            raise CharacterStateError("old activation profile must be INACTIVE")

        def transform(current: CharacterRegistry) -> CharacterRegistry:
            if current.active_character != old_profile.character_id:
                raise RegistryConflictError("active character changed in another session")
            if new_profile.character_id not in current.characters:
                raise CharacterStateError(f"character does not exist: {new_profile.character_id}")
            now = utc_now().isoformat()
            characters = dict(current.characters)
            characters[old_profile.character_id] = CharacterRegistryEntry(
                old_profile.character_id,
                old_profile.display_name,
                old_profile.status,
                old_profile_path,
                old_profile.profile_sha256,
                now,
            )
            characters[new_profile.character_id] = CharacterRegistryEntry(
                new_profile.character_id,
                new_profile.display_name,
                new_profile.status,
                new_profile_path,
                new_profile.profile_sha256,
                now,
            )
            return CharacterRegistry(
                registry_version=current.registry_version,
                revision=current.revision + 1,
                active_character=new_profile.character_id,
                previous_active_character=old_profile.character_id,
                characters=characters,
                last_event={
                    "type": event_type,
                    "character_id": new_profile.character_id,
                    "previous_active_character": old_profile.character_id,
                    "profile_sha256": new_profile.profile_sha256,
                    "at": now,
                },
            )

        return self.mutate(
            transform,
            expected_revision=expected_revision,
            expected_active=expected_active,
        )

    def mutate(
        self,
        transform: Callable[[CharacterRegistry], CharacterRegistry],
        *,
        expected_revision: int | None = None,
        expected_active: str | None = None,
    ) -> CharacterRegistry:
        with self._locked(exclusive=True):
            current = self._read_unlocked()
            self.validate_profiles(current)
            if expected_revision is not None and current.revision != expected_revision:
                raise RegistryConflictError(
                    f"registry revision changed: expected {expected_revision}, got {current.revision}",
                    user_message="人物列表已在另一个窗口更新，请刷新后重试。",
                )
            if expected_active is not None and current.active_character != expected_active:
                raise RegistryConflictError(
                    "active character changed in another session",
                    user_message="当前人物已在另一个窗口切换，请刷新后重试。",
                )
            updated = transform(current)
            if updated.revision != current.revision + 1:
                raise CharacterIntegrityError("registry mutation must increment revision exactly once")
            # All referenced immutable snapshots must be valid before the sole
            # current-state pointer is replaced.
            self.validate_profiles(updated)
            self._write_unlocked(updated)
        return updated

    def _read_unlocked(self) -> CharacterRegistry:
        if not self.registry_path.is_file():
            raise CharacterIntegrityError("character registry does not exist")
        try:
            raw = yaml.safe_load(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            raise CharacterIntegrityError("character registry is unreadable") from exc
        if not isinstance(raw, Mapping):
            raise CharacterIntegrityError("character registry root must be a mapping")
        return CharacterRegistry.from_dict(raw)

    def _write_unlocked(self, registry: CharacterRegistry) -> None:
        payload = to_primitive(registry)
        text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
        temporary = self.registry_path.with_name(
            f".{self.registry_path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            with temporary.open("x", encoding="utf-8", newline="") as output:
                output.write(text)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.registry_path)
            directory_fd = os.open(self.registry_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)

    @contextmanager
    def _locked(self, *, exclusive: bool) -> Iterator[None]:
        descriptor = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
