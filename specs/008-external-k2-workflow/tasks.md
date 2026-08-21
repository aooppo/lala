# Tasks: Reviewed External K2 Workflow

**Input**: Design documents from `specs/008-external-k2-workflow/`
**Tests**: Required by Owner and constitution; write failing tests first.

**Status rule**: A source file's presence is not completion. Check a task only after its independent
verification passes. On 2026-08-21 focused verification reached 39 passed and the complete offline
suite reached 302 passed; the real candidate was then imported and left pending Human review.

## Phase 1: Setup

- [X] T001 Record baseline Git state, approved-source hashes, K1 manifest, and V7 evidence hashes in `specs/008-external-k2-workflow/quickstart.md`
- [X] T002 Verify Python/runtime ignore patterns and candidate runtime isolation in `.gitignore`

## Phase 2: Foundational

- [X] T003 Define and verify external candidate/review constants, ordered CSV schema, path/MIME/size/hash validation, and handled-failure cleanup in `src/lala_workflow/video/keyframe_candidates.py` (FR-001–FR-008, NFR-001–NFR-004)
- [X] T004 Extend and verify approved-keyframe domain/manifest validation for truthful external promotion provenance in `src/lala_workflow/video/domain.py` and `src/lala_workflow/video/validation.py` (FR-009–FR-013)

## Phase 3: User Story 1 - Stage External Candidate (P1)

**Independent Test**: Valid exact-byte import yields pending provenance and blank review; unsafe inputs leave no candidate.

- [X] T005 [US1] Complete passing valid/hash/exact-byte/symlink/traversal/invalid-MIME/oversize/duplicate/overwrite/source-drift tests in `tests/test_video_external_keyframes.py` (FR-001–FR-005, SC-001–SC-002)
- [X] T006 [US1] Implement and verify exclusive exact-byte external candidate ingest, truthful provenance, blank review, and failure cleanup in `src/lala_workflow/video/keyframe_candidates.py` (FR-001–FR-005, NFR-001–NFR-004)
- [X] T007 [US1] Add and verify `video keyframe import-candidate` parsing/dispatch/zero-call output in `src/lala_workflow/video/cli.py` and `src/lala_workflow/video/runner.py` (FR-001–FR-005, SC-001)

## Phase 4: User Story 2 - Human Review and Promotion (P1)

**Independent Test**: Only a fully passing, attributable exact-candidate review promotes identical bytes and manifest authority.

- [X] T008 [US2] Complete passing blank/schema/incomplete/reviewer/time/hash/role/mismatch/collision/cleanup and exact-byte promotion tests in `tests/test_video_external_keyframes.py` (FR-006–FR-010, SC-002–SC-003)
- [X] T009 [US2] Implement and verify review-copy validation plus exclusive exact-byte promotion, handled-failure rollback, and manifest registration in `src/lala_workflow/video/keyframe_candidates.py` (FR-006–FR-010, NFR-002–NFR-004)
- [X] T010 [US2] Add and verify `video keyframe promote-candidate` parsing/dispatch and redaction-safe output in `src/lala_workflow/video/cli.py` and `src/lala_workflow/video/runner.py` (FR-007–FR-010, NFR-003)
- [X] T011 [US2] Add passing external-promotion approved-source validation and legacy provenance regression tests in `tests/test_video_media_validation.py` (FR-009–FR-013, SC-003)

## Phase 5: User Story 3 - Dual Talking/ Motion Resolution (P1)

**Independent Test**: Product Page talking requests/evidence use K2, motion/V7 use unchanged K1, and missing K2 blocks before provider/run allocation.

- [X] T012 [US3] Complete passing dual resolver/evidence/V7/hash-invariance/missing-or-ambiguous-K2/run-zero/factory-zero tests in `tests/test_video_pilot_preflight.py` and `tests/test_video_dry_run.py` (FR-011–FR-016, SC-004–SC-005)
- [X] T013 [US3] Implement and verify role-unique talking/motion resolution plus additive selectors in `src/lala_workflow/video/runner.py` and `src/lala_workflow/video/cli.py` (FR-011, FR-013, FR-014, FR-015)
- [X] T014 [US3] Split talking/motion request translation and `dual-keyframe-evidence/v1` while preserving historical readers in `src/lala_workflow/video/runner.py` (FR-012–FR-016, SC-004–SC-005)

## Phase 6: Polish and Real Candidate

- [X] T015 Reconcile final implemented behavior, commands, requirement/task/test traceability, known limits, and evidence in `README.md`, `PROGRESS.md`, and `specs/008-external-k2-workflow/` after all tests pass (FR-001–FR-017, NFR-001–NFR-004, SC-001–SC-008)
- [X] T016 Run focused/full tests, compileall, video validate, diff/security/source-hash checks; only when green import real `k2_candidate_01.png`, verify its exact expected hash and blank review, record zero-call accounting, and create one local commit without promotion (FR-017, SC-006, SC-007, SC-008)

## Dependencies & Execution Order

- T001–T004 establish baseline/contracts.
- US1 T005–T007 precedes US2 because promotion consumes staged candidates.
- US2 T008–T011 precedes real import but can complete before US3 integration.
- US3 T012–T014 depends on external approved provenance fixture support from US2.
- T015–T016 depend on all stories.

## Requirement Coverage

| Requirement set | Tasks | Verification evidence |
|---|---|---|
| FR-001–FR-005 | T003, T005–T007 | Exact-byte import and blank-review tests; CLI output |
| FR-006–FR-010 | T003–T004, T008–T011 | Review rejection, promotion equality, collision/rollback tests |
| FR-011–FR-016 | T004, T011–T015 | Dual resolver/evidence, V7 compatibility, pre-provider blocking tests |
| FR-017 | T015–T016 | Real candidate pending evidence; no promotion |
| NFR-001–NFR-004 | T003, T006, T008–T010, T012, T015–T016 | Size/path/network/redaction/cleanup/security checks |
| SC-001–SC-005 | T005–T014 | Story-focused test suites |
| SC-006–SC-008 | T015–T016 | Full gate log, traceability audit, final pending handoff |

## Parallel Opportunities

- After T003–T004, US1 negative-path tests and CLI routing can be refined in parallel, but T006
  remains the integration point.
- US2 test completion and manifest-validation regressions touch different test files and can run in
  parallel before T009/T010 integration.
- US3 dry-run evidence tests and live preflight/factory-zero tests can be split across the two named
  test modules; resolver changes remain serialized with fixture updates.
- T015 documentation can be drafted during verification but must not be checked complete until T016
  supplies final green evidence.

## Implementation Strategy

Implement test-first in strict task order. Stop the real workflow after T016 import at `READY_FOR_K2_HUMAN_REVIEW`; never fill the review or invoke promotion.

Suggested MVP is US1 only on synthetic fixtures. The production checkpoint still requires US2 and
US3 because the real candidate must not enter an unverified or ambiguously resolved workflow.

## Phase 7: Convergence

- [X] T017 Add a direct relative source `..` traversal rejection test in `tests/test_video_external_keyframes.py` per FR-002 and SC-002 (partial)
- [X] T018 Add direct missing-review-column/schema-mismatch and staged-byte-drift rejection tests in `tests/test_video_external_keyframes.py` per FR-008 and SC-002 (partial)
- [X] T019 Add fault-injection coverage proving approved media/promotion cleanup and unchanged manifest bytes after promotion publication failure in `tests/test_video_external_keyframes.py` per FR-010 and NFR-004 (partial)
- [X] T020 Assert `dual-keyframe-evidence/v1` and distinct talking/motion request IDs, roles, and SHA-256 values in `tests/test_video_pilot_preflight.py` per FR-012 and SC-004 (partial)
