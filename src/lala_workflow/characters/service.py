from __future__ import annotations

import os
import uuid
import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Mapping

import yaml

from ..config import load_project_config
from ..domain import to_primitive, utc_now
from .builder import CharacterProfileBuilder
from .domain import (
    CharacterProfile,
    CharacterLifecycleEvent,
    CharacterRegistry,
    CharacterRegistryEntry,
    CharacterStatus,
    CharacterUpload,
    CharacterView,
)
from .errors import CharacterIntegrityError, CharacterStateError
from .preview import (
    MotionCharacterPreviewOperation,
    PreviewCoordinator,
    RunwayMotionPreviewOperation,
    StaticRunnerPreviewOperation,
    StaticCharacterPreviewOperation,
)
from .registry import CharacterRegistryStore
from .resolver import legacy_profile_from_manifest
from .storage import CharacterStorage
from .validation import validate_reference_file


class CharacterService:
    def __init__(
        self,
        project_root: Path,
        *,
        static_preview_operation: StaticCharacterPreviewOperation | None = None,
        motion_preview_operation: MotionCharacterPreviewOperation | None = None,
        max_runway_credits: float = 25.0,
        bootstrap: bool = True,
    ) -> None:
        self.root = project_root.resolve()
        self.storage = CharacterStorage(
            self.root, secrets=(str(os.environ.get("RUNWAYML_API_SECRET") or ""),)
        )
        self.registry = CharacterRegistryStore(self.root, storage=self.storage)
        if bootstrap and not self.registry.exists():
            bootstrap_legacy_character(self.root, storage=self.storage, registry=self.registry)
        self.builder = CharacterProfileBuilder(
            self.root, storage=self.storage, registry=self.registry
        )
        static_operation = static_preview_operation or StaticRunnerPreviewOperation(self.root)
        motion_operation = motion_preview_operation or RunwayMotionPreviewOperation(
            self.root, max_runway_credits=max_runway_credits, storage=self.storage
        )
        self.previews = PreviewCoordinator(
            self.root,
            storage=self.storage,
            static_operation=static_operation,
            motion_operation=motion_operation,
        )

    def list_characters(self) -> CharacterRegistry:
        return self.registry.load()

    def show(self, character_id: str) -> CharacterView:
        registry = self.registry.load()
        entry = registry.characters.get(character_id)
        if entry is None:
            raise CharacterStateError(f"character does not exist: {character_id}")
        profile = self.storage.load_profile(entry.profile)
        return CharacterView(
            profile=profile,
            build=self.storage.load_latest_build(character_id),
            registry_revision=registry.revision,
            is_active=registry.active_character == character_id,
        )

    def import_character(
        self,
        uploads: Mapping[str, CharacterUpload],
        *,
        display_name: str | None = None,
        created_by: str = "cli",
    ) -> CharacterProfile:
        registry_before = self.registry.load()
        incoming_hashes = {name: hashlib.sha256(item.content).hexdigest() for name, item in uploads.items()}
        for existing_entry in registry_before.characters.values():
            existing = self.storage.load_profile(existing_entry.profile)
            existing_hashes = {name: item.sha256 for name, item in existing.references.items()}
            if incoming_hashes == existing_hashes:
                from .errors import RegistryConflictError

                raise RegistryConflictError(
                    f"identical character sources already imported: {existing.character_id}",
                    user_message="这组人物照片已经导入，无需重复创建。",
                )
        profile, path = self.builder.create(
            uploads, display_name=display_name, created_by=created_by
        )
        self.registry.register(profile, path, expected_revision=registry_before.revision)
        self.storage.append_event(
            profile.character_id,
            "created",
            {"profile_sha256": profile.profile_sha256, "actor": created_by},
        )
        return profile

    def build(self, character_id: str):
        view = self.show(character_id)
        profile = view.profile
        if view.is_active:
            raise CharacterStateError("the active character does not require a staging build")
        for reference in profile.references.values():
            validate_reference_file(self.root, reference, allow_staging=True)
        if profile.status is not CharacterStatus.BUILDING:
            building = profile.transition(CharacterStatus.BUILDING, build_started_at=utc_now().isoformat())
            building, building_path = self.storage.write_profile(building)
            registry = self.registry.load()
            self.registry.update_profile(
                building,
                building_path,
                event_type="build_started",
                expected_revision=registry.revision,
                expected_active=registry.active_character,
            )
            profile = building
        ready = profile.transition(
            CharacterStatus.READY_FOR_GENERATION,
            source_hashes={name: ref.sha256 for name, ref in profile.references.items()},
        )
        ready, ready_path = self.storage.write_profile(ready)
        registry = self.registry.load()
        self.registry.update_profile(
            ready,
            ready_path,
            event_type="build_ready",
            expected_revision=registry.revision,
            expected_active=registry.active_character,
        )
        build = self.previews.create_build(ready)
        self.storage.write_build(build)
        self.storage.append_event(character_id, "build_ready", {"build_id": build.build_id})
        return build

    def preview(self, character_id: str, *, live: bool = False):
        view = self.show(character_id)
        if view.is_active or view.profile.status not in {
            CharacterStatus.READY_FOR_GENERATION,
            CharacterStatus.READY_FOR_PREVIEW,
            CharacterStatus.FAILED,
        }:
            raise CharacterStateError("character is not ready for staging preview")
        build = view.build or self.previews.create_build(view.profile)
        result = self.previews.run(view.profile, build, live=live)
        self.storage.write_build(result)
        self.storage.append_event(
            character_id,
            "preview_ready" if result.status is CharacterStatus.READY_FOR_APPROVAL else "preview_planned",
            {"build_id": result.build_id, "status": result.status.value, "live": live},
        )
        if result.status is CharacterStatus.READY_FOR_APPROVAL:
            self._mark_preview_ready(view.profile, result)
        return result

    def recover_motion(self, character_id: str, *, live: bool = False):
        view = self.show(character_id)
        build = view.build
        if view.is_active or build is None or build.static_preview is None:
            raise CharacterStateError("character has no staging static preview to recover")
        if view.profile.status not in {
            CharacterStatus.READY_FOR_GENERATION,
            CharacterStatus.READY_FOR_PREVIEW,
            CharacterStatus.FAILED,
        }:
            raise CharacterStateError("character is not eligible for motion-only recovery")
        legacy_unknown = (
            build.status is CharacterStatus.FAILED
            and build.motion_preview is None
            and any(str(item.get("code")) == "preview_failed" for item in build.errors)
        )
        result = self.previews.recover_motion(
            view.profile,
            build,
            live=live,
            legacy_submission_unknown=legacy_unknown,
        )
        self.storage.write_build(result)
        self.storage.append_event(
            character_id,
            "motion_preview_recovered",
            {"build_id": result.build_id, "status": result.status.value, "live": live},
        )
        if result.status is CharacterStatus.READY_FOR_APPROVAL:
            self._mark_preview_ready(view.profile, result)
        return result

    def _mark_preview_ready(self, source_profile: CharacterProfile, result):
        profile = source_profile
        if profile.status is CharacterStatus.READY_FOR_GENERATION:
            profile = profile.transition(CharacterStatus.READY_FOR_PREVIEW)
        if profile.status is CharacterStatus.READY_FOR_PREVIEW:
            profile = profile.transition(
                CharacterStatus.READY_FOR_APPROVAL,
                build_id=result.build_id,
                static_preview_sha256=result.static_preview.sha256 if result.static_preview else None,
                motion_preview_sha256=result.motion_preview.sha256 if result.motion_preview else None,
            )
        if profile.status is not CharacterStatus.READY_FOR_APPROVAL:
            raise CharacterStateError("character profile cannot enter preview approval state")
        profile, path = self.storage.write_profile(profile)
        registry = self.registry.load()
        self.registry.update_profile(
            profile,
            path,
            event_type="preview_ready",
            expected_revision=registry.revision,
            expected_active=registry.active_character,
        )
        return profile

    def approve_and_activate(
        self, character_id: str, *, expected_revision: int | None = None
    ) -> CharacterLifecycleEvent:
        registry = self.registry.load()
        if expected_revision is not None and registry.revision != expected_revision:
            from .errors import RegistryConflictError

            raise RegistryConflictError("registry changed in another session")
        if registry.active_character == character_id:
            raise CharacterStateError("character is already active")
        entry = registry.characters.get(character_id)
        if entry is None:
            raise CharacterStateError(f"character does not exist: {character_id}")
        profile = self.storage.load_profile(entry.profile)
        if profile.status is CharacterStatus.READY_FOR_APPROVAL:
            build = self.storage.load_latest_build(character_id)
            if build is None or build.status is not CharacterStatus.READY_FOR_APPROVAL:
                raise CharacterStateError("character has no complete preview evidence")
            self.previews.revalidate(build)
        elif profile.status is not CharacterStatus.INACTIVE:
            raise CharacterStateError("character is not ready for activation")
        for reference in profile.references.values():
            validate_reference_file(self.root, reference, allow_staging=True)
        promoted = self.storage.promote_sources(profile) if profile.character_id != "lala-v1" else profile
        new_active = promoted.transition(
            CharacterStatus.ACTIVE,
            approved_by="local_user",
            approved_at=utc_now().isoformat(),
        )
        old_entry = registry.characters[registry.active_character]
        old_profile = self.storage.load_profile(old_entry.profile)
        old_inactive = old_profile.transition(CharacterStatus.INACTIVE)
        old_inactive, old_path = self.storage.write_profile(old_inactive)
        new_active, new_path = self.storage.write_profile(new_active)
        updated = self.registry.activate(
            new_profile=new_active,
            new_profile_path=new_path,
            old_profile=old_inactive,
            old_profile_path=old_path,
            expected_revision=registry.revision,
            expected_active=registry.active_character,
            event_type="reactivated" if profile.status is CharacterStatus.INACTIVE else "approved_and_activated",
        )
        event = CharacterLifecycleEvent(
            event_id=uuid.uuid4().hex,
            event_type=str(updated.last_event["type"]),
            character_id=character_id,
            profile_sha256=new_active.profile_sha256,
            previous_active_character=registry.active_character,
            registry_revision=updated.revision,
            at=str(updated.last_event["at"]),
            actor="local_user",
        )
        self.storage.append_event(character_id, event.event_type, to_primitive(event))
        return event

    def reject(self, character_id: str, *, expected_revision: int | None = None) -> CharacterProfile:
        registry = self.registry.load()
        if expected_revision is not None and registry.revision != expected_revision:
            from .errors import RegistryConflictError

            raise RegistryConflictError("registry changed in another session")
        if registry.active_character == character_id:
            raise CharacterStateError("the active character cannot be rejected")
        entry = registry.characters.get(character_id)
        if entry is None:
            raise CharacterStateError(f"character does not exist: {character_id}")
        profile = self.storage.load_profile(entry.profile)
        if profile.status not in {
            CharacterStatus.READY_FOR_GENERATION,
            CharacterStatus.READY_FOR_PREVIEW,
            CharacterStatus.READY_FOR_APPROVAL,
        }:
            raise CharacterStateError("character cannot be rejected in its current state")
        rejected = profile.transition(CharacterStatus.REJECTED, rejected_at=utc_now().isoformat())
        rejected, path = self.storage.write_profile(rejected)
        self.registry.update_profile(
            rejected,
            path,
            event_type="rejected",
            expected_revision=registry.revision,
            expected_active=registry.active_character,
        )
        self.storage.append_event(character_id, "rejected", {"profile_sha256": rejected.profile_sha256})
        return rejected


def bootstrap_legacy_character(
    project_root: Path,
    *,
    storage: CharacterStorage | None = None,
    registry: CharacterRegistryStore | None = None,
) -> CharacterRegistry:
    root = project_root.resolve()
    storage = storage or CharacterStorage(root)
    registry = registry or CharacterRegistryStore(root, storage=storage)
    if registry.exists():
        return registry.load()
    manifest = load_project_config(root).manifest
    profile = legacy_profile_from_manifest(manifest, root)
    profile_path = storage.profiles_root / "lala-v1-v001.yaml"
    if profile_path.exists():
        loaded = storage.load_profile(profile_path.relative_to(root))
        if loaded.profile_sha256 != profile.profile_sha256:
            raise CharacterIntegrityError("checked-in legacy character seed does not match approved anchors")
        profile = loaded
        relative = profile_path.relative_to(root)
    else:
        profile, relative = storage.write_profile(profile)
    now = profile.created_at
    entry = CharacterRegistryEntry(
        character_id="lala-v1",
        display_name=profile.display_name,
        status=CharacterStatus.ACTIVE,
        profile=relative,
        profile_sha256=profile.profile_sha256,
        updated_at=now,
    )
    initial = CharacterRegistry(
        revision=0,
        active_character="lala-v1",
        previous_active_character=None,
        characters={"lala-v1": entry},
        last_event={"type": "legacy_bootstrap", "character_id": "lala-v1", "at": now},
    )
    return registry.initialize(initial)
