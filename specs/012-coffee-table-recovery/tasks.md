# Tasks: Coffee Table Failed-Task Recovery

**Input**: Design documents from `/specs/012-coffee-table-recovery/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required by the feature specification and repository governance. Automated tests must be offline and network-blocked.

## Phase 1: Setup

**Purpose**: Freeze the new recovery-only source and test surface without modifying original Live evidence.

- [x] T001 Record the pre-work approved-source and original execution/provider evidence hashes in `specs/012-coffee-table-recovery/tasks.md` implementation notes
- [x] T002 Add the exact Owner-supplied TASK-04 recovery prompt as versioned bytes in `prompts/coffee-table-task-04-sit-hero-v3.txt`
- [x] T003 [P] Create recovery test scaffolding and immutable fixture constants in `tests/test_coffee_table_recovery.py`

---

## Phase 2: Foundational Validation and CLI Boundary

**Purpose**: Establish provider-free recovery types, constants, exact input validation, and an offline-only CLI contract before any derived media work.

**Critical**: No user-story implementation may proceed until these gates prove original evidence and source identities.

- [x] T004 Implement recovery identities, outcome type, canonical JSON/exclusive-write helpers, and exact path/hash constants in `src/lala_workflow/video/coffee_table_recovery.py`
- [x] T005 Implement parent manifest, failed run, original evidence snapshot, historical task, raw artifact, PDP source, and prompt validation in `src/lala_workflow/video/coffee_table_recovery.py`
- [x] T006 [P] Add `--prepare-recovery` and `--failed-live-run` as an offline mutually exclusive Coffee Table mode in `src/lala_workflow/video/cli.py`
- [x] T007 Wire the provider-free recovery preparation handler and response fields in `src/lala_workflow/video/runner.py`
- [x] T008 Add CLI and pre-allocation failure tests proving exact bindings and no provider/network path in `tests/test_coffee_table_recovery.py`

**Checkpoint**: Exact historical/source gates run before output allocation, and recovery cannot be combined with Live.

---

## Phase 3: User Story 1 — Preserve the Failed Live History (Priority: P1)

**Goal**: Reuse TASK-01/TASK-02 and retain TASK-03's real durable FAILED provider record without touching original evidence.

**Independent Test**: Prepare the historical section from the stopped run, verify exact task IDs/status/error/credits and original file hashes, and prove TASK-03 is neither retried nor reclassified.

- [x] T009 [US1] Add immutable-history tests for TASK-01/TASK-02 reuse, TASK-03 durable FAILED semantics, TASK-04 NOT_SUBMITTED, and byte-stable originals in `tests/test_coffee_table_recovery.py`
- [x] T010 [US1] Implement normalized historical task records and immutable before/after evidence revalidation in `src/lala_workflow/video/coffee_table_recovery.py`

**Checkpoint**: Historical provider truth is independently reproducible with zero new task IDs or calls.

---

## Phase 4: User Story 2 — Build the Local Product Cutaway (Priority: P1)

**Goal**: Create a deterministic local 72-frame product shot from the exact PDP source with full transformation/media evidence.

**Independent Test**: Run cutaway generation twice from the exact source and compare hashes while validating three seconds, 1280x720, 24 fps, H.264/yuv420p, no audio, and a fixed filter/argv.

- [x] T011 [US2] Add real FFmpeg determinism, PDP SHA/dimension gate, media-contract, and failure cleanup tests in `tests/test_coffee_table_recovery.py`
- [x] T012 [US2] Implement fixed center-crop/1.035 optical-push command construction and local cutaway generation in `src/lala_workflow/video/coffee_table_recovery.py`
- [x] T013 [US2] Implement exact frame-count/media validation and LOCAL-TASK-03 transformation/hash/zero-cost evidence in `src/lala_workflow/video/coffee_table_recovery.py`

**Checkpoint**: LOCAL-TASK-03 validates independently and is structurally distinct from historical provider TASK-03.

---

## Phase 5: User Story 3 — Freeze the Proposed TASK-04 Input (Priority: P1)

**Goal**: Extract only TASK-02 zero-based frame 96, validate it, bind it to the new prompt, and keep TASK-04 unsubmitted.

**Independent Test**: Repeatedly extract index 96 from the fixed TASK-02 bytes, compare PNG hashes, validate dimensions, and prove drift/short input fails without choosing another frame or constructing a provider.

- [x] T014 [US3] Add fixed-index extraction, TASK-02 SHA gate, insufficient-frame, prompt SHA, and no-fallback/no-provider tests in `tests/test_coffee_table_recovery.py`
- [x] T015 [US3] Implement deterministic zero-based frame-96 extraction, PNG validation, and exact lineage evidence in `src/lala_workflow/video/coffee_table_recovery.py`
- [x] T016 [US3] Implement frozen future TASK-04 proposal evidence and separate-manifest-authorization gate in `src/lala_workflow/video/coffee_table_recovery.py`

**Checkpoint**: TASK-04 has an exact reviewable source/prompt proposal but remains `FUTURE_NOT_SUBMITTED`.

---

## Phase 6: User Story 4 — Review a Complete Recovery Contract (Priority: P1)

**Goal**: Produce one append-only recovery manifest with exact lineage, timeline, delivery, budget, and terminal review state.

**Independent Test**: Generate and validate a manifest fixture for exact parent/run bindings, eight contiguous 20-second segments, guarded-local ratios, 50/25/75-credit arithmetic, zero calls, collision safety, and final manifest SHA.

- [x] T017 [US4] Add recovery manifest schema, timeline, budget, collision, source-revalidation, and response contract tests in `tests/test_coffee_table_recovery.py`
- [x] T018 [US4] Implement recovery ID allocation, new output/manifest directories, exclusive canonical manifest creation, and safe partial-attempt cleanup in `src/lala_workflow/video/coffee_table_recovery.py`
- [x] T019 [US4] Implement exact eight-segment timeline, delivery policy, budget arithmetic, zero-call counters, and terminal review gate in `src/lala_workflow/video/coffee_table_recovery.py`
- [x] T020 [US4] Integrate validation, local media, lineage, manifest hashing, post-write revalidation, and outcome reporting in `src/lala_workflow/video/coffee_table_recovery.py`

**Checkpoint**: One hashed recovery contract is ready for Owner review; no future provider work has executed.

---

## Phase 7: Polish, Execution, and Cross-Cutting Verification

**Purpose**: Complete traceability, run the authorized local preparation, and prove repository/approved-source integrity.

- [x] T021 Update recovery behavior, exact command, zero-call state, paid-call count, and review boundary in `README.md` and `PROGRESS.md`
- [x] T022 Mark requirement-to-task traceability and completed task status in `specs/012-coffee-table-recovery/tasks.md`
- [x] T023 Run `uv run pytest tests/test_coffee_table_recovery.py`, full `uv run pytest`, compileall, `git diff --check`, video validation, and secret scan; record exact results in `PROGRESS.md`
- [x] T024 Execute the exact offline recovery command from `specs/012-coffee-table-recovery/contracts/cli-and-manifest.md` and inspect generated local media/manifest evidence
- [x] T025 Recompute every approved-source hash plus original manifest/provider-results hashes, compare with T001, and record the final integrity result in `PROGRESS.md`
- [x] T026 Run the Spec Kit convergence audit against `specs/012-coffee-table-recovery/spec.md`, `plan.md`, and this file; append any remaining work before handoff

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately and freezes prompt/test inputs.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **US1 (Phase 3)**: Depends on Foundational; establishes immutable historical truth.
- **US2 (Phase 4)**: Depends on Foundational and consumes validated PDP source; may be developed alongside US1 after gates exist.
- **US3 (Phase 5)**: Depends on Foundational and consumes validated TASK-02; may be developed alongside US2 after gates exist.
- **US4 (Phase 6)**: Depends on US1, US2, and US3 evidence models.
- **Polish/Execution (Phase 7)**: Depends on all user stories and must finish before handoff.

### User Story Dependency Graph

```text
Foundational
├── US1 Preserve History ─┐
├── US2 Local Cutaway ────┼── US4 Recovery Contract ── Verification/Execution
└── US3 TASK-04 Freeze ───┘
```

### Parallel Opportunities

- T003 can start alongside prompt freezing after T001.
- T006 can run alongside T004–T005 because it edits a different file, but T007 waits for both.
- After foundational gates, US1 tests/implementation, US2 tests/implementation, and US3 tests/implementation touch shared test/module files and therefore should be serialized in this worktree despite conceptual independence.
- Documentation updates can begin after the CLI/schema stabilize, but final evidence waits for T023–T025.

## Parallel Example: User Story Design Split

```text
Task A: Specify immutable historical record assertions in tests/test_coffee_table_recovery.py
Task B: Review the fixed local cutaway media contract in specs/012-coffee-table-recovery/contracts/cli-and-manifest.md
Task C: Verify the frame-96 and prompt contract in specs/012-coffee-table-recovery/data-model.md
```

Implementation edits remain serialized because all three stories converge in `coffee_table_recovery.py` and one test module.

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational gates.
2. Complete US1 to prove immutable historical truth and no retry path.
3. Stop and verify original bytes before deriving media.

### Incremental Delivery

1. Add and validate the local cutaway (US2).
2. Add and validate fixed frame/prompt lineage (US3).
3. Compose the append-only contract (US4).
4. Run all gates, prepare the actual recovery once, rehash protected sources, and stop for Owner review.

## Implementation Notes

- Pre-work approved-source SHA snapshot was captured in the active session before specification work; T025 must recompute the same complete directory set.
- Pre-work original execution manifest SHA: `ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea`.
- Pre-work original provider results SHA: `111a05f526944b26381fdf023cbcba4d8aaa58124490e3f7e9ceeedc3301c609`.
- Provider submissions and paid calls authorized by this feature: `0`.

## Requirement Traceability

- FR-001–FR-007, SC-001–SC-002: T001, T004–T010, T023, T025.
- FR-008–FR-009, SC-003: T011–T013, T017, T020, T023–T024.
- FR-010–FR-012, SC-004: T002, T014–T017, T020, T023–T024.
- FR-013–FR-017, SC-005, SC-007: T017–T021, T024.
- FR-018–FR-019, SC-006: T003, T008–T009, T011, T014, T017, T023, T025.
- US1 acceptance: T009–T010 and generated manifest `historical_tasks` inspection.
- US2 acceptance: T011–T013 and generated `LOCAL-TASK-03.mp4` FFprobe/visual inspection.
- US3 acceptance: T014–T016 and generated frame-96/prompt lineage inspection.
- US4 acceptance: T017–T020 and recovery-manifest schema/timeline/budget inspection.

---

## Phase 8: Owner-Authorized Recovery V2 Foundation

**Purpose**: Extend the completed preparation feature without altering its historical artifacts.

- [x] T027 Record the Recovery V2 and complete protected pre-work SHA snapshot in `specs/012-coffee-table-recovery/tasks.md`
- [x] T028 [P] Add one-submit lifecycle, exact V2 integrity, and CLI contract tests in `tests/test_coffee_table_recovery_live.py`
- [x] T029 [P] Add real local eight-segment assembly, last-frame hold, safe-area blocking, and blank review-package tests in `tests/test_coffee_table_recovery_live.py`
- [x] T030 Add exact Recovery V2 identities, outcome/error types, aggregate hashing, and transitive manifest validation in `src/lala_workflow/video/coffee_table_recovery_live.py`
- [x] T031 Add `--recovery-live` as a required modifier of Coffee Table `--live` and route V2 separately in `src/lala_workflow/video/cli.py` and `src/lala_workflow/video/runner.py`

## Phase 9: User Story 5 — Execute Authorized TASK-04 Once (Priority: P1)

**Goal**: Submit only the exact manifest-bound TASK-04 and preserve an append-only idempotent lifecycle.

**Independent Test**: A fake provider receives exactly one frame-92/prompt-v3 request; PREPARED, SUBMITTING, durable task ID, SUBMITTED, and terminal states persist; all failure paths make no replacement.

- [x] T032 [US5] Implement exact permission/credential/cap and prior-execution gates before run/provider allocation in `src/lala_workflow/video/coffee_table_recovery_live.py`
- [x] T033 [US5] Implement PREPARED/SUBMITTING/task-ID/SUBMITTED/terminal persistence and no-ID `BLOCKED_SUBMISSION_UNKNOWN` handling in `src/lala_workflow/video/coffee_table_recovery_live.py`
- [x] T034 [US5] Implement the single TASK-04 provider-neutral request, Runway adapter construction with submission retries zero, one-result download validation, and provider accounting in `src/lala_workflow/video/coffee_table_recovery_live.py`
- [x] T035 [US5] Complete fake-provider success/failure/ambiguity/known-ID/cap/redaction assertions in `tests/test_coffee_table_recovery_live.py`

## Phase 10: User Story 6 — Assemble Exact Master (Priority: P1)

**Goal**: Create one deterministic 480-frame master from exact-byte reused inputs and TASK-04's last decoded frame.

**Independent Test**: Synthetic colored clips prove the eight ordered source intervals, exact frame count/media contract, and two-second final-frame PNG hold.

- [x] T036 [US6] Implement deterministic last-decoded-frame extraction with count/index/PNG hash evidence in `src/lala_workflow/video/coffee_table_recovery_live.py`
- [x] T037 [US6] Implement exact eight-segment 24-fps assembly, input hash/argv capture, and strict master validation in `src/lala_workflow/video/coffee_table_recovery_live.py`
- [x] T038 [US6] Complete real FFmpeg timeline, 480-frame, last-frame, drift, and media validation tests in `tests/test_coffee_table_recovery_live.py`

## Phase 11: User Story 7 — Guarded Delivery and Human Review (Priority: P1)

**Goal**: Fail closed on unprovable alternate-ratio crops and deliver complete blank Owner review evidence.

**Independent Test**: Both ratios are `BLOCKED_SAFE_AREA` without files/provider calls, while exact raw/master copies and every blank checklist row reach `READY_FOR_OWNER_REVIEW`.

- [x] T039 [US7] Implement objective safe-area contract detection and fail-closed 1:1/9:16 results in `src/lala_workflow/video/coffee_table_recovery_live.py`
- [x] T040 [US7] Implement exact-byte review copies, evidence manifest, complete blank Owner checklist, and terminal review state in `src/lala_workflow/video/coffee_table_recovery_live.py`
- [x] T041 [US7] Complete safe-area, review copy/hash, blank-field, no-approval, and no-native-generation tests in `tests/test_coffee_table_recovery_live.py`

## Phase 12: Live Preflight, Execution, and Final Verification

**Purpose**: Prove the code offline, execute the one authorized task if every gate passes, and stop at Owner review.

- [x] T042 Update V2 Live behavior, exact command, paid-call boundary, and review stop in `README.md` and `PROGRESS.md`
- [x] T043 Run focused Coffee Table tests, full offline suite, both validators, compileall, `git diff --check`, and secret/signed-URL scans; record results in `PROGRESS.md`
- [x] T044 Recompute the approved-source aggregate and every V2 protected hash, inspect only YES/NO environment gate status, print the final execution plan, and run the exact command from `specs/012-coffee-table-recovery/contracts/cli-and-manifest.md`
- [x] T045 Validate TASK-04, master, final frame, safe-area results, review package, costs, provider counts, protected hashes, and no-secret evidence; record `READY_FOR_OWNER_REVIEW` or the exact blocker in `PROGRESS.md`
- [x] T046 Run the Spec Kit convergence audit and append/complete any remaining traceable work in `specs/012-coffee-table-recovery/tasks.md`

## Recovery V2 Requirement Traceability

- FR-020–FR-023, SC-008: T027–T032, T035, T043–T045.
- FR-024–FR-027, SC-009: T028, T033–T035, T043–T045.
- FR-028–FR-029, SC-010: T029, T036–T038, T043–T045.
- FR-030–FR-032, SC-011–SC-012: T029, T039–T042, T044–T045.
- FR-033: T028–T029, T035, T038, T041, T043.

## Recovery V2 Pre-work Integrity Snapshot

- Approved-source aggregate SHA-256: `9c228cd1a31952d0709738f3891a3d3e335afac1e20cb9c0bccea40dd893acf2` across 35 files.
- Recovery Manifest V2 SHA-256: `e97ea0d34f4ea541ab07e6898083e7a35c3b82502030f8f40a06d58fb43e6cc3`.
- Historical Recovery Manifest SHA-256: `8adaab7e3c3c128e7b1ae8c160804002aabae6b7a3ce11b5bb00646a2917b7b4`.
- Parent Execution Manifest SHA-256: `ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea`.
- Original provider results SHA-256: `111a05f526944b26381fdf023cbcba4d8aaa58124490e3f7e9ceeedc3301c609`.
- TASK-01/TASK-02/LOCAL-TASK-03 SHA-256: `2c61cb10a6563d9d4c1e43811be17ef06c3244fc6eb2356d349f064cff6ffd4b`, `9565691a30e312518cc867792063194ae2a667b70d586fbee06d821cc9b7413f`, `edda268e70ce2af85ab4e11b93e684bbfd363b098f692bb45ae369f0c5928cef`.
- Frame 92 / prompt v3 SHA-256: `95f68fa1f9bd3dcf6db94c2298511a224484c85c1fc5f278c3c67aa72e765e2e`, `e73cc7844806f8a25249c22da261e57df67ba7c3762172746b33a3b45b24f669`.
