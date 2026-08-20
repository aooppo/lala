# Feature Specification: One-Click Character Switch

**Feature Branch**: `codex/phase1-character-switch`

**Created**: 2026-08-20

**Status**: Draft

**Input**: Phase 1 One-Click Character Switch requirements supplied by the owner.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a Staging Character (Priority: P1)

A non-technical local user supplies one front-facing photo, one full-body photo, and one
three-quarter-view photo, optionally gives the character a display name, and chooses Create
Character. The system validates and safely stores the uploads, creates a stable character profile,
registers it as a staging character, and prepares preview work without changing the current active
character.

**Why this priority**: Safe character creation is the entry point for the entire switch workflow.
It must protect current production behavior even when uploads or preview work fail.

**Independent Test**: Starting with `lala-v1` active, submit three valid local fixture images and
verify that a generated character ID, immutable source copies, profile, hashes, provenance, and a
non-active registry entry are produced while `lala-v1` remains active.

**Acceptance Scenarios**:

1. **Given** `lala-v1` is active and the three required photos are valid, **When** the user creates
   a character, **Then** the system creates a non-colliding technical ID, validates and safely
   stores all inputs, records exact hashes and provenance, and registers the new character without
   changing the active character.
2. **Given** one required photo is missing, corrupt, unsupported, oversized, duplicated in an
   unsafe way, or attempts path escape, **When** creation is requested, **Then** no incomplete
   profile is registered, the active character is unchanged, and the user receives an actionable
   message naming the affected photo.
3. **Given** a profile already exists for a technical ID, **When** a repeated write could overwrite
   it, **Then** the system either returns the existing identical result or safely rejects the
   collision and never overwrites an active or approved profile.

---

### User Story 2 - Review Static and Motion Previews (Priority: P1)

After successful import, the system selects the correct character and scene references for a
staging-only static preview, uses that candidate for a staging-only motion preview, runs automatic
technical checks and Subject Lock diagnostics, and presents the source images and both previews in
one review state. These artifacts never become production-approved keyframes or videos merely by
being created.

**Why this priority**: The single human decision is safe only when it is based on both still and
motion evidence tied to the exact staging character.

**Independent Test**: With fake static and motion generators, build one staging character and
verify deterministic reference selection, character-bound preview evidence, blank human review
fields, diagnostic-only Subject Lock status, and transition to ready for approval without altering
production keyframe or video approval records.

**Acceptance Scenarios**:

1. **Given** a valid staging profile, **When** preview generation succeeds, **Then** the system
   produces a character-bound static preview and motion preview, records their hashes and selected
   references, performs technical checks, and marks the character ready for approval.
2. **Given** a staging profile and a preset requiring face, body, three-quarter, or scene context,
   **When** references are selected, **Then** selection is deterministic, respects provider limits,
   includes only available approved references, and records logical name, role, tag, and hash.
3. **Given** live generation is not authorized, **When** the profile is built, **Then** the system
   creates no provider task, reports that live preview is unavailable, leaves the character ready
   for generation rather than approval, and keeps the active character unchanged.
4. **Given** static or motion preview generation fails, **When** the failure is recorded, **Then**
   existing successful evidence is preserved, the staging character is not activated, and the
   current active character remains unchanged.
5. **Given** Subject Lock reports any diagnostic outcome, **When** the review screen is shown,
   **Then** the outcome is presented as diagnostic evidence only and no identity, quality, or MTL
   approval is inferred.

---

### User Story 3 - Approve, Reject, or Roll Back (Priority: P1)

The user makes exactly one final visual decision. Approve & Activate revalidates the staging
profile and previews, records the explicit approval event, and switches active character safely.
Reject records rejection while retaining evidence. A previously inactive character, including
`lala-v1`, can later be activated through the same safe operation.

**Why this priority**: Activation is the production boundary; it must be concurrency-safe and
failure-atomic so production never has zero or multiple active characters.

**Independent Test**: Prepare two complete profiles and verified previews, then test successful
activation, simulated write failure, concurrent registry change, rejection, and reactivation of
`lala-v1`; at every observation point exactly one character remains active.

**Acceptance Scenarios**:

1. **Given** `lala-v1` is active and a staging character has hash-valid required assets plus both
   verified previews, **When** the user chooses Approve & Activate, **Then** one approval event is
   recorded, the old character becomes inactive, the staging character becomes active, and exactly
   one active character is durably visible.
2. **Given** registry persistence fails or another session changes the active character during
   activation, **When** activation cannot complete safely, **Then** the prior active character
   remains active, no second active character is exposed, and the user receives a retryable error.
3. **Given** a staging character, **When** the user chooses Reject, **Then** its status becomes
   rejected, its evidence is retained, and the current active character is unchanged.
4. **Given** an inactive legacy character, **When** the user activates it, **Then** the same
   validation and atomic-switch rules apply and prior production evidence remains unchanged.

---

### User Story 4 - Complete the Flow Without Technical Operations (Priority: P1)

A local user can open one simple character screen, upload the three required photos, start the
automatic build, see status and previews, and choose Reject or Approve & Activate without using a
terminal or editing configuration files.

**Why this priority**: Removing terminal, path, manifest, and hash knowledge is the core product
outcome of this phase.

**Independent Test**: Run a manual usability scenario from the local screen using three fixture
images and a fake/offline preview backend; the operator performs only upload, create, review, and
one final decision while the screen never asks for a technical confirmation.

**Acceptance Scenarios**:

1. **Given** a first-time non-technical user, **When** they use the default screen, **Then** the
   required inputs are labeled in ordinary language and the primary workflow contains no manifest,
   hash, provider, model, prompt, or promotion step.
2. **Given** character creation is in progress, **When** stages change, **Then** the screen shows
   understandable progress and normalized errors without requiring intermediate confirmation.
3. **Given** a character is ready for approval, **When** the review view appears, **Then** it shows
   the three sources, static preview, motion preview, technical status, diagnostic status, and only
   the final Reject and Approve & Activate decisions.
4. **Given** the optional user-interface dependency is not installed, **When** existing command-line
   workflows are used, **Then** they continue to load and operate normally.

---

### User Story 5 - Automate and Preserve Legacy Workflows (Priority: P2)

Technical operators can list, inspect, import, build, preview, activate, and reject characters
through commands backed by the same services as the local screen. Existing static and video
commands continue to work, defaulting to the active character while accepting an explicit staging
character where preview-safe.

**Why this priority**: Shared service behavior makes the UI testable and preserves automation and
rollback without duplicating workflow logic.

**Independent Test**: Exercise every character command against a temporary project, then run the
existing static validation/dry runs and video validation/previews; legacy records remain readable,
approved sources remain byte-identical, and no network call occurs.

**Acceptance Scenarios**:

1. **Given** multiple registered characters, **When** a command or internal request explicitly
   selects one, **Then** that character is used; otherwise the active character is used; if no
   registry is available, the legacy Lady LaLa sources remain the final compatibility fallback.
2. **Given** no character option on an existing static command, **When** it runs after migration,
   **Then** it uses the active character and preserves the provider request contract, existing
   preset behavior, and run readability.
3. **Given** existing Goal 1 and Goal 2 evidence, **When** the feature is installed, **Then** those
   files are not rewritten and legacy records may be interpreted as `lala-v1` only at read time.
4. **Given** a new character-bound run, **When** evidence is written, **Then** it includes character
   ID, profile version and integrity hash, source hashes, and selected-reference hashes without
   secrets, signed URLs, credentials, or data payloads.

### Edge Cases

- Two sessions attempt activation from the same prior registry revision.
- A process stops after upload storage but before profile registration, or after preview generation
  but before status transition.
- A user uploads the same bytes for multiple required roles or reuses the same filename for
  different bytes.
- A filename contains separators, traversal segments, control characters, HTML, or script text.
- An upload is a symlink, an image decompression bomb, a supported extension with invalid content,
  zero bytes, unsupported MIME, or above the configured size limit.
- A profile references a missing or hash-changed source after import.
- The registry is malformed, has no active character, has two active entries, or disagrees with
  the referenced profile status.
- A preset requests more references than the chosen provider accepts.
- A prompt references a logical tag that is not present in selected references.
- The static preview succeeds but motion preview fails or diagnostics are insufficient.
- A rejected or failed character is requested for production generation.
- `lala-v1` lacks a three-quarter source; legacy full-body flows must remain usable, while presets
  requiring that role fail clearly rather than inventing one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain a character registry with at most one active character and
  MUST initially register the existing Lady LaLa identity as `lala-v1` without changing approved
  source bytes.
- **FR-002**: The system MUST represent character status, profile, reference, registry, build, and
  lifecycle events explicitly, including draft, validating, building, ready-for-generation,
  ready-for-preview, ready-for-approval, active, inactive, failed, and rejected outcomes.
- **FR-003**: A character profile MUST record a system-generated technical ID, optional independent
  display name, version, status, creation source/time, required references, optional references,
  exact content hashes, media metadata, and source provenance; it MUST NOT invent reviewer,
  provider task, approval, or prompt facts.
- **FR-004**: Character IDs MUST be generated by the system, remain safe as storage identifiers,
  be stable after creation, and avoid collision without using display names as paths.
- **FR-005**: Character creation MUST require front-face, full-body, and three-quarter photos and
  MAY accept optional side, expression, product-pose, hair, or accessory references without
  generating missing optional assets.
- **FR-006**: Upload validation MUST verify role completeness, non-zero bounded size, supported MIME
  and format, successful image decoding, positive dimensions, safe containment, and exact hash
  before profile registration.
- **FR-007**: Upload handling MUST ignore user filenames for canonical paths, prevent traversal,
  symlink escape, arbitrary overwrite, active-content interpretation, decompression bombs, and
  collisions, and MUST return role-specific user-facing errors.
- **FR-008**: Original uploads MUST be stored as immutable, character-isolated source evidence;
  derived previews and provenance MUST remain outside all approved-source directories.
- **FR-009**: Character creation MUST be idempotent for an identical safely identifiable request or
  reject duplication without overwriting an existing active, inactive, approved, or staging profile.
- **FR-010**: A failed upload or profile build MUST not leave a registered half-profile, alter the
  active character, delete evidence, or change historical outputs.
- **FR-011**: The registry MUST validate referenced profiles and required asset hashes, reject zero
  or multiple active entries, retain the previous active ID, and persist lifecycle events with
  provenance.
- **FR-012**: Registry mutation and activation MUST use concurrency control and failure-atomic
  persistence so readers never observe zero or multiple active characters.
- **FR-013**: Character resolution MUST follow explicit selection, then active registry selection,
  then legacy fallback, and MUST distinguish production-eligible active characters from staging
  characters permitted only for preview.
- **FR-014**: The system MUST keep character identity references separate from the existing scene
  reference while adapting selected character plus scene references into the current static
  generation contract.
- **FR-015**: Reference selection MUST be deterministic for baseline/full-body, home, medium or
  three-quarter, and product contexts; include only present eligible references; respect provider
  maximums; and record logical name, role, tag, and hash in order.
- **FR-016**: Stable logical tags MUST allow prompts to follow character selection without user
  edits, and every prompt tag MUST exactly correspond to a selected reference within provider tag
  constraints.
- **FR-017**: Existing static generation MUST accept an explicit character selection, otherwise use
  the active character, preserve legacy command behavior, and record character profile integrity
  plus selected character references in new run evidence.
- **FR-018**: New static and motion preview work MUST explicitly bind the staging character ID and
  MUST NOT require changing the global active character.
- **FR-019**: A generated static preview MUST remain a staging keyframe candidate and MUST NOT be
  represented as a production-approved keyframe or become eligible for normal keyframe promotion
  without the existing production review gate.
- **FR-020**: Motion preview MUST reuse the current bounded motion-smoke policy through a distinct
  preview-only path, record character and candidate provenance, and leave production video gates
  unchanged.
- **FR-021**: Activation MUST require a complete hash-valid profile plus decodable, hash-valid static
  and motion previews; offline plans or missing/failed motion previews MUST not satisfy activation.
- **FR-022**: Technical checks MAY report source integrity, reference selection, media decoding,
  generation state, export state, and Subject Lock diagnostic status, but MUST NOT infer human
  identity, creative, voice, lip-sync, keyframe, video, or MTL approval.
- **FR-023**: The default mode MUST make zero network or paid calls; live preview MUST retain every
  existing credential, exact permission, smoke, budget, count, retry, timeout, and task-ID safety
  gate and MUST fail gracefully when unavailable.
- **FR-024**: Approve & Activate MUST revalidate the staging profile and previews, record an explicit
  local-user approval event, atomically make the new character active, and make the prior character
  inactive only if the full operation succeeds.
- **FR-025**: Reject MUST mark the staging character rejected, retain all evidence, and leave the
  current active character unchanged.
- **FR-026**: Any complete inactive character, including `lala-v1`, MUST be eligible for safe
  reactivation using the same validation and atomicity rules.
- **FR-027**: The system MUST provide one local character screen with ordinary-language required
  uploads, optional uploads, Create Character, current status, source previews, static preview,
  motion preview, technical checks, diagnostic status, Reject, Approve & Activate, and current/
  previous character controls.
- **FR-028**: The primary screen MUST require no terminal, path, configuration, manifest, hash,
  provider, prompt, model, or intermediate approval action; technical details MAY appear only in a
  collapsed advanced section.
- **FR-029**: The UI MUST call application services directly rather than shell commands, and the UI
  dependency MUST remain optional so existing installation and commands work without it.
- **FR-030**: Shared services MUST support character list, show, import, build, preview, activate,
  and reject commands with actionable output and safe project-root handling.
- **FR-031**: Character-specific new artifacts MUST record character ID, profile version and hash,
  required source hashes, selected-reference hashes, preview hashes, build state, and relevant task
  provenance while applying recursive secret and signed-URL redaction.
- **FR-032**: Existing Goal 1 and Goal 2 records, approved sources, QA sheets, promotions, prompts,
  provider adapters, and historical outputs MUST remain byte-unchanged and readable.
- **FR-033**: New automated tests MUST cover domain serialization, image validation and upload
  security, registry invariants and concurrent mutation, resolver precedence, deterministic
  reference limits, static/video staging provenance, activation/rejection failure safety, shared
  UI-service lifecycle, legacy compatibility, and zero network access.
- **FR-034**: Project documentation and progress evidence MUST explain the non-technical flow,
  required photos, local screen startup, commands, offline/live behavior, rollback, safety gates,
  test evidence, paid-call count, and remaining Phase 1 limitations.

### Key Entities

- **CharacterStatus**: The controlled lifecycle state of one character and the transitions allowed
  between staging, approval, active, inactive, failure, and rejection.
- **CharacterReference**: One exact character image with logical name, role, stable tag, canonical
  path, hash, MIME type, dimensions, and source provenance.
- **CharacterProfile**: Versioned identity bundle for one technical character ID, containing its
  required and optional references, attributes, creation metadata, status, and integrity evidence.
- **CharacterRegistry**: The authoritative mapping of character IDs to profiles, exactly one active
  character, prior active ID, revision, and lifecycle events.
- **CharacterBuild**: A staging attempt binding one profile to static and motion preview status,
  artifacts, technical checks, diagnostics, errors, and provenance.
- **ReferenceSelection**: Ordered, deterministic references chosen for one character, scene,
  preset, and provider limit.
- **ActivationEvent**: Append-only evidence of an explicit approve, reject, or reactivation action,
  including registry revision and affected character IDs without fabricated review claims.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can complete upload, create, preview, and one final decision using
  only the local character screen and no terminal or configuration edits.
- **SC-002**: For 100% of tested upload failures, current active character and historical production
  outputs remain unchanged and no registered half-profile exists.
- **SC-003**: For 100% of successful and simulated-failure activation tests, registry readers observe
  exactly one active character, including under two concurrent activation attempts.
- **SC-004**: All required reference-selection contexts produce the same ordered selection on
  repeated runs and never exceed the selected provider's reference limit.
- **SC-005**: Every new character-bound static or motion artifact has verifiable profile, source,
  selection, and artifact hashes, while every human decision field remains unset until the user
  takes the final action.
- **SC-006**: Default UI, dry-run, and automated test execution produce zero external network calls,
  zero Runway paid calls, zero HeyGen paid calls, and zero other paid calls.
- **SC-007**: The complete pre-existing test suite plus all character tests passes, static dry runs
  retain 10/5/5 request counts and eight artifacts, and representative video previews retain their
  existing evidence contracts.
- **SC-008**: Every approved-source SHA-256 captured before implementation is identical after
  implementation, and no legacy run, review, output, or promotion record is rewritten.
- **SC-009**: When live preview is unauthorized, the user receives a clear unavailable status,
  creation ends in ready-for-generation rather than ready-for-approval, and no run or provider task
  is created accidentally.
- **SC-010**: `lala-v1` is active immediately after migration and can be restored through one safe
  activation command or one UI action without deleting or modifying the newer character.

## Assumptions

- Phase 1 is a single-user local tool, but separate local sessions may race and therefore registry
  writes still need concurrency protection.
- Motion preview is required for activation because the production use case depends on video;
  static-only success remains reviewable evidence but not activation-ready.
- The existing three Lady LaLa approved anchors remain authoritative. `lala-v1` references the
  existing face and full-body files; the scene remains shared and is not copied into the profile.
- `lala-v1` has no invented three-quarter asset. Legacy presets continue to work, while a context
  that truly requires a three-quarter reference reports the missing role.
- Provider-backed preview may be configured by an operator, but the default user experience remains
  offline/disabled and never weakens paid-call gates.
- Phase 1 does not generate missing viewpoints, expressions, product poses, embeddings, or automatic
  identity scores and does not add authentication, multi-user approval, a database, cloud hosting,
  or a separate web API.
