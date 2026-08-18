# Feature Specification: Reproducible Lady LaLa Static Images

**Feature Branch**: `001-lala-static-images`

**Created**: 2026-08-18

**Status**: Implemented; offline acceptance complete, live smoke test externally blocked

**Input**: User description: "Build a production-ready, reproducible Lady LaLa static-image generation pipeline using approved anchors as the only authoritative visual identity source."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate and Preview a Safe Run (Priority: P1)

As an image-production operator, I can validate the approved anchors and preview a complete
generation run without contacting a paid generation service, so I can catch configuration,
identity-source, prompt, and request problems before spending credits.

**Why this priority**: Safe, reproducible validation is the minimum viable workflow and is a
prerequisite for every paid or reviewed output.

**Independent Test**: Place the approved anchors at their configured paths, select each preset in
preview mode, and verify that the run produces a complete request preview and reproducibility
record without any generation or paid call.

**Acceptance Scenarios**:

1. **Given** all required approved anchors and valid configuration, **When** the operator previews
   the baseline preset, **Then** the workflow validates the assets, hashes them, resolves the
   versioned prompt and references, validates provider capabilities, and records a ten-candidate
   request without contacting the provider.
2. **Given** a missing, unreadable, unsupported, or invalid anchor, **When** validation runs,
   **Then** it stops before submission and identifies the exact invalid logical anchor.
3. **Given** duplicate anchor roles or reference tags, **When** validation runs, **Then** the
   manifest is rejected before any provider interaction.
4. **Given** preview mode, **When** the run finishes, **Then** no paid or generation request has
   occurred and a complete sanitized run record exists.

---

### User Story 2 - Generate Controlled Static Candidates (Priority: P2)

As an image-production operator, I can generate bounded batches from approved identity and scene
references using three controlled presets, so I can produce consistent candidates for studio,
home-decor, and product-page uses.

**Why this priority**: Candidate generation delivers the primary production value after the safe
preview path is proven.

**Independent Test**: Use a simulated provider to run each preset and verify requested counts,
references, prompt versions, output retrieval, bounded retries/timeouts, and normalized metadata;
with explicit paid-call authorization, run exactly one live smoke-test image.

**Acceptance Scenarios**:

1. **Given** the baseline identity preset, **When** no count override is supplied, **Then** ten
   variations are requested using only the face and full-body anchors and all identity-preserving
   constraints.
2. **Given** the home-decor preset, **When** no count override is supplied, **Then** five variations
   are requested using the face, full-body, and approved scene anchors.
3. **Given** the product-page-clean preset, **When** no count override is supplied, **Then** five
   variations are requested using the approved identity and full-body look on a clean warm-neutral
   background.
4. **Given** any live request, **When** one of explicit live mode, live-call permission, or provider
   credentials is absent, **Then** the workflow refuses submission before a paid call.
5. **Given** transient provider failures, **When** retry or timeout bounds are reached, **Then** the
   run stops, records the normalized failure, and performs no unbounded retries.
6. **Given** a provider result with downloadable images, **When** the task succeeds, **Then** each
   output is stored separately from approved anchors with its source task and reproducibility data.

---

### User Story 3 - Review Candidates Without Fabricated Approval (Priority: P3)

As a human reviewer, I receive one review row per generated candidate with all subjective fields
blank, so I can evaluate identity, appearance, scene quality, and keyframe readiness without the
system pretending to make an approval decision.

**Why this priority**: Human QA protects Lady LaLa's identity and is required before generated
images can become downstream video keyframes.

**Independent Test**: Produce a simulated successful run with multiple outputs and verify the
review sheet contains one row per output, all required provenance fields, and blank subjective
decision fields.

**Acceptance Scenarios**:

1. **Given** a run with three outputs, **When** its review sheet is created, **Then** it contains
   exactly three rows with the required identity, appearance, scene, readiness, reviewer, and note
   fields.
2. **Given** a newly generated review sheet, **When** it is opened, **Then** all subjective pass,
   readiness, reviewer, review-time, and note fields are blank.
3. **Given** a completed human review, **When** a run summary is requested, **Then** the operator can
   inspect the run's configuration, prompt, references, outputs, and review artifact together.

---

### User Story 4 - Promote a Human-Approved Keyframe (Priority: P4)

As a reviewer, I can promote a specifically reviewed candidate to the approved-keyframe area
without replacing its original, so future video work receives a traceable, human-approved static
source.

**Why this priority**: Promotion is the handoff boundary between this static-image goal and the
future video pipeline.

**Independent Test**: Mark a fixture candidate as ready with reviewer and approval date, promote
it, and verify the original remains intact while the approved copy and promotion metadata identify
the source run, source image hash, anchor version, prompt version, provider, model, reviewer, and
approval date.

**Acceptance Scenarios**:

1. **Given** a review row not explicitly marked video-keyframe-ready, **When** promotion is
   attempted, **Then** promotion is rejected without copying or replacing an image.
2. **Given** a ready row with reviewer and approval date, **When** promotion is requested, **Then**
   the image is copied to the approved-keyframe area, the original remains unchanged, and complete
   promotion metadata is recorded.
3. **Given** a missing output or a source whose hash no longer matches the run record, **When**
   promotion is attempted, **Then** promotion stops with an actionable integrity error.

### Edge Cases

- A configured anchor path escapes the approved-anchor directory or points to a derived file.
- Extra character-sheet, profile, back-view, wardrobe, or expression images exist beside required
  anchors but are not explicitly selected as generation inputs.
- A prompt file is empty, has an unrecognized version name, or references a tag not present in the
  selected anchors.
- A requested count, concurrency, retry count, timeout, ratio, resolution, model, or seed exceeds
  the selected provider's declared capabilities.
- A provider does not support deterministic seeds; seed metadata must distinguish requested,
  accepted, and unavailable behavior.
- A provider task remains pending until the polling or overall-run timeout expires.
- A task succeeds with no output URLs, a malformed output, or an output download failure.
- An error or provider payload contains strings that resemble configured secrets.
- Two runs start during the same second and must still receive distinct run identifiers.
- A review CSV has reordered rows, unknown output IDs, missing reviewer data, or invalid approval
  timestamps at promotion time.
- An approved keyframe filename already exists; the existing keyframe must not be silently
  overwritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The workflow MUST treat files in the approved-anchor package as immutable and MUST
  store all derived and generated files elsewhere.
- **FR-002**: The workflow MUST map exactly one configured face anchor, full-body anchor, and scene
  anchor from existing source filenames without renaming source files.
- **FR-003**: Extra character-sheet, profile, back-view, wardrobe, or expression images MUST remain
  QA-only unless explicitly selected in configuration as generation references.
- **FR-004**: Anchor validation MUST verify required roles, unique roles, unique reference tags,
  approved paths, readability, supported image type, valid dimensions, and hashability.
- **FR-005**: Every selected anchor and generated output MUST have a recorded SHA-256 digest.
- **FR-006**: Operators MUST be able to select a named generation preset and override count,
  provider, model, aspect ratio, resolution, seed where supported, concurrency, retry limit, and
  timeout within configured safety and capability limits.
- **FR-007**: The workflow MUST provide `baseline_identity`, `home_decor`, and
  `product_page_clean` presets with default counts of 10, 5, and 5 respectively.
- **FR-008**: The baseline preset MUST use the face and full-body anchors and require complete body
  visibility, approved wardrobe, jewelry and hairstyle, a neutral warm studio background, and no
  extra people, text, logo, props, or wardrobe redesign.
- **FR-009**: The home-decor preset MUST use face, full-body, and scene anchors and require approved
  identity and appearance, a premium warm-neutral contemporary interior, realistic commercial
  photography, a slightly off-center subject, and no extra people, text, or logo.
- **FR-010**: The product-page-clean preset MUST preserve approved identity and appearance, provide
  a clean warm-neutral separated background with commercial lighting, and prohibit extra people,
  text, logos, and objects in hands.
- **FR-011**: Long-form prompts MUST be stored in separately versioned files and run records MUST
  include prompt filename, version, SHA-256, resolved text, and referenced anchor tags.
- **FR-012**: The generation workflow MUST use a provider-neutral request, task, result, and
  download contract so another provider can be added without changing batch or reporting behavior.
- **FR-013**: Provider-specific validation and translation MUST reject unsupported models,
  reference counts/syntax, ratios, resolutions, and seed options before submission.
- **FR-014**: Provider behavior for generation, reference support, reference limits/syntax,
  supported dimensions, task polling, output retrieval, and model/API versions MUST be verified
  against current official provider documentation before live use.
- **FR-015**: Preview mode MUST validate all configuration and inputs, resolve prompts and
  references, construct and validate provider-neutral requests, write previews and run metadata,
  and make zero generation or paid calls.
- **FR-016**: Paid calls MUST be disabled by default and require explicit live mode, explicit
  environment permission, and configured provider credentials simultaneously.
- **FR-017**: Live generation MUST enforce maximum outputs, bounded concurrency, bounded retries,
  polling timeout, and overall-run timeout; the automated live smoke test MUST request no more
  than one image.
- **FR-018**: The workflow MUST never expose credentials or authorization headers in committed
  files, logs, task events, run metadata, serialized errors, or test fixtures.
- **FR-019**: Every run MUST have a unique, human-readable identifier and store request preview,
  resolved configuration, resolved prompt, anchor hashes, task events, normalized result, review
  sheet, and summary together.
- **FR-020**: Task events MUST capture ordered submission, polling, retry, completion, timeout, and
  failure transitions without secrets.
- **FR-021**: Successful provider outputs MUST be downloaded with bounded timeouts, stored outside
  approved anchors, hashed, and represented by normalized result records.
- **FR-022**: The workflow MUST create exactly one QA review row per output with all required
  provenance and subjective review fields, including video-keyframe and MTL readiness.
- **FR-023**: Subjective review, readiness, reviewer, timestamp, and notes fields MUST be blank by
  default; the system MUST NOT automatically approve identity, MTL readiness, or keyframe status.
- **FR-024**: A reviewed static image MAY be promoted only when its review row explicitly records
  video-keyframe readiness plus reviewer and approval date.
- **FR-025**: Promotion MUST preserve the original image and record source run ID, source image,
  image SHA-256, approved anchor version, prompt version, provider, model, reviewer, and approval
  date beside the approved keyframe.
- **FR-026**: The workflow MUST provide operator commands for validation, preview/live generation,
  run reporting, and approved-keyframe promotion.
- **FR-027**: Automated verification MUST cover configuration and manifest loading, anchor
  existence/hash/deduplication, prompt loading/hashing, run IDs, preview isolation, provider
  translation, timeout/retry bounds, secret redaction, result serialization, review generation,
  downloads, normalized errors, and keyframe promotion without paid calls.
- **FR-028**: Project documentation MUST cover setup, supported runtime, environment controls,
  anchor placement, all presets, preview and one-image live smoke-test workflows, human QA,
  promotion, troubleshooting, provider extensibility, and cost controls.
- **FR-029**: Each implementation checkpoint MUST record files changed, tests run, results,
  blockers, remaining work, and paid-call count.
- **FR-030**: The system MUST remain limited to static-image candidates and static keyframe
  promotion and MUST NOT implement talking video, voice cloning, lip sync, final video editing,
  ComfyUI, Coze, Shopify, or automatic MTL/face-recognition approval.

### Key Entities

- **Approved Anchor Set**: Versioned, immutable collection of logical face, full-body, and scene
  sources plus optional QA-only references.
- **Generation Preset**: Named constraints, selected logical references, versioned prompt, default
  candidate count, and default image dimensions for a production use case.
- **Generation Request**: Provider-neutral resolved intent for one candidate, including run/output
  identity, prompt provenance, references, model/dimensions, and optional seed semantics.
- **Provider Task**: External or simulated asynchronous work item with bounded lifecycle events.
- **Generation Result**: Normalized success or failure containing provider provenance, requested
  and actual seed behavior, output files/hashes, timing, and sanitized error details.
- **Run Record**: Immutable reproducibility bundle joining resolved inputs, events, outputs, review
  rows, and summary under one run identifier.
- **Review Row**: One candidate's provenance and blank-or-human-entered QA decisions.
- **Approved Keyframe**: Preserved copy of a human-approved candidate plus promotion provenance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can preview each of the three presets from valid local inputs and receive
  a complete run record within 60 seconds, with zero generation calls and zero paid calls.
- **SC-002**: The baseline, home-decor, and product-page presets request exactly 10, 5, and 5
  candidates by default and resolve only their documented approved references.
- **SC-003**: One hundred percent of previewed and simulated runs contain all eight required run
  artifacts and hashes for every selected anchor and downloaded output.
- **SC-004**: One hundred percent of newly created review sheets contain exactly one row per output
  and leave every subjective human-review field blank.
- **SC-005**: All configured retry, concurrency, polling, and total-run bounds terminate at their
  declared limits in automated verification; no test performs a network or paid generation call.
- **SC-006**: All approved anchor hashes match their pre-implementation baseline after delivery.
- **SC-007**: A provider adapter can be replaced by a simulated alternative while validation,
  batching, run storage, reporting, and review behavior continue unchanged.
- **SC-008**: Every promotion attempt either produces a traceable approved keyframe while
  preserving the source image, or rejects the attempt before copying when review/integrity data is
  insufficient.
- **SC-009**: A security audit finds zero credentials or authorization headers in versioned files,
  logs, fixtures, request previews, task events, results, or summaries.
- **SC-010**: When valid credentials and explicit paid-call permission are supplied, exactly one
  live smoke-test candidate completes successfully; otherwise all offline outcomes remain complete
  and the missing live smoke test is reported as an external blocker.

## Assumptions

- The filenames `lala-face-front.png`, `lala-red-gown-full-body.png`, and
  `lala-home-decor-scene.png` correctly map to face, full-body, and scene authority respectively;
  the other two existing scene-folder images are QA-only.
- Human reviewers edit the generated review CSV using a tool that preserves its header names and
  output identifiers.
- Internet connectivity is required only for official provider documentation verification and
  explicitly authorized live calls; preview and automated verification remain offline-capable.
- Provider credentials and explicit paid-call permission may be unavailable during implementation;
  this blocks only the one-image live smoke test.
- Static images promoted here are consumed later by a separate video workflow that is outside this
  feature's implementation and acceptance scope.

## Dependencies

- Access to the existing approved-anchor package in its current filenames and directory layout.
- Current official documentation for the selected primary image-generation provider.
- Valid provider credentials and explicit paid-call authorization only for the optional-at-build,
  required-when-authorized one-image live smoke test.
