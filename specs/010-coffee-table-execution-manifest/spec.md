# Feature Specification: Coffee Table Execution Manifest

**Feature Branch**: `010-coffee-table-execution-manifest`

**Created**: 2026-08-21

**Status**: V2 approved for offline implementation after V1 Owner rejection

**Input**: Freeze an unambiguous, reviewable four-request Coffee Table execution contract bound to the already-approved Candidate 16 dry-run plan, add a minimal offline CLI and tests, make zero provider submissions, and stop for Owner manifest review.

## User Scenarios & Testing

### User Story 1 - Freeze the Four Requests (Priority: P1)

As the Owner, I can inspect one immutable execution manifest that proves exactly which four motion requests would later be submitted without changing the frozen twenty-second story.

**Why this priority**: A paid run cannot be authorized safely while keyframes, prompts, request parameters, and six-to-four beat mapping remain implicit.

**Independent Test**: Build the manifest from the frozen parent plan and verify its parent identity, four exact tasks, prompt and keyframe hashes, time mapping, hard limits, and zero-call state.

**Acceptance Scenarios**:

1. **Given** the exact approved parent plan, **When** the operator prepares the execution manifest, **Then** the result records the parent path and SHA and exactly four five-second 16:9 motion tasks.
2. **Given** six frozen storyboard beats, **When** four tasks and local assembly are mapped, **Then** the final timeline remains exactly 0:00–0:20 in the original order and meaning.
3. **Given** the published Candidate 16 keyframes, frozen PDP product image, and four versioned prompts, **When** the manifest is created, **Then** every static referenced file exists and its recorded SHA matches its bytes.
4. **Given** Task 02 later succeeds, **When** Task 04 becomes eligible, **Then** its source is the deterministically extracted last valid frame of Task 02 with runtime artifact and frame hashes recorded before submission.

---

### User Story 2 - Refuse Drift and Paid Work (Priority: P1)

As the production operator, I receive a precise refusal before any output or provider construction when the parent plan, approved sources, prompts, limits, or explicit preparation authorization do not match.

**Why this priority**: The preparation step must not create an alternate production plan or accidentally cross the paid execution gate.

**Independent Test**: Mutate each input or authorization precondition in isolated fixtures and verify failure creates no manifest and makes zero network/provider calls.

**Acceptance Scenarios**:

1. **Given** a wrong parent SHA or changed parent file, **When** preparation is attempted, **Then** it fails before creating an output directory.
2. **Given** a changed prompt or keyframe, **When** preparation is attempted, **Then** it fails on the exact hash gate.
3. **Given** any requested value above four tasks, five seconds, one hundred credits, one dollar, concurrency one, or zero retries/replacements, **When** preparation is attempted, **Then** it fails closed.
4. **Given** valid inputs, **When** preparation succeeds, **Then** provider submissions, provider task IDs, HTTP requests, and paid calls remain zero.

---

### User Story 3 - Hand Off an Owner-Reviewable Identity (Priority: P2)

As the Owner, I receive the manifest path, SHA-256, concise four-task summary, assembly map, test evidence, and a terminal state that cannot be mistaken for Live authorization.

**Why this priority**: The execution manifest itself is the object that must be reviewed and approved before any paid call.

**Independent Test**: Run the real offline preparation command and verify its output reports the manifest identity and stops at the exact Owner-review state.

**Acceptance Scenarios**:

1. **Given** a successful preparation, **When** the command returns, **Then** it reports `READY_FOR_OWNER_COFFEE_TABLE_EXECUTION_MANIFEST_REVIEW` and the manifest SHA.
2. **Given** the prepared manifest, **When** inspected, **Then** native-ratio regeneration, HeyGen, TTS, dialogue, lip sync, paid retries, and replacement tasks are explicitly unauthorized.

### Edge Cases

- The parent path points outside the project, is not the approved run, is a symlink, or has the right filename but wrong bytes.
- The execution output identity already exists.
- A prompt or the frozen PDP product source is missing, exceeds its supported limits, or changes after its first hash check.
- K1 or K3 changes during preparation; K2 remains part of the approved set but is intentionally unused by this motion-only contract.
- The storyboard order, total duration, product, character, V7 winner, provider, model, cost, or safety semantics differ from the frozen parent.
- Local assembly would require native-ratio generation or an unapproved extra provider task.
- Task 02 lacks a successful downloaded MP4, its hash changes, frame counting fails, or the last valid frame cannot be deterministically extracted and hashed.

## Requirements

### Functional Requirements

- **FR-001**: The workflow MUST accept only the frozen parent plan at `outputs/campaign-previews/COFFEE-TABLE-DRY-20260821-071433-640204/plan.json` with SHA-256 `ed30e4984dd488cde79188e7e327bc4472ab0c331125a0c600d739a0d388ac5f`.
- **FR-002**: The manifest MUST record exactly four ordered Runway `gen4_turbo` tasks, each five seconds at 16:9, with exact semantic purpose, storyboard beat coverage, prompt path/SHA/text, request parameters, expected usable interval, and either an exact static source path/SHA or an exact runtime source-lineage rule.
- **FR-003**: The task mapping and assembly MUST preserve the frozen beat order and exact 0:00–0:20 timeline without adding or replanning story content.
- **FR-004**: Long motion prompts MUST live in four versioned files outside approved-source directories and MUST be hash-bound by the manifest.
- **FR-005**: The manifest MUST hard-code a maximum of four tasks, one hundred Runway credits, one dollar projected cost, concurrency one, and zero automatic paid retries or replacement tasks.
- **FR-006**: The manifest MUST explicitly forbid HeyGen, TTS, dialogue, lip sync, native-ratio regeneration, a fifth task, automatic approval, and any paid action during preparation.
- **FR-007**: The preparation CLI MUST require the exact parent plan path, exact parent SHA, and an explicit Owner-authorized preparation flag.
- **FR-008**: Preparation MUST validate parent semantics, Goal 2 readiness, Candidate 16 active identity, published K1/K2/K3 set, V7-B winner, keyframe hashes, frozen PDP path/SHA, prompt hashes, prompt length, and every hard limit before creating output.
- **FR-009**: Preparation MUST be collision-safe, fail closed, and leave no partial manifest directory when validation or writing fails.
- **FR-010**: Preparation MUST construct no provider, perform no network request, submit no task, and report all provider/paid counters as zero.
- **FR-011**: The manifest MUST define deterministic local master assembly, including Task 3 trimming and Task 4 terminal-frame hold, plus guarded local 1:1 and 9:16 delivery; actual media assembly remains outside this preparation feature.
- **FR-012**: Human review and approval fields MUST remain blank and terminal status MUST be exactly `READY_FOR_OWNER_COFFEE_TABLE_EXECUTION_MANIFEST_REVIEW`.
- **FR-013**: K2 MUST remain validated as a member of the approved set but MUST NOT be used as a motion source because its portrait talking composition conflicts with the 16:9 motion-only campaign contract.
- **FR-014**: The command result MUST report parent plan SHA, execution manifest path/SHA, four task identities, assembly summary, zero-call accounting, and terminal state.
- **FR-015**: V1 manifest SHA `69746bff9ee06a4c6c762168d30151a6aab692f245f7a16271607cd716cf9b26` MUST be recorded as `REJECT_FOR_LIVE` with reason `MATERIAL_CONTINUITY_RISK` and MUST NOT be accepted as a Live authority.
- **FR-016**: Task 03 MUST use product-only source `outputs/reviews/candidate16-keyframes-v2/references/02.jpg`, SHA-256 `4bf6e13b82f9c9c4d4525180aa412ebc22e4ca6c541e6d9c33c905271814b5c5`, and MUST show no Candidate 16 or wine glass.
- **FR-017**: Task 04 MUST use source type `UPSTREAM_TASK_FRAME` from Task 02 with selector `LAST_VALID_FRAME`; its Task 02 MP4 SHA and extracted PNG SHA MUST remain explicitly `RUNTIME_BOUND` until a future authorized execution writes runtime evidence.
- **FR-018**: The Task 04 lineage rule MUST require Task 02 success, download completion, MP4 hash verification, deterministic local final-decoded-frame extraction, extracted-frame validation/hash recording, and zero provider calls for extraction before Task 04 submission may become eligible.
- **FR-019**: Task 04's exact prompt MUST state that the single glass already rests on the Coffee Table, Candidate 16's hands are empty, the glass remains untouched, and she moves calmly to the sofa and sits over four seconds before the hero ending.
- **FR-020**: V2 MUST preserve the parent plan, Candidate 16/K1/K2/K3/V7-B authority, four tasks, twenty generated seconds, six-beat order, one-hundred-credit/one-dollar caps, concurrency one, and zero automatic retries/replacements.

### Key Entities

- **Parent Plan Identity**: Exact path and content hash of the already-approved dry-run business plan.
- **Execution Manifest**: Immutable, collision-safe, review-pending contract containing limits, tasks, assembly, delivery, and zero-call evidence.
- **Execution Task**: One exact future provider request with stable task identity, source, prompt, parameters, beat coverage, and usable interval.
- **Runtime Source Lineage**: A deterministic dependency from a successful upstream artifact through exact local frame extraction to a runtime-bound input hash.
- **Assembly Mapping**: Ordered local edit decisions that transform selected task intervals and a deterministic terminal hold into the frozen twenty-second master timeline.

## Success Criteria

### Measurable Outcomes

- **SC-001**: One preparation command produces exactly one manifest with four fully specified tasks and a reproducible SHA-256 identity.
- **SC-002**: The assembly map covers every millisecond from 0:00 through 0:20 exactly once and preserves all six beats in order.
- **SC-003**: All invalid parent, source, prompt, authorization, and bound-limit fixtures fail before output creation with zero provider/network activity.
- **SC-004**: Offline tests verify the successful and fail-closed paths without any real provider client or credential.
- **SC-005**: Approved-source SHA-256 values are identical before and after implementation and real manifest preparation.
- **SC-006**: The final checkpoint reports provider submissions 0, task IDs 0, HTTP requests 0, paid calls 0, and the exact Owner-review terminal state.
- **SC-007**: Task 03 contains exactly one hash-bound product-only source and no Candidate 16/glass source semantics.
- **SC-008**: Task 04 contains no static K3 source and freezes one unambiguous Task 02 last-valid-frame extraction rule with both runtime hashes unfilled.
- **SC-009**: V2 preparation produces a new manifest SHA while leaving V1, the parent plan, and all approved sources byte-identical.

## Assumptions

- The approved parent plan and Candidate 16 Goal 2 binding remain unchanged.
- K1 is the wide establishing/walk source; K3 is the table-interaction source; the frozen PDP image is the product-detail source; K2 is validated but intentionally unused.
- The future Live executor will implement and log the frozen last-valid-frame extraction rule; this offline feature records the rule and runtime gates but does not fabricate its future hashes.
- The final two seconds are a deterministic local hold of Task 4's terminal hero frame, not new generation.
- The future paid executor and actual local media rendering require a later Owner approval of this manifest SHA and are outside this feature.
