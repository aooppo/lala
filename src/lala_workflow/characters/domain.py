from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from ..domain import to_primitive
from .errors import CharacterIntegrityError, CharacterStateError


CHARACTER_ID_RE = re.compile(r"^(?:lala-v1|character-\d{8}-\d{3})$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_REFERENCE_NAMES = ("face", "full_body", "three_quarter")
OPTIONAL_REFERENCE_NAMES = ("side", "expression", "product_pose", "hair_accessory")
REFERENCE_NAMES = frozenset(REQUIRED_REFERENCE_NAMES + OPTIONAL_REFERENCE_NAMES)


class CharacterStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    BUILDING = "BUILDING"
    READY_FOR_GENERATION = "READY_FOR_GENERATION"
    READY_FOR_PREVIEW = "READY_FOR_PREVIEW"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


ALLOWED_TRANSITIONS: Mapping[CharacterStatus, frozenset[CharacterStatus]] = {
    CharacterStatus.DRAFT: frozenset({CharacterStatus.VALIDATING, CharacterStatus.BUILDING}),
    CharacterStatus.VALIDATING: frozenset({CharacterStatus.BUILDING, CharacterStatus.FAILED}),
    CharacterStatus.BUILDING: frozenset(
        {CharacterStatus.READY_FOR_GENERATION, CharacterStatus.FAILED}
    ),
    CharacterStatus.READY_FOR_GENERATION: frozenset(
        {CharacterStatus.READY_FOR_PREVIEW, CharacterStatus.FAILED, CharacterStatus.REJECTED}
    ),
    CharacterStatus.READY_FOR_PREVIEW: frozenset(
        {CharacterStatus.READY_FOR_APPROVAL, CharacterStatus.FAILED, CharacterStatus.REJECTED}
    ),
    CharacterStatus.READY_FOR_APPROVAL: frozenset(
        {CharacterStatus.ACTIVE, CharacterStatus.REJECTED, CharacterStatus.FAILED}
    ),
    CharacterStatus.ACTIVE: frozenset({CharacterStatus.INACTIVE}),
    CharacterStatus.INACTIVE: frozenset({CharacterStatus.ACTIVE}),
    CharacterStatus.FAILED: frozenset({CharacterStatus.BUILDING}),
    CharacterStatus.REJECTED: frozenset({CharacterStatus.BUILDING}),
}


def require_transition(current: CharacterStatus, target: CharacterStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise CharacterStateError(f"invalid character transition: {current.value} -> {target.value}")


def _timestamp(value: str, name: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CharacterIntegrityError(f"{name} must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CharacterIntegrityError(f"{name} must include a timezone")
    return parsed.isoformat()


@dataclass(frozen=True, slots=True)
class CharacterUpload:
    role: str
    content: bytes
    filename: str | None = None
    declared_mime_type: str | None = None


@dataclass(frozen=True, slots=True)
class CharacterReference:
    logical_name: str
    path: Path
    sha256: str
    role: str
    tag: str
    mime_type: str
    width: int
    height: int
    size_bytes: int
    source_filename: str | None = None

    def __post_init__(self) -> None:
        if self.logical_name not in REFERENCE_NAMES:
            raise CharacterIntegrityError(f"unknown character reference: {self.logical_name}")
        if self.path.is_absolute() or ".." in self.path.parts or not self.path.as_posix():
            raise CharacterIntegrityError("character reference path must be safe and project-relative")
        if not HASH_RE.fullmatch(self.sha256):
            raise CharacterIntegrityError("character reference sha256 is invalid")
        if not self.role or not re.fullmatch(r"^[a-z][a-z0-9_]*$", self.tag):
            raise CharacterIntegrityError("character reference role/tag is invalid")
        if self.mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise CharacterIntegrityError("character reference MIME type is invalid")
        if self.width <= 0 or self.height <= 0 or self.size_bytes <= 0:
            raise CharacterIntegrityError("character reference dimensions/size are invalid")

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CharacterReference:
        return cls(
            logical_name=str(raw.get("logical_name") or ""),
            path=Path(str(raw.get("path") or "")),
            sha256=str(raw.get("sha256") or ""),
            role=str(raw.get("role") or ""),
            tag=str(raw.get("tag") or ""),
            mime_type=str(raw.get("mime_type") or ""),
            width=int(raw.get("width") or 0),
            height=int(raw.get("height") or 0),
            size_bytes=int(raw.get("size_bytes") or 0),
            source_filename=(str(raw["source_filename"]) if raw.get("source_filename") else None),
        )


@dataclass(frozen=True, slots=True)
class CharacterProfile:
    character_id: str
    display_name: str | None
    profile_version: int
    status: CharacterStatus
    created_at: str
    created_by: str
    references: Mapping[str, CharacterReference]
    attributes: Mapping[str, str | None] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"
    profile_sha256: str = ""

    def __post_init__(self) -> None:
        if not CHARACTER_ID_RE.fullmatch(self.character_id):
            raise CharacterIntegrityError(f"invalid character ID: {self.character_id}")
        if self.profile_version < 1 or self.schema_version != "1.0":
            raise CharacterIntegrityError("character profile version is invalid")
        _timestamp(self.created_at, "created_at")
        if self.created_by not in {"local_ui", "cli", "legacy_migration", "test"}:
            raise CharacterIntegrityError("character profile created_by is invalid")
        if set(self.references) != {item.logical_name for item in self.references.values()}:
            raise CharacterIntegrityError("character reference mapping keys do not match logical names")
        missing = set(REQUIRED_REFERENCE_NAMES) - set(self.references)
        if missing and self.created_by != "legacy_migration":
            raise CharacterIntegrityError(
                f"character profile is missing required references: {', '.join(sorted(missing))}"
            )
        if self.created_by == "legacy_migration" and set(self.references) != {"face", "full_body"}:
            raise CharacterIntegrityError("legacy profile must contain exact face and full-body references")
        if self.display_name is not None and not 1 <= len(self.display_name.strip()) <= 100:
            raise CharacterIntegrityError("display name must be 1..100 characters")
        if self.profile_sha256 and not HASH_RE.fullmatch(self.profile_sha256):
            raise CharacterIntegrityError("character profile sha256 is invalid")

    def with_hash(self) -> CharacterProfile:
        return replace(self, profile_sha256=profile_sha256(self))

    def transition(self, target: CharacterStatus, **provenance: Any) -> CharacterProfile:
        require_transition(self.status, target)
        updated = replace(
            self,
            profile_version=self.profile_version + 1,
            status=target,
            provenance={**dict(self.provenance), **provenance},
            profile_sha256="",
        )
        return updated.with_hash()

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any], *, verify_hash: bool = True) -> CharacterProfile:
        references_raw = raw.get("references")
        if not isinstance(references_raw, Mapping):
            raise CharacterIntegrityError("character profile references must be a mapping")
        profile = cls(
            schema_version=str(raw.get("schema_version") or ""),
            character_id=str(raw.get("character_id") or ""),
            display_name=(str(raw["display_name"]) if raw.get("display_name") is not None else None),
            profile_version=int(raw.get("profile_version") or 0),
            status=CharacterStatus(str(raw.get("status") or "")),
            created_at=str(raw.get("created_at") or ""),
            created_by=str(raw.get("created_by") or ""),
            references={
                str(name): CharacterReference.from_dict(item)
                for name, item in references_raw.items()
                if isinstance(item, Mapping)
            },
            attributes=dict(raw.get("attributes") or {}),
            provenance=dict(raw.get("provenance") or {}),
            profile_sha256=str(raw.get("profile_sha256") or ""),
        )
        expected = profile_sha256(profile)
        if verify_hash and profile.profile_sha256 != expected:
            raise CharacterIntegrityError(
                f"character profile digest mismatch: expected {profile.profile_sha256}, got {expected}"
            )
        return profile


def profile_payload(profile: CharacterProfile, *, include_hash: bool = True) -> dict[str, Any]:
    payload = to_primitive(profile)
    if not include_hash:
        payload.pop("profile_sha256", None)
    return payload


def profile_sha256(profile: CharacterProfile) -> str:
    encoded = json.dumps(
        profile_payload(profile, include_hash=False),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CharacterRegistryEntry:
    character_id: str
    display_name: str | None
    status: CharacterStatus
    profile: Path
    profile_sha256: str
    updated_at: str

    def __post_init__(self) -> None:
        if not CHARACTER_ID_RE.fullmatch(self.character_id):
            raise CharacterIntegrityError(f"invalid registry character ID: {self.character_id}")
        if self.profile.is_absolute() or ".." in self.profile.parts:
            raise CharacterIntegrityError("registry profile path must be project-relative")
        if not HASH_RE.fullmatch(self.profile_sha256):
            raise CharacterIntegrityError("registry profile sha256 is invalid")
        _timestamp(self.updated_at, "updated_at")

    @classmethod
    def from_dict(cls, character_id: str, raw: Mapping[str, Any]) -> CharacterRegistryEntry:
        return cls(
            character_id=character_id,
            display_name=(str(raw["display_name"]) if raw.get("display_name") is not None else None),
            status=CharacterStatus(str(raw.get("status") or "")),
            profile=Path(str(raw.get("profile") or "")),
            profile_sha256=str(raw.get("profile_sha256") or ""),
            updated_at=str(raw.get("updated_at") or ""),
        )


@dataclass(frozen=True, slots=True)
class CharacterRegistry:
    revision: int
    active_character: str
    previous_active_character: str | None
    characters: Mapping[str, CharacterRegistryEntry]
    last_event: Mapping[str, Any] = field(default_factory=dict)
    registry_version: str = "1.0"

    def __post_init__(self) -> None:
        if self.registry_version != "1.0" or self.revision < 0:
            raise CharacterIntegrityError("character registry version/revision is invalid")
        if set(self.characters) != {entry.character_id for entry in self.characters.values()}:
            raise CharacterIntegrityError("registry entry keys do not match character IDs")
        active = [entry.character_id for entry in self.characters.values() if entry.status is CharacterStatus.ACTIVE]
        if active != [self.active_character]:
            raise CharacterIntegrityError("character registry must contain exactly one matching ACTIVE entry")
        if self.previous_active_character is not None and self.previous_active_character not in self.characters:
            raise CharacterIntegrityError("previous active character does not exist")

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CharacterRegistry:
        characters = raw.get("characters")
        if not isinstance(characters, Mapping):
            raise CharacterIntegrityError("registry characters must be a mapping")
        return cls(
            registry_version=str(raw.get("registry_version") or ""),
            revision=int(raw.get("revision") if raw.get("revision") is not None else -1),
            active_character=str(raw.get("active_character") or ""),
            previous_active_character=(
                str(raw["previous_active_character"])
                if raw.get("previous_active_character") is not None
                else None
            ),
            characters={
                str(name): CharacterRegistryEntry.from_dict(str(name), item)
                for name, item in characters.items()
                if isinstance(item, Mapping)
            },
            last_event=dict(raw.get("last_event") or {}),
        )


@dataclass(frozen=True, slots=True)
class PreviewArtifact:
    kind: str
    path: Path
    sha256: str
    mime_type: str
    width: int
    height: int
    duration_seconds: float | None = None
    source_run_id: str | None = None
    provider_task_id: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    status: str = "STAGING_PREVIEW_ONLY_NOT_PRODUCTION_APPROVED"

    def __post_init__(self) -> None:
        if self.kind not in {"static", "motion"}:
            raise CharacterIntegrityError("preview kind must be static or motion")
        if self.path.is_absolute() or ".." in self.path.parts:
            raise CharacterIntegrityError("preview path must be project-relative")
        if not HASH_RE.fullmatch(self.sha256) or self.width <= 0 or self.height <= 0:
            raise CharacterIntegrityError("preview integrity fields are invalid")
        if self.kind == "motion" and (self.duration_seconds is None or self.duration_seconds <= 0):
            raise CharacterIntegrityError("motion preview duration is required")

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> PreviewArtifact:
        return cls(
            kind=str(raw.get("kind") or ""),
            path=Path(str(raw.get("path") or "")),
            sha256=str(raw.get("sha256") or ""),
            mime_type=str(raw.get("mime_type") or ""),
            width=int(raw.get("width") or 0),
            height=int(raw.get("height") or 0),
            duration_seconds=(float(raw["duration_seconds"]) if raw.get("duration_seconds") is not None else None),
            source_run_id=(str(raw["source_run_id"]) if raw.get("source_run_id") else None),
            provider_task_id=(str(raw["provider_task_id"]) if raw.get("provider_task_id") else None),
            provenance=dict(raw.get("provenance") or {}),
            status=str(raw.get("status") or ""),
        )


@dataclass(frozen=True, slots=True)
class CharacterBuild:
    build_id: str
    character_id: str
    character_profile_version: int
    character_profile_sha256: str
    status: CharacterStatus
    created_at: str
    selected_references: tuple[Mapping[str, Any], ...] = ()
    static_preview: PreviewArtifact | None = None
    motion_preview: PreviewArtifact | None = None
    technical_checks: Mapping[str, str] = field(default_factory=dict)
    subject_lock: Mapping[str, Any] | None = None
    errors: tuple[Mapping[str, Any], ...] = ()
    events_path: Path | None = None

    def __post_init__(self) -> None:
        if not self.build_id or not CHARACTER_ID_RE.fullmatch(self.character_id):
            raise CharacterIntegrityError("character build identity is invalid")
        if self.character_profile_version < 1 or not HASH_RE.fullmatch(self.character_profile_sha256):
            raise CharacterIntegrityError("character build profile evidence is invalid")
        _timestamp(self.created_at, "build created_at")
        if self.events_path is not None and (
            self.events_path.is_absolute() or ".." in self.events_path.parts
        ):
            raise CharacterIntegrityError("character build events path must be project-relative")

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CharacterBuild:
        return cls(
            build_id=str(raw.get("build_id") or ""),
            character_id=str(raw.get("character_id") or ""),
            character_profile_version=int(raw.get("character_profile_version") or 0),
            character_profile_sha256=str(raw.get("character_profile_sha256") or ""),
            status=CharacterStatus(str(raw.get("status") or "")),
            created_at=str(raw.get("created_at") or ""),
            selected_references=tuple(raw.get("selected_references") or ()),
            static_preview=(PreviewArtifact.from_dict(raw["static_preview"]) if isinstance(raw.get("static_preview"), Mapping) else None),
            motion_preview=(PreviewArtifact.from_dict(raw["motion_preview"]) if isinstance(raw.get("motion_preview"), Mapping) else None),
            technical_checks=dict(raw.get("technical_checks") or {}),
            subject_lock=(dict(raw["subject_lock"]) if isinstance(raw.get("subject_lock"), Mapping) else None),
            errors=tuple(raw.get("errors") or ()),
            events_path=(Path(str(raw["events_path"])) if raw.get("events_path") else None),
        )


@dataclass(frozen=True, slots=True)
class SelectedReference:
    logical_name: str
    path: Path
    sha256: str
    role: str
    tag: str

    def __post_init__(self) -> None:
        if self.logical_name not in REFERENCE_NAMES | {"scene"}:
            raise CharacterIntegrityError("selected reference logical name is invalid")
        if self.path.is_absolute() or ".." in self.path.parts:
            raise CharacterIntegrityError("selected reference path must be project-relative")
        if not HASH_RE.fullmatch(self.sha256):
            raise CharacterIntegrityError("selected reference digest is invalid")
        if not self.role or not re.fullmatch(r"^[a-z][a-z0-9_]*$", self.tag):
            raise CharacterIntegrityError("selected reference role/tag is invalid")


@dataclass(frozen=True, slots=True)
class ReferenceSelection:
    context: str
    references: tuple[SelectedReference, ...]
    max_references: int

    def __post_init__(self) -> None:
        if self.context not in {"baseline", "home", "medium", "product"}:
            raise CharacterIntegrityError("reference selection context is invalid")
        if not 1 <= len(self.references) <= self.max_references:
            raise CharacterIntegrityError("reference selection exceeds provider limits")
        names = [item.logical_name for item in self.references]
        tags = [item.tag for item in self.references]
        if len(names) != len(set(names)) or len(tags) != len(set(tags)):
            raise CharacterIntegrityError("reference selection contains duplicates")


@dataclass(frozen=True, slots=True)
class CharacterView:
    profile: CharacterProfile
    build: CharacterBuild | None
    registry_revision: int
    is_active: bool
    integrity: str = "PASS"


@dataclass(frozen=True, slots=True)
class CharacterLifecycleEvent:
    event_id: str
    event_type: str
    character_id: str
    profile_sha256: str
    registry_revision: int
    at: str
    actor: str
    previous_active_character: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id or not CHARACTER_ID_RE.fullmatch(self.character_id):
            raise CharacterIntegrityError("character lifecycle event identity is invalid")
        if self.event_type not in {
            "created",
            "build_started",
            "preview_ready",
            "approved_and_activated",
            "rejected",
            "reactivated",
            "failed",
        }:
            raise CharacterIntegrityError("character lifecycle event type is invalid")
        if not HASH_RE.fullmatch(self.profile_sha256) or self.registry_revision < 0:
            raise CharacterIntegrityError("character lifecycle event evidence is invalid")
        _timestamp(self.at, "lifecycle event at")
        if self.actor not in {"local_user", "local_ui", "cli", "test", "legacy_migration"}:
            raise CharacterIntegrityError("character lifecycle event actor is invalid")

    def __getitem__(self, name: str) -> Any:
        aliases = {"type": "event_type"}
        return getattr(self, aliases.get(name, name))


ActivationEvent = CharacterLifecycleEvent
