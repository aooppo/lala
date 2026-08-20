# Tasks: Subject Lock Diagnostics

**Input**: Design documents from `specs/004-subject-lock-diagnostics/`
**Tests**: Required by the feature specification and project constitution; execute TDD.

## Phase 1: Setup

- [x] T001 Add validated subject-lock threshold configuration in `configs/video-qa.yaml` and `src/lala_workflow/video/qa/subject_lock.py`
- [x] T002 Create the provider-neutral QA package exports in `src/lala_workflow/video/qa/__init__.py`

---

## Phase 2: Foundational Tests and Domain

- [x] T003 [P] Add failing synthetic perfect-lock, translation, scale, tracking-loss, and threshold tests in `tests/test_subject_lock.py`
- [x] T004 [P] Add failing review-package artifact, checksum, ZIP, secret-scan, and review-immutability tests in `tests/test_subject_lock_review_package.py`
- [x] T005 Define `SubjectTracker`, boxes, observations, thresholds, results, validation, aggregation, and fail-closed status rules in `src/lala_workflow/video/qa/subject_lock.py`

**Checkpoint**: Domain and failing contract tests exist before tracker/package implementation.

---

## Phase 3: User Story 1 - Quantify Subject Lock (Priority: P1)

**Goal**: Produce deterministic position/scale diagnostics or insufficient evidence.

**Independent Test**: Synthetic locked/translated/scaled/lost sequences satisfy SC-001–SC-004.

- [x] T006 [US1] Implement bounded Pillow color-component subject tracking with explicit `color_region_proxy` scope in `src/lala_workflow/video/qa/subject_lock.py`
- [x] T007 [US1] Implement local FFmpeg frame sampling and video analysis without network/model downloads in `src/lala_workflow/video/qa/subject_lock.py`
- [x] T008 [US1] Generate JSON, trajectory CSV, and diagnostic overlay outputs in `src/lala_workflow/video/qa/subject_lock.py`
- [x] T009 [US1] Make all synthetic subject-lock tests pass and prove tracking failure never becomes within-threshold in `tests/test_subject_lock.py`

---

## Phase 4: User Story 2 - Package Diagnostic Evidence (Priority: P1)

**Goal**: Integrate subject evidence into motion review packages and reports while preserving human QA.

**Independent Test**: A local fixture package contains all required artifacts in checksum/ZIP and reports diagnostic vs human state separately.

- [x] T010 [US2] Implement safe review-package diagnostic finalization, sorted checksums, deterministic ZIP, integrity verification, and secret scan in `src/lala_workflow/video/qa/review_package.py`
- [x] T011 [US2] Add local-only `video subject-lock` parsing/routing in `src/lala_workflow/video/cli.py` and `src/lala_workflow/video/runner.py`
- [x] T012 [US2] Add optional subject-lock summary and separate `human_qa_status` to `video report` in `src/lala_workflow/video/reporting.py`
- [x] T013 [US2] Make package/report tests pass and prove run/package review bytes remain unchanged in `tests/test_subject_lock_review_package.py` and `tests/test_video_reporting.py`

---

## Phase 5: User Story 3 - Continue P1-2 Safely Offline (Priority: P1)

**Goal**: Allow failed-review offline/dry-run planning and preserve strict pre-provider live blocking.

**Independent Test**: A failed P1-1 review permits a three-candidate dry-run with zero submissions and blocks mocked live before construction.

- [x] T014 [US3] Add failing failed-review dry-run-allowed and live-pre-provider-blocked tests in `tests/test_video_motion_variations.py`
- [x] T015 [US3] Refactor mode-aware P1-2 smoke provenance/review validation without weakening live approval in `src/lala_workflow/video/runner.py`
- [x] T016 [US3] Execute and inspect the canonical V6 three-candidate dry-run with zero provider construction/submissions/tasks in ignored runtime evidence

---

## Phase 6: V6 Regression, Documentation, and Full Verification

- [x] T017 Run the local V6 diagnostic, update its ignored review package checksums/ZIP, and verify material non-zero evidence or `INSUFFICIENT_EVIDENCE` without changing source review/media
- [x] T018 [P] Update feature/Goal 2 contracts, `README.md`, and `PROGRESS.md` with diagnostic-only semantics and P1-2 mode gates
- [x] T019 Run compileall, focused Subject Lock/Motion Smoke/P1-2/report suites, full pytest, package integrity/secret scans, approved-source pre/post hashes, and `git diff --check`
- [x] T020 Record requirements-to-tasks-to-tests evidence and mark completed tasks in `specs/004-subject-lock-diagnostics/tasks.md`

## Completion Evidence — 2026-08-20

- FR-001–FR-006 / SC-001–SC-004: `tests/test_subject_lock.py` covers provider-neutral tracking,
  threshold loading, exact lock/translation/scale, and fail-closed tracking loss.
- FR-007–FR-010 / SC-005–SC-006: `tests/test_subject_lock_review_package.py` covers artifacts,
  checksum/ZIP/secret integrity, review immutability, and diagnostic-vs-human reporting. V6 produced
  `OUTSIDE_THRESHOLD` with 11/11 frames tracked and material position/scale change.
- FR-011–FR-012 / SC-007–SC-008: `tests/test_video_motion_variations.py` covers failed-review
  three-candidate dry-run and pre-provider Live blocking. Runtime dry-run
  `LALA-VIDEO-20260820-061940-MOTION-GENERATE-001` recorded three planned calls, three blank QA
  rows, 75 estimated credits, zero submissions, and no task IDs.
- FR-013–FR-015 / SC-009: no dependency or prompt was added; compileall passed; focused suites
  passed 9/10/11; full offline pytest passed 207 tests; all approved anchors matched baseline;
  package/runtime secret and tracked-media scans plus `git diff --check` passed; paid calls were 0.

---

## Dependencies & Execution Order

- Phase 1 precedes all implementation.
- T003/T004 are parallel failing-test tasks; T005 follows their contracts.
- US1 (T006–T009) precedes package integration.
- US2 and US3 touch different primary modules except final runner/CLI integration and execute sequentially where files overlap.
- V6 runtime analysis requires US1/US2; full verification requires all stories.

## Parallel Opportunities

- T003 and T004 may be authored independently.
- Documentation T018 may begin after contracts stabilize while V6 runtime inspection proceeds.

## Implementation Strategy

1. Deliver synthetic fail-closed measurement first.
2. Add package/report integration without changing run evidence.
3. Separate P1-2 offline and live gates under tests.
4. Validate V6, canonical dry-run, full suite, hashes, integrity, and zero-provider accounting.
