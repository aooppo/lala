# Feature Specification: Reproducible Lady LaLa Video Pipeline

**Feature Branch**: `main`

**Feature Directory**: `002-lala-video-pipeline`

**Created**: 2026-08-18

**Status**: Offline authoritative-input import complete; an approved reusable voice profile or
approved per-script narration remains an external prerequisite

**Input**: User description: "Build and complete a reproducible Lady LaLa video-generation
pipeline using approved Goal 1 keyframes, the approved Lady LaLa voice, and exact MTL-provided
scripts for product-page, tooltip, and homepage pilot videos."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate a Video Run Without Spending (Priority: P1)

As a video-production operator, I can validate all approved inputs and preview a resolved shot plan
without contacting a paid generation service, so missing assets, altered copy, unsupported
settings, excessive variation counts, and incomplete reproducibility evidence are caught before
credits are spent.

**Why this priority**: Safe input validation and zero-cost preview are prerequisites for every
talking shot, motion shot, and final candidate.

**Independent Test**: Supply approved fixture inputs for one preset, request a preview, and verify
that every source is validated and hashed, the exact script and planned provider-call count are
recorded, all run evidence is created, and no generation service is contacted.

**Acceptance Scenarios**:

1. **Given** an approved keyframe, approved audio, exact MTL script, and valid preset, **When** the
   operator previews the run, **Then** the workflow validates and hashes every source, preserves
   the exact script, resolves prompts and shots, reports call counts and available cost estimates,
   and creates sanitized evidence without a paid call.
2. **Given** a missing keyframe, voice asset, or authoritative script, **When** validation runs,
   **Then** it stops before provider interaction and identifies every missing required input.
3. **Given** script content that does not match its recorded hash, **When** validation runs,
   **Then** it rejects the run and does not create replacement copy.
4. **Given** a requested variation, duration, concurrency, retry, or timeout value above an owner-
   reviewed bound, **When** preview or live validation runs, **Then** it rejects the request before
   provider interaction.

---

### User Story 2 - Prove One Short Talking Shot (Priority: P2)

As a video-production operator, I can produce a tightly bounded short talking-shot candidate from
one approved keyframe and one approved audio segment, so a human reviewer can assess identity and
lip-sync quality before any complete pilot video is attempted.

**Why this priority**: Talking-shot quality is the highest-risk dependency and must be proven at
the smallest paid scope before broader generation.

**Independent Test**: With simulated providers, complete a one-result short talking-shot run and
verify source integrity, bounded task behavior, downloaded output, cost record, and blank human QA
fields. With owner authorization and valid credentials, the same flow can be reviewed using one
real result.

**Acceptance Scenarios**:

1. **Given** validated approved inputs and simulated provider success, **When** the smoke-test flow
   runs, **Then** exactly one short talking result is downloaded and receives complete run, cost,
   and review evidence.
2. **Given** live mode without exact environment permission or credentials, **When** submission is
   attempted, **Then** it is refused before a paid call.
3. **Given** a provider task identifier has been returned, **When** polling or download encounters
   a retryable failure, **Then** the workflow continues that task within bounds and never submits a
   duplicate paid task.
4. **Given** a completed short result, **When** the QA sheet is opened, **Then** a reviewer can
   record visual identity, face stability, hair, wardrobe, jewelry, lip sync, mouth and teeth,
   eyes, background, motion, audio, and synchronization decisions without any pre-filled approval.

---

### User Story 3 - Generate Three Pilot Workflows (Priority: P3)

As a video-production operator, I can prepare and run product-page, tooltip, and homepage video
workflows from exact approved copy, so MTL receives reviewable candidate versions for all three
required placements.

**Why this priority**: These three candidates are the business deliverables, but they depend on a
successful talking-shot review and approved source package.

**Independent Test**: Run each preset against simulated providers and verify its script selection,
shot structure, variations, deterministic final naming, source-to-output traceability, and final
review rows independently of the other two presets.

**Acceptance Scenarios**:

1. **Given** the product-page preset and approved inputs, **When** it is resolved, **Then** it uses
   the exact product-page script and supports an opening Lady LaLa shot, product interaction and
   reward visuals, and a Lady LaLa closing.
2. **Given** the tooltip preset and approved inputs, **When** it is resolved, **Then** it uses the
   exact tooltip script and supports one concise Lady LaLa shot plus an optional reward graphic.
3. **Given** the homepage preset and approved inputs, **When** it is resolved, **Then** it uses the
   exact homepage script and supports an establishing scene, Lady LaLa introduction and closing,
   product interaction, and reward visuals.
4. **Given** any preset, **When** a simpler fallback is selected, **Then** it can produce a single-
   talking-shot candidate without changing script wording or approved sources.

---

### User Story 4 - Compare Alternate Shots Before Final Assembly (Priority: P4)

As an MTL reviewer, I can review a small, bounded set of alternate talking and motion shots before
expensive final assembly, so preferred material can be selected without generating unnecessary
complete videos.

**Why this priority**: Shot-level selection controls cost while preserving creative choice.

**Independent Test**: Resolve a multi-shot fixture preset with the default variation policy and
verify that three talking alternatives and three motion alternatives per applicable shot can be
reviewed before at most two final edits are prepared.

**Acceptance Scenarios**:

1. **Given** default settings, **When** a multi-shot run is planned, **Then** no applicable talking
   or motion shot requests more than three alternatives and no video requests more than two final
   edits.
2. **Given** shot alternatives have not been selected by a human, **When** final assembly is
   requested, **Then** the workflow refuses expensive assembly or uses only an explicitly
   configured MVP fallback.
3. **Given** selected downloaded shots and approved audio, **When** final candidates are assembled,
   **Then** the repeatable edit operations and exact inputs are recorded with each output.

---

### User Story 5 - Review and Promote a Final Candidate (Priority: P5)

As an MTL reviewer, I receive one blank decision row per candidate and can promote only a
specifically approved final video by copying it with provenance, so candidates remain immutable
evidence and approvals are explicit.

**Why this priority**: The workflow is complete only when reviewable final candidates and a safe
approval boundary exist.

**Independent Test**: Mark one fixture candidate as reviewed, promote it, and verify the source is
unchanged, the approved copy has deterministic naming, and provenance identifies the source run,
candidate, hashes, scripts, media inputs, providers, reviewer, and date.

**Acceptance Scenarios**:

1. **Given** newly generated candidates, **When** their QA file is created, **Then** there is
   exactly one row per candidate and all subjective, reviewer, time, note, and readiness fields
   are blank.
2. **Given** a candidate without explicit MTL readiness, reviewer, and review date, **When**
   promotion is attempted, **Then** it is rejected without copying or overwriting media.
3. **Given** a fully reviewed candidate whose hash matches its run evidence, **When** it is
   promoted, **Then** a new approved copy and provenance record are created while the candidate
   remains unchanged.

### Edge Cases

- An approved input path escapes its configured approved-source directory or points to a derived
  asset without promotion provenance.
- A generated keyframe exists without a promotion record, or an owner-supplied legacy keyframe
  exists without its distinct package hash, package-relative source path, provenance record, and
  owner-approval reference.
- A legacy keyframe record attempts to imitate generated-run provenance, or accepting it weakens
  the required Goal 1 promotion evidence for ordinary generated keyframes.
- An approved audio file is unreadable, silent, empty, not in an accepted lossless format, or does
  not correspond to the selected script.
- A reusable voice profile is configured but its approval status is blank or not approved.
- Script line endings or trailing newline behavior changes while visible wording appears the same.
- A subtitle or caption would require altering punctuation, capitalization, or wording.
- A talking provider is configured for motion-only work, or a motion provider is assigned talking
  or lip-sync work it does not officially support.
- A task remains pending until its overall timeout, succeeds without a downloadable result, or
  returns a malformed result.
- A submission response is lost after the provider accepted the task, so safe retry cannot prove
  whether another paid task would be created.
- A download succeeds partially, has an unexpected media type, or fails content validation.
- Selected shots have incompatible dimensions, frame rates, audio streams, durations, or aspect
  ratios.
- Exact audio duration does not fit the planned shot timing without trimming spoken content.
- Available pricing is missing, outdated, uses a different currency, or cannot determine actual
  cost after completion.
- Two runs begin in the same second or two candidates would receive the same deterministic name.
- Review rows are reordered, duplicated, missing candidate identifiers, or contain an invalid
  review time.
- An approved filename already exists; neither the prior approval nor the new candidate may be
  overwritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The workflow MUST consume approved anchors, keyframes, voice sources, approved audio,
  and MTL scripts without modifying, renaming, moving, recompressing, or replacing them.
- **FR-002**: Derived audio, talking shots, motion shots, edit candidates, final candidates, and
  approved copies MUST remain separate from every approved-source directory.
- **FR-003**: Validation MUST require at least one human-approved keyframe with provenance before a
  talking or complete video run can proceed. It MUST accept either a genuine Goal 1 copy-based
  promotion or the separately audited `owner_supplied_legacy_asset` provenance type, without
  treating an approved anchor as a generated Goal 1 promotion.
- **FR-004**: Validation MUST support both an existing approved audio file and an approved reusable
  voice profile, and MUST prefer existing approved audio when it is available for the selected
  script.
- **FR-005**: The workflow MUST require distinct authoritative MTL script files for product-page,
  tooltip, and homepage presets and MUST never generate replacement copy when one is absent.
- **FR-006**: Every script MUST have a version, MTL source attribution, immutable modification
  policy, exact recorded content, and SHA-256 digest.
- **FR-007**: Before any generation, the workflow MUST reject script content whose current digest
  does not match its configured or recorded digest.
- **FR-008**: Captions and subtitles MAY reproduce a selected script exactly but MUST NOT alter its
  wording, punctuation, capitalization, or sequence.
- **FR-009**: Operators MUST be able to select product-page, tooltip, and homepage presets, each
  linked to exactly one authoritative script and an independently reviewable shot plan.
- **FR-010**: Each preset MUST support multiple talking and motion shots and MUST also support a
  simple single-talking-shot fallback.
- **FR-011**: Product-page plans MUST support a Lady LaLa opening, product interaction or graphic,
  reward explanation visual, and Lady LaLa closing.
- **FR-012**: Tooltip plans MUST support a short Lady LaLa message and an optional exact reward
  graphic.
- **FR-013**: Homepage plans MUST support a home-decor establishing shot, Lady LaLa introduction,
  product interaction, reward visual, and Lady LaLa closing.
- **FR-014**: Talking, motion, and optional voice work MUST remain replaceable responsibilities so
  a provider is used only for capabilities documented in its current official interface.
- **FR-015**: Provider capability and pricing claims used for live work or estimates MUST cite the
  official source and verification date; unavailable pricing MUST remain explicitly unknown.
- **FR-016**: A short talking-shot smoke-test workflow MUST accept one approved keyframe and an
  eight-to-twelve-second approved audio segment and support review of up to three alternatives.
- **FR-017**: The first live video-provider test MUST request exactly one short talking result and
  MUST precede complete pilot-video generation.
- **FR-018**: Default variation policy MUST allow up to three talking alternatives per applicable
  shot, three motion alternatives per applicable shot, and two final edits per video.
- **FR-019**: Variation counts, generated duration, concurrency, retries, provider timeouts, and
  final-edit counts MUST remain within owner-reviewed maximums.
- **FR-020**: The workflow MUST support shot-level human selection before complete candidate
  assembly so full-video generation is not multiplied unnecessarily.
- **FR-021**: Repeatable local operations MUST perform ordinary concatenation, trimming, audio
  normalization or replacement, transitions, scaling, letterboxing, synchronization, and export
  where practical, and the exact operations MUST be recorded.
- **FR-022**: Preview mode MUST validate all sources and recorded hashes, resolve prompts and shot
  plans, validate provider settings, calculate expected provider calls, include cost estimates
  only where supportable, write request previews, and make zero generation or paid calls.
- **FR-023**: Paid video calls MUST be disabled by default and require explicit live mode, exact
  video-call environment permission, and a non-empty local credential for every provider that
  would receive a request.
- **FR-024**: Live submission MUST enforce one-at-a-time default concurrency, at most two retryable
  attempts where safe, and an overall provider timeout no greater than thirty minutes unless the
  owner approves a bounded change.
- **FR-025**: Once a provider returns a task identifier, retries MUST continue or download that
  task and MUST NOT create a replacement submission automatically.
- **FR-026**: Every run MUST have a unique identifier and an append-only evidence bundle containing
  request, resolved configuration, exact script, script hash, audio hash, keyframe hash, shot plan,
  task events, provider results, edit operations, review rows, cost record, and summary.
- **FR-027**: Run evidence MUST record provider and model, generated seconds, attempt counts,
  success and failure counts, estimated or actual cost when known, currency, and pricing source
  date when available, without fabricating unavailable values.
- **FR-028**: Every downloaded or locally produced media output MUST be content-validated, hashed,
  and traceable to its source request, source media, script, provider task, and edit inputs.
- **FR-029**: Final candidate filenames MUST deterministically identify Lady LaLa, the selected
  preset, candidate status, and a monotonically increasing version without overwriting an existing
  file.
- **FR-030**: Every newly generated candidate MUST receive exactly one QA row covering run,
  preset, candidate, visual identity, face, hair, wardrobe, jewelry, lip sync, mouth and teeth,
  eyes, audio, synchronization, background, motion, script match, technical export, MTL readiness,
  reviewer, review time, and notes.
- **FR-031**: All subjective QA, readiness, reviewer, review-time, and note fields MUST start blank;
  the workflow MUST NOT automatically approve identity, voice, script, lip sync, or MTL readiness.
- **FR-032**: Promotion MUST require an explicitly ready candidate with reviewer and review time,
  verify source integrity, copy rather than move the candidate, refuse overwrite, and record
  complete provenance beside the approved version.
- **FR-033**: Credentials, secret values, authorization headers, and sensitive provider payloads
  MUST NOT appear in versioned files, requests, events, errors, results, logs, fixtures, or run
  summaries.
- **FR-034**: Automated verification MUST cover source and script immutability, hashing, presets,
  shot plans, provider translation, safe retries, timeouts, live-call guards, downloads, local
  assembly, costs, QA rows, naming, run evidence, failure recovery, and secret redaction without
  network or paid calls.
- **FR-035**: Operator documentation MUST describe input placement and approval expectations,
  preview and staged live workflows, each pilot preset, human shot and candidate review, cost and
  security controls, failure recovery, reporting, and promotion.
- **FR-036**: An `owner_supplied_legacy_asset` keyframe MUST record and validate its provenance
  type, approved-source path and digest, provenance-record path, source package name and SHA-256,
  package-relative source path, and owner-approval reference. It MUST NOT require or fabricate a
  Goal 1 run/output ID, provider task ID, prompt version, model, reviewer, or approval timestamp.
- **FR-037**: Canonical Lady LaLa voice-cloning WAVs MUST be registered through a hash-pinned
  source manifest, validated as non-empty PCM WAV files under `assets/voice/source/`, and remain
  semantically distinct from approved per-script narration and an approved reusable voice
  profile. Their presence alone MUST NOT unblock talking execution.
- **FR-038**: Importing an owner-supplied authoritative package MUST copy each selected source
  without byte changes, verify package/member digests before copy and destination digests after
  copy, preserve existing approved anchors and run evidence, and record the package provenance in
  repository manifests.

### Key Entities

- **Approved Source Package**: Immutable visual anchors, genuine promoted keyframes or narrowly
  audited owner-supplied legacy keyframes, approved voice sources or audio, and exact MTL scripts
  required by a run.
- **Voice Profile**: Approval and provenance for an optional reusable voice, including source,
  provider identity, version, output characteristics, and configured delivery traits without
  credentials.
- **Script Record**: One immutable MTL source file plus preset role, version, exact content,
  attribution, modification policy, and digest.
- **Video Preset**: Named pilot-video intent joining one script, output format, variation policy,
  shot strategy, and single-shot fallback.
- **Shot Plan**: Ordered talking, motion, graphic, or deterministic-edit steps plus source roles,
  variation counts, selection requirements, and expected duration.
- **Provider Request**: Validated, provider-neutral intent for voice, talking, or motion work with
  source provenance and bounded execution settings.
- **Provider Task and Result**: External or simulated asynchronous work item, ordered lifecycle
  evidence, normalized success or failure, outputs, durations, and sanitized diagnostics.
- **Video Run**: Append-only reproducibility bundle joining source hashes, resolved plan, requests,
  task evidence, downloaded assets, edit operations, costs, candidates, and review rows.
- **Cost Record**: Known or unknown voice, talking, motion, editing, storage, and total costs plus
  currency, basis, provider/model, generated seconds, attempts, and pricing source date.
- **Video Review Row**: One candidate's provenance and blank-or-human-entered technical,
  identity, synchronization, quality, and MTL-readiness decisions.
- **Approved Video**: Preserved copy of a specifically reviewed final candidate plus promotion
  provenance; never a replacement for the source candidate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can preview each of the three presets and receive a complete validation
  result, resolved shot plan, call count, and sanitized evidence bundle within 60 seconds, with
  zero generation calls and zero paid calls.
- **SC-002**: One hundred percent of accepted runs record and revalidate SHA-256 digests for every
  approved keyframe, selected audio source, and exact script used.
- **SC-003**: One hundred percent of the three authoritative scripts used in candidates match their
  source content byte-for-byte and are attributed to MTL; absent scripts stop before generation.
- **SC-004**: A simulated short talking test produces exactly one reviewable result from one
  keyframe and one eight-to-twelve-second audio segment, while a live test cannot exceed that scope
  until it has been explicitly reviewed.
- **SC-005**: Default plans never exceed three talking alternatives per applicable shot, three
  motion alternatives per applicable shot, or two final edits per video.
- **SC-006**: Product-page, tooltip, and homepage workflows each produce independently reviewable,
  deterministically named candidates in simulated end-to-end verification.
- **SC-007**: One hundred percent of runs contain all thirteen required evidence artifacts, and
  every cost field without verified evidence remains empty rather than fabricated.
- **SC-008**: One hundred percent of newly created QA sheets contain exactly one row per candidate
  and leave every subjective or human-entered review field blank.
- **SC-009**: All automated retry, timeout, concurrency, variation, and live-call guards terminate
  at their configured bounds, and no automated test performs a network or paid call.
- **SC-010**: Approved visual-anchor hashes remain identical to the Goal 1 baseline, and every
  supplied approved keyframe, voice asset, and script remains byte-for-byte unchanged after all
  preview, simulated, and live workflows.
- **SC-011**: A provider for one responsibility can be replaced by a simulated alternative while
  planning, evidence, assembly, reporting, and review behavior remain unchanged.
- **SC-012**: Every promotion attempt either creates a new traceable approved copy while preserving
  the candidate or rejects the attempt before copying when review or integrity evidence is
  insufficient.
- **SC-013**: A security audit finds zero credential values, authorization headers, or unredacted
  sensitive provider payloads in versioned files, tests, logs, run evidence, and outputs.
- **SC-014**: When authoritative inputs, valid credentials, exact live permission, and prior-stage
  approval are present, one short talking result can complete successfully; otherwise all offline
  acceptance remains complete and each missing external prerequisite is reported precisely.
- **SC-015**: The owner-supplied package keyframe, all three MTL scripts, and all eight canonical
  voice sources revalidate to their package-recorded SHA-256 values after import, while every
  approved-anchor digest remains identical to the Goal 1 baseline.
- **SC-016**: With the imported keyframe, scripts, and canonical voice-source manifest present,
  production validation reports only the absence of a real approved HeyGen Starfish/private Lady
  LaLa voice profile or approved per-script narration WAVs; it creates no run and makes zero
  provider calls.

## Assumptions

- The owner supplied `lala-goal2-authoritative-inputs-v1.0.0.zip`, approved its landscape pilot
  keyframe candidate, approved all eight canonical voice-cloning source WAVs, and identified three
  authoritative MTL scripts. No genuine Goal 1 promoted keyframe exists in the repository, so the
  package keyframe uses the distinct `owner_supplied_legacy_asset` provenance path.
- The canonical voice-cloning WAVs are not the three scripts' final narration. A real approved
  HeyGen Starfish/private Lady LaLa voice profile or approved per-script WAVs remains required.
- Human reviewers determine whether the live talking-shot smoke result passes before any complete
  pilot generation and select preferred shot alternatives before final assembly.
- Exact script matching is byte-for-byte, including punctuation, capitalization, line endings,
  and trailing newline; any normalization is a recorded owner decision, not automatic behavior.
- Existing approved audio is preferred over new synthesis whenever it is available for the exact
  selected script.
- Generated subtitles are optional and, when enabled, reproduce authoritative script content
  exactly.
- Network access is required only for official provider research and explicitly authorized live
  calls; previews, local assembly tests, and all automated verification remain offline-capable.
- Missing provider pricing is represented as unknown and does not block preview or simulated
  verification.
- The repository remains responsible only for static-image and video media production workflows;
  storefront integration, automated biometric scoring, and automatic MTL approval remain outside
  scope.

## Dependencies

- A genuine promoted Goal 1 keyframe or a separately audited owner-approved external/legacy
  keyframe with unchanged approved-anchor sources.
- Approved Lady LaLa per-script audio or an approved reusable voice profile suitable for the exact
  MTL scripts; canonical clone-source WAVs alone are insufficient.
- Authoritative MTL product-page, tooltip, and homepage script files with exact package hashes.
- Current official documentation for every configured talking, motion, and optional voice
  provider, including supported capabilities and available pricing evidence.
- A local deterministic media-editing runtime for assembly and export.
- Provider credentials, exact paid-call permission, and explicit owner authorization only for the
  staged live talking test and later approved generation stages.
