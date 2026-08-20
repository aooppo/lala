from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import load_project_config
from ..domain import AnchorImage, AnchorManifest
from .domain import CharacterProfile, CharacterStatus
from .errors import CharacterStateError
from .registry import CharacterRegistryStore
from .storage import CharacterStorage


PREVIEW_ELIGIBLE = {
    CharacterStatus.DRAFT,
    CharacterStatus.BUILDING,
    CharacterStatus.READY_FOR_GENERATION,
    CharacterStatus.READY_FOR_PREVIEW,
    CharacterStatus.READY_FOR_APPROVAL,
    CharacterStatus.FAILED,
}


@dataclass(frozen=True, slots=True)
class ResolvedCharacter:
    profile: CharacterProfile
    manifest: AnchorManifest
    selection_source: str


class CharacterResolver:
    def __init__(
        self,
        project_root: Path,
        *,
        storage: CharacterStorage | None = None,
        registry: CharacterRegistryStore | None = None,
    ) -> None:
        self.root = project_root.resolve()
        self.storage = storage or CharacterStorage(self.root)
        self.registry = registry or CharacterRegistryStore(self.root, storage=self.storage)

    def resolve(
        self,
        character_id: str | None = None,
        *,
        allow_staging: bool = False,
    ) -> ResolvedCharacter:
        legacy = load_project_config(self.root).manifest
        if not self.registry.exists():
            profile = legacy_profile_from_manifest(legacy, self.root)
            if character_id not in (None, "lala-v1"):
                raise CharacterStateError(f"character does not exist: {character_id}")
            return ResolvedCharacter(profile, legacy, "legacy_fallback")
        registry = self.registry.load()
        selected_id = character_id or registry.active_character
        entry = registry.characters.get(selected_id)
        if entry is None:
            raise CharacterStateError(f"character does not exist: {selected_id}")
        profile = self.storage.load_profile(entry.profile)
        if allow_staging:
            if profile.status not in PREVIEW_ELIGIBLE and profile.status not in {
                CharacterStatus.ACTIVE,
                CharacterStatus.INACTIVE,
            }:
                raise CharacterStateError(f"character is not preview eligible: {profile.status.value}")
        elif profile.status is not CharacterStatus.ACTIVE:
            raise CharacterStateError("production generation requires the active character")
        return ResolvedCharacter(
            profile,
            legacy if profile.character_id == "lala-v1" else adapt_profile_manifest(profile, legacy),
            "explicit" if character_id else "active_registry",
        )


def adapt_profile_manifest(profile: CharacterProfile, legacy: AnchorManifest) -> AnchorManifest:
    anchors: dict[str, AnchorImage] = {}
    priority = 1
    for name in ("face", "full_body", "three_quarter"):
        reference = profile.references.get(name)
        if reference is None:
            continue
        anchors[name] = AnchorImage(
            name=name,
            path=reference.path,
            role=reference.role,
            tag=reference.tag,
            priority=priority,
            generation_input=True,
            sha256=reference.sha256,
            mime_type=reference.mime_type,
            width=reference.width,
            height=reference.height,
        )
        priority += 1
    anchors["scene"] = legacy.anchors["scene"]
    return AnchorManifest(
        project=legacy.project,
        anchor_set_version=f"character:{profile.character_id}:v{profile.profile_version}",
        status="approved" if profile.status in {CharacterStatus.ACTIVE, CharacterStatus.INACTIVE} else "staging",
        anchors=anchors,
        qa_references=legacy.qa_references,
    )


def legacy_profile_from_manifest(manifest: AnchorManifest, project_root: Path) -> CharacterProfile:
    from .domain import CharacterReference

    refs = {}
    for name in ("face", "full_body"):
        anchor = manifest.anchors[name]
        path = anchor.path
        refs[name] = CharacterReference(
            logical_name=name,
            path=path,
            sha256=anchor.sha256,
            role=anchor.role,
            tag=anchor.tag,
            mime_type=anchor.mime_type,
            width=anchor.width,
            height=anchor.height,
            size_bytes=(project_root / path).stat().st_size,
        )
    return CharacterProfile(
        character_id="lala-v1",
        display_name="Lady LaLa (Legacy)",
        profile_version=1,
        status=CharacterStatus.ACTIVE,
        created_at="2026-08-20T00:00:00+08:00",
        created_by="legacy_migration",
        references=refs,
        provenance={"source": "legacy_anchor_manifest"},
    ).with_hash()
