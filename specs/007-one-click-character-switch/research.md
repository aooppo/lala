# Research: One-Click Character Switch

## Decision 1: Preserve the current pipelines through a character-to-anchor adapter

**Decision**: Add `CharacterResolver` and `ReferenceSelector`, then adapt their result into the
existing `AnchorManifest`, `ReferenceImage`, `GenerationRequest`, and `MotionVideoRequest` models.

**Rationale**: The static runner already enforces prompt tags, provider reference limits, bounded
calls, redaction, and eight-file evidence. The video layer already enforces motion request limits,
task-ID recovery, media validation, blank QA, and live gates. Narrow adapters preserve that tested
behavior and provider-neutral boundaries.

**Alternatives considered**: A separate character generation pipeline would duplicate safety and
evidence logic. A broad redesign of all manifests and presets would risk legacy compatibility and
is beyond Phase 1.

## Decision 2: Use immutable profile snapshots and an atomic registry pointer

**Decision**: Persist each profile state as a new versioned YAML snapshot. Keep current status,
profile path, active ID, previous active ID, and monotonic revision in one registry file protected by
an advisory filesystem lock. Mutations write/fsync a temporary registry, verify the expected
revision/active ID, and atomically replace it.

**Rationale**: Atomic replacement of one file is reliable on the local filesystem; attempting to
atomically rewrite two profiles plus one registry is not. Readers resolve state only through the
registry, so orphan prewritten snapshots cannot create a second active character.

**Alternatives considered**: In-place profile updates lose immutable provenance. A database is out
of scope. Locking without revision compare-and-swap does not detect stale UI sessions.

## Decision 3: Stage uploads outside authority, copy exact bytes on activation

**Decision**: Store validated raw uploads exclusively under `assets/characters/<id>/source/` while
building. On activation, copy exact required/reference bytes with exclusive creation into
`assets/approved_anchors/characters/<id>/`, verify hashes, and point the new active profile snapshot
to those copies. Derived previews remain under `outputs/characters/`.

**Rationale**: This preserves the constitution's `assets/approved_anchors/` authority boundary,
avoids treating unreviewed uploads as approved, and keeps promotion copy-only. The existing anchors
are never modified.

**Alternatives considered**: Keeping active assets under `assets/characters/` would make a second
authority root. Writing previews into approved anchors would violate source immutability.

## Decision 4: Optional Streamlit UI with a service-only business layer

**Decision**: Add Streamlit as a `ui` optional dependency and keep the app module limited to upload
widgets, status presentation, preview rendering, and calls into `CharacterService`.

**Rationale**: The repository is Python-only, Phase 1 is local/single-page, and Streamlit supports
uploads/images/video without Node or a separate API. Optional installation keeps existing CLI/tests
unchanged.

**Alternatives considered**: React/Vue plus an API is explicitly out of scope. A terminal UI fails
the non-technical-user requirement. Embedding logic in Streamlit would make lifecycle/security hard
to test.

## Decision 5: Validate uploads from bounded bytes, not trusted paths or names

**Decision**: Accept an application-level upload object containing role, bytes/stream, declared MIME,
and optional display filename. Enforce a configurable byte limit while copying to an exclusive
temporary file under the character root, reject symlinks/path input, validate MIME against decoded
Pillow format, convert decompression-bomb warnings to errors, hash exact bytes, and atomically place
the canonical role/format filename.

**Rationale**: Streamlit upload names and MIME are user-controlled. Validating inside the controlled
root prevents traversal, arbitrary overwrite, and TOCTOU path substitution.

**Alternatives considered**: Accepting arbitrary source paths is retained only for the technical
CLI import, where paths are read-only inputs and their bytes are copied into the same controlled
validator; paths never select destinations.

## Decision 6: Reuse legacy logical tags for prompt compatibility

**Decision**: Map character roles to stable tags `lala_face`, `lala_look`, and `lala_3q`, and keep
the shared scene tag `lala_scene`. Existing prompts continue unchanged; one versioned character
preview prompt can use the three character tags.

**Rationale**: Tags are logical provider identifiers, not filenames. Reusing the existing face/body
tags avoids rewriting proven prompts and stays within Runway's recorded 3–16 character constraint.

**Alternatives considered**: Renaming all tags to `char_*` would force prompt/config migrations with
no user value. Character-specific tags would make prompt editing necessary and risk collisions.

## Decision 7: Motion preview is preview-only and mandatory for activation

**Decision**: Use the current five-second, one-result, bounded motion-smoke request policy against
the staging static candidate, but persist it under character preview evidence with an explicit
`CHARACTER_PREVIEW_ONLY_NOT_PRODUCTION_APPROVED` keyframe status. Both static and motion media must
exist, decode, and match recorded hashes before activation.

**Rationale**: The final decision needs eyes, mouth, framing, and stability evidence. Existing
production video validation correctly rejects unapproved keyframes, so a distinct staging path is
safer than weakening that validator.

**Alternatives considered**: Adding staging candidates to the approved keyframe manifest would
conflate approval domains. Allowing static-only activation conflicts with the video-focused use
case and the owner's recommended first-version rule.

## Decision 8: Offline means planned, never simulated approval

**Decision**: Character creation and profile build are always offline. Without explicit live gates,
preview returns `READY_FOR_GENERATION`, writes no fake media, makes no provider task, and disables
activation. Tests and demos may inject fake backends that create real local fixture media and are
clearly marked simulated.

**Rationale**: A dry-run request is not a visual preview. Treating it as one would make the final
human decision meaningless and weaken paid-call safety.

**Alternatives considered**: Copying uploads as generated previews is misleading. Automatically
enabling live work violates the constitution and direct owner prohibition.

## Decision 9: No new provider fields or pricing claims

**Decision**: Character integration changes only provider-neutral provenance and reference source
selection. It uses the current provider requests, models, limits, prompts, and pricing evidence
already documented in `specs/001-lala-static-images/research.md` and
`specs/002-lala-video-pipeline/research.md`.

**Rationale**: The feature does not require a provider API expansion, and repository rules prohibit
inferring fields from web UIs.

**Alternatives considered**: No alternative is necessary until a provider capability requirement
changes; such a change would require new official evidence.
