# Feature Specification: P1-1 V7 Human QA Closure

**Feature Branch**: `main`

**Created**: 2026-08-20

**Status**: Approved for implementation

**Input**: The owner explicitly decided V7-A PASS, V7-B FAIL, V7-C FAIL/reserve, selected V7-A-stability-first as the P1-1 winner, and authorized an offline-only closure that unlocks—but does not execute—P1-2 Live.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Archive the Human Decision (Priority: P1)

As the production owner, I can preserve my explicit V7 A/B/C decision in the existing reviewed-copy schema while the append-only run review remains blank and the winning media provenance remains verifiable.

**Why this priority**: The owner decision is the sole authority for P1-1 acceptance and every later state depends on an honest immutable reviewed copy.

**Independent Test**: Validate the reviewed copy against the original blank run review, confirm exactly three provenance-matching rows, and confirm only V7-A is fully passing and MTL-ready.

**Acceptance Scenarios**:

1. **Given** the successful fixed V7 parent run and the explicit owner decision, **When** closure records the decision, **Then** V7-A is PASS and MTL-ready, V7-B is FAIL, and V7-C is FAIL with reserve noted.
2. **Given** the reviewed copy, **When** provenance is checked, **Then** the run ID, candidate IDs, task IDs, and media hashes match the append-only live evidence and the original run review remains byte-unchanged.
3. **Given** the human decision, **When** authority is reported, **Then** it is identified as explicit human review and never as automatic QA or diagnostic output.

---

### User Story 2 - Unlock P1-2 Without Executing It (Priority: P1)

As the production operator, I can use the selected passing V7 parent candidate as the P1-1 prerequisite for later P1-2 Live work while all other live permissions remain independently required.

**Why this priority**: A recorded state label is insufficient unless the production gate can validate the same selected reviewed evidence before any provider construction.

**Independent Test**: Under fakes or offline validation, prove the selected passing V7-A review satisfies the P1-1 prerequisite, failing or ambiguous V7 reviews do not, and no provider is constructed or called.

**Acceptance Scenarios**:

1. **Given** V7-A is the unique passing and MTL-ready selected row, **When** the P1-2 prerequisite is evaluated, **Then** the canonical gate reports P1-2 Live ready without starting P1-2 execution.
2. **Given** V7-B, V7-C, multiple passing rows, a mismatched candidate, changed media, or changed provenance, **When** the gate is evaluated, **Then** readiness is rejected before provider construction.
3. **Given** P1-2 is ready, **When** no separate live command, permission, credential, and budget authorization is supplied, **Then** provider calls remain zero.

---

### User Story 3 - Preserve Closure Evidence (Priority: P2)

As an auditor, I can inspect a new final closure package without losing or overwriting the original pre-human-review evidence package.

**Why this priority**: The state transition must be reproducible and distinguish live-generation evidence from later human authorization.

**Independent Test**: Verify the original package hash is unchanged, the new package passes archive and checksum verification, and its manifest identifies V7-A, the reviewed copy, all original task/media facts, the diagnostics gap, and zero new provider calls.

**Acceptance Scenarios**:

1. **Given** the original evidence ZIP, **When** closure completes, **Then** its filename, bytes, and SHA-256 remain unchanged and a separately named closure package exists.
2. **Given** the closure package, **When** its manifest is inspected, **Then** P1-1 Human PASS, V7-A selection, MTL readiness, P1-2 Live readiness, and the retained diagnostics gap are explicit.
3. **Given** secret and integrity scans, **When** the package is verified, **Then** all checksums match and no credential, authorization header, bearer value, or signed query secret is present.

### Edge Cases

- The review schema has no literal Camera Lock or Framing columns; closure must use the repository's established motion mappings and make those mappings explicit in human notes.
- The schema has no reserve state; V7-C remains formally FAIL and the reserve designation is preserved only in notes.
- A passing row without MTL readiness, reviewer identity, timezone-aware review time, or all required motion QA decisions must not unlock P1-2.
- The three-candidate V7 parent must not be sent to the single-result post-live diagnostics entrypoint.
- Existing B/C media, task IDs, and evidence must remain present after selecting A.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Closure MUST record exactly the owner-authorized outcomes: V7-A PASS, V7-B FAIL, and V7-C FAIL/reserve.
- **FR-002**: Closure MUST identify V7-A-stability-first as the unique P1-1 winner and all downstream P1-1 prerequisite references MUST resolve to that candidate.
- **FR-003**: The reviewed copy MUST retain the existing exact review schema and original four provenance fields for every row.
- **FR-004**: V7-A MUST contain explicit human PASS decisions for Camera Lock, Framing, Identity, Eyes, Mouth, Motion, technical validity, overall readiness, reviewer, and review time using established schema equivalents.
- **FR-005**: V7-B and V7-C MUST remain explicit human failures; V7-C's reserve status MAY appear only in notes.
- **FR-006**: The append-only run review and original pre-human-review package MUST remain byte-unchanged.
- **FR-007**: The production P1-2 prerequisite gate MUST accept a successful V7 parent run only when exactly one reviewed candidate is fully passing, MTL-ready, provenance-consistent, media-present, and hash-valid.
- **FR-008**: The same gate MUST reject missing, failing, duplicated, ambiguous, mismatched, mutated, or incomplete V7 review evidence before any provider construction.
- **FR-009**: Unlocking P1-2 MUST NOT execute P1-2 and MUST NOT weaken the independent live command, environment permission, credential, input, count, or budget guards.
- **FR-010**: Closure MUST preserve `POST_LIVE_DIAGNOSTIC_ENTRYPOINT_NOT_AVAILABLE` and MUST NOT change the subject-lock algorithm, thresholds, V6 baseline, or fabricate V7 diagnostics.
- **FR-011**: A separately named closure package MUST preserve the selected candidate, reviewed copy, all three original task IDs and media hashes, canonical states, diagnostics gap, and provider accounting.
- **FR-012**: Package archive integrity, internal checksums, source/media checksums, secret scans, full offline tests, bytecode compilation, and whitespace checks MUST pass before closure is complete.
- **FR-013**: This closure MUST make zero new Runway, HeyGen, voice, talking, assembly, P1-2, or other paid provider calls.
- **FR-014**: Approved-source hashes MUST match the recorded baselines before and after closure.

### Key Entities

- **V7 Human Review**: The external reviewed copy containing three provenance-bound candidate rows and explicit owner decisions.
- **P1-1 Selection**: The unique V7-A winner, its task ID, media path, media hash, and human readiness evidence.
- **P1-2 Prerequisite Evidence**: Read-only evidence that the selected P1-1 candidate passed and is MTL-ready; it does not itself authorize a provider call.
- **Closure Package**: A new immutable audit bundle that joins live evidence with the later human review and canonical state transition.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Exactly one of three V7 candidates is fully passing and MTL-ready, and it is V7-A-stability-first.
- **SC-002**: One hundred percent of the three task IDs and media SHA-256 values match the fixed live run evidence after closure.
- **SC-003**: The original evidence ZIP retains SHA-256 `268842f10553856b821496f8d76662bee2419069b443aeb55f48c7781fcb25ef`.
- **SC-004**: Offline gate tests accept the valid V7-A reviewed selection and reject every incomplete, failing, ambiguous, or mutated variant before provider construction.
- **SC-005**: The closure package passes archive integrity, all internal checksum verification, and secret scan with zero findings.
- **SC-006**: The complete offline test suite, bytecode compilation, and whitespace validation pass with zero real provider calls.
- **SC-007**: All approved-source hashes are identical before and after closure.
- **SC-008**: Final state evidence reports P1-1 live/media/human PASS, selected V7-A, MTL ready, P1-2 offline/live ready, P1-2 live not executed, and the diagnostics entrypoint gap retained.

## Assumptions

- The owner is the human reviewer and the task request itself is the authorization source.
- The existing motion QA mapping treats `background` as Camera Lock/background stability and `body_proportions` as Framing/proportions stability; notes will state this mapping.
- V7-A's explicit overall PASS authorizes all named human closure dimensions; the workflow will not infer decisions from image analysis or diagnostics.
- Runtime review/package evidence follows the existing ignore policy and is not forced into version control.
- No branch, commit, push, pull request, or P1-2 live execution is required by this task.
