# Tasks: One-Click Character Switch

**Input**: Design documents from `specs/007-one-click-character-switch/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tests**: Required by FR-033 and the repository constitution; test tasks precede implementation.

## Phase 1: Setup

**Purpose**: Add optional UI packaging and the checked-in legacy compatibility seed without changing approved bytes.

- [X] T001 Add optional Streamlit `ui` dependency and character runtime ignore patterns in `pyproject.toml` and `.gitignore`
- [X] T002 Create the legacy `lala-v1` registry/profile seed in `configs/characters/registry.yaml` and `configs/characters/profiles/lala-v1-v001.yaml`
- [X] T003 Create package exports and UI namespace in `src/lala_workflow/characters/__init__.py` and `src/lala_workflow/ui/__init__.py`

---

## Phase 2: Foundational Domain, Validation, and Registry

**Purpose**: Establish immutable typed data, secure upload storage, profile snapshots, and one-active registry invariants.

- [X] T004 [P] Add serialization, canonical profile hash, enum, transition, and ID tests in `tests/characters/test_domain.py`
- [X] T005 [P] Add required-role, MIME/decode, corrupt, oversized, decompression-bomb, duplicate, traversal, symlink, and collision tests in `tests/characters/test_validation.py`
- [X] T006 [P] Add registry parse/invariant, exactly-one-active, atomic replacement, failure rollback, and stale revision tests in `tests/characters/test_registry.py`
- [X] T007 Implement character enums, references, profiles, registry/build/preview/event dataclasses and canonical hashing in `src/lala_workflow/characters/domain.py`
- [X] T008 Implement stable redacted character error codes and user-facing role messages in `src/lala_workflow/characters/errors.py`
- [X] T009 Implement bounded upload/image validation and controlled canonical copy in `src/lala_workflow/characters/validation.py`
- [X] T010 Implement character storage roots, exclusive immutable writes, versioned profile snapshots, build evidence, and event append in `src/lala_workflow/characters/storage.py`
- [X] T011 Implement locked registry loading, profile-integrity validation, revision CAS, and atomic fsync/replace mutations in `src/lala_workflow/characters/registry.py`
- [X] T012 Run foundational character tests and record the checkpoint in `PROGRESS.md`

**Checkpoint**: Typed snapshots, controlled inputs, and registry transactions work independently of generation.

---

## Phase 3: User Story 1 - Create a Staging Character (Priority: P1) MVP

**Goal**: Import three required photos into a complete staging profile while keeping `lala-v1` active.

**Independent Test**: Import three local fixtures and verify generated ID, immutable source bytes, hashes, profile, registry entry, and unchanged active ID.

- [X] T013 [P] [US1] Add builder/import success, missing-role, duplicate-byte policy, idempotency, and no-half-profile tests in `tests/characters/test_builder.py`
- [X] T014 [P] [US1] Add legacy `lala-v1` profile byte/hash compatibility tests in `tests/characters/test_legacy.py`
- [X] T015 [US1] Implement collision-safe character ID allocation and profile construction in `src/lala_workflow/characters/builder.py`
- [X] T016 [US1] Implement initial import/build/list/show orchestration with active-character preservation in `src/lala_workflow/characters/service.py`
- [X] T017 [US1] Validate and load the checked-in `lala-v1` compatibility seed without copying the shared scene in `src/lala_workflow/characters/registry.py`
- [X] T018 [US1] Run User Story 1 tests and record source/hash evidence in `PROGRESS.md`

**Checkpoint**: A new character can be built entirely offline and cannot change production identity.

---

## Phase 4: User Story 2 - Review Static and Motion Previews (Priority: P1)

**Goal**: Resolve deterministic references and create explicit character-bound preview-only evidence without weakening production promotion.

**Independent Test**: Inject fake static/motion operations, create both fixture media previews, and verify exact provenance, diagnostics, blank human decisions, and `READY_FOR_APPROVAL`.

- [X] T019 [P] [US2] Add explicit/active/legacy resolver precedence plus inactive/staging eligibility tests in `tests/characters/test_resolver.py`
- [X] T020 [P] [US2] Add baseline/home/medium/product deterministic order and max-reference tests in `tests/characters/test_references.py`
- [X] T021 [P] [US2] Add offline plan, fake static/motion success, partial failure, hash validation, and diagnostic-only tests in `tests/characters/test_preview.py`
- [X] T022 [P] [US2] Add static GenerationRequest and eight-artifact character provenance regression tests in `tests/integration/test_character_static.py`
- [X] T023 [P] [US2] Add preview-only motion request/evidence and production-keyframe-gate isolation tests in `tests/test_character_video_preview.py`
- [X] T024 [US2] Implement explicit/active/legacy character resolution and legacy AnchorManifest adaptation in `src/lala_workflow/characters/resolver.py`
- [X] T025 [US2] Implement deterministic context policies, logical tags, scene composition, and provider-limit enforcement in `src/lala_workflow/characters/references.py`
- [X] T026 [US2] Add optional character provenance fields to static domain/config serialization in `src/lala_workflow/domain.py` and `src/lala_workflow/config.py`
- [X] T027 [US2] Integrate `RunOptions.character_id`, character-aware references, and new run provenance without changing provider APIs in `src/lala_workflow/runner.py`
- [X] T028 [US2] Extend static report/anchor evidence with backward-compatible character facts in `src/lala_workflow/reporting.py`
- [X] T029 [US2] Implement provider-neutral static/motion preview protocols, offline planning, media verification, build status, and diagnostic evidence in `src/lala_workflow/characters/preview.py`
- [X] T030 [US2] Implement the distinct staging motion preview entry point with current bounded request/live guards in `src/lala_workflow/video/runner.py`
- [X] T031 [US2] Wire preview orchestration and failure preservation into `src/lala_workflow/characters/service.py`
- [X] T032 [US2] Add the versioned three-reference character static preview prompt in `prompts/character-static-preview-v1.txt`
- [X] T033 [US2] Run User Story 2 tests and record zero-call/provider-boundary evidence in `PROGRESS.md`

**Checkpoint**: Both previews can be produced under fakes/live guards, and neither is production-approved evidence.

---

## Phase 5: User Story 3 - Approve, Reject, or Roll Back (Priority: P1)

**Goal**: Make one final decision the only production identity switch boundary.

**Independent Test**: Activate, reject, simulate profile/copy/registry failure, race two revisions, and reactivate `lala-v1`; exactly one active remains throughout.

- [X] T034 [P] [US3] Add activation precondition, copy-only authority promotion, rollback, rejection, write failure, and stale-session tests in `tests/characters/test_activation.py`
- [X] T035 [P] [US3] Add full mocked upload-build-preview-activate/reject lifecycle tests in `tests/characters/test_service.py`
- [X] T036 [US3] Implement exact-byte activation source promotion and preview revalidation in `src/lala_workflow/characters/storage.py`
- [X] T037 [US3] Implement atomic approve/activate, reject, reactivation, and append-only event transitions in `src/lala_workflow/characters/service.py`
- [X] T038 [US3] Ensure failed/orphan prewrites cannot alter current registry visibility in `src/lala_workflow/characters/registry.py`
- [X] T039 [US3] Run User Story 3 tests and record concurrency/rollback evidence in `PROGRESS.md`

**Checkpoint**: Approval is failure-atomic, rejection is non-destructive, and `lala-v1` rollback works.

---

## Phase 6: User Story 4 - Complete the Flow Without Technical Operations (Priority: P1)

**Goal**: Provide the one-page ordinary-language UI backed only by tested services.

**Independent Test**: Import the app without UI extras, test view-state helpers, and manually run upload -> create -> preview status -> final decision with fake/offline service behavior.

- [X] T040 [P] [US4] Add UI adapter/view-state, ordinary-language error, and no-intermediate-confirmation tests in `tests/characters/test_ui.py`
- [X] T041 [US4] Implement the one-page required/optional upload, status, source/static/motion preview, diagnostics, reject/activate, and current/previous controls in `src/lala_workflow/ui/app.py`
- [X] T042 [US4] Keep Streamlit imports lazy and all business decisions inside `CharacterService` in `src/lala_workflow/ui/app.py`
- [X] T043 [US4] Run UI/service tests and record the non-technical manual flow result in `PROGRESS.md`

**Checkpoint**: Normal operation requires no terminal, YAML, paths, hashes, providers, or intermediate approval.

---

## Phase 7: User Story 5 - Automate and Preserve Legacy Workflows (Priority: P2)

**Goal**: Expose shared lifecycle commands and prove legacy static/video/QA/promotion compatibility.

**Independent Test**: Exercise every character command in a temporary project, then run existing static/video commands and verify unchanged schemas and source bytes.

- [X] T044 [P] [US5] Add list/show/import/build/preview/activate/reject CLI contract and error-exit tests in `tests/characters/test_cli.py`
- [X] T045 [P] [US5] Add legacy static/video/QA/promotion and missing-registry fallback regression tests in `tests/characters/test_backward_compatibility.py`
- [X] T046 [US5] Add the `character` parser tree and static `--character` option in `src/lala_workflow/cli.py`
- [X] T047 [US5] Route character commands to the shared service with redacted JSON and existing exit semantics in `src/lala_workflow/cli.py`
- [X] T048 [US5] Update README operating instructions, rollback, offline/live behavior, and limitations in `README.md`
- [X] T049 [US5] Update project agent behavior and Definition of Done for character authority/preview safety in `AGENTS.md`
- [X] T050 [US5] Run User Story 5 compatibility tests and record command results in `PROGRESS.md`

**Checkpoint**: UI and CLI share services; existing Goal 1/Goal 2 behavior stays compatible.

---

## Phase 8: Polish and Cross-Cutting Verification

- [X] T051 [P] Audit all character and new run evidence for credential, Bearer, authorization, signed-query, data-URI, and absolute developer-path leakage in `src/lala_workflow/characters/` and `tests/characters/`
- [X] T052 [P] Validate profile/registry/build documentation and runnable scenarios against `specs/007-one-click-character-switch/quickstart.md`
- [X] T053 Run `uv run pytest -q`, `uv run python -m compileall -q src tests`, and `git diff --check`, fixing all failures in affected files
- [X] T054 Run static validation and required 10/5/5 dry runs, inspecting eight-artifact counts and character provenance in `runs/`
- [X] T055 Run representative Goal 2 offline validation/previews and record unchanged thirteen-artifact, QA, and promotion gates in `PROGRESS.md`
- [X] T056 Recompute every approved-source SHA-256 and prove exact equality with the pre-change baseline in `PROGRESS.md`
- [X] T057 Audit FR-001–FR-034, SC-001–SC-010, user acceptance scenarios, and mark all completed tasks in `specs/007-one-click-character-switch/tasks.md`
- [X] T058 Record final architecture, test counts, paid-call counts, remaining Phase 1 limitations, and external live blocker if any in `PROGRESS.md`

---

## Dependencies and Execution Order

- Phase 1 has no dependencies.
- Phase 2 blocks all user stories.
- US1 blocks US2 because previews require a valid staging profile.
- US2 blocks US3 because activation requires both verified previews.
- US3 and its service contract block the final UI decisions in US4.
- US5 integrates all prior stories and runs compatibility coverage.
- Phase 8 runs only after every story checkpoint passes.

## Parallel Opportunities

- T004, T005, and T006 test distinct foundational concerns.
- T013 and T014 cover separate US1 behavior.
- T019–T023 cover resolver, selector, preview, static integration, and video isolation in separate files.
- T034 and T035 cover transaction detail and end-to-end lifecycle separately.
- T044 and T045 cover new CLI and old behavior separately.
- T051 and T052 are read-only audits after implementation.

## Implementation Strategy

1. Complete Phase 2 with tests first; do not integrate generation until registry invariants pass.
2. Deliver the offline-safe US1 MVP: import/build while `lala-v1` remains active.
3. Add preview selection and fake-provider evidence before wiring real guarded runners.
4. Add activation only after preview-only isolation is proven.
5. Keep the UI last among P1 stories so it remains a thin adapter over complete services.
6. Finish CLI/backward compatibility and full verification without any live provider call.
