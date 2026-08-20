# Feature Specification: P1-1 Motion V7 Targeted Fix

**Feature Branch**: `fix/p1-1-motion-v7`

**Created**: 2026-08-20

**Status**: Implemented and offline-verified

**Input**: Prepare a controlled, offline-only V7 motion experiment following V6 human-QA failure and Subject Lock diagnostics. Supply three deliberately graded candidates, compare future evidence to V6 without inventing V7 values, and preserve all existing live gates and human-review authority.

## User Scenarios & Testing

### User Story 1 - Review a Controlled V7 Motion Ladder (Priority: P1)

As the P1-1 owner, I can inspect three distinct, low-motion V7 candidates with exact prompt provenance and bounded estimates so I can choose an explicitly approved live batch that first tests stability rather than expressiveness.

**Why this priority**: V6 failed framing, eyes, and motion while Subject Lock found material position/scale change. The next experiment must isolate motion magnitude as the independent variable.

**Independent Test**: Resolve the V7 planning command locally and confirm it produces exactly the three canonical candidates in order, each with its own versioned prompt, UTF-16 measurement, Runway estimate, and no live authorization.

**Acceptance Scenarios**:

1. **Given** the approved V6 baseline and project configuration, **When** V7 planning is requested, **Then** it resolves `v7-a-stability-first`, `v7-b-natural-micro-motion`, and `v7-c-controlled-upper-bound` in that order.
2. **Given** any V7 candidate, **When** its prompt is resolved, **Then** it specifies a locked camera, preserved framing and identity, stable camera-facing eyes, stable environment, and only the candidate's bounded motion intent.
3. **Given** the three candidates, **When** their planning record is written, **Then** each has a unique prompt path, measured UTF-16 units below 1,000, provider, estimator-derived credits, `live_allowed=false`, and no task ID.

---

### User Story 2 - Compare Future V7 Evidence to V6 Without Replacing Human QA (Priority: P1)

As a reviewer, I can see a consistent V6-versus-V7 comparison scaffold alongside blank human QA so diagnostic movement measurements can inform review without making an automatic decision.

**Why this priority**: Subject Lock diagnostics are supporting evidence only. V7 has no generated video yet and must never receive fabricated measurement or QA values.

**Independent Test**: Inspect a V7 dry-run record and confirm every V6 metric is fixed, each V7 and delta value is pending, and all seven human-review fields remain blank.

**Acceptance Scenarios**:

1. **Given** no real V7 media, **When** V7 comparison evidence is written, **Then** V6 X/Y drift, width/height change, maximum scale change, tracking success, and diagnostic status are present while V7 and delta fields are null/pending.
2. **Given** a V7 dry-run, **When** its review CSV is read, **Then** Camera Lock, Framing, Identity, Eyes, Mouth, Motion, and MTL Ready are blank for all three candidates.
3. **Given** a Subject Lock diagnostic state, **When** V7 evidence is displayed, **Then** it is labelled diagnostic-only and cannot alter human QA fields.

---

### User Story 3 - Maintain the Paid-Call Boundary (Priority: P1)

As a production operator, I can generate V7 offline review preparation while P1-2 Live remains blocked until a later explicit human P1-1 pass.

**Why this priority**: V7 readiness is not authorization to pay for a provider call or unlock P1-2.

**Independent Test**: Run the V7 dry-run with an environment containing no provider permissions and confirm one three-candidate record, zero submissions/task IDs/provider requests, and explicit continued P1-2 live blocking.

**Acceptance Scenarios**:

1. **Given** the current failed V6 review, **When** V7 dry-run is requested, **Then** it writes a unique local run with three planned calls, zero submissions, zero provider construction, zero task IDs, and three blank QA rows.
2. **Given** a V7 candidate configuration, **When** it is inspected, **Then** no candidate is marked live-allowed and the existing P1-2 human-pass gate is unchanged.
3. **Given** prompt text exceeding the verified provider limit, **When** V7 planning is attempted, **Then** it fails before any provider request or run creation.

### Edge Cases

- A V7 candidate file is missing, outside `prompts/`, unversioned, duplicated, or exceeds the UTF-16 limit.
- Candidate IDs are duplicated, reordered, or a candidate is accidentally marked live-allowed.
- V6 comparison input is incomplete or altered.
- A dry-run has no generated video or Subject Lock artifacts; it must retain pending V7 metrics rather than create placeholders that look measured.
- Runtime outputs or environment values contain credential-like text; no secret can enter the run evidence.

## Requirements

### Functional Requirements

- **FR-001**: The workflow MUST provide exactly three V7 candidates in the fixed A/B/C order: `v7-a-stability-first`, `v7-b-natural-micro-motion`, and `v7-c-controlled-upper-bound`.
- **FR-002**: Each V7 candidate MUST reference a new immutable versioned prompt file under `prompts/`; historical V2/V3 prompts and V6 evidence MUST remain unchanged.
- **FR-003**: Every V7 prompt MUST preserve camera lock, framing, identity, eye direction, and background while expressing only its stated motion rung: stability-first, natural micro-motion, or controlled upper bound.
- **FR-004**: Prompt validation MUST calculate UTF-16 code units and reject any candidate at or above the documented Runway limit before provider construction or HTTP activity.
- **FR-005**: Candidate metadata MUST preserve candidate ID, prompt path, experiment level, motion intent, provider, estimator-derived credits, and `live_allowed=false`.
- **FR-006**: The V7 dry-run MUST produce one append-only derived run with exactly three planned motion calls, zero submissions, no task IDs, no provider construction, zero paid calls, and three blank human QA rows.
- **FR-007**: The V7 comparison scaffold MUST preserve the authoritative V6 Subject Lock values and represent all V7/delta measurements as pending until actual V7 diagnostic evidence exists.
- **FR-008**: Subject Lock evidence MUST remain explicitly diagnostic-only and MUST NOT create, fill, or change human QA or MTL-readiness fields.
- **FR-009**: Existing review-package checksum, ZIP membership, and secret-scan behavior MUST remain usable when Subject Lock artifacts exist; V7 dry-run MUST not fabricate unavailable video diagnostics or package artifacts.
- **FR-010**: P1-2 offline and dry-run availability MUST remain unchanged, and P1-2 Live MUST remain blocked pending an explicit later P1-1 human pass; V7 implementation or diagnostic status MUST not unlock it.
- **FR-011**: Automated coverage MUST prove candidate order/metadata, prompt provenance and UTF-16 limits, V6 pending comparison, blank QA, no live permission, existing Subject Lock/package behavior, and P1-2 gate regression.
- **FR-012**: All work and verification for this feature MUST be offline and make zero Runway, HeyGen, voice, talking, or other provider requests.

### Key Entities

- **V7 Candidate**: A fixed-rung motion experiment record containing exact prompt provenance, motion intent, provider, estimated credit cost, and non-authorizing live flag.
- **V7 Dry-Run Record**: A normal append-only video run that records three planned candidate requests, blank review rows, cost evidence, and a V6 comparison scaffold.
- **Subject Lock Comparison**: The authoritative V6 diagnostics plus pending V7/delta fields, always labelled as diagnostic evidence rather than human QA.

## Success Criteria

### Measurable Outcomes

- **SC-001**: V7 planning resolves exactly three unique candidates in the prescribed A/B/C order, each under 1,000 UTF-16 code units.
- **SC-002**: The single V7 dry-run records three planned Runway calls and 75 estimator-derived credits under the current configuration, with zero submissions, task IDs, provider requests, or paid calls.
- **SC-003**: The V7 dry-run creates exactly three review rows, and all subjective human-review and MTL-readiness fields are blank.
- **SC-004**: Every V7 comparison record preserves all seven V6 diagnostic facts and reports all V7/delta facts as pending before real V7 media exists.
- **SC-005**: One hundred percent of V7 candidate metadata records are non-authorizing and existing P1-2 Live rejection tests remain green.
- **SC-006**: The full offline test suite, compile check, package integrity tests, secret scan, and approved-anchor hash check pass with zero provider calls.

## Assumptions

- V7 is a preparation experiment only; no live submission, assembly, promotion, or automatic human decision is in scope.
- Current Runway `gen4_turbo`, five-second, `1280:720`, five-credits-per-second evidence remains the estimator input.
- Existing VideoRunStorage and the Subject Lock review package are reused; unavailable future-media artifacts are not fabricated in a dry-run.
- The approved V6 review and its corrected blank/reviewed SHA labels remain immutable evidence.
