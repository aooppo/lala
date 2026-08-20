# Tasks: P1-1 Motion V7 Controlled Live Batch

**Input**: Design documents from `specs/006-p1-1-motion-v7-live-batch/`

**Tests**: Required by the specification and project constitution. Use TDD and fake providers only.

## Phase 1: Setup

- [x] T001 Record the authoritative prompt mappings and immutable hashes as V7 live invariants in `src/lala_workflow/video/motion_v7.py`
- [x] T002 Verify existing Python ignore and runtime-output exclusions remain sufficient in `.gitignore`

---

## Phase 2: Foundational Tests and Contracts

- [x] T003 [P] Add CLI parser guard tests for required confirmations and absence of candidate selectors in `tests/test_motion_v7_live.py`
- [x] T004 [P] Add fake authorized A/B/C order, prompt association, evidence-before-submit, provider-isolation, and no-fourth-submission tests in `tests/test_motion_v7_live.py`
- [x] T005 [P] Add required A/B oversize, C missing, wrong count/order/mapping, missing authorization, invalid source, and unknown estimate zero-submission tests in `tests/test_motion_v7_live.py`
- [x] T006 [P] Add A-success/B-submission-error fail-stop, no-retry, no-replacement, and durable evidence tests in `tests/test_motion_v7_live.py`

**Checkpoint**: New tests fail for the missing live path without contacting a network.

---

## Phase 3: User Story 1 - Execute One Fixed Authorized V7 Batch (Priority: P1)

**Goal**: Provide the single explicitly authorized fixed A/B/C command and provider-neutral orchestration.

**Independent Test**: An injected fake receives exactly A/B/C once in order and the command has no selector surface.

- [x] T007 [US1] Add the fixed `motion-v7-live` command and runtime confirmation arguments in `src/lala_workflow/video/cli.py`
- [x] T008 [US1] Add exact canonical prompt mapping/hash and duplicate validation in `src/lala_workflow/video/motion_v7.py`
- [x] T009 [US1] Implement authorization, known-credit/cap, source, configuration, and complete three-request preparation in `src/lala_workflow/video/runner.py`
- [x] T010 [US1] Wire CLI handling to the same injectable live-batch runner with Runway-only real-provider construction in `src/lala_workflow/video/runner.py`

**Checkpoint**: Authorized fake execution follows the fixed interface and provider isolation contract.

---

## Phase 4: User Story 2 - Fail Closed Before First Submission (Priority: P1)

**Goal**: Guarantee complete request validation and verified append-only plan evidence before A submission.

**Independent Test**: Every required invalid A/B/C/source/auth/mapping/count scenario leaves fake submissions empty.

- [x] T011 [US2] Validate all three final motion requests through the provider protocol before the first submission in `src/lala_workflow/video/runner.py`
- [x] T012 [US2] Write the parent request/config/keyframe/plan/review/cost evidence before submission in `src/lala_workflow/video/runner.py`
- [x] T013 [US2] Read back and verify candidate order, mappings, hashes, estimates, source, and blank QA before emitting the preflight-complete event in `src/lala_workflow/video/runner.py`

**Checkpoint**: Submission A is impossible until complete batch and evidence validation succeeds.

---

## Phase 5: User Story 3 - Preserve Partial Failure Evidence and Human Authority (Priority: P1)

**Goal**: Execute sequentially with no replay, preserve partial task evidence, and keep all human/downstream gates unchanged.

**Independent Test**: Fake A succeeds/B fails; C is not submitted, A task ID survives, all three QA rows stay blank, and P1-2 stays blocked.

- [x] T014 [US3] Implement the V7 single-attempt executor and fail-stop candidate state transitions in `src/lala_workflow/video/runner.py`
- [x] T015 [US3] Complete ordered provider results, separate HTTP/task accounting, cost facts, summary, and not-submitted rows in `src/lala_workflow/video/runner.py`
- [x] T016 [US3] Add exact Runway adapter API HTTP counting without exposing credentials in `src/lala_workflow/providers/runway_video.py`
- [x] T017 [US3] Preserve pending Subject Lock, three blank QA rows, and explicit P1-2 blocked evidence in `src/lala_workflow/video/runner.py`

**Checkpoint**: Success and every partial failure leave complete sanitized thirteen-artifact evidence without replacement tasks.

---

## Phase 6: Polish, Regression, and Documentation

- [x] T018 [P] Document the implemented-but-not-executed guarded V7 live batch in `README.md`
- [x] T019 [P] Record acceptance evidence, unchanged gates, and zero real provider accounting in `PROGRESS.md`
- [x] T020 Run focused V7 live/dry-run, Motion Smoke, Subject Lock, P1-2, provider preflight, and secret/package tests per `specs/006-p1-1-motion-v7-live-batch/quickstart.md`
- [x] T021 Run `python -m compileall .`, full `uv run pytest -q`, approved-source hashes, secret scans, and `git diff --check`

---

## Dependencies & Execution Order

- Phase 1 precedes all code changes.
- Phase 2 tests precede their Phase 3-5 implementation (TDD).
- User Story 1 establishes the interface and prepared request batch.
- User Story 2 depends on User Story 1 and establishes the first-submission barrier.
- User Story 3 depends on the verified preflight barrier and completes execution/evidence.
- Documentation and full regression follow all user stories.

## Parallel Opportunities

- T003-T006 target independent test scenarios but share one new test file, so apply sequentially if edited by one agent.
- T018 and T019 edit different documentation files and may run in parallel.

## Implementation Strategy

1. Make all safety and orchestration tests fail first.
2. Implement the fixed command and full request preparation.
3. Add the evidence-before-submit checkpoint.
4. Add single-attempt fail-stop execution and complete evidence.
5. Run focused regressions, converge against every FR/SC, then run the full offline suite.
