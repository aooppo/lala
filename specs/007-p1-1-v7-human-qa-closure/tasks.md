# Tasks: P1-1 V7 Human QA Closure

**Input**: Design documents from `specs/007-p1-1-v7-human-qa-closure/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required by the feature specification and project constitution. Provider clients remain fake and network-blocked.

**Organization**: Tasks are grouped by user story and ordered so human evidence exists before gate validation, and gate validation exists before the closure package claims readiness.

## Phase 1: Setup and Evidence Baseline

- [x] T001 Record Git heads, dirty-worktree scope, original run-review/ZIP hashes, target media hashes, and all approved-source hashes in the execution evidence
- [x] T002 Inspect the exact QA schema, fixed V7 parent requests/results, and existing P1-2 prerequisite ordering in `src/lala_workflow/video/runner.py`

---

## Phase 2: User Story 1 - Archive the Human Decision (Priority: P1) 🎯 MVP

**Goal**: Preserve the explicit owner decision in the external reviewed copy while keeping append-only run evidence unchanged.

**Independent Test**: The external CSV has three provenance-matching human-reviewed rows, exactly V7-A is fully passing/MTL-ready, and the original run review hash is unchanged.

- [x] T003 [US1] Write the owner-authorized A PASS, B FAIL, C FAIL/reserve decisions with exact-schema motion QA mappings in `outputs/reviews/LALA-VIDEO-20260820-075843-MOTION-V7-001-review.csv`
- [x] T004 [US1] Verify external review provenance, selected V7-A task/media hashes, three explicit human decisions, and unchanged blank parent review in `runs/LALA-VIDEO-20260820-075843-MOTION-V7-001/review.csv`

**Checkpoint**: Human decision evidence is complete and append-only sources are unchanged.

---

## Phase 3: User Story 2 - Unlock P1-2 Without Executing It (Priority: P1)

**Goal**: Make the production P1-2 prerequisite accept the selected reviewed V7-A parent candidate without weakening any live guard.

**Independent Test**: Focused tests accept the unique valid V7-A selection, reject invalid/ambiguous/mutated evidence before provider construction, and a real repository dry-run plans three calls with zero submissions.

- [x] T005 [US2] Add failing V7 parent unique-selection, invalid-review, provenance/media drift, and zero-provider-construction tests in `tests/test_video_motion_variations.py`
- [x] T006 [US2] Extend the existing motion prerequisite validation for canonical V7 parent selection in `src/lala_workflow/video/runner.py`
- [x] T007 [US2] Run focused motion review/V7/P1-2 tests and execute the fixed reviewed V7 parent through the existing offline motion-generate preview

**Checkpoint**: P1-2 reports offline/live readiness from V7-A evidence, but no P1-2 provider execution occurred.

---

## Phase 4: User Story 3 - Preserve Closure Evidence (Priority: P2)

**Goal**: Produce a separately named, integrity-checked closure package that preserves the original pre-review package.

**Independent Test**: Original ZIP hash is unchanged; new closure ZIP contains the reviewed copy, selection/canonical states, original task/media facts, diagnostics gap, and zero-call accounting, and passes checksum/archive/secret verification.

- [x] T008 [US3] Build the non-overwriting closure directory and manifest under `outputs/packages/P1-1-V7-LALA-VIDEO-20260820-075843-MOTION-V7-001-human-qa-closure/`
- [x] T009 [US3] Generate deterministic closure checksums and `outputs/packages/P1-1-V7-LALA-VIDEO-20260820-075843-MOTION-V7-001-human-qa-closure.zip`
- [x] T010 [US3] Verify original/new ZIP integrity, all source/package checksums, diagnostics-gap preservation, and package/runtime secret scans

**Checkpoint**: Auditable final closure evidence exists beside the byte-unchanged original package.

---

## Phase 5: Polish and Cross-Cutting Verification

- [x] T011 Update operator behavior and P1-1/P1-2 canonical states in `README.md`
- [x] T012 Update acceptance traceability, validation results, approved-source integrity, and zero-call accounting in `PROGRESS.md`
- [x] T013 Mark completed work and verification evidence in `specs/007-p1-1-v7-human-qa-closure/tasks.md`
- [x] T014 Run full `uv run pytest -q`, compileall, `git diff --check`, approved-source post-hashes, final Git status, and zero-provider accounting checks

---

## Dependencies & Execution Order

- Phase 1 establishes immutable baselines and blocks all later phases.
- User Story 1 must complete before User Story 2 because the gate consumes the reviewed copy.
- User Story 2 must complete before User Story 3 because the package must report a real validated readiness state.
- Documentation and final verification depend on all three user stories.

## Parallel Opportunities

- No implementation tasks that touch the same review/gate evidence should run concurrently.
- After T007, README and package assembly could be prepared independently, but final manifest state and PROGRESS evidence remain sequential.
- Archive integrity, checksum verification, and secret scan may be run independently after the closure ZIP exists.

## Implementation Strategy

1. Preserve the human decision first and verify original evidence immutability.
2. Add tests before changing the gate; retain the legacy one-result smoke behavior.
3. Prove readiness through a dry-run only.
4. Package the already-validated state without overwriting pre-review evidence.
5. Complete tracked documentation and full offline regression.

## Format Validation

All executable tasks use the required checkbox, sequential task ID, optional story label, concrete file/path, and dependency order.
