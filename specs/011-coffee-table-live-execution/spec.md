# Feature Specification: Coffee Table Live Execution

**Feature Branch**: `011-coffee-table-live-execution`

**Created**: 2026-08-21

**Status**: Owner authorized for implementation and one bounded Live execution

**Input**: Execute only the Owner-approved Coffee Table Manifest V2 SHA `ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea`, submit at most four sequential Runway tasks under 100 credits / USD 1.00, apply its deterministic runtime lineage and local assembly, and stop at Owner review.

## User Scenarios & Testing

### User Story 1 - Execute the Approved Contract (Priority: P1)

As the Owner, I can execute exactly the four requests I approved, in order, with durable task evidence and no parameter drift or unapproved paid work.

**Why this priority**: The authorization applies to one immutable contract identity and no other production plan.

**Independent Test**: With fake providers, execute an exact manifest fixture and verify four sequential task IDs, four raw MP4s, fixed request inputs/prompts, maximum budget, and zero retries/replacements.

**Acceptance Scenarios**:

1. **Given** the exact approved manifest and explicit authorization flags, **When** Live starts, **Then** Tasks 01–04 are submitted serially with their frozen provider parameters and no fifth task.
2. **Given** Task 02 succeeds, **When** Task 04 is prepared, **Then** the exact final decoded Task 02 frame is extracted locally, hashed, recorded, reverified, and used without aesthetic selection.
3. **Given** any failed, cancelled, timed-out, ambiguous, drifted, or over-budget condition, **When** it occurs, **Then** execution stops and submits no later task or replacement.

---

### User Story 2 - Produce Deterministic Review Media (Priority: P1)

As the Owner, I receive four traceable raw outputs, a deterministic twenty-second 16:9 master, and guarded local delivery variants without native regeneration.

**Why this priority**: Provider success is not delivery; review requires exact local assembly and provenance.

**Independent Test**: Assemble synthetic five-second sources using the manifest timeline, validate duration/dimensions/hashes, and prove all derived outputs use zero provider calls.

**Acceptance Scenarios**:

1. **Given** four successful raw outputs, **When** assembly runs, **Then** it uses Task 01 `[0,5)`, Task 02 `[0,5)`, Task 03 `[0,3)`, Task 04 `[0,5)`, and a two-second Task 04 last-frame hold to create one twenty-second master.
2. **Given** a valid master, **When** delivery variants are prepared, **Then** 1:1 and 9:16 are created locally only when guarded processing succeeds; failure never triggers provider regeneration.

---

### User Story 3 - Stop for Human Review (Priority: P1)

As the Owner, I receive blank review evidence and an exact review-ready state without any inferred creative approval.

**Why this priority**: Task 02 glass placement and all final visual quality remain human decisions.

**Independent Test**: Inspect the completed run and verify blank Human QA fields, complete hashes/cost evidence, and terminal state `READY_FOR_OWNER_REVIEW` only.

**Acceptance Scenarios**:

1. **Given** successful generation and local delivery, **When** the run closes, **Then** all review fields are blank and the only terminal state is `READY_FOR_OWNER_REVIEW`.
2. **Given** any incomplete task or local validation failure, **When** the run closes, **Then** it records a precise stopped state and never claims PASS, APPROVED, MTL_READY, or FINAL.

### Edge Cases

- The manifest path is a symlink, escapes the project, changes bytes, or has the right SHA argument but different content.
- A source or prompt changes between preflight and submission.
- A submission raises before returning a durable task ID, or a task ID exists but polling/downloading fails.
- Task 02 output has no decodable frame, its recorded hash drifts, or extracted PNG validation fails.
- Actual reported cost is absent or differs from projection.
- A raw output is shorter than its authorized usable interval or has incompatible dimensions.
- A local 1:1 or 9:16 operation fails its media checks.

## Requirements

### Functional Requirements

- **FR-001**: Live MUST accept only the exact approved manifest path and SHA supplied by the Owner.
- **FR-002**: Live MUST require explicit `--live`, exact Owner authorization confirmation, exact `VIDEO_ALLOW_LIVE_CALLS=true`, and a non-empty local Runway credential.
- **FR-003**: Preflight MUST revalidate the manifest, parent plan, V1 rejection, current Candidate 16/Goal 2/V7/K1/K2/K3 authority, static sources, prompt bytes, hard limits, blank review, and zero-call preparation evidence before provider construction or run allocation.
- **FR-004**: Execution MUST use Runway `gen4_turbo`, exactly four ordered five-second requests, 1280:720 ratio, concurrency one, at most 100 credits / projected USD 1.00, and zero submission retries or replacement tasks.
- **FR-005**: Each durable provider task ID MUST be persisted immediately and form an idempotency boundary; a task with an ID MUST never be resubmitted automatically.
- **FR-006**: A submission exception without a durable task ID MUST be recorded as ambiguous and MUST stop all later submissions.
- **FR-007**: Any task failure, cancellation, timeout, validation failure, source/prompt drift, budget failure, or lineage failure MUST stop execution without a fifth or replacement task.
- **FR-008**: Task 04 MUST consume a locally extracted Task 02 `LAST_VALID_FRAME` selected exactly as decoded frame count minus one, with upstream MP4 and PNG hashes recorded and reverified before submission.
- **FR-009**: Runtime lineage extraction MUST make zero provider calls and MUST permit no manual or aesthetic frame selection.
- **FR-010**: Successful execution MUST download and validate exactly four raw MP4 files and record task IDs, artifact hashes, media properties, cost facts, and redacted provenance.
- **FR-011**: Local assembly MUST follow the manifest's exact 0–20 second mapping and create a 16:9 master from eighteen seconds of authorized motion plus a two-second Task 04 last-frame hold.
- **FR-012**: 1:1 and 9:16 outputs MUST be local guarded derivatives only; native-ratio provider generation is prohibited even when a local variant fails.
- **FR-013**: HeyGen, TTS, dialogue, lip sync, new keyframes, new V7, changed prompts, changed beat mapping, changed timeline, higher caps, automatic approval, and any fifth task MUST remain prohibited.
- **FR-014**: Run evidence MUST be append-only, secret-redacted, collision-safe, and sufficient to distinguish no-ID submission ambiguity from a durable task that later fails.
- **FR-015**: Human review fields MUST start blank; successful delivery MUST stop exactly at `READY_FOR_OWNER_REVIEW` and MUST NOT emit PASS, APPROVED, MTL_READY, or FINAL.
- **FR-016**: Automated tests MUST use fakes, block network activity, and make zero paid calls.
- **FR-017**: Approved-source hashes MUST be identical before and after implementation and Live execution.
- **FR-018**: If Live cannot complete, the workflow MUST preserve all completed/task-ID evidence and report the exact stop reason without automatically resuming or replacing work.

### Key Entities

- **Live Authorization**: Exact manifest path/SHA, Owner decision, hard caps, and prohibited actions.
- **Campaign Live Run**: Append-only execution identity, state, ordered task records, costs, and stop reason.
- **Task Runtime Record**: Request identity, durable provider task ID, status, raw artifact, cost, and submission boundary.
- **Runtime Lineage**: Task 02 MP4 hash, decoded frame count, fixed final-frame index, extracted PNG hash, and Task 04 input binding.
- **Delivery Artifact**: Raw MP4, 16:9 master, or guarded local derivative with content hash and media validation.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A valid authorized run submits no more than four tasks and never exceeds 20 generated seconds, 100 planned credits, or projected USD 1.00.
- **SC-002**: Every provider task ID is durably recorded before the next task can begin.
- **SC-003**: Task 04 input hash exactly matches the deterministic PNG extracted from Task 02's last decoded frame.
- **SC-004**: A successful run produces four validated raw MP4s and one validated twenty-second 16:9 master; local variants either validate or are explicitly marked unavailable with zero regeneration.
- **SC-005**: All failure fixtures stop before later submissions and produce zero automatic paid retries, replacements, or fifth tasks.
- **SC-006**: Full offline tests pass before Live and all approved-source SHA values remain unchanged afterward.
- **SC-007**: The completed successful run reports `READY_FOR_OWNER_REVIEW` with all Human QA fields blank.

## Assumptions

- The existing project `.env` contains a valid Runway credential; the authorized command may set the exact live permission variable for its process without persisting it.
- Existing Runway provider translation and download validation remain authoritative and official-API-backed.
- Provider-reported actual credit cost may be unavailable; unknown cost is recorded honestly while the fixed request projection enforces the cap.
- Guarded delivery may fail closed for either local ratio without invalidating successfully generated raw/master evidence.
