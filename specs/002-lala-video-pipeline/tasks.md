# Tasks: Lady LaLa Reproducible Video Pipeline

**Input**: Design documents from `/specs/002-lala-video-pipeline/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required by FR-034 and the Goal 2 brief. For each story, write the listed tests first, confirm the new tests fail for the intended missing behavior, then implement.

**Organization**: Tasks are grouped by user story so each increment can be verified independently. Tests use synthetic fixtures that are explicitly marked non-approved and must never be accepted as production inputs.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it changes distinct files and has no incomplete prerequisite in the same phase.
- **[Story]**: Maps the task to a user story in `spec.md`.
- Every task names its implementation or verification path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the video workspace, dependencies, pending configuration, and versioned prompts without changing approved sources.

- [X] T001 Create normalized immutable-input and derived-output directories with tracked placeholders in `assets/approved_keyframes/.gitkeep`, `assets/voice/source/.gitkeep`, `assets/voice/approved/.gitkeep`, `assets/voice/metadata/.gitkeep`, `assets/scripts/.gitkeep`, `runs/.gitkeep`, `outputs/audio/.gitkeep`, `outputs/talking_shots/.gitkeep`, `outputs/broll/.gitkeep`, `outputs/edits/.gitkeep`, `outputs/final/.gitkeep`, and `outputs/approved_videos/.gitkeep`
- [X] T002 Update runtime dependencies to the researched Runway SDK version and add the HTTP client in `pyproject.toml`, then regenerate `uv.lock`
- [X] T003 [P] Add fail-closed pending manifests and bounded defaults in `configs/keyframe-manifest.yaml`, `configs/script-manifest.yaml`, `configs/voice-profile.yaml`, `configs/video-presets.yaml`, and `configs/providers.yaml`
- [X] T004 [P] Add versioned provider-neutral motion instructions in `prompts/talking-motion-v1.txt`, `prompts/home-broll-v1.txt`, and `prompts/product-broll-v1.txt`
- [X] T005 [P] Protect local credentials and transient media while retaining tracked evidence roots in `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish provider-neutral entities, immutable input validation, media validation, evidence storage, redaction, and deterministic test doubles used by every story.

**Critical**: No user story implementation begins until this phase is complete.

- [X] T006 [P] Add failing protocol and request-validation tests for talking, motion, and voice responsibilities in `tests/test_video_provider_contracts.py`
- [X] T007 [P] Add failing script-byte immutability, metadata, SHA-256, and attribution tests in `tests/test_video_scripts.py`
- [X] T008 [P] Add failing approved keyframe, approved audio, WAV, and downloaded-video content validation tests in `tests/test_video_media_validation.py`
- [X] T009 Implement immutable video run, source, script, audio, shot, provider-task, candidate, cost, and review entities in `src/lala_workflow/video/domain.py`
- [X] T010 Implement strict pending-aware manifest, preset, provider, and safety-limit loading in `src/lala_workflow/video/config.py`
- [X] T011 [P] Implement exact-byte script verification and approved-audio/keyframe validation in `src/lala_workflow/video/scripts.py` and `src/lala_workflow/audio/validation.py`
- [X] T012 [P] Define provider-neutral `TalkingVideoProvider`, `MotionVideoProvider`, and `VoiceProvider` protocols in `src/lala_workflow/providers/talking_base.py`, `src/lala_workflow/providers/motion_base.py`, and `src/lala_workflow/providers/voice_base.py`
- [X] T013 Implement append-only run storage, media hashing, content validation, and deterministic candidate naming in `src/lala_workflow/video/storage.py` and `src/lala_workflow/video/naming.py`
- [X] T014 [P] Extend recursive credential and authorization-header redaction for video payloads in `src/lala_workflow/redaction.py`
- [X] T015 [P] Create zero-network talking, motion, voice, downloader, and clock fakes plus explicitly non-approved media fixtures in `tests/fakes_video.py` and `tests/fixtures/video/README.md`
- [X] T016 Add nested `video` command dispatch without changing existing static-image commands in `src/lala_workflow/cli.py` and `src/lala_workflow/video/cli.py`
- [X] T017 Extend the global test network prohibition to all video-provider paths in `tests/conftest.py`

**Checkpoint**: Shared video types and fail-closed source handling are ready.

---

## Phase 3: User Story 1 — Validate a Video Run Without Spending (Priority: P1) MVP

**Goal**: Validate authoritative inputs and hashes, resolve each preset and shot plan, estimate bounded calls/costs, and write exactly thirteen run artifacts without a provider call.

**Independent Test**: With synthetic approved-status fixture manifests, preview all three presets and verify deterministic plans, hashes, call counts, estimates, thirteen append-only artifacts, blank QA fields, and zero fake-provider submissions; with repository pending manifests, verify a precise input error and no run directory.

### Tests for User Story 1

- [X] T018 [P] [US1] Add failing anchor/keyframe/script/voice manifest, preset-limit, prompt-hash, missing-input, and digest-mismatch tests in `tests/test_video_config.py`
- [X] T019 [P] [US1] Add failing deterministic shot-plan and provider-call-count tests for all three presets and single-shot fallback in `tests/test_video_planning.py`
- [X] T020 [P] [US1] Add failing dry-run isolation, thirteen-artifact, append-only, cost-preview, and exact QA-header integration tests in `tests/test_video_dry_run.py`

### Implementation for User Story 1

- [X] T021 [P] [US1] Implement deterministic multi-shot and single-talking-shot planning for product-page, tooltip, and homepage presets in `src/lala_workflow/video/planning.py`
- [X] T022 [P] [US1] Implement source-dated provider price-table loading and non-fabricated estimate serialization in `src/lala_workflow/video/costing.py`
- [X] T023 [US1] Implement the exact thirteen-artifact evidence bundle and initially blank candidate QA rows in `src/lala_workflow/video/reporting.py`
- [X] T024 [US1] Implement preflight anchor-manifest, approved-source, source-hash, prompt, preset, provider, and executable validation in `src/lala_workflow/video/validation.py`
- [X] T025 [US1] Implement a zero-submit preview runner that resolves requests, call counts, estimates, and evidence in `src/lala_workflow/video/runner.py`
- [X] T026 [US1] Wire `video validate`, dry-run `video talking-smoke-test`, and dry-run `video generate` with documented exit codes in `src/lala_workflow/video/cli.py`
- [X] T027 [US1] Run the User Story 1 test slice and append checkpoint commands, outcomes, paid-call count, and blockers in `specs/002-lala-video-pipeline/tasks.md` and `PROGRESS.md`

**Checkpoint**: The safe preview workflow is independently usable and makes zero paid calls.

---

## Phase 4: User Story 2 — Prove One Short Talking Shot (Priority: P2)

**Goal**: Translate one approved keyframe plus 8–12 seconds of approved audio into exactly one guarded talking result, preserving task identity across retries and producing review evidence.

**Independent Test**: A fake live smoke test with all gates and prior-stage approval enabled submits once, polls by returned task ID, downloads and validates exactly one video, and writes one blank QA row; every missing gate or invalid duration fails before submission.

### Tests for User Story 2

- [X] T028 [P] [US2] Add failing HeyGen image-plus-audio request, asset upload, polling, and response translation tests in `tests/test_heygen_talking_provider.py`
- [X] T029 [P] [US2] Add failing approved-custom-avatar Runway request translation and mismatched-keyframe rejection tests in `tests/test_runway_talking_provider.py`
- [X] T030 [P] [US2] Add failing `VIDEO_LIVE_SMOKE_TEST=true`, general live-gate, first-result limit, broader-generation smoke approval, retry, task-ID preservation, timeout, download, and failure-recovery tests in `tests/test_video_live_execution.py`
- [X] T031 [P] [US2] Add a failing mocked talking-smoke-test integration covering one result, one QA row, hashes, costs, and zero credential serialization in `tests/test_video_talking_smoke.py`

### Implementation for User Story 2

- [X] T032 [P] [US2] Implement current official HeyGen v3 image-avatar asset upload, audio-to-video submission, polling, and result translation in `src/lala_workflow/providers/heygen_talking.py`
- [X] T033 [P] [US2] Implement opt-in Runway `gwm1_avatars` translation restricted to a configured approved custom-avatar/keyframe digest mapping in `src/lala_workflow/providers/runway_talking.py`
- [X] T034 [US2] Implement bounded submit/poll/download state handling with task-ID-aware retries and event persistence in `src/lala_workflow/video/execution.py`
- [X] T035 [US2] Implement streamed result download, content validation, hashing, and provenance storage in `src/lala_workflow/video/downloads.py`
- [X] T036 [US2] Enforce `--live`, exact `VIDEO_ALLOW_LIVE_CALLS=true`, exact `VIDEO_LIVE_SMOKE_TEST=true` for the first provider smoke, provider credentials, 8–12-second audio, and exactly one first result in `src/lala_workflow/video/runner.py` and `src/lala_workflow/video/cli.py`
- [X] T037 [US2] Run the User Story 2 mocked test slice and append checkpoint commands, outcomes, paid-call count, and blockers in `specs/002-lala-video-pipeline/tasks.md` and `PROGRESS.md`

**Checkpoint**: One short talking result can be safely proven with a fake and is ready for an explicitly authorized provider smoke test.

---

## Phase 5: User Story 3 — Generate Three Pilot Workflows (Priority: P3)

**Goal**: Generate bounded shot-level alternatives for each pilot preset using exact scripts, approved audio or optional voice synthesis, talking video, and Runway motion/B-roll.

**Independent Test**: Fake providers execute each preset from the same approved fixture inputs, enforce the 3/3 variation maxima and concurrency one, preserve exact script bytes, and create independently reviewable talking and motion outputs without assembling expensive final edits.

### Tests for User Story 3

- [X] T038 [P] [US3] Add failing Runway image-to-video request, model capability, prompt, duration, polling, and download translation tests in `tests/test_runway_motion_provider.py`
- [X] T039 [P] [US3] Add failing approved-WAV bypass and optional provider-neutral voice-synthesis/hash tests in `tests/test_video_voice.py`
- [X] T040 [P] [US3] Add failing product-page, tooltip, and homepage shot-generation integration tests for exact scripts, default variations, concurrency, limits, costs, and partial failures in `tests/test_video_generate.py`
- [X] T041 [P] [US3] Add failing prompt loading, version, digest, and preset-tag resolution tests in `tests/test_video_prompts.py`

### Implementation for User Story 3

- [X] T042 [P] [US3] Implement current official Runway image-to-video translation and task polling for configurable supported models in `src/lala_workflow/providers/runway_video.py`
- [X] T043 [P] [US3] Implement approved-WAV mode and optional provider-neutral voice synthesis with immutable derived-audio provenance in `src/lala_workflow/video/voice.py`
- [X] T044 [P] [US3] Implement versioned prompt loading and digest recording in `src/lala_workflow/video/prompts.py`
- [X] T045 [US3] Implement bounded shot-level talking and motion generation with partial-failure recovery in `src/lala_workflow/video/runner.py`
- [X] T046 [US3] Wire live `video generate --preset product_page|tooltip|homepage` with a reviewed passing `--smoke-run-id` prerequisite while retaining preview-by-default behavior in `src/lala_workflow/video/cli.py`
- [X] T047 [US3] Run all three fake-provider preset integrations and append checkpoint commands, outcomes, paid-call count, and blockers in `specs/002-lala-video-pipeline/tasks.md` and `PROGRESS.md`

**Checkpoint**: All three pilot workflows can independently produce reviewable shot alternatives under mocks and can run live only through explicit gates.

---

## Phase 6: User Story 4 — Compare Alternate Shots Before Final Assembly (Priority: P4)

**Goal**: Let MTL select existing shot alternatives and deterministically assemble up to two final candidates without new provider submissions.

**Independent Test**: Given a human-authored selection manifest and synthetic valid media, assemble two deterministic MP4 candidates through FFmpeg, log exact commands, validate/hash outputs, and prove the fake providers received no calls.

### Tests for User Story 4

- [X] T048 [P] [US4] Add failing selection-manifest validation and nonexistent/cross-run/duplicate-shot rejection tests in `tests/test_video_selection.py`
- [X] T049 [P] [US4] Add failing FFmpeg concat, trim, scale, letterbox, audio normalization/replacement, transition, timeout, and command-log tests in `tests/test_video_ffmpeg.py`
- [X] T050 [P] [US4] Add a failing no-provider assembly integration with deterministic names, hashes, provenance, and edit limits in `tests/test_video_assemble.py`

### Implementation for User Story 4

- [X] T051 [P] [US4] Implement immutable human shot-selection manifest loading and source-run validation in `src/lala_workflow/video/selection.py`
- [X] T052 [P] [US4] Implement argument-safe deterministic FFmpeg probing and assembly operations in `src/lala_workflow/editing/ffmpeg.py`
- [X] T053 [US4] Implement final-edit orchestration, output validation, hashes, cost updates, and command logging in `src/lala_workflow/video/assembly.py`
- [X] T054 [US4] Wire `video assemble --run-id --selection` with a two-edit maximum and no provider construction in `src/lala_workflow/video/cli.py`
- [X] T055 [US4] Run the mocked FFmpeg/assembly test slice and append checkpoint commands, outcomes, paid-call count, and blockers in `specs/002-lala-video-pipeline/tasks.md` and `PROGRESS.md`

**Checkpoint**: Selected shots can be compared as deterministic final candidates without paid generation.

---

## Phase 7: User Story 5 — Review and Promote a Final Candidate (Priority: P5)

**Goal**: Report technical evidence, preserve blank human judgments, and copy only an explicitly review-ready candidate into an approved location with provenance.

**Independent Test**: A candidate with completed required review fields is copied to the deterministic approved name and receives a provenance sidecar while its source and reviewed CSV remain byte-identical; blank, malformed, or ambiguous reviews fail without writes.

### Tests for User Story 5

- [X] T056 [P] [US5] Add failing exact QA-header, one-row-per-candidate, blank-human-field, no-rewrite, and readiness tests in `tests/test_video_review.py`
- [X] T057 [P] [US5] Add failing run-summary, cost serialization, missing-price, partial-failure, and no-fabrication tests in `tests/test_video_reporting.py`
- [X] T058 [P] [US5] Add failing deterministic candidate/approved naming, copy-only promotion, provenance, collision, and rejection tests in `tests/test_video_promotion.py`

### Implementation for User Story 5

- [X] T059 [P] [US5] Implement exact QA CSV generation and strict reviewed-row parsing without automated subjective decisions in `src/lala_workflow/video/review.py`
- [X] T060 [P] [US5] Implement evidence-backed summary and aggregate cost reporting for complete and partial runs in `src/lala_workflow/video/reporting.py`
- [X] T061 [US5] Implement review-gated copy-only promotion with deterministic approved names and provenance sidecars in `src/lala_workflow/video/promotion.py`
- [X] T062 [US5] Wire `video report --run-id` and `video promote --run-id --candidate --approved-version` in `src/lala_workflow/video/cli.py`
- [X] T063 [US5] Add an append-only reviewed-fixture workflow that never edits an existing run record in `tests/fixtures/video/review/README.md`
- [X] T064 [US5] Run the reporting/review/promotion test slice and append checkpoint commands, outcomes, paid-call count, and blockers in `specs/002-lala-video-pipeline/tasks.md` and `PROGRESS.md`

**Checkpoint**: Technical reporting and human-gated promotion are independently usable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integrate governance, operator guidance, full offline verification, integrity checks, and final consistency evidence.

- [X] T065 [P] Update architecture, input placement, CLI examples, live gates, staged approvals, QA, and external-blocker guidance in `README.md`
- [X] T066 [P] Update repository scope, immutable video inputs, provider boundaries, test commands, live restrictions, and Goal 2 definition of done in `AGENTS.md`
- [X] T067 Update Goal 2 status, provider decisions, paid-call count, verification evidence, immutable-source digests, and precise missing-input blockers without overwriting existing user history in `PROGRESS.md`
- [X] T068 Run `uv sync --extra dev`, the full offline test suite, static-image regression previews, a real local FFmpeg fixture export, the dry-run 60-second budget check, and all feasible video validation/preview commands; record evidence in `specs/002-lala-video-pipeline/tasks.md`
- [X] T069 Run secret-pattern scans, verify no tracked runtime media or credentials, compare approved-anchor pre/post SHA-256 digests, and record evidence in `specs/002-lala-video-pipeline/tasks.md`
- [X] T070 Reconcile FR-001–FR-035 and SC-001–SC-014 against code, tests, commands, and task status; append any missing work to `specs/002-lala-video-pipeline/tasks.md`
- [X] T071 Run final `git diff --check`, inspect the complete diff for unrelated-user-change preservation, and record the completion or exact external blockers in `specs/002-lala-video-pipeline/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all stories.
- **User Story 1 (Phase 3)**: Depends on Foundational and is the MVP.
- **User Story 2 (Phase 4)**: Depends on the validation/evidence core in User Story 1.
- **User Story 3 (Phase 5)**: Depends on User Story 2 execution safety; its motion and voice adapters remain independently testable.
- **User Story 4 (Phase 6)**: Depends on candidate/media records from User Story 3 but never submits provider work.
- **User Story 5 (Phase 7)**: Depends on candidate records and deterministic names; reporting portions can be tested earlier.
- **Polish (Phase 8)**: Depends on every desired story.

### User Story Dependency Graph

```text
Setup -> Foundation -> US1 Preview -> US2 Talking Smoke -> US3 Pilot Shots
                                                               |
                                                               v
                                                        US4 Assembly -> US5 Review/Promotion
```

### Within Each User Story

- Write story tests first and confirm the intended failures.
- Implement entities/adapters before orchestration.
- Implement orchestration before CLI wiring.
- Run the independent story test before advancing.
- A provider task ID is a durable idempotency boundary; never resubmit after it exists.

### Parallel Opportunities

- T003–T005 can proceed independently after T001.
- T006–T008 and T011–T012, T014–T015 touch distinct foundation files.
- The test tasks at the start of each story can be authored in parallel.
- HeyGen and restricted Runway talking adapters (T032–T033) are independent.
- Runway motion, voice handling, and prompt loading (T042–T044) are independent.
- Selection and FFmpeg layers (T051–T052) are independent.
- QA/reports and promotion tests/implementations use distinct files until CLI integration.

---

## Parallel Examples

### User Story 1

```text
T018 tests/test_video_config.py
T019 tests/test_video_planning.py
T020 tests/test_video_dry_run.py
```

### User Story 2

```text
T028 tests/test_heygen_talking_provider.py -> T032 src/lala_workflow/providers/heygen_talking.py
T029 tests/test_runway_talking_provider.py -> T033 src/lala_workflow/providers/runway_talking.py
```

### User Story 3

```text
T038 tests/test_runway_motion_provider.py -> T042 src/lala_workflow/providers/runway_video.py
T039 tests/test_video_voice.py -> T043 src/lala_workflow/video/voice.py
T041 tests/test_video_prompts.py -> T044 src/lala_workflow/video/prompts.py
```

### User Story 4

```text
T048 tests/test_video_selection.py -> T051 src/lala_workflow/video/selection.py
T049 tests/test_video_ffmpeg.py -> T052 src/lala_workflow/editing/ffmpeg.py
```

### User Story 5

```text
T056 tests/test_video_review.py -> T059 src/lala_workflow/video/review.py
T058 tests/test_video_promotion.py -> T061 src/lala_workflow/video/promotion.py
```

---

## Requirement Traceability

| Requirement group | Primary tasks |
|---|---|
| Immutable inputs, exact scripts, hashes (FR-001–FR-008) | T001, T007–T011, T018, T024, T039, T043, T077, T079–T082 |
| Three presets, composition, provider separation (FR-009–FR-015) | T003–T004, T006, T009, T012, T019, T021, T038–T046, T077–T078 |
| Smoke test, variations, selection (FR-016–FR-020) | T028–T037, T040, T045–T051, T076 |
| Deterministic editing and dry-run (FR-021–FR-022) | T018–T027, T048–T055 |
| Live safety, bounded recovery (FR-023–FR-025) | T030, T034, T036, T040, T045–T046 |
| Evidence, costs, output validation/names (FR-026–FR-029) | T013, T020, T022–T025, T031, T034–T035, T050, T053, T057–T060 |
| QA and promotion (FR-030–FR-032) | T023, T056–T064 |
| Secrets, tests, documentation (FR-033–FR-035) | T014–T017, T065–T071, T078 |
| Owner package, legacy keyframe, canonical voice sources (FR-036–FR-038) | T079–T084 |
| Measurable success criteria (SC-001–SC-016) | T027, T037, T047, T055, T064, T068–T071, T082–T084 |

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete User Story 1.
3. Validate all three presets with synthetic approved-status test fixtures and prove repository pending inputs fail closed.
4. Only then add live-capable adapters and staged execution.

### Incremental Delivery

1. Safe preview and evidence bundle.
2. One-result talking smoke path under mocks.
3. Three pilot shot-generation workflows under mocks.
4. Local assembly with explicit shot selection.
5. Human review reporting and copy-only promotion.
6. An actual first provider smoke test only after real approved inputs, credentials, budget permission, and prior-stage approval exist.

## Notes

- Approved anchors, keyframes, voice sources/audio, and MTL scripts are never modified.
- Human QA and MTL readiness start blank; tests may use clearly labeled reviewed fixture copies.
- Production manifests stay pending until authoritative files and recorded approvals are supplied.
- No task authorizes a live call by itself; runtime gates still apply.
- If production inputs or explicit paid-call permission remain unavailable, complete all offline tasks and report `BLOCKED_EXTERNAL` rather than inventing inputs or treating the dependency as a code failure.

## Implementation Evidence

### User Story 1 checkpoint — 2026-08-19

- `uv run pytest tests/test_video_config.py tests/test_video_planning.py tests/test_video_dry_run.py -q`: 16 passed.
- Production `video validate`: exit 4; reported pending approved keyframe, product-page/tooltip/homepage MTL metadata/files, and approved voice/audio together; run-directory count remained 24 before and after.
- Synthetic fixture previews: deterministic product-page/tooltip/homepage provider-call counts 9/3/12; single-shot count 3; exactly 13 artifacts; zero provider submissions. Product-page and homepage each use one full-script talking performance with a deterministic closing reprise so approved audio is not duplicated.
- Paid video calls: 0.

### User Story 2 checkpoint — 2026-08-19

- `uv run pytest tests/test_heygen_talking_provider.py tests/test_runway_talking_provider.py tests/test_video_live_execution.py tests/test_video_talking_smoke.py -q`: 14 passed.
- Cumulative Goal 2 slice: 43 passed; one mocked live smoke submission produced one validated MP4, one blank QA row, and exactly 13 evidence artifacts.
- Guard/recovery evidence: exact environment flags and credential, 8–12-second audio, one result, idempotency-safe pre-ID retry only, no resubmission after task ID, bounded timeout/download retry, and ambiguous-submit fail-closed behavior all verified.
- Paid video calls: 0; all clients and media were local fakes.

### User Story 3 checkpoint — 2026-08-19

- `uv run pytest tests/test_video*.py tests/test_heygen_talking_provider.py tests/test_runway_talking_provider.py tests/test_runway_motion_provider.py -q`: 54 passed.
- Simulated product-page/tooltip/homepage generation produced 9/3/12 sequential shot-level submissions with three talking alternatives, at most three motion alternatives, exact script/audio hashes, one blank QA row per output, partial-failure evidence, and no final assembly.
- An unreviewed smoke run was rejected before either fake provider received a call; approved-WAV bypass and optional cloned-voice derived WAV provenance both passed.
- Paid video calls: 0.

### User Story 4 checkpoint — 2026-08-19

- `uv run pytest tests/test_video_selection.py tests/test_video_ffmpeg.py tests/test_video_assemble.py -q`: 9 passed; cumulative Goal 2 suite: 63 passed.
- A real local FFmpeg integration produced `lady-lala-product-page-candidate-v001.mp4` and `v002.mp4` from an immutable selection, logged cut/crossfade commands, validated/hashes both MP4s, wrote exactly 13 assembly artifacts and two blank QA rows, and left the source generation run byte-identical.
- Provider submissions during assembly: 0; paid video calls: 0.

### User Story 5 checkpoint — 2026-08-19

- `uv run pytest tests/test_video_review.py tests/test_video_reporting.py tests/test_video_promotion.py -q`: 7 passed; cumulative Goal 2 suite: 70 passed.
- Exact QA rows begin blank, reviewed rows are parsed read-only, reports preserve unknown costs as null, and review-gated promotion copies hash-verified final candidates to monotonically versioned approved names with complete provenance while refusing collisions.
- Paid video calls: 0.

## Phase 9: Convergence

- [X] T072 CRITICAL Require human-reviewed QA as a separate immutable input for smoke approval and final promotion so run evidence is never rewritten per Constitution II, FR-026, US4/AC3, and US5 (contradicts)
- [X] T073 Prefer an approved script-matched WAV in either voice mode and support provider-neutral synthesized audio for the bounded talking smoke flow per FR-004 and FR-016 (partial)
- [X] T074 Finalize a complete sanitized thirteen-artifact failure bundle when voice synthesis or talking-smoke execution fails after run allocation per FR-026 and FR-034 (partial)
- [X] T075 Enforce strictly monotonic explicit approved-video versions and remove both media and provenance on any incomplete promotion per FR-029, FR-032, and SC-012 (partial)

### Convergence remediation checkpoint — 2026-08-19

- Focused T072–T075 suite: 28 passed; final full offline suite: 145 passed in 17.44 seconds.
- Real local FFmpeg and all-presets preview budget slice: 5 passed in 2.01 seconds; static 10/5/5 previews and validation passed.
- Production Goal 2 validate and all three preview commands failed closed with exit 4 and left the run count unchanged at 33.
- All five approved-anchor hashes match baseline; credential/Bearer scans, tracked-runtime-media checks, compilation, and `git diff --check` passed.
- Paid video calls: 0. External production input, live permission, budget, credentials, and human approvals remain precisely blocked.
- Follow-up convergence checked 35 FRs, 14 SCs, 16 acceptance scenarios, seven plan decisions,
  and five constitution principles with zero remaining findings; it left `tasks.md` byte-identical.
- Final diff review preserved the pre-existing Goal 1 specification status edit and found no
  unrelated source mutation, whitespace error, tracked credential, or tracked runtime media.

## Phase 10: Convergence

- [X] T076 Add a reviewed post-first-smoke talking-validation path that executes up to three talking-only alternatives while preserving the exact one-result first live gate per FR-016 and FR-017 (partial)
- [X] T077 Implement and wire a concrete provider-neutral HeyGen Starfish `VoiceProvider` for approved cloned-voice Mode B, including exact-script translation, safe audio download/WAV conversion, credentials, evidence, and offline tests per FR-004 and FR-014 (partial)
- [X] T078 Refresh official voice-provider research, provider/CLI contracts, immutable reviewed-copy documentation, verification evidence, and final regression/security checks per plan: official-provider evidence and append-only storage (partial)

### Convergence remediation checkpoint — 2026-08-19 (Phase 10)

- Reviewed expansion preserves the first-live one-result guard, requires a successful smoke and
  immutable human QA copy, and then executes at most three talking-only alternatives sequentially.
- Approved cloned-voice Mode B now has a concrete HeyGen Starfish adapter with exact-script
  translation, bounded synchronous request/download/conversion, validated PCM WAV output,
  provider-request provenance, and credential redaction; approved per-script WAVs still win.
- Focused T076–T078 suite: 36 passed; final full offline suite: 152 passed in 18.88 seconds.
- Dependency sync, compilation, static validation, 10/5/5 dry runs, five-anchor hash comparison,
  runtime/source secret scans, tracked-runtime-media scan, and `git diff --check` passed.
- Goal 2 production validate and all three previews exited 4 with the complete authoritative-input
  blocker and left the run count unchanged at 36. Paid video calls: 0.

## Phase 11: Convergence

- [X] T079 Add failing tests for strict `owner_supplied_legacy_asset` provenance, unchanged generated-promotion requirements, canonical voice-source manifest/hash/media validation, and canonical-source/non-narration separation per FR-034, FR-036, and FR-037 (missing)
- [X] T080 Implement a provider-neutral keyframe provenance union and a narrowly audited legacy validation branch without weakening ordinary Goal 1 promotion validation per FR-003 and FR-036 (missing)
- [X] T081 Require per-script authoritative MTL source references and validate hash-pinned canonical Lady LaLa source WAV metadata while keeping voice approval pending per FR-006 and FR-037 (partial)
- [X] T082 Copy the owner-supplied keyframe, three exact-byte scripts, and eight canonical voice WAVs into existing authoritative locations; register package/member provenance and verify pre/post digests without changing approved anchors or run evidence per FR-001, FR-038, and SC-015 (missing)
- [X] T083 Update Goal 2 data/configuration contracts, research, quickstart, operator guidance, and append-only progress evidence to distinguish imported canonical sources from the remaining approved voice prerequisite per FR-035 and SC-016 (partial)
- [X] T084 Run the full offline suite, production `video validate`, tooltip talking dry-run, approved-source/package hash comparisons, no-run/provider-call checks, secret/runtime scans, and `git diff --check`; record the sole precise Voice blocker and zero paid calls per FR-034, SC-015, and SC-016 (missing)

### Authoritative input import checkpoint — 2026-08-19 (Phase 11)

- `lala-goal2-authoritative-inputs-v1.0.0.zip` passed archive integrity and every
  `SHA256SUMS.txt` member check; received ZIP SHA-256 is
  `ecb747c66aca39e78de9718439a81c2bff603b3d1992259a43384327071f5282`.
- No genuine Goal 1 promoted keyframe existed. The owner-selected landscape source was copied
  byte-exactly and registered as `owner_supplied_legacy_asset`; generated-promotion validation
  still requires its original run/output/reviewer/time evidence.
- Three exact-byte MTL scripts and eight canonical clone-source WAVs were copied into the existing
  authoritative locations. Every source/destination `cmp` and SHA-256 check passed. The WAVs
  remain outside `script_audio` and do not satisfy voice approval.
- New/updated focused slice: 31 passed. Final full offline suite: 160 passed in 19.48 seconds;
  compilation and static-image validation/10/5/5 previews passed at
  `LALA-RUNWAY-20260819-050155-BASELINE-IDENTITY-001`,
  `LALA-RUNWAY-20260819-050155-HOME-DECOR-001`, and
  `LALA-RUNWAY-20260819-050155-PRODUCT-PAGE-CLEAN-001`.
- Production `video validate`, tooltip talking-smoke dry-run, and all three Goal 2 pilot previews
  each exited 4 with the sole approved-voice blocker; the run count remained 42 before and after.
- All five approved-anchor hashes match the Checkpoint 1 baseline. Source/runtime secret scans,
  tracked runtime-media checks, compilation, and `git diff --check` passed.
- `BLOCKED_EXTERNAL: Goal 2 still requires a real approved HeyGen Starfish/private Lady LaLa voice
  profile or approved per-script Lady LaLa narration WAVs.`
- Paid calls made: 0 for the Goal 2 authoritative-input import and offline validation.
