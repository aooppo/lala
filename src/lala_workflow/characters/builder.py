from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping

from ..domain import utc_now
from .domain import CharacterProfile, CharacterStatus, CharacterUpload
from .errors import CharacterIntegrityError, RegistryConflictError
from .registry import CharacterRegistryStore
from .storage import CharacterStorage
from .validation import DEFAULT_MAX_UPLOAD_BYTES, validate_uploads


class CharacterProfileBuilder:
    def __init__(
        self,
        project_root: Path,
        *,
        storage: CharacterStorage | None = None,
        registry: CharacterRegistryStore | None = None,
        max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    ) -> None:
        self.root = project_root.resolve()
        self.storage = storage or CharacterStorage(self.root)
        self.registry = registry or CharacterRegistryStore(self.root, storage=self.storage)
        self.max_upload_bytes = max_upload_bytes

    def allocate_id(self, *, now: datetime | None = None) -> str:
        day = (now or utc_now()).strftime("%Y%m%d")
        existing: set[str] = set()
        if self.registry.exists():
            existing.update(self.registry.load().characters)
        for sequence in range(1, 1000):
            candidate = f"character-{day}-{sequence:03d}"
            if candidate in existing:
                continue
            if (self.storage.staging_root / candidate).exists():
                continue
            if any(self.storage.profiles_root.glob(f"{candidate}-v*.yaml")):
                continue
            return candidate
        raise RegistryConflictError("could not allocate a collision-free character ID")

    def create(
        self,
        uploads: Mapping[str, CharacterUpload],
        *,
        display_name: str | None,
        created_by: str,
        now: datetime | None = None,
    ) -> tuple[CharacterProfile, Path]:
        validated = validate_uploads(uploads, max_upload_bytes=self.max_upload_bytes)
        character_id = self.allocate_id(now=now)
        references = self.storage.write_sources(character_id, validated)
        created_at = (now or utc_now()).isoformat()
        profile = CharacterProfile(
            character_id=character_id,
            display_name=display_name.strip() if display_name is not None else None,
            profile_version=1,
            status=CharacterStatus.DRAFT,
            created_at=created_at,
            created_by=created_by,
            references=references,
            provenance={
                "event": "imported",
                "source_hashes": {name: item.sha256 for name, item in references.items()},
            },
        )
        try:
            return self.storage.write_profile(profile)
        except FileExistsError as exc:
            raise CharacterIntegrityError("character profile collision; no file was overwritten") from exc
