# Tasks: Candidate 16 Keyframe Publish

**Input**: Design documents from `/specs/009-candidate16-keyframe-publish/`

**Tests**: Required by the feature specification and repository constitution. Execute test tasks before their corresponding implementation tasks.

## Phase 1: Setup

- [x] T001 Record pre-mutation approved-source and Candidate 16 V1/V2 integrity baselines under `tmp/`
- [x] T002 Verify current CLI/config/keyframe/character/V7 contracts and dirty-worktree overlap in `src/lala_workflow/video/`, `configs/`, and `PROGRESS.md`

---

## Phase 2: Foundational

- [x] T003 [P] Add shared review-package, promotion, set, publish, binding, and blocker fixture builders in `tests/test_candidate16_keyframe_sets.py`
- [x] T004 [P] Add motion-only campaign/zero-provider fixture builders in `tests/test_coffee_table_campaign.py`
- [x] T005 Define Candidate 16 role/schema constants and safe local persistence helpers in `src/lala_workflow/video/keyframe_sets.py`

**Checkpoint**: Reusable fixtures and domain rules exist; no production authority has changed.

---

## Phase 3: User Story 1 - Approve and Promote One Keyframe per Role (Priority: P1)

**Goal**: Validate the seven-row Owner review and exact-byte promote only one Candidate 16 authority per role.

**Independent Test**: Valid review selects exact K1/K2/K3; invalid role/hash/applicability/count/time fails; each promotion copies identical bytes and rolls back on collision/failure.

- [x] T006 [US1] Add failing review-package schema, role-applicability, selected-count, hash, reviewer, timezone, non-selected-blank, and active-character tests in `tests/test_candidate16_keyframe_sets.py`
- [x] T007 [US1] Implement immutable V2 manifest/file/review parsing and exactly-one-per-role validation in `src/lala_workflow/video/keyframe_sets.py`
- [x] T008 [US1] Add failing exact-byte promotion, provenance, manifest registration, collision, and rollback tests in `tests/test_candidate16_keyframe_sets.py`
- [x] T009 [US1] Implement Candidate 16 reviewed-package promotion in `src/lala_workflow/video/keyframe_sets.py`
- [x] T010 [US1] Extend approved keyframe domain/provenance validation for role-aware Candidate 16 promotions in `src/lala_workflow/video/domain.py` and `src/lala_workflow/video/validation.py`

**Checkpoint**: Three individually promoted fixture authorities are exact-byte and all rejected cases fail closed.

---

## Phase 4: User Story 2 - Build and Publish a Candidate 16 Keyframe Set (Priority: P1)

**Goal**: Build immutable role-complete set evidence and publish it through an append-only event plus atomic current pointer.

**Independent Test**: A valid three-role fixture builds/publishes once; mixed character, missing/ambiguous role, drift, collision, and synthetic write failure leave no partial authority.

- [x] T011 [US2] Add failing set build/member digest/immutable manifest/collision tests in `tests/test_candidate16_keyframe_sets.py`
- [x] T012 [US2] Implement set build and revalidation in `src/lala_workflow/video/keyframe_sets.py`
- [x] T013 [US2] Add failing publish event/registry revision/idempotency/rollback tests in `tests/test_candidate16_keyframe_sets.py`
- [x] T014 [US2] Implement append-only publish events and atomic revisioned registry in `src/lala_workflow/video/keyframe_sets.py`

**Checkpoint**: Fixture current state resolves exactly one published Candidate 16 set while prior evidence remains immutable.

---

## Phase 5: User Story 3 - Rebind and Preflight Goal 2 (Priority: P1)

**Goal**: Bind Goal 2 to the current Candidate 16 set and distinguish reusable V7 methodology from identity-bound evidence.

**Independent Test**: Valid binding resolves exact K1/K2/K3; stale/mixed/drifted bindings fail before provider/run work; legacy V7 returns the explicit Candidate 16 execution blocker.

- [x] T015 [US3] Add failing Goal 2 binding/preflight/current-revision/legacy-authority/V7-character tests in `tests/test_candidate16_keyframe_sets.py`
- [x] T016 [US3] Implement revisioned Goal 2 binding, integrity preflight, and V7 classification in `src/lala_workflow/video/keyframe_sets.py`

**Checkpoint**: Goal 2 identity authority is explicit; old Lady LaLa V7 media is never relabeled.

---

## Phase 6: User Story 4 - Preview a Motion-Only Coffee Table Campaign (Priority: P2)

**Goal**: Emit a zero-call Coffee Table plan only after Goal 2/V7 readiness.

**Independent Test**: Fixture-ready preflight produces exact product/scene/performance/storyboard/ratio/cost evidence with no talking or provider construction; blocked preflight creates no preview.

- [x] T017 [US4] Add failing and passing motion-only brief, six-beat duration, protected-composition ratios, budget, blocker, and zero-provider tests in `tests/test_coffee_table_campaign.py`
- [x] T018 [US4] Implement collision-safe Coffee Table dry-run planning and bounded live projections in `src/lala_workflow/video/campaigns.py`

**Checkpoint**: The campaign planner is independently verified, while the real repository remains gated by actual V7 status.

---

## Phase 7: CLI Integration and Real Authorized State

- [x] T019 Add CLI parser/dispatch/help and zero-live guards for review, promotion, set, binding, preflight, and campaign commands in `src/lala_workflow/video/cli.py` and `src/lala_workflow/video/runner.py`
- [x] T020 Run focused CLI/service tests and mark all implementation tasks complete in `specs/009-candidate16-keyframe-publish/tasks.md`
- [x] T021 Record the exact Owner PASS decisions with timezone-aware current execution time only on selected rows in `outputs/reviews/candidate16-keyframes-v2/review.csv`
- [x] T022 Validate the real V2 package and exact-byte promote K1-V2-002, K2-002, and K3-V2-002 through the implemented CLI
- [x] T023 Build/publish `candidate16-keyframe-set-v1`, bind Goal 2, and run real preflight without provider work through the implemented CLI
- [x] T024 Conditionally run the real Coffee Table dry-run only if preflight is `GOAL2_READY`; otherwise preserve the exact V7 blocker and make zero preview/provider calls

---

## Phase 8: Polish & Cross-Cutting Concerns

- [x] T025 Update operator behavior, traceability, paid-call count, V7 distinction, and current state in `README.md` and `PROGRESS.md`
- [x] T026 Run focused tests, full `uv run pytest -q`, compileall, diff check, project/video validation as applicable, and CLI dry-run/help checks
- [x] T027 Compare pre-existing approved/V1/V2/historical evidence hashes, inspect new provenance/set/events/binding evidence, and run secret/provider-submission scans
- [x] T028 Run the Spec Kit convergence audit and append/implement any remaining traceable gaps in `specs/009-candidate16-keyframe-publish/tasks.md`

## Dependencies & Execution Order

- Phase 1 precedes all mutations.
- Phase 2 blocks every user story.
- US1 blocks US2; US2 blocks US3; US3 readiness blocks the real US4 preview.
- US4 implementation/tests can use isolated fixtures after Phase 2 and does not authorize the real preview.
- CLI integration precedes real Owner review mutation and all authorized real operations.
- Final verification and convergence follow the actual repository endpoint, including a legitimate external V7 blocker.

## Parallel Opportunities

- T003 and T004 touch separate test modules.
- Documentation integrity review can proceed alongside isolated test execution only when it does not edit overlapping files.
- Promotion operations are intentionally sequential because they mutate one shared manifest.

## Requirement Traceability

| Requirements | Tasks |
|---|---|
| FR-001–FR-005, SC-001–SC-002 | T006–T010, T021–T022 |
| FR-006–FR-009, SC-003–SC-004 | T011–T014, T023 |
| FR-010–FR-012, SC-005 | T015–T016, T023–T024 |
| FR-013–FR-016, SC-006–SC-007 | T017–T019, T024 |
| FR-017–FR-018, SC-008 | T001–T002, T025–T028 |

## Implementation Strategy

MVP is US1 plus US2: trustworthy Owner review, exact-byte promotion, and an immutable published Candidate 16 set. US3 adds safe downstream authority. US4 remains zero-call and conditionally blocked until Candidate 16-specific V7 evidence is separately authorized.

## Phase 9: Owner-Authorized Candidate 16 V7 Closure

**Goal**: Record and validate the V7-B decision, advance Goal 2, produce the real Coffee Table dry-run and exact non-executed Live/cost plan, then stop at the authorization boundary.

**Independent Test**: Exact parent/recovery/review/package provenance selects only V7-B; Goal 2 becomes ready; Coffee Table preview is created with zero provider activity and the requested terminal state.

- [x] T029 [US5] Add split-run Candidate 16 V7 review/registration, mutation rejection, unique-winner, and zero-provider tests in `tests/test_candidate16_v7_review.py`
- [x] T030 [US5] Implement collision-safe Candidate 16 V7 review registration and evidence validation in `src/lala_workflow/video/candidate16_v7.py`
- [x] T031 [US5] Integrate validated Candidate 16 V7 registration into Goal 2 classification and CLI dispatch in `src/lala_workflow/video/keyframe_sets.py`, `src/lala_workflow/video/cli.py`, and `src/lala_workflow/video/runner.py`
- [x] T032 [US5] Record the exact Owner V7-B decision in `outputs/reviews/candidate16-v7/review.csv` without changing append-only run reviews or the original package manifest
- [x] T033 [US5] Register V7-B and run the real Goal 2 preflight plus Coffee Table dry-run, recording `READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION` evidence under `outputs/reviews/candidate16-v7/` and `outputs/campaign-previews/`
- [x] T034 [US5] Record the exact bounded non-executed Coffee Table Live/cost plan and zero-call accounting in `README.md` and `PROGRESS.md`
- [x] T035 Run focused/full offline tests, validation, compilation, diff/hash/archive/secret checks, and approved-source post-hashes from the repository root
- [x] T036 Run the Spec Kit convergence audit and implement any remaining traceable gaps in `specs/009-candidate16-keyframe-publish/tasks.md`

### Phase 9 Dependencies

T029 precedes T030–T031. T031 precedes the real review registration and preflight. T032 precedes T033. T034–T036 follow the real zero-call endpoint.

### Phase 9 Traceability

| Requirements | Tasks |
|---|---|
| FR-019–FR-020, SC-009 | T029, T032 |
| FR-021–FR-023, SC-009–SC-010 | T029–T033 |
| FR-024, SC-010 | T033–T036 |
