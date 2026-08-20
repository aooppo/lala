# Tasks: P1-1 Motion V7 Targeted Fix

**Input**: Design documents from `specs/005-p1-1-motion-v7/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/dry-run-evidence.md`, and `quickstart.md`

**Tests**: Required by FR-011 and project governance. Tests must use no network or paid provider.

## Phase 1: Setup

- [X] T001 Create the versioned V7 candidate manifest in `configs/motion-v7.yaml` with the canonical three candidate IDs, fixed ordering, and `live_allowed: false`.
- [X] T002 [P] Create `prompts/p1-1-motion-v7-a-v1.txt` for the Stability First rung without modifying historical prompts.
- [X] T003 [P] Create `prompts/p1-1-motion-v7-b-v1.txt` for the Natural Micro Motion rung without modifying historical prompts.
- [X] T004 [P] Create `prompts/p1-1-motion-v7-c-v1.txt` for the Controlled Upper Bound rung without modifying historical prompts.

## Phase 2: Foundational Candidate and Comparison Model

- [X] T005 Add failing candidate/UTF-16/comparison validation tests in `tests/test_motion_v7.py` for FR-001 through FR-005 and FR-007.
- [X] T006 Implement candidate manifest loading, exact-order validation, prompt provenance resolution, configured credit estimates, and pending V6/V7 comparison construction in `src/lala_workflow/video/motion_v7.py`.
- [X] T007 Add the dry-run-only V7 CLI command in `src/lala_workflow/video/cli.py` with no `--live` option.

## Phase 3: User Story 1 - Controlled Motion Ladder (Priority: P1)

**Goal**: Produce three distinct candidate records with exact prompt and estimated-cost provenance.

**Independent Test**: Candidate loading returns A/B/C in order with the intended files, sub-limit UTF-16 units, and a non-authorizing live flag.

- [X] T008 [US1] Add V7 prompt and candidate-order assertions in `tests/test_motion_v7.py`.
- [X] T009 [US1] Implement candidate request/shot-plan assembly with one prompt per V7 candidate in `src/lala_workflow/video/runner.py`.

## Phase 4: User Story 2 - Pending Comparison and Blank QA (Priority: P1)

**Goal**: Preserve V6 diagnostics and blank review authority in the V7 dry-run record.

**Independent Test**: A no-video V7 dry-run contains fixed V6 values, pending V7/deltas, diagnostic-only authority, and three blank human-review rows.

- [X] T010 [US2] Add V6-pending-comparison and blank-QA assertions in `tests/test_motion_v7.py`.
- [X] T011 [US2] Write candidate metadata and comparison evidence through existing run JSON artifacts in `src/lala_workflow/video/runner.py`.

## Phase 5: User Story 3 - Offline Boundary Preservation (Priority: P1)

**Goal**: Make one three-candidate V7 dry-run possible with zero provider activity while preserving the P1-2 live gate.

**Independent Test**: The CLI and runner create one normal run with three planned requests, zero submissions/task IDs, and three blank rows; existing P1-2 live rejection remains unchanged.

- [X] T012 [US3] Add dry-run isolation, no-live-command, artifact-count, and P1-2 regression assertions in `tests/test_motion_v7.py`.
- [X] T013 [US3] Implement the V7 dry-run runner path and 13-artifact record writing in `src/lala_workflow/video/runner.py`.

## Phase 6: Polish and Verification

- [X] T014 Update `README.md` and `PROGRESS.md` with V6 result, V7 controlled ladder, corrected SHA labels, no-live status, and retained P1-2 gate.
- [X] T015 Run focused V7, Subject Lock/package, Motion Smoke, and P1-2 gate tests; record results in `specs/005-p1-1-motion-v7/tasks.md` and `PROGRESS.md`.
- [X] T016 Run the V7 CLI dry-run, compileall, full pytest, approved-source hashes, secret scan, and `git diff --check`; record results in `PROGRESS.md`.

## Dependencies and Execution Order

- T001–T004 precede T005–T007.
- T005 precedes T006; T006 and T007 precede T008–T013.
- T008/T009, T010/T011, and T012/T013 proceed in their stated order.
- T014–T016 run after the implementation suites are green.

## Parallel Opportunities

- T002, T003, and T004 modify independent prompt files.
- Test preparation in T005 can proceed while prompt files are prepared, but implementation tasks sharing runner files stay sequential.

## Implementation Strategy

1. Build and validate the static candidate matrix first.
2. Add a local-only, three-request evidence path without adding a live path.
3. Prove pending diagnostics and blank review isolation before documentation and complete regression verification.
