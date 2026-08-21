# Tasks: Coffee Table Live Execution

**Input**: Design documents from `/specs/011-coffee-table-live-execution/`

**Tests**: Required by the specification; provider clients are fakes and network is blocked.

## Phase 1: Setup

- [x] T001 Record the exact approved Manifest V2 identity and Live constants in `src/lala_workflow/video/coffee_table_live.py`
- [x] T002 [P] Add manifest-bound Live CLI argument parsing tests in `tests/test_coffee_table_live.py`

## Phase 2: Foundational Validation

- [x] T003 [P] Add exact path/SHA, Owner flag, environment, credential, authority/source/prompt, budget, and no-prior-run failure tests in `tests/test_coffee_table_live.py`
- [x] T004 Implement fail-closed authorization and static preflight before run/provider creation in `src/lala_workflow/video/coffee_table_live.py`
- [x] T005 Add the mutually exclusive Coffee Table `--live` contract in `src/lala_workflow/video/cli.py` and dispatch in `src/lala_workflow/video/runner.py`

## Phase 3: User Story 1 - Execute the Approved Contract (Priority: P1)

**Goal**: Submit only the four approved requests in order with durable task IDs and fail-stop behavior.

**Independent Test**: Fake provider proves exact request translation, serial ordering, immediate ID persistence, four-task cap, and stop-on-first-failure/ambiguity.

- [x] T006 [P] [US1] Add fake-provider success, task failure, ambiguous submission, task-ID persistence, and no-later-task tests in `tests/test_coffee_table_live.py`
- [x] T007 [US1] Implement manifest request reconstruction, planned budget reservation, serial execution, immediate task-ID evidence, and failure preservation in `src/lala_workflow/video/coffee_table_live.py`
- [x] T008 [US1] Implement deterministic Task 02 final-frame extraction, hash evidence, and Task 04 submission gate in `src/lala_workflow/video/coffee_table_live.py`

## Phase 4: User Story 2 - Produce Deterministic Review Media (Priority: P1)

**Goal**: Create exact raw, master, and guarded local delivery artifacts without provider regeneration.

**Independent Test**: Synthetic media produces a validated twenty-second master and local variants with logged commands and zero provider calls.

- [x] T009 [P] [US2] Add real local FFmpeg lineage/assembly and fake-provider artifact tests in `tests/test_coffee_table_live.py`
- [x] T010 [US2] Implement exact timeline assembly and local 1:1/9:16 derivatives with validation and no-native fallback in `src/lala_workflow/video/coffee_table_live.py`
- [x] T011 [US2] Persist raw, lineage, assembly, delivery, provenance, and cost evidence in `src/lala_workflow/video/coffee_table_live.py`

## Phase 5: User Story 3 - Stop for Human Review (Priority: P1)

**Goal**: Deliver blank Human QA and only `READY_FOR_OWNER_REVIEW` on success.

**Independent Test**: Success evidence has blank review fields and no approval tokens; stopped runs retain exact failure evidence.

- [x] T012 [P] [US3] Add blank-review, terminal-state, redaction, and stopped-run evidence tests in `tests/test_coffee_table_live.py`
- [x] T013 [US3] Build the review package and final success/stopped summaries in `src/lala_workflow/video/coffee_table_live.py`

## Phase 6: Verification and Authorized Execution

- [x] T014 Run focused/full offline tests, compileall, validation, diff/secret scans, approved-source hashes, and Spec Kit analysis before Live; record preflight evidence in `README.md` and `PROGRESS.md`
- [x] T015 Rehash the authorized manifest, execute exactly one bounded Live command, audit all runtime/cost/review evidence, recompute approved-source hashes, run Spec Kit convergence, and stop at `READY_FOR_OWNER_REVIEW` on success or the exact authorized fail-stop state on any task failure

## Dependencies & Execution Order

- Phase 2 depends on Phase 1 and blocks all Live implementation.
- User Story 1 depends on foundational validation.
- User Story 2 depends on successful User Story 1 artifacts.
- User Story 3 depends on delivery evidence from User Story 2.
- Live execution is last and only after every offline gate passes.

## Implementation Strategy

Write failing tests first, then authorization/preflight, then execution/idempotency evidence, then deterministic local delivery, then review handoff. No implementation test may instantiate a real provider or access the network. The authorized paid command runs once only after all offline verification succeeds.
