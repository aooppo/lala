# Tasks: Coffee Table Execution Manifest

**Input**: Design documents from `/specs/010-coffee-table-execution-manifest/`

## Phase 1: Setup

- [x] T001 Record the four exact versioned motion prompts in `prompts/coffee-table-task-01-establish-walk-v1.txt`, `prompts/coffee-table-task-02-walk-place-v1.txt`, `prompts/coffee-table-task-03-product-detail-v1.txt`, and `prompts/coffee-table-task-04-sit-hero-v1.txt`
- [x] T002 Add execution-manifest fixture builders and zero-provider sentinels in `tests/test_coffee_table_execution_manifest.py`

---

## Phase 2: Foundational Validation

- [x] T003 [P] Add parent path/SHA, frozen semantics, Goal 2, source hash, prompt hash/length, and hard-bound failure tests in `tests/test_coffee_table_execution_manifest.py`
- [x] T004 [P] Add exact four-task, six-beat timeline, deterministic hold, blank-review, and zero-call success tests in `tests/test_coffee_table_execution_manifest.py`
- [x] T005 Implement exact parent, authority, approved-source, prompt, and boundary validators in `src/lala_workflow/video/campaigns.py`

---

## Phase 3: User Story 1 - Freeze the Four Requests (Priority: P1)

**Goal**: Produce one immutable four-request contract that preserves the frozen story.

**Independent Test**: A valid fixture yields four exact task records and a gap-free twenty-second assembly map.

- [x] T006 [US1] Implement four provider-neutral task records with K1/K3 and versioned prompt identities in `src/lala_workflow/video/campaigns.py`
- [x] T007 [US1] Implement the exact Task 1/2 full-use, Task 3 trim, Task 4 full-use plus terminal-hold assembly map in `src/lala_workflow/video/campaigns.py`
- [x] T008 [US1] Implement canonical collision-safe manifest serialization and returned SHA identity in `src/lala_workflow/video/campaigns.py`

---

## Phase 4: User Story 2 - Refuse Drift and Paid Work (Priority: P1)

**Goal**: Fail before output creation for any drift while making provider construction impossible.

**Independent Test**: All mutated fixtures fail closed and provider/network counters stay zero.

- [x] T009 [US2] Enforce explicit preparation authorization and mutually exclusive dry-run/preparation CLI arguments in `src/lala_workflow/video/cli.py`
- [x] T010 [US2] Dispatch only the offline preparation function and expose no Live/provider path in `src/lala_workflow/video/runner.py`
- [x] T011 [US2] Verify output rollback/collision behavior and absence of provider imports or calls in `tests/test_coffee_table_execution_manifest.py`

---

## Phase 5: User Story 3 - Hand Off an Owner-Reviewable Identity (Priority: P2)

**Goal**: Return a complete manifest identity and stop at Owner review.

**Independent Test**: The CLI result reports the parent/manifest identities, task/assembly summary, exact status, and zero counters.

- [x] T012 [US3] Add CLI result assertions and exact terminal-state coverage in `tests/test_coffee_table_execution_manifest.py`
- [x] T013 [US3] Return the complete review handoff payload from `src/lala_workflow/video/campaigns.py` and `src/lala_workflow/video/runner.py`

---

## Phase 6: Verification and Documentation

- [x] T014 Run focused and full offline pytest suites and record results in `PROGRESS.md`
- [x] T015 Run the real offline preparation command, inspect the manifest, and record its SHA and zero-call evidence in `PROGRESS.md`
- [x] T016 Update the preparation command and authorization boundary in `README.md`
- [x] T017 Recompute every approved-source SHA and run a secret scan, recording unchanged hashes and paid-call count in `PROGRESS.md`

## Dependencies

- Phase 1 precedes validation and implementation.
- T003 and T004 may be authored together before T005.
- User Story 1 depends on foundational validation.
- User Story 2 depends on the manifest builder and gates User Story 3.
- Real evidence and documentation follow all focused tests.

## Implementation Strategy

Implement prompts and failing tests first, then validation and manifest construction, then CLI dispatch. Run focused tests before the real offline command, full tests before handoff, and finish with hash/secret/convergence audits. No task in this feature may construct a provider or execute Live.

## Phase 7: V2 Continuity Correction

**Goal**: Remove both held-glass resets without changing the parent plan, task count, duration, or budget.

**Independent Test**: V2 binds Task 03 to the exact PDP product-only source and Task 04 to one deterministic Task 02 last-valid-frame lineage, while V1 is rejected and every provider counter remains zero.

- [x] T018 [US1] Record the V1 Owner rejection and V2 supersession identity in `outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-074417-152920/owner-review.json` and `src/lala_workflow/video/campaigns.py`
- [x] T019 [US1] Replace Task 03 with the frozen PDP `02.jpg` path/SHA and product-only source semantics in `src/lala_workflow/video/campaigns.py`
- [x] T020 [US1] Replace Task 04 static K3 with Task 02 `LAST_VALID_FRAME` runtime lineage, exact extraction commands, runtime hash gates, and execution dependency in `src/lala_workflow/video/campaigns.py`
- [x] T021 [US1] Revise Task 03 and Task 04 prompts for product-only detail and empty-hand/glass-on-table continuity in `prompts/coffee-table-task-03-product-detail-v2.txt` and `prompts/coffee-table-task-04-sit-hero-v2.txt`
- [x] T022 [P] [US2] Add V1 rejection, PDP drift, no-K3 Task 03/04, runtime-bound hash, extraction-rule, and zero-call tests in `tests/test_coffee_table_execution_manifest.py`
- [x] T023 [US3] Emit `execution-manifest-v2.json`, run the real offline command, and verify the new SHA/status in `tests/test_coffee_table_execution_manifest.py` and `outputs/campaign-execution-manifests/`
- [x] T024 Update V2 continuity design, verification, zero-call accounting, and terminal state in `README.md` and `PROGRESS.md`
- [x] T025 Run focused/full offline tests, approved-source before/after hashes, secret scan, manifest audit, and convergence against `specs/010-coffee-table-execution-manifest/`
