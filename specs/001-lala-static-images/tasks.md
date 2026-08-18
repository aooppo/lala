# Tasks: Reproducible Lady LaLa Static Images

**Input**: Design documents from `/specs/001-lala-static-images/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required by FR-027 and the project constitution. Tests precede their implementation.

**Organization**: Tasks are grouped by user story and preserve traceability to independent tests.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the package, runtime dependencies, configuration source artifacts, and safe
runtime directories.

- [X] T001 Create the Python package/test directory structure and package entry points in `src/lala_workflow/__init__.py`, `src/lala_workflow/__main__.py`, `src/lala_workflow/providers/__init__.py`, `tests/unit/`, `tests/integration/`, and `tests/fixtures/`
- [X] T002 Define Python 3.11+, pinned Runway SDK, YAML/image dependencies, pytest settings, and console entry point in `pyproject.toml`
- [X] T003 [P] Add Python, secret, runtime run/output, cache, editor, and macOS exclusions in `.gitignore` and safe placeholders in `runs/.gitkeep`, `outputs/.gitkeep`, `outputs/approved_keyframes/.gitkeep`, and `assets/derived/.gitkeep`
- [X] T004 [P] Add secret-free live-call environment documentation in `.env.example`
- [X] T005 [P] Map the three authority anchors and two QA-only references without modifying sources in `configs/anchor-manifest.yaml`
- [X] T006 [P] Define provider versions/capabilities and bounded defaults in `configs/generation.yaml`
- [X] T007 [P] Define baseline/product presets in `configs/look-presets.yaml` and home-decor preset in `configs/scene-presets.yaml`
- [X] T008 [P] Write versioned, tagged prompt templates in `prompts/baseline-identity-v1.txt`, `prompts/home-decor-v1.txt`, and `prompts/product-page-clean-v1.txt`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build provider-neutral types, hashing, configuration, prompt resolution, and redaction
used by every story.

**⚠️ CRITICAL**: No user story work begins until this phase passes its tests.

- [X] T009 [P] Write provider-neutral domain serialization and run-ID tests in `tests/unit/test_domain.py`
- [X] T010 [P] Write hash, image-inspection, and immutable-path validation tests in `tests/unit/test_hashing.py`
- [X] T011 [P] Write config/manifest required-role, duplicate-role/tag, preset, and limit tests in `tests/unit/test_config.py`
- [X] T012 [P] Write prompt version, hash, UTF-16 length, and selected-tag resolution tests in `tests/unit/test_prompts.py`
- [X] T013 [P] Write recursive secret/header/data-URI redaction tests in `tests/unit/test_redaction.py`
- [X] T014 Implement provider-neutral anchors, prompts, presets, requests, task results, outputs, run results, and serialization in `src/lala_workflow/domain.py`
- [X] T015 [P] Implement SHA-256, Pillow-backed image inspection, approved-path containment, and data-URI sizing helpers in `src/lala_workflow/hashing.py`
- [X] T016 Implement YAML loading, manifest/preset/default validation, CLI override resolution, and live guard configuration in `src/lala_workflow/config.py`
- [X] T017 Implement versioned prompt loading, hashing, at-tag extraction, and selected-reference validation in `src/lala_workflow/prompts.py`
- [X] T018 Implement recursive sanitizer and redacted exception formatting in `src/lala_workflow/redaction.py`
- [X] T019 Define the runtime-checkable `ImageProvider` protocol and provider exception taxonomy in `src/lala_workflow/providers/base.py`

**Checkpoint**: Foundational tests pass and approved-anchor bytes remain unchanged.

---

## Phase 3: User Story 1 - Validate and Preview a Safe Run (Priority: P1) 🎯 MVP

**Goal**: Validate approved inputs and create complete offline request/run previews for all presets.

**Independent Test**: Execute each preset in dry-run mode and verify exact request counts, hashes,
prompt/reference provenance, eight run artifacts, and zero provider calls.

### Tests for User Story 1

- [X] T020 [P] [US1] Write run storage, collision-safe ID, required artifact, JSONL, and sanitized serialization tests in `tests/unit/test_storage.py`
- [X] T021 [P] [US1] Write dry-run request expansion, sequential seed, count limit, and zero-provider-call tests in `tests/unit/test_runner_dry_run.py`
- [X] T022 [P] [US1] Write validate/generate dry-run CLI contract tests in `tests/integration/test_cli_dry_run.py`

### Implementation for User Story 1

- [X] T023 [US1] Implement append-only run directories, atomic JSON/YAML/text/JSONL writes, and run-ID allocation in `src/lala_workflow/storage.py`
- [X] T024 [US1] Implement manifest/preset/prompt resolution and provider-neutral request expansion for dry runs in `src/lala_workflow/runner.py`
- [X] T025 [US1] Implement `validate` and safe-default `generate --dry-run` command handling in `src/lala_workflow/cli.py` and `src/lala_workflow/__main__.py`
- [X] T026 [US1] Record checkpoint files/tests/results/blockers/paid-call count and anchor hash baseline in `PROGRESS.md`

**Checkpoint**: US1 works independently for 10/5/5 requests and makes no network call.

---

## Phase 4: User Story 2 - Generate Controlled Static Candidates (Priority: P2)

**Goal**: Execute explicitly authorized bounded Runway batches behind the provider-neutral boundary.

**Independent Test**: Use fake SDK/provider responses for all three presets and verify documented
translation, task states, output downloads, retry/timeout limits, normalized errors, and guards.

### Tests for User Story 2

- [X] T027 [P] [US2] Write Runway model/ratio/reference/tag/prompt/seed/output-count capability validation tests in `tests/unit/test_runway_validation.py`
- [X] T028 [P] [US2] Write official SDK field translation and local data-URI boundary tests in `tests/unit/test_runway_translation.py`
- [X] T029 [P] [US2] Write task polling success/failure/cancel/timeout and minimum-interval tests with fake clock/client in `tests/unit/test_runway_polling.py`
- [X] T030 [P] [US2] Write bounded submission/download retry, partial result, and output hash tests in `tests/unit/test_runner_live.py`
- [X] T031 [P] [US2] Write mocked end-to-end live guard/concurrency/result persistence tests in `tests/integration/test_mocked_runway.py`

### Implementation for User Story 2

- [X] T032 [US2] Implement verified Runway capabilities, SDK translation, bounded polling, normalization, and downloads in `src/lala_workflow/providers/runway.py`
- [X] T033 [US2] Implement provider factory, three live-call guards, optional credit ceiling, bounded concurrency/retries/overall timeout, and partial failures in `src/lala_workflow/runner.py`
- [X] T034 [US2] Add live options, blocked/provider exit statuses, and one-image smoke-test cap in `src/lala_workflow/cli.py`
- [X] T035 [US2] Record provider implementation and mocked-test evidence with zero paid calls in `PROGRESS.md`

**Checkpoint**: US2 passes mocked integration; no automated test reaches the network or paid API.

---

## Phase 5: User Story 3 - Review Candidates Without Fabricated Approval (Priority: P3)

**Goal**: Produce complete normalized results, one blank human QA row per output, and summaries.

**Independent Test**: Feed a multi-output normalized result and verify exact review headers/rows,
blank subjective fields, sanitized result JSON/events, and report output.

### Tests for User Story 3

- [X] T036 [P] [US3] Write exact review schema, one-row-per-output, and blank-subjective-field tests in `tests/unit/test_reporting.py`
- [X] T037 [P] [US3] Write result/summary/report command and secret-redaction integration tests in `tests/integration/test_reporting.py`

### Implementation for User Story 3

- [X] T038 [US3] Implement result aggregation, exact QA CSV generation, and sanitized Markdown summaries in `src/lala_workflow/reporting.py`
- [X] T039 [US3] Integrate result/review/summary finalization for dry, success, partial, and failed runs in `src/lala_workflow/runner.py`
- [X] T040 [US3] Implement read-only `report --run-id` command handling in `src/lala_workflow/cli.py`

**Checkpoint**: US3 leaves every human decision blank and creates exactly one row per output.

---

## Phase 6: User Story 4 - Promote a Human-Approved Keyframe (Priority: P4)

**Goal**: Copy only explicitly reviewed, integrity-verified outputs to approved keyframes with full
provenance while preserving originals.

**Independent Test**: Promote an approved fixture, reject unapproved/missing/mismatched cases, and
verify source preservation plus all required promotion metadata.

### Tests for User Story 4

- [X] T041 [P] [US4] Write readiness/reviewer/date/source/hash/collision promotion tests in `tests/unit/test_promotion.py`
- [X] T042 [P] [US4] Write promote CLI success and rejection integration tests in `tests/integration/test_promote_cli.py`

### Implementation for User Story 4

- [X] T043 [US4] Implement truthy review parsing, integrity validation, no-overwrite copy, and promotion JSON in `src/lala_workflow/reporting.py`
- [X] T044 [US4] Implement `promote --run-id --output-id` command handling in `src/lala_workflow/cli.py`

**Checkpoint**: US4 promotes only human-ready rows and leaves source run/output bytes untouched.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Complete operating guidance, comprehensive offline evidence, and final requirement audit.

- [X] T045 [P] Replace the placeholder project rules with purpose, immutable anchors, boundaries, test gates, paid-call restrictions, and Definition of Done in `AGENTS.md`
- [X] T046 [P] Document installation, environment, anchors, configuration, presets, dry/live workflows, QA, promotion, troubleshooting, abstraction, and cost controls in `README.md`
- [X] T047 [P] Add shared fake provider/SDK/image/run fixtures with no credentials or network behavior in `tests/conftest.py` and `tests/fixtures/`
- [X] T048 Run and fix the complete offline test suite and record exact results in `PROGRESS.md`
- [X] T049 Execute all three CLI dry runs, inspect all required run artifacts, and record run IDs/evidence in `PROGRESS.md`
- [X] T050 Recompute and compare all five approved-anchor hashes and scan source/tests/run metadata for secrets in `PROGRESS.md`
- [X] T051 Review final files against FR-001–FR-030, SC-001–SC-010, provider/CLI contracts, and constitution; record gaps or completion evidence in `PROGRESS.md`
- [X] T052 Document the live one-image smoke-test outcome or exact `BLOCKED_EXTERNAL` condition without making an unauthorized paid call in `PROGRESS.md`

---

## Phase 8: Goal Completion Audit Remediation

**Purpose**: Re-read the authoritative goal, strengthen weak evidence, and reconverge the current
implementation against every explicit Definition of Done item.

- [X] T053 Revalidate the live official Runway OpenAPI, generated API reference, polling guidance, PyPI release, and installed SDK signatures in `specs/001-lala-static-images/research.md`
- [X] T054 Fix live `FAILED`/`PARTIAL` CLI exit status behavior and add contract coverage in `src/lala_workflow/cli.py` and `tests/integration/test_cli_dry_run.py`
- [X] T055 Add explicit missing-anchor, full-result serialization, and test-suite network-isolation evidence in `tests/unit/test_config.py`, `tests/unit/test_domain.py`, and `tests/conftest.py`
- [X] T056 Re-run full offline tests, validation, three dry runs, live-guard rejection, hashes, artifact inspection, scope inventory, and security scans; record evidence in `PROGRESS.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately; independent source/config tasks marked `[P]` may run in parallel.
- **Foundational (Phase 2)**: Depends on setup and blocks all stories.
- **US1 (Phase 3)**: Depends on foundational and provides the required safe MVP.
- **US2 (Phase 4)**: Depends on foundational plus US1 run storage/request expansion.
- **US3 (Phase 5)**: Depends on domain/storage and can be developed with fake result fixtures; final runner integration follows US2.
- **US4 (Phase 6)**: Depends on US3's review/result contracts.
- **Polish (Phase 7)**: Depends on all implementation stories.
- **Completion audit (Phase 8)**: Depends on polish and reconverges the delivered state against the
  authoritative goal.

### Requirement Traceability

| Story/phase | Primary requirements |
|-------------|----------------------|
| Setup/Foundation | FR-001–FR-014, FR-018, FR-027, FR-030 |
| US1 | FR-015, FR-019, FR-026; SC-001–SC-003, SC-006, SC-007 |
| US2 | FR-006–FR-017, FR-020–FR-021; SC-002, SC-005, SC-007, SC-010 |
| US3 | FR-018–FR-023, FR-026; SC-003–SC-004, SC-009 |
| US4 | FR-024–FR-026; SC-008 |
| Polish | FR-027–FR-030; all success criteria and governance evidence |
| Completion audit | FR-004, FR-013–FR-014, FR-018, FR-027–FR-029; SC-005, SC-009–SC-010 |

### Parallel Opportunities

- T003–T008 can be authored independently after T001/T002 establish paths.
- T009–T013 test separate foundational modules in parallel; T015 and T018 implement separate files.
- T020–T022, T027–T031, T036–T037, and T041–T042 are file-independent test tasks.
- T045–T047 can proceed in parallel after behavior stabilizes.

## Parallel Examples

### User Story 1

```text
T020: tests/unit/test_storage.py
T021: tests/unit/test_runner_dry_run.py
T022: tests/integration/test_cli_dry_run.py
```

### User Story 2

```text
T027: tests/unit/test_runway_validation.py
T028: tests/unit/test_runway_translation.py
T029: tests/unit/test_runway_polling.py
T031: tests/integration/test_mocked_runway.py
```

### User Stories 3 and 4

```text
T036: tests/unit/test_reporting.py
T037: tests/integration/test_reporting.py
T041: tests/unit/test_promotion.py (after review schema is fixed)
T042: tests/integration/test_promote_cli.py (after review schema is fixed)
```

## Implementation Strategy

### MVP First

1. Complete setup and foundational modules/tests.
2. Complete US1 and prove all three offline preset previews.
3. Preserve this safe usable increment before enabling any live path.

### Incremental Delivery

1. US1: deterministic validation and dry-run evidence.
2. US2: bounded provider integration using fakes first.
3. US3: human review and reporting.
4. US4: reviewed keyframe promotion.
5. Polish: docs, full suite, three dry runs, hashes, secret scan, final audit.
6. Completion audit: authoritative-goal reread, evidence strengthening, and final reconvergence.

## Format Validation

All 56 task entries use the required checkbox, sequential ID, optional `[P]`, required story label
within story phases, and explicit repository file paths.
