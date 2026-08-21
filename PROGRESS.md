# Progress

## Checkpoint 1 — Repository and approved anchors inspected

- Files changed: initial project structure only; approved sources untouched.
- Tests executed: image content/dimension inspection and SHA-256 baseline calculation.
- Result: three authority anchors mapped confidently; two additional images classified QA-only.
- Baseline hashes:
  - `face/lala-face-front.png`: `b33743fb7a4ec88ca178bb2393cdc99ebe20bf96071c0d8e332496b6ff97ac1b`
  - `full_body/lala-red-gown-full-body.png`: `512dade3fe0762ac778da050c613f30250b5d4b6a270188bd85b807fddc331d9`
  - `scene/lala-home-decor-scene.png`: `ab53d9d0551bcf926a41072567493cf640815d99ff92503d9bc111ec3ce7b9ca`
  - `scene/lady-lala-wardrobe-b-v0.6.png`: `174aaec2242d096e4c465a8dce1a96048017d8f3ea72582316c106b41891f074`
  - `scene/lady-lala-character-sheet-exploration-v0.8.png`: `427006aee23b59bdaec4ae2b97d4640b7088bc12e1a0d3105d0c13f83913409d`
- Blockers: none.
- Remaining work: specify, design, implement, and verify the workflow.
- Paid calls made: 0.

## Checkpoint 2 — Spec Kit specification and design

- Files changed: `.specify/`, `.agents/skills/`, `specs/001-lala-static-images/`.
- Tests executed: specification checklist (16/16 complete), task-format validation (52/52).
- Result: constitution v1.0.0, specification, research, plan, data model, CLI/provider contracts,
  quickstart, and dependency-ordered tasks complete.
- Blockers: none.
- Remaining work: implement the dependency-ordered task list and complete acceptance verification.
- Paid calls made: 0.

## Checkpoint 3 — Foundation

- Files changed: `pyproject.toml`, configuration/prompt sources, `src/lala_workflow/domain.py`,
  `hashing.py`, `config.py`, `prompts.py`, `redaction.py`, `providers/base.py`, foundation tests.
- Tests executed: `uv run pytest tests/unit/test_domain.py tests/unit/test_hashing.py
  tests/unit/test_config.py tests/unit/test_prompts.py tests/unit/test_redaction.py -q`.
- Result: 16 passed. One redaction boundary failure was fixed and rerun green.
- Blockers: none.
- Remaining work: implement the four user stories, operating documentation, and final audit.
- Paid calls made: 0.

## Checkpoint 4 — US1 validation and dry run

- Files changed: `src/lala_workflow/storage.py`, `runner.py`, `reporting.py`, `cli.py`, US1 tests.
- Tests executed: `uv run pytest tests/unit/test_storage.py tests/unit/test_runner_dry_run.py
  tests/integration/test_cli_dry_run.py -q` plus real `validate` and ten-request baseline dry run.
- Result: 8 passed. Run `LALA-RUNWAY-20260818-140417-BASELINE-IDENTITY-001` contains all eight
  required artifacts, 10 requests, zero outputs, one header-only review CSV, and two events.
- Blockers: none; live smoke test remains intentionally unattempted until final authorization gate.
- Remaining work: bounded provider execution, human QA/reporting, promotion, and final polish.
- Paid calls made: 0.

## Checkpoint 5 — US2 bounded Runway integration

- Files changed: `src/lala_workflow/providers/runway.py`, live execution in `runner.py`, provider
  capability validation, Runway/live mocked tests.
- Tests executed: `uv run pytest tests/unit/test_runway_validation.py
  tests/unit/test_runway_translation.py tests/unit/test_runway_polling.py
  tests/unit/test_runner_live.py tests/integration/test_mocked_runway.py -q`.
- Result: 18 passed after fixing temporary download suffix handling. Covered documented SDK fields,
  1–3 references, tags, seeds, ratios, 5-second polling, success/failure/cancel/timeout, bounded
  submit/download retries, partial results, downloaded hashes, guards, and secret redaction.
- Guard check: unauthorized real CLI `--live` returned exit 4 with the exact `BLOCKED_EXTERNAL`
  message and created no run directory.
- Blockers: none for offline implementation; live smoke test awaits credentials and explicit paid
  permission.
- Remaining work: human QA/reporting, keyframe promotion, documentation, and final audit.
- Paid calls made: 0.

## Checkpoint 6 — US3 human QA and reporting

- Files changed: completed `src/lala_workflow/reporting.py`, report CLI handling, reporting tests,
  pytest import isolation.
- Tests executed: `uv run pytest tests/unit/test_reporting.py
  tests/integration/test_reporting.py -q`.
- Result: 5 passed. Exact review schema, blank subjective fields, one row per output, summary counts,
  read-only report, path traversal rejection, and serialized secret redaction verified.
- Blockers: none.
- Remaining work: keyframe promotion, full documentation, and final acceptance audit.
- Paid calls made: 0.

## Checkpoint 7 — US4 approved keyframe promotion

- Files changed: keyframe promotion in `src/lala_workflow/reporting.py`, promote CLI handling,
  promotion unit/integration tests.
- Tests executed: `uv run pytest tests/unit/test_promotion.py
  tests/integration/test_promote_cli.py -q`.
- Result: 8 passed. Human readiness/reviewer/timezone gates, source/result agreement, hash integrity,
  collision refusal, source preservation, exact promotion provenance, and CLI behavior verified.
- Blockers: none.
- Remaining work: complete documentation, full-suite/dry-run/hash/security evidence, requirement
  audit, and the authorized live-smoke decision.
- Paid calls made: 0.

## Checkpoint 8 — Final offline acceptance and convergence audit

- Files changed: completed `AGENTS.md`, `README.md`, shared fake fixtures, final runner/CLI contract
  fixes, Spec Kit status/tasks, and this progress record. Approved sources remained untouched.
- Tests executed:
  - `uv run pytest -q`
  - `uv run python -m lala_workflow validate`
  - all three required `generate ... --dry-run` commands at counts 10/5/5
  - all-run artifact inspection, five-file SHA-256 comparison, repository/runtime secret scans,
    static-scope/placeholder inventory, and Spec Kit cross-artifact analysis
- Result: 60 tests passed in 0.57 seconds; validation passed with Runway API `2024-11-06` and SDK
  `5.14.0`. The latest inspected dry runs are:
  - `LALA-RUNWAY-20260818-142552-BASELINE-IDENTITY-001`: 10 requests; face + full-body
  - `LALA-RUNWAY-20260818-142552-HOME-DECOR-001`: 5 requests; face + full-body + scene
  - `LALA-RUNWAY-20260818-142552-PRODUCT-PAGE-CLEAN-001`: 5 requests; face + full-body
- Run evidence: each latest run has exactly eight required files, `DRY_RUN` status, zero outputs,
  two ordered events, and a header-only review CSV. Every run directory currently present passed
  the same eight-file/status/count/reference inspection.
- Anchor integrity: all five SHA-256 values exactly match Checkpoint 1:
  - `face/lala-face-front.png`: `b33743fb7a4ec88ca178bb2393cdc99ebe20bf96071c0d8e332496b6ff97ac1b`
  - `full_body/lala-red-gown-full-body.png`: `512dade3fe0762ac778da050c613f30250b5d4b6a270188bd85b807fddc331d9`
  - `scene/lala-home-decor-scene.png`: `ab53d9d0551bcf926a41072567493cf640815d99ff92503d9bc111ec3ce7b9ca`
  - `scene/lady-lala-wardrobe-b-v0.6.png`: `174aaec2242d096e4c465a8dce1a96048017d8f3ea72582316c106b41891f074`
  - `scene/lady-lala-character-sheet-exploration-v0.8.png`: `427006aee23b59bdaec4ae2b97d4640b7088bc12e1a0d3105d0c13f83913409d`
- Security result: no high-entropy API-key/Bearer pattern appeared in project files; no unredacted
  credential or authorization value appeared in run/output metadata; no runtime Runway secret was
  configured. Only the secret-free `.env.example` is present.
- Requirement audit:
  - FR-001–FR-005: PASS — immutable contained anchors, exact authority mapping, explicit QA-only
    defaults/selection, image validation, and recorded hashes.
  - FR-006–FR-017: PASS — bounded overrides, three presets/prompts, provider-neutral contracts,
    verified Runway translation, offline preview, three live guards, and capped execution.
  - FR-018–FR-026: PASS — redaction, eight-file records/events, downloaded-output hashes, blank
    human QA, integrity-gated promotion, and validate/generate/report/promote commands.
  - FR-027–FR-030: PASS — 60 offline tests, complete operating documentation, checkpoint evidence,
    and static-image-only source inventory.
  - SC-001–SC-009: PASS with the test, dry-run, artifact, hash, simulated-provider, promotion, and
    security evidence above.
  - SC-010: `BLOCKED_EXTERNAL` only; all offline outcomes remain complete.
- Contract/governance audit: CLI and provider contracts match implementation; all 40 FR/SC items
  map to the 52 completed tasks; Spec Kit found zero ambiguity, duplication, unmapped task, or
  constitution conflict. The directory is not a Git repository, so final review used complete file
  inventory/content instead of a Git diff.
- Blocker: `BLOCKED_EXTERNAL: Runway live smoke test requires valid credentials and explicit paid-call permission.`
- Remaining work: only the optional one-image paid smoke test after the owner supplies both valid
  credentials and explicit paid-call authorization.
- Paid calls made: 0.

## Checkpoint 9 — Authoritative goal reread and completion-proof strengthening

- Files changed: `src/lala_workflow/cli.py`, explicit config/result/CLI regression tests, global
  test network guard, fixture documentation, Runway research, Spec Kit tasks, and this record.
- Tests and checks executed:
  - live official `openapi.json`, generated `api.md`, usage guide, PyPI metadata, and installed SDK
    signature inspection
  - `uv run pytest -q` with socket connections automatically rejected
  - `uv run python -m compileall -q src tests`
  - `uv run python -m lala_workflow validate`
  - all three required 10/5/5 dry-run commands and exact eight-artifact inspection
  - an unauthorized one-image `--live` guard invocation with the secret removed and permission false
  - all five approved-image hashes, repository/run secret scans, and static-only source inventory
- Result: 63 tests passed in 0.55 seconds with network disabled. New coverage proves missing source
  anchors fail with the logical anchor name, complete normalized results serialize correctly, and
  live `FAILED`/`PARTIAL` outcomes return provider-failure exit status 3 as the CLI contract requires.
- Current provider evidence: official API version remains `2024-11-06`; endpoint remains
  `POST /v1/text_to_image`; Gen-4 fields/limits, six task states, five-second polling guidance, and
  expiring output URLs match implementation. PyPI still reports `runwayml==5.14.0` as latest.
- Latest dry-run evidence:
  - `LALA-RUNWAY-20260818-143247-BASELINE-IDENTITY-001`: 10 requests; 8 files; face + full-body
  - `LALA-RUNWAY-20260818-143247-HOME-DECOR-001`: 5 requests; 8 files; face + full-body + scene
  - `LALA-RUNWAY-20260818-143247-PRODUCT-PAGE-CLEAN-001`: 5 requests; 8 files; face + full-body
  - all three are `DRY_RUN`, have zero outputs, two ordered events, and header-only review CSVs
- Anchor integrity: all five hashes still exactly match the Checkpoint 1 baseline. Visual inspection
  also reconfirmed the configured face, full-body red-gown, and home-decor scene roles.
- Security/scope result: no credential/high-entropy Bearer match and no unredacted authorization
  value appeared in source or run metadata; no out-of-scope implementation module was found.
- Live guard evidence: the command returned exit 4 with the exact blocker below and left the run
  directory count unchanged at seven, proving it stopped before provider construction/submission.
- Task/requirement status: 56/56 tasks complete; every objective requirement and Definition of Done
  item has direct source, test, run-artifact, hash, documentation, or official-provider evidence,
  except the explicitly conditional paid smoke test.
- Blocker: `BLOCKED_EXTERNAL: Runway live smoke test requires valid credentials and explicit paid-call permission.`
- Remaining work: exactly one paid live image only after valid credentials and explicit owner
  authorization become available; no offline implementation work remains.
- Paid calls made: 0.

## Checkpoint 10 — Authorized Runway live smoke test

- Files changed: this progress record and the active specification status only; implementation,
  configuration, prompts, and approved anchors were unchanged.
- Authorization and cost boundary: local `.env` supplied a non-empty `RUNWAYML_API_SECRET` plus
  exact `RUNWAY_ALLOW_LIVE_CALLS=true` and `RUNWAY_LIVE_SMOKE_TEST=true`. Exactly one
  `gen4_image_turbo` candidate was requested and exactly one provider submission occurred.
- Commands and checks executed:
  - `uv run python -m lala_workflow validate`
  - `uv run python -m lala_workflow generate --preset baseline_identity --model gen4_image_turbo --count 1 --dry-run`
  - `uv run python -m lala_workflow generate --preset baseline_identity --model gen4_image_turbo --count 1 --live`
    after loading the ignored local `.env`
  - `uv run python -m lala_workflow report --run-id LALA-RUNWAY-20260818-154718-BASELINE-IDENTITY-001`
  - `uv run pytest -q` and all three required 10/5/5 dry-run commands
- Result: live run `LALA-RUNWAY-20260818-154718-BASELINE-IDENTITY-001` completed `SUCCEEDED` in
  22.328 seconds with one request, one downloaded output, zero errors, and one paid call. Its run
  directory contains all eight required records; the event log contains authorization, one submit
  attempt, task submission, polling, terminal success, download, and completion events.
- Output evidence: `outputs/LALA-RUNWAY-20260818-154718-BASELINE-IDENTITY-001/output-001.png` is a
  readable 1088 x 1456 RGB PNG with SHA-256
  `bfb7117235386c6ec0c71c12b302c2621e431ecc03e03be6d717a0a482b729a8`. The report command reads
  the run successfully and reports provider/model `runway` / `gen4_image_turbo`, one downloaded
  output, zero errors, and one paid call.
- Regression result: 63 tests passed in 0.58 seconds. The required baseline/home/product dry runs
  completed with 10/5/5 requests and zero paid outputs.
- Security and integrity: the live run/output contain neither the configured secret value nor a
  Bearer/authorization pattern. All five approved-anchor SHA-256 values still match Checkpoint 1.
- Blockers: none. SC-010 is now satisfied by the authorized live evidence above.
- Paid calls made: 1 in this checkpoint; 1 total for the project.

## Goal 2 Checkpoint 1 — Video setup and provider-neutral foundation

- Files changed: Goal 2 pending manifests, video presets/provider capability records, versioned
  motion prompts, video/audio/editing package namespaces, provider-neutral domain/protocols,
  immutable script/audio/keyframe validation, append-only video storage primitives, deterministic
  naming, recursive redaction, nested video CLI routing, synthetic test fakes, dependency pins, and
  `specs/002-lala-video-pipeline/tasks.md`.
- Tests executed:
  - `uv run pytest tests/test_video_provider_contracts.py tests/test_video_scripts.py tests/test_video_media_validation.py tests/unit/test_redaction.py -q`
  - `uv run pytest tests/unit tests/integration -q`
- Result: 15 targeted tests and all 63 Goal 1 regression tests passed. The Goal 2 production
  manifests remain explicitly pending; no keyframe, voice media, or MTL copy was invented.
- Blockers: authoritative approved keyframe/provenance, approved voice or per-script WAVs, and all
  three MTL script files/versions/hashes are not present yet. This does not block offline code or
  mocked integration work.
- Remaining work: implement safe preview/evidence, provider adapters and live guards, pilot shot
  workflows, deterministic assembly, review/promotion, full convergence, and documentation.
- Paid calls made: 0 for Goal 2; no video provider was constructed or contacted.

## Goal 2 Checkpoint 2 — US1 validation, planning, cost preview, and evidence

- Files changed: video prompt loading, deterministic shot planning, approved-WAV resolution,
  source-dated cost estimation, thirteen-artifact reporting, safe preview runner, validation/report
  CLI paths, and US1 unit/mocked integration tests.
- Tests executed: `uv run pytest tests/test_video_config.py tests/test_video_planning.py
  tests/test_video_dry_run.py -q`.
- Result: 16 passed. After the pre-US3 audio-integrity correction, synthetic product-page/tooltip/
  homepage plans resolve 9/3/12 provider calls; single-shot fallback resolves 3. Product-page and
  homepage use one full-script talking performance plus deterministic closing reuse, avoiding a
  duplicate rendering of the same approved WAV. Each accepted preview writes thirteen artifacts,
  byte-exact script evidence, keyframe/audio/anchor hashes, supported estimates, and a header-only
  blank QA sheet while making zero submissions.
- Production guard evidence: `video validate` exited 4, reported the approved keyframe, all three
  MTL script files/metadata, and approved voice/audio blockers together, and left the repository
  run-directory count unchanged at 24.
- Blockers: the authoritative Goal 2 input package is still absent; offline provider and assembly
  implementation can continue.
- Remaining work: talking/motion adapters and bounded live execution, pilot workflows, local
  assembly, review/promotion, documentation, and convergence.
- Paid calls made: 0 for Goal 2.

## Goal 2 Checkpoint 3 — US2 one-result talking smoke under mocks

- Files changed: official-contract HeyGen v3 talking adapter, approved-mapping-only Runway avatar
  adapter, bounded execution state machine, streamed/validated video download layer, first-smoke
  live guards, live smoke evidence finalization, and talking-provider mocked tests.
- Tests executed:
  - `uv run pytest tests/test_heygen_talking_provider.py tests/test_runway_talking_provider.py tests/test_video_live_execution.py tests/test_video_talking_smoke.py -q`
  - cumulative Goal 2 targeted slice through US2.
- Result: 14 US2 tests and 43 cumulative Goal 2 tests passed. The simulated live flow produced one
  valid MP4 from one approved-status fixture keyframe/audio pair, exactly thirteen run artifacts,
  one blank QA row, hash/cost/task evidence, and no serialized credential. Tests also prove
  idempotency-safe pre-ID retry only, no resubmission after task ID, ambiguous-submit fail-closed,
  bounded polling/download recovery, and terminal timeout behavior.
- Blockers: an actual provider smoke still requires the real approved input package, credentials,
  exact paid-call permission, and owner review; no live attempt was made.
- Remaining work: Runway motion and all three pilot shot workflows, voice Mode B abstraction,
  deterministic assembly, review/promotion, documentation, and convergence.
- Paid calls made: 0 for Goal 2.

## Goal 2 Checkpoint 4 — US3 three pilot shot workflows under mocks

- Files changed: current Runway image-to-video adapter, approved-WAV/optional cloned-voice
  resolution, full pilot live guards and reviewed-smoke gate, sequential shot-generation
  orchestration, prompt integrity tests, Runway motion tests, and all-preset mocked integrations.
- Tests executed: `uv run pytest tests/test_video*.py tests/test_heygen_talking_provider.py
  tests/test_runway_talking_provider.py tests/test_runway_motion_provider.py -q`.
- Result: 54 passed. Product-page/tooltip/homepage plans produced 9/3/12 simulated provider tasks,
  respectively, with three talking alternatives, at most three motion alternatives per applicable
  shot, concurrency one, exact script/audio/keyframe/prompt hashes, per-output blank QA rows,
  cost/task evidence, and bounded partial-failure recovery. An unreviewed smoke was rejected before
  any fake call. One full-script talking performance plus deterministic closing reuse prevents
  duplicate approved-audio rendering in multi-shot presets.
- Blockers: live pilot work still requires a real passing one-result smoke and its reviewed QA,
  plus authoritative inputs, credentials, and explicit paid permission.
- Remaining work: shot selection, FFmpeg assembly, final QA/reporting/promotion, documentation,
  full suite, security/integrity checks, and convergence.
- Paid calls made: 0 for Goal 2.

## Goal 2 Checkpoint 5 — US4 human selection and deterministic assembly

- Files changed: immutable selection-manifest validation, argument-safe FFmpeg editor, local
  assembly orchestration, assembly CLI routing, and selection/FFmpeg/assembly tests.
- Tests executed:
  - `uv run pytest tests/test_video_selection.py tests/test_video_ffmpeg.py tests/test_video_assemble.py -q`
  - cumulative Goal 2 video test selection.
- Result: 9 US4 tests and 63 cumulative Goal 2 tests passed. A real local FFmpeg integration
  normalized selected shots, used the full approved-status fixture WAV exactly once, created a cut
  and logged crossfade candidate named `lady-lala-product-page-candidate-v001.mp4`/`v002.mp4`,
  validated and hashed both MP4s, wrote a separate thirteen-artifact assembly run and two blank QA
  rows, and left the source generation run unchanged. Missing, duplicate, unknown, and cross-run
  selections fail before editing.
- Blockers: production assembly awaits actual selected shots produced after a real reviewed smoke;
  local implementation is complete.
- Remaining work: final review/report/promotion, operating documentation, full regression/security/
  integrity verification, and convergence.
- Paid calls made: 0 for Goal 2; assembly constructs no provider.

## Goal 2 Checkpoint 6 — US5 review, reporting, and approved-video promotion

- Files changed: exact QA review parser, evidence-backed video reports, integrity-gated copy-only
  final-video promotion, report/promote CLI routing, and review/report/promotion tests.
- Tests executed:
  - `uv run pytest tests/test_video_review.py tests/test_video_reporting.py tests/test_video_promotion.py -q`
  - cumulative Goal 2 video test selection.
- Result: 7 US5 tests and 70 cumulative Goal 2 tests passed. QA headers are exact, new human fields
  are blank, review parsing is read-only, unknown pricing remains null, and an explicitly ready
  hash-verified candidate is copied to deterministic approved versions without changing the
  candidate or reviewed CSV. Provenance records the exact MTL script, audio, keyframe/anchors,
  selected shots, providers/models, reviewer, and timestamps; collisions are refused.
- Blockers: real MTL review/promotion awaits real generated candidates; no decision was fabricated.
- Remaining work: documentation, full regression/command/integrity/security verification, Spec Kit
  convergence, and conditional live-stage decision.
- Paid calls made: 0 for Goal 2.

## Goal 2 Checkpoint 7 — Offline-complete video pipeline and convergence remediation

- Files changed: active Goal 2 Spec Kit artifacts; provider-neutral video/audio/editing domains;
  HeyGen talking, restricted Runway talking, and Runway motion adapters; immutable input and
  reviewed-copy validation; append-only thirteen-artifact storage; guarded live orchestration;
  deterministic FFmpeg assembly; reporting/promotion; pending production manifests; tests;
  `README.md`; `AGENTS.md`; and this append-only progress record.
- Final offline verification:
  - `uv sync --extra dev`: resolved 23 packages and checked 22.
  - `uv run pytest -q`: 145 passed in 17.44 seconds with the global network prohibition active.
  - `uv run python -m compileall -q src tests`: passed.
  - real local FFmpeg/assembly plus all-three-preview 60-second check: 5 passed in 2.01 seconds.
  - static-image validation and required dry runs passed with 10/5/5 requests at
    `LALA-RUNWAY-20260819-035448-BASELINE-IDENTITY-001`,
    `LALA-RUNWAY-20260819-035448-HOME-DECOR-001`, and
    `LALA-RUNWAY-20260819-035448-PRODUCT-PAGE-CLEAN-001`.
- Goal 2 production guard evidence: `video validate` and product-page/tooltip/homepage previews each
  exited 4 with the complete missing approved-keyframe, three-script, and voice/audio blocker. Run
  directory count remained 33 before and after, proving no partial production run or provider call.
- Convergence remediation: approved script-matched WAVs now take precedence in either voice mode;
  provider-neutral cloned voice can feed one bounded talking result; smoke/final human QA uses an
  explicit hash-recorded copy under `outputs/reviews/` while run evidence remains blank and
  immutable; post-allocation voice/smoke failures receive all thirteen sanitized artifacts; and
  approved-video promotion is strictly monotonic and cleans both outputs on incomplete provenance.
- Integrity/security: all five approved-anchor SHA-256 values exactly match the Checkpoint 1
  baseline. Credential-value and run/output Bearer/authorization scans returned no matches;
  `.env`, keys, and runtime audio/video are not tracked; `git diff --check`, untracked-text
  whitespace scans, and compilation passed. The pre-existing Goal 1 specification status edit was
  preserved unchanged.
- Goal 2 status: offline implementation and mocked acceptance are complete. Actual production dry
  runs, a live talking smoke, the three rendered pilot videos, and MTL promotion remain external,
  input- and approval-dependent stages rather than code failures.
- Blocker: `BLOCKED_EXTERNAL: Goal 2 production execution requires at least one human-approved Goal
  1 keyframe with matching promotion provenance, authoritative MTL product-page/tooltip/homepage
  script files with versions and SHA-256 values, and approved Lady LaLa per-script WAVs or an
  approved reusable voice/profile. Live work additionally requires provider credentials, exact
  VIDEO_ALLOW_LIVE_CALLS=true, exact VIDEO_LIVE_SMOKE_TEST=true for the first one-result smoke,
  explicit owner budget authorization, and a separate reviewed smoke QA copy before any broader
  generation.`
- Paid calls made: 0 for Goal 2; the repository's previously authorized Goal 1 image call remains
  the only project paid call recorded in this file.

## Goal 2 Checkpoint 8 — Staged talking validation and concrete cloned voice

- Files changed: reviewed post-first-smoke talking validation, HeyGen Starfish voice adapter,
  provider configuration/factory wiring, synthesized-audio task provenance, regression tests,
  official-provider research, CLI/quickstart/operator documentation, Spec Kit traceability, and
  this append-only checkpoint.
- Behavior: the first live video test remains exactly one 8–12-second talking result and still
  requires exact `VIDEO_LIVE_SMOKE_TEST=true`. Only after that result has a successful immutable
  external QA copy may a separate talking-only run execute up to three alternatives, sequentially
  and under the general live guard. Full pilots retain their reviewed-smoke prerequisite.
- Voice Mode B: an approved `heygen_voice` / `starfish` private voice profile can now submit the
  exact immutable script to HeyGen speech generation, download within bounded retries/overall
  timeout, convert to validated PCM WAV, and record provider request ID, script hash, and source
  provenance. A configured approved per-script WAV remains preferred, and no generated WAV is
  promoted implicitly.
- Verification:
  - focused T076–T078 suite: 36 passed in 5.67 seconds.
  - `uv run pytest -q`: 152 passed in 18.88 seconds with network blocked.
  - `uv sync --extra dev` and `uv run python -m compileall -q src tests`: passed.
  - static validation and required 10/5/5 dry runs passed at
    `LALA-RUNWAY-20260819-041224-BASELINE-IDENTITY-001`,
    `LALA-RUNWAY-20260819-041224-HOME-DECOR-001`, and
    `LALA-RUNWAY-20260819-041224-PRODUCT-PAGE-CLEAN-001`; each contains eight artifacts.
  - all five approved-anchor SHA-256 values match the Checkpoint 1 baseline exactly.
  - runtime evidence contains no Bearer/authentication/signed-query material; source contains no
    credential-looking Bearer literal; no derived WAV/MP4 is tracked; `git diff --check` passed.
- Goal 2 production guard evidence: `video validate` plus product-page, tooltip, and homepage
  previews each exited 4 with the complete approved-keyframe, three-script, and voice/audio
  blocker. Run count stayed 36 before and after, proving no partial video run or provider call.
- Blocker: `BLOCKED_EXTERNAL: Goal 2 production execution requires a human-approved Goal 1
  keyframe with matching promotion provenance, authoritative MTL product-page/tooltip/homepage
  scripts with versions and SHA-256 values, and approved per-script Lady LaLa WAVs or an approved
  reusable HeyGen Starfish private voice profile. Any live stage additionally requires local
  credentials, exact VIDEO_ALLOW_LIVE_CALLS=true, explicit owner budget permission, exact
  VIDEO_LIVE_SMOKE_TEST=true for the first one-result smoke, and the required immutable human QA
  copy before expansion or full generation.`
- Paid calls made: 0 for Goal 2; the repository's previously authorized Goal 1 image call remains
  the only project paid call recorded in this file.

## Goal 2 Checkpoint 9 — Final continuation and external-blocker audit

- Files changed: this append-only verification checkpoint only; application code, approved inputs,
  and completed Spec Kit tasks were unchanged during the audit.
- Verification:
  - `uv sync --extra dev`: resolved 23 packages and checked 22.
  - `uv run pytest -q`: 152 passed in 18.73 seconds with the global network prohibition active.
  - `uv run python -m compileall -q src tests`: passed.
  - Goal 1 validation and required 10/5/5 dry runs passed at
    `LALA-RUNWAY-20260819-042430-BASELINE-IDENTITY-001`,
    `LALA-RUNWAY-20260819-042430-HOME-DECOR-001`, and
    `LALA-RUNWAY-20260819-042430-PRODUCT-PAGE-CLEAN-001`.
  - Goal 2 `video validate`, talking-smoke preview, and all three pilot previews each exited 4 with
    the complete authoritative-input blocker; the run count remained 39 before and after.
  - all five approved-anchor SHA-256 values still exactly match the Checkpoint 1 baseline.
  - runtime credential/Bearer/authorization/signed-query scans, source high-entropy scans, tracked
    runtime-media checks, task-format/completion checks, and `git diff --check` passed.
- Convergence: 35 functional requirements, 14 success criteria, 16 acceptance scenarios, seven
  plan decisions, and five constitution principles were rechecked. No missing, partial,
  contradictory, or unrequested implementation finding remains; all 78 tasks stay complete.
- Blocker: `BLOCKED_EXTERNAL: Goal 2 production execution requires a human-approved Goal 1
  keyframe with matching promotion provenance, authoritative MTL product-page/tooltip/homepage
  scripts with versions and SHA-256 values, and approved per-script Lady LaLa WAVs or an approved
  reusable HeyGen Starfish private voice profile. Any live stage additionally requires local
  credentials, exact VIDEO_ALLOW_LIVE_CALLS=true, explicit owner budget permission, exact
  VIDEO_LIVE_SMOKE_TEST=true for the first one-result smoke, and the required immutable human QA
  copy before expansion or full generation.`
- Paid calls made: 0 for Goal 2 in this checkpoint and in total; the repository's previously
  authorized Goal 1 image call remains the only project paid call recorded in this file.

## Goal 2 Checkpoint 10 — Authoritative input import and offline validation

- Package verification: `/Users/tj/Downloads/lala-goal2-authoritative-inputs-v1.0.0.zip` passed
  `unzip -t`, all package `SHA256SUMS.txt` checks, safe target-existence checks, and has received
  SHA-256 `ecb747c66aca39e78de9718439a81c2bff603b3d1992259a43384327071f5282`.
- Keyframe decision: no genuine Goal 1 promoted keyframe exists in
  `assets/approved_keyframes/` or `outputs/approved_keyframes/`. The owner-selected
  `lady-lala-home-context-v0.7.png` was copied to `assets/approved_keyframes/` byte-exactly and
  registered as `owner_supplied_legacy_asset`, with package/name/hash/source-path and owner-request
  provenance only. No Goal 1 run/output, provider task, prompt/model, reviewer, or approval time
  was invented. Generated-promotion tests remain strict.
- Script import: `assets/scripts/product-page.txt`, `tooltip.txt`, and `homepage.txt` are exact
  package copies at version `1.0.0`, attributed to MTL Appendix A with SHA-256 values
  `62cbee3e53ea53627f0e517e4d414183d4ad376fc2764dd8a3ded267ae5d5a08`,
  `1f588cbbd03be867581833caddf6828282b47175ffcf840af9e2c42b1e3d7c6e`, and
  `6aeddc065fd3fe66338ef17b9c5b66dd0f3ae633dd1e1571f9565444461b2475`.
- Voice import: eight byte-exact canonical clone-source WAVs now live under
  `assets/voice/source/` and are hash/media-validated through
  `assets/voice/metadata/canonical-source-manifest-v1.0.0.json`. They remain source material only;
  `script_audio` is empty, `mode`/`approval_status` remain `pending`, and no Starfish `voice_id`
  was fabricated.
- Implementation: added a provider-neutral keyframe provenance union, a narrow legacy branch that
  rejects generated/fabricated claims, per-script `source_reference`, canonical PCM WAV manifest
  validation, and regression tests proving canonical sources do not satisfy narration/profile
  approval. Goal 2 Spec Kit artifacts, configuration contracts, quickstart, research, README, and
  Phase 11 tasks were updated traceably.
- Verification:
  - focused import/validation slice: 31 passed.
  - `uv run pytest -q`: 160 passed in 19.48 seconds with network blocked.
  - `uv run python -m compileall -q src tests`: passed.
  - Goal 1 validation and 10/5/5 dry runs passed at
    `LALA-RUNWAY-20260819-050155-BASELINE-IDENTITY-001`,
    `LALA-RUNWAY-20260819-050155-HOME-DECOR-001`, and
    `LALA-RUNWAY-20260819-050155-PRODUCT-PAGE-CLEAN-001`.
  - Goal 2 `video validate`, tooltip talking-smoke dry-run, and product-page/tooltip/homepage pilot
    previews each exited 4 with the same sole Voice blocker; the run count stayed 42 before/after.
  - all imported members matched their package sources with `cmp` and SHA-256; all five approved
    anchor hashes still match Checkpoint 1; secret/signed-query/runtime-media scans and
    `git diff --check` passed.
- Blocker: `BLOCKED_EXTERNAL: Goal 2 still requires a real approved HeyGen Starfish/private Lady
  LaLa voice profile or approved per-script Lady LaLa narration WAVs.`
- Live readiness: not ready. A real approved Starfish/private profile or three approved
  script-matched narration WAVs must be supplied before the separately required credentials,
  budget permission, exact live flags, and staged human review can become relevant.
- Paid calls made: 0 for this import and offline-validation checkpoint; the earlier authorized
  Goal 1 image call remains outside this Goal 2 task.

## Goal 2 Checkpoint 11 — Production-readiness completion and read-only Voice Verify

- Provider contracts: HeyGen asset uploads now use streamed `multipart/form-data` with the
  canonical `file` field, one `x-api-key` header, content/endpoint/mime-scoped idempotency, bounded
  `409 request_in_progress`/`429` handling, current `failure_code`/`failure_message` fields, and
  run-local asset reuse without reusing video tasks. Runway translation omits optional empty prompt
  text, enforces the 5 MB prompt-image bound, and preserves estimated versus terminal actual
  credits.
- Independent motion stage: `video motion-smoke-test` now works without voice/script approval,
  supports the exact one-result five-second `gen4_turbo` gate at no more than 25 credits, records
  task/cost/hash/FFprobe data, first/middle/last frames, a contact sheet, and a blank QA row. The
  command was previewed successfully at `LALA-VIDEO-20260819-142903-MOTION-SMOKE-001` with zero
  submissions.
- Budget/media/graphics: every real live entry point checks an explicit ceiling before provider
  construction and each submission; unknown costs remain null unless explicitly accepted. FFprobe
  now records container, codecs, pixel format, frame rate, audio stream, sample rate, channels,
  and bit rate. Tooltip local graphics are deterministic exact-caption PNG drafts under
  `outputs/graphics/`, actually overlaid by FFmpeg, labeled `REVIEW_READY_DRAFT_ASSETS`, and
  rejected by promotion. `derive-talking-crop` creates only a hashed, unapproved candidate under
  `outputs/keyframes/derived/`. Full live generation additionally requires a reviewed motion-smoke
  copy with matching keyframe hash.
- QA/schema: blank rows now include visual identity, face/age/hair/body, wardrobe/jewelry,
  lip-sync/mouth/teeth/eyes, background/motion, audio identity/pronunciation/script match,
  audio-video sync, technical export, MTL readiness, reviewer/time, and notes. Run evidence remains
  append-only and reviewed copies remain under `outputs/reviews/`.
- Voice Verify: read-only HeyGen verification succeeded as
  `LALA-VOICE-VERIFY-20260819-141633-001` for voice ID
  `7a738e1ced454de6b92d2c76a6ccb8c0`, `Lady LaLa v1`, `female`, `English`, `private`, and
  `starfish`. The safe result was `VERIFIED_FOR_SMOKE`; no voice mutation, speech synthesis, or
  video call occurred. `configs/voice-profile.yaml` records `approved_for_smoke`, verification
  run/time, and API-derived metadata; production approval remains human-gated.
- Offline verification: `uv sync --extra dev` resolved 24 packages/checked 23; full suite
  `uv run pytest -q` passed **181 tests**; compileall passed; Goal 1 validation plus 10/5/5 dry
  runs passed at `LALA-RUNWAY-20260819-142850-BASELINE-IDENTITY-001`,
  `LALA-RUNWAY-20260819-142850-HOME-DECOR-001`, and
  `LALA-RUNWAY-20260819-142850-PRODUCT-PAGE-CLEAN-001`. Goal 2 validation and tooltip,
  product-page, homepage, and talking/motion smoke previews passed with zero provider submissions:
  `LALA-VIDEO-20260819-142902-TOOLTIP-001`,
  `LALA-VIDEO-20260819-142902-PRODUCT-PAGE-001`,
  `LALA-VIDEO-20260819-142903-TOOLTIP-001`,
  `LALA-VIDEO-20260819-142903-HOMEPAGE-001`, and
  `LALA-VIDEO-20260819-142903-MOTION-SMOKE-001`; each run has the exact thirteen-artifact bundle.
- Integrity/security: the five approved-anchor hashes remain exactly the Checkpoint 1 baseline;
  all three script hashes, the imported keyframe hash, and all eight canonical WAV hashes match
  their manifests. Run/output scans found no credentials, Bearer values, authorization headers,
  signed query strings, or data URIs; no runtime media is tracked; CI still disables dotenv,
  installs FFmpeg, compiles, and runs the offline suite; `git diff --check` passed.
- Live truth: `OFFLINE_COMPLETE`; `VOICE_VERIFIED`; `MOTION_SMOKE_SUCCEEDED=NOT_RUN`;
  `TALKING_SMOKE_SUCCEEDED=NOT_RUN`; `TOOLTIP_E2E_SUCCEEDED=NOT_RUN`.
  The exact live flags were not enabled, so no Runway motion task, HeyGen speech request, HeyGen
  talking task, or Tooltip E2E was attempted. Human motion/talking QA, approved brand assets (if
  promotion is required), and the separately reviewed motion-smoke copy remain external gates.
- Paid calls made: **0** for this checkpoint and this Goal 2 task. The read-only Voice Verify is
  not a paid generation call; the earlier authorized Goal 1 image call remains outside Goal 2.

### Post-smoke Runway motion variation generation

- Implemented independent `video motion-smoke-test` and `video motion-generate` paths. Motion
  smoke remains one `gen4_turbo` result at exactly five seconds and a maximum 25-credit cap.
- Post-smoke live generation requires exact video permission, a successful motion smoke, an
  immutable passing review copy, matching keyframe/prompt digests, explicit credit cap, and a
  variation count within the configured 1–5 maximum. It constructs Runway only and writes the
  standard thirteen-artifact bundle with blank human QA rows.
- Added fake-provider coverage for strict bounds, failed review/keyframe/cap/variation gates,
  zero-call dry-runs, independent results, and Runway-only submissions.
- Verification: motion-specific suite passed; live paid calls made: 0. Production live execution
  remains blocked because local credentials and explicit owner authorization are absent.

## Goal 2 Checkpoint 12 — Post-smoke motion variation audit

- Post-smoke motion variations implementation: offline complete. Smoke and post-smoke variation
  remain separate stages; the latter requires an immutable external review copy and never fills
  human QA fields automatically.
- Real motion smoke provider execution: succeeded previously as
  `LALA-VIDEO-20260819-154007-MOTION-SMOKE-001`. Its original `review.csv` and the copied review
  CSV under `outputs/reviews/` remain byte-identical and blank; real motion smoke manual QA:
  pending.
- `motion-generate` live: not run. With the blank real review copy it returns
  `BLOCKED_EXTERNAL: motion smoke manual QA review has incomplete or failing decisions` before
  Runway provider construction.
- The origin/main audit exposed a Python 3.13 protocol-introspection collection error; the
  compatibility repair restores the recorded 181-test baseline. Current collection/full suite:
  188 tests, all passed; seven new tests cover motion variation guards, legacy schema compatibility,
  blank-review zero-call behavior, and complete bundles.
- New paid calls in this task: 0. The smoke dry-run completed with one planned provider call and
  zero paid calls; synthetic reviewed variation dry-runs also use zero submissions.

## Goal 2 Checkpoint 13 — Motion smoke visual rejection and subject-lock prompt revision

- External review copy `outputs/reviews/LALA-VIDEO-20260819-154007-MOTION-SMOKE-001-review.csv`
  records the supplied visual QA decision: identity, face, age, eyes, motion, and MTL readiness
  failed; hair, body proportions, wardrobe, jewelry, background, and technical export passed.
  The original run `review.csv` remains blank and unchanged. Reviewer and review time remain blank
  because the supplied document did not provide those human fields.
- The rejected smoke showed Lady LaLa walking toward the foreground-left, becoming blurred/cropped,
  and leaving the frame. No post-smoke variations were generated and no `mtl_review_ready` approval
  was recorded.
- Added `prompts/home-broll-v2.txt` with a stationary, fully visible subject, locked camera, and
  explicitly prohibited walking, reframing, cropping, lip movement, and scene transitions. Motion
  Smoke remains backward-compatible with the v1 default; the corrected smoke selects v2 explicitly,
  while the homepage establishing shot uses v2 in its preset configuration.
- Verification: `uv run python -m compileall -q src tests`; `uv run pytest -q` (**190 passed**);
  the prescribed v2 Motion Smoke dry-run completed with one planned provider call and
  `submission_count=0`, using the v2 prompt hash. No live provider call was attempted.
- Paid calls made in this checkpoint: **0**. A new live Smoke remains conditional on explicit
  owner authorization, exact video smoke flags, valid Runway credentials, and manual QA.

## Goal 2 Checkpoint 14 — Runway prompt preflight and Motion Smoke v3

- Added a provider-configured Runway image-to-video Prompt preflight using UTF-16 code units;
  over-limit prompts are rejected by the runner before provider construction and by the Provider
  contract before submission. Runway model capabilities record the 1000-unit limit.
- Added `prompts/home-broll-v3.txt` (892 UTF-16 units) and configured new Motion Smoke CLI requests
  and the homepage establishing shot to use v3. The immutable v2 prompt remains unchanged for
  existing evidence, with its recorded 1001-unit length preserved.
- Verification: `uv run pytest` passed **193 tests**; no Runway, HeyGen, or other paid Provider
  call was attempted. v2 SHA-256 remains `27af6d0b902e98f94d816280deef6fdca7537d1eb1b3ea53d71bdf71d9e1f9f2`.

## Goal 2 Checkpoint 15 — P1-2 controlled motion variation planning

- Baseline Smoke `LALA-VIDEO-20260820-040258-MOTION-SMOKE-001` is treated as passed for this
  planning task per the owner request. Its original `review.csv` and external copy remain blank,
  byte-preserved, and immutable; the dry-run records `passed_by_owner_instruction` separately.
- Added three versioned prompt candidates: `MOTION-VAR-001` breathing/blink/tiny-head (959 UTF-16,
  low risk), `MOTION-VAR-002` decor gaze shift (985 UTF-16, low-medium risk), and `MOTION-VAR-003`
  restrained one-hand presentation (997 UTF-16, medium risk). All retain the 5s/gen4_turbo/1280:720
  invariants and explicit forbidden-motion list.
- Dry-run: `LALA-VIDEO-20260820-041837-MOTION-GENERATE-001`, 3 planned Runway calls, estimated 75
  credits / $0.75, `paid_calls: 0`; evidence is under
  `outputs/broll/p1-2-motion-variation-plan-20260820-001/p1-2-dry-run.json`.
- Verification: targeted motion suite **9 passed**; full offline suite **195 passed**; compileall,
  `git diff --check`, configuration validation, and evidence JSON validation passed.
- Recommendation: generate `MOTION-VAR-001` first; if only one 25-credit Live call is allowed,
  choose the same candidate. P1-2 is not Live-ready until Owner approves the variation plan and
  separately authorizes Live with exact permission and credentials. Paid calls in this checkpoint: 0.

## Goal 2 Checkpoint 16 — P1-1 v4 Camera-Lock candidate

- The P1-1 v3 Motion Smoke `LALA-VIDEO-20260820-040258-MOTION-SMOKE-001` retained stable visual
  identity, apparent age, and wardrobe, but external human review found camera/framing drift. It
  is not human-QA approved.
- Added `prompts/home-broll-v4.txt` as a Camera-Lock smoke candidate. It explicitly preserves the
  source composition and pixel positions and prohibits global scene translation, camera drift, and
  reframing. Its explicit v4 dry-run succeeded with one planned call and zero submissions. The
  separately authorized one-result Runway smoke succeeded as
  `LALA-VIDEO-20260820-045551-MOTION-SMOKE-001` (task
  `cf1f9010-5b04-485c-b64e-32568cdbc792`): H.264 MP4, 1280×720, 5.041667 seconds, SHA-256
  `311a14556a22582d941b114531b952e4e40f0cf97137325313277924e6bb513a`, and 25 actual credits.
  A review package is under `outputs/review-packages/P1-1-MOTION-SMOKE-V4-20260820/`; its review
  CSV remains blank. v4 is awaiting human QA and is not approved, production-ready, or MTL-ready.
- The v3 default, homepage establishing preset, P1-2 motion-variation prompts, and historical
  prompt evidence remain unchanged. P1-2 remains blocked pending P1-1 v4 human QA.
- Paid calls made in this checkpoint: **1** (the single authorized Runway P1-1 v4 smoke). No
  P1-2, HeyGen, voice, talking, or other provider call was made.

## Goal 2 Checkpoint 17 — P1-1 v5 Eye/Mouth Lock candidate

- Owner human QA accepted the v4 camera lock, framing, background, identity, face, age, hair, body
  proportions, wardrobe, jewelry, and technical export. Eyes, mouth, and motion failed because of
  two prolonged eye-closure periods, slight late-shot mouth opening, and unnecessary subject
  movement; v4 is not MTL-ready. The original run review remains blank, and the reviewed FAIL copy
  is stored outside Git under `outputs/reviews/`.
- Added `prompts/home-broll-v5.txt` as an eye/mouth/body-lock candidate. It removes blink and
  breathing instructions, requires naturally open eyes, steady gaze, gently closed lips, and a
  visually steady body while retaining v4's camera/framing lock. Its dry-run succeeded with one
  planned call and zero submissions. The separately authorized one-result Runway smoke succeeded
  as `LALA-VIDEO-20260820-051013-MOTION-SMOKE-001` (task
  `d3c4d0e7-ea1f-443f-a8fd-3966c789cdc4`): H.264 MP4, 1280×720, 5.041667 seconds, SHA-256
  `c4fd95d620e0a2e854456a672fffd6e8a7542078afd280f45b3d51195ff543f1`, and 25 actual credits.
  Its blank-review package is under `outputs/review-packages/P1-1-MOTION-SMOKE-V5-20260820/`.
  v5 is awaiting human QA; it is not approved, production-ready, or MTL-ready.
- The v3 default, homepage establishing preset, P1-2 motion-variation prompts, and historical v1–v4
  evidence remain unchanged. P1-2 remains blocked pending P1-1 v5 human QA.
- Verification: targeted Motion Smoke suite **9 passed**; full offline suite **197 passed**;
  compileall, `git diff --check`, package SHA-256 verification, ZIP integrity, and secret scan passed.
- Paid calls made in this checkpoint: **1** (the single authorized Runway P1-1 v5 smoke). No
  P1-2, HeyGen, voice, talking, assembly, promotion, or other provider call was made.

## Goal 2 Checkpoint 18 — P1-1 v6 combined Camera + Eye/Mouth Lock candidate

- Owner human QA accepted v5 identity, face, age, hair, body proportions, wardrobe, jewelry, eyes,
  mouth, background, and technical export. Motion failed because static-background analysis found
  approximately 1.5 px horizontal and 12.7 px vertical global translation; v5 is not MTL-ready.
  The original run review remains blank, and the reviewed FAIL copy is stored outside Git under
  `outputs/reviews/`.
- Added `prompts/home-broll-v6.txt` as a strict combination of v4's pixel-position camera lock and
  v5's eye/mouth/subject lock. It adds no blink, breathing, head, hand, gaze-shift, or presentation
  request. Its dry-run succeeded with one planned call and zero submissions. The separately
  authorized one-result Runway smoke succeeded as `LALA-VIDEO-20260820-052930-MOTION-SMOKE-001`
  (task `e538580c-fccc-47f0-b176-7f31344081c7`): H.264 MP4, 1280×720, 5.041667 seconds, SHA-256
  `e23ced6ec64be4037f25c5f9c8f433d18df2a0577739921ba5aca2c94b10fa2b`, and 25 actual credits.
  Four-region static-background integer-pixel analysis estimated median X/Y drift at 0.0/0.0 px;
  this is diagnostic evidence, not automatic QA. The blank-review package is under
  `outputs/review-packages/P1-1-MOTION-SMOKE-V6-20260820/`.
- Owner review is now archived separately under ignored runtime evidence with Camera Lock PASS,
  Framing FAIL, Identity PASS, Eyes FAIL, Mouth PASS, Motion FAIL, and MTL Ready FAIL. Technical
  execution passed, but human visual acceptance failed because the subject changed position and
  apparent scale relative to the locked background and violated the strict eyes-open target. The
  formal status is `P1_1_V6_SMOKE_HUMAN_QA_FAILED`; the original run `review.csv` remains blank and
  byte-unchanged. P1-1 is not passed, and v6 is not approved, production-ready, or MTL-ready.
- The v3 default, homepage establishing preset, P1-2 motion-variation prompts, and historical v1–v5
  evidence remain unchanged. P1-2 offline implementation and dry-run planning are allowed, while
  P1-2 live provider execution remains blocked until P1-1 receives an explicit human MTL-ready
  pass. Prompt-only subject locking is no longer considered sufficient acceptance evidence.
- Verification: targeted Motion Smoke suite **10 passed**; full offline suite **198 passed**;
  compileall, `git diff --check`, package SHA-256 verification, ZIP integrity, and secret scan passed.
- Paid calls made in this checkpoint: **1** (the single authorized Runway P1-1 v6 smoke). No
  P1-2, HeyGen, voice, talking, assembly, promotion, or other provider call was made.

## Goal 2 Checkpoint 19 — Subject Lock diagnostics and P1-2 offline gate

- V6 Owner QA was archived as `P1_1_V6_SMOKE_HUMAN_QA_FAILED`: Camera Lock PASS, Framing FAIL,
  Identity PASS, Eyes FAIL, Mouth PASS, Motion FAIL, and MTL Ready FAIL. Technical execution
  remains PASS while human visual acceptance is FAIL. The original run review remains blank and
  byte-identical; the ignored reviewed copy records the Owner decision separately. The original
  blank package review SHA-256 is
  `c04e271773e31f81744f94602a9ed782b1a8b792bdbbdaa2e81c704a9b86fa31`; the reviewed-copy
  SHA-256 is `67ceedc5ce97a9436086fd6b4ff5a3cb8026bd56c68042ddcc4c56dd6eb7ab8e`.
- Added provider-neutral local Subject Lock diagnostics under `src/lala_workflow/video/qa/` with
  configured thresholds in `configs/video-qa.yaml`. The bounded Pillow tracker measures the
  dominant red-gown region as `color_region_proxy`; it does not claim face/full-body segmentation,
  requires no network/model download, and returns `INSUFFICIENT_EVIDENCE` rather than zero drift
  when tracking coverage or endpoints are inadequate.
- Review-package integration produces `subject-lock.json`, `subject-trajectory.csv`, and
  `subject-overlay.png`, recomputes sorted SHA-256 evidence, creates/verifies a deterministic ZIP,
  scans text artifacts for secrets, and leaves media/review/run evidence unchanged. `video report`
  presents diagnostic and human-QA status separately.
- V6 offline result: 11/11 frames tracked (100%); first-to-last X/Y drift `-14.0/+10.0 px`, width/
  height change `-8.641975%/-3.496503%`, maximum center distance `23.4094 px`, maximum scale change
  `13.580247%`, diagnostic `OUTSIDE_THRESHOLD`. This is diagnostic evidence, not automatic human
  QA, and does not make V6 MTL-ready.
- P1-2 mode gate now permits provenance-validated offline/dry-run planning with a failing review
  while retaining strict human PASS plus MTL readiness for Live before provider construction. The
  canonical V6 three-candidate dry-run planned three calls and 75 credits, wrote three blank QA
  rows, and produced zero submissions, task IDs, provider constructions, or paid calls.
- Feature traceability lives in `specs/004-subject-lock-diagnostics/`. P1-2 state is
  `Offline: ALLOWED`, `Dry-run: ALLOWED`, `Live: BLOCKED` pending P1-1 human pass.
- Verification: compileall passed; Subject Lock/report **9 passed**; Motion Smoke **10 passed**;
  P1-2 gate **11 passed**; full offline suite **207 passed**. V6 checksum/ZIP integrity and secret
  scan passed; all five approved-anchor hashes match the Checkpoint 1 baseline; tracked runtime
  media/evidence scan and `git diff --check` passed.
- Paid calls made in this checkpoint: **0**. Runway HTTP requests/tasks, HeyGen, voice, talking,
  assembly, promotion, and all other provider calls: **0**.

## Goal 2 Checkpoint 20 — P1-1 Motion V7 targeted stability preparation

- V6 remains the authoritative failed baseline: Camera Lock PASS, Framing FAIL, Identity PASS,
  Eyes FAIL, Mouth PASS, Motion FAIL, and MTL Ready FAIL. The Subject Lock proxy result remains
  11/11 tracked frames (100%), X/Y drift `-14.0/+10.0 px`, width/height change
  `-8.641975%/-3.496503%`, maximum scale change `13.580247%`, and `OUTSIDE_THRESHOLD`.
  It remains diagnostic evidence only, never automatic Human QA.
- Added a V7 controlled A/B/C motion ladder: Stability First, Natural Micro Motion, and Controlled
  Upper Bound. Each new versioned prompt keeps the camera, framing, identity, eyes, and background
  locked while raising only the allowed natural micro-motion. Prompt UTF-16 units are 663, 716,
  and 752, all strictly below 1,000. Historical V2/V3 prompts were not modified.
- Added the dry-run-only `video motion-v7-dry-run` command, which has no `--live` option. It loads
  the fixed `configs/motion-v7.yaml` matrix, rejects a live-enabled/malformed/overlong candidate
  before run creation, and writes one normal 13-artifact planning bundle with three blank QA rows.
  `LALA-VIDEO-20260820-065832-MOTION-V7-001` planned three `gen4_turbo` 5-second calls against
  `pilot_home_context`, estimated 25 credits each / 75 total from configured pricing, and made zero
  submissions, task IDs, provider constructions, or paid calls. Its V6 comparison records V7 and
  delta values as `PENDING`; it does not fabricate a video, Subject Lock artifact, or review package.
- The corrected V6 evidence labels remain: blank package review SHA-256
  `c04e271773e31f81744f94602a9ed782b1a8b792bdbbdaa2e81c704a9b86fa31`; reviewed-copy SHA-256
  `67ceedc5ce97a9436086fd6b4ff5a3cb8026bd56c68042ddcc4c56dd6eb7ab8e`.
- P1-2 remains `Offline: ALLOWED`, `Dry-run: ALLOWED`, and `Live: BLOCKED` pending an explicit
  P1-1 human pass with MTL readiness. V7 preparation and diagnostics do not change that gate.
- Verification: V7 focused **6 passed**; V7 + Subject Lock/package + Motion Smoke + P1-2 focused
  regression **34 passed**; `python -m compileall .` and full offline suite **213 passed**. Approved
  anchor hashes, secret scan, run artifact inspection, and `git diff --check` passed.
- Paid calls made in this checkpoint: **0**. Runway HTTP requests/tasks, HeyGen, voice, talking,
  assembly, promotion, and all other provider calls: **0**.

## Goal 2 Checkpoint 21 — P1-1 Motion V7 guarded controlled live batch implementation

- Implemented the dedicated `video motion-v7-live` execution path for exactly
  `v7-a-stability-first` → `v7-b-natural-micro-motion` → `v7-c-controlled-upper-bound`. It has no
  candidate, subset, skip, or range selection. Canonical `configs/motion-v7.yaml` remains
  `live_allowed: false` for all three candidates.
- Live execution requires both `--execute-live` and `--confirm-v7-batch`, exact
  `VIDEO_ALLOW_LIVE_CALLS=true`, a non-empty local Runway credential, and an explicit finite credit
  cap covering the known estimator-derived batch total (currently 25 credits per candidate / 75
  total). No live execution was performed in this checkpoint.
- The runner prepares and validates the entire A/B/C matrix, authoritative prompt mappings/hashes,
  UTF-16 limits, approved keyframe provenance, provider settings, all three final neutral requests,
  known estimates, cap, authorization, and evidence destination before the first submission. It
  then writes and verifies the parent plan evidence before A can be submitted.
- Task creation is sequential and single-attempt: maximum one new task per candidate / three per
  batch, automatic submission retry and replacement are disabled, and the first failure stops all
  later candidates. Durable task IDs, provider results, output references, API HTTP accounting,
  task-submission accounting, and not-submitted states are recorded separately in one append-only
  13-artifact parent run.
- Fake-provider tests exercise the same live orchestration used by the CLI. The new focused suite
  is **16 passed**; it proves exact A/B/C
  prompt order and association, no fourth submission, all required zero-submission preflight
  failures (including invalid B after valid A), provider isolation, and A-success/B-error fail-stop
  behavior with zero retries or replacements.
- Human QA remains manual and blank in run evidence. Subject Lock remains
  `measurement_scope=color_region_proxy` with automatic Human QA disabled and V7 diagnostics
  `PENDING`. P1-2 remains `Offline: ALLOWED`, `Dry-run: ALLOWED`, and `Live: BLOCKED` pending an
  explicit P1-1 Human QA plus MTL-ready pass; task or diagnostic success is not that pass.
- Feature traceability lives in `specs/006-p1-1-motion-v7-live-batch/`. The required focused V7,
  Motion Smoke, Subject Lock/package, P1-2, provider-preflight, secret/package regression is
  **81 passed**; `python -m compileall .` passed; the full offline suite is **229 passed**;
  approved-source and V7 prompt hashes, secret scan, and `git diff --check` passed. The V7 dry-run
  regression `LALA-VIDEO-20260820-073638-MOTION-V7-001` retained 13 artifacts, three planned calls,
  zero submissions/task IDs/paid calls, 75 estimated credits, and three blank Human QA rows.
- Provider accounting for this implementation checkpoint: real Runway HTTP requests **0**, Runway
  tasks **0**, paid calls **0**, HeyGen **0**, voice **0**, talking **0**, assembly **0**, promotion
  **0**, P1-2 generation **0**, and all other providers **0**. Fake submissions occurred only in
  automated tests and are reported separately from real accounting.

## Goal 2 Checkpoint 22 — P1-1 V7 Human QA closure and P1-2 unlock

- The separately authorized fixed live parent run
  `LALA-VIDEO-20260820-075843-MOTION-V7-001` is now archived as executed and media-valid. Its three
  original Runway tasks remain `9a4c1f1d-4571-4bdd-932b-e10a58f680d3`,
  `be188963-5576-417b-a037-3eb94866343f`, and
  `eb5fa0c5-5d69-40e6-a327-972087b996c4`; the corresponding media SHA-256 values remain
  `79400f291c47dbf5f67d84e779f995b6cde835ce7c10ef8c3bbb7f64ec3505cb`,
  `e55e64bc46debf7e5465b4acb5c44aec55c79a5d21fe65fda74c7f927ea158d2`, and
  `fb66a9f889a53ba58656efc68e98225159a227083c6af8a0bc9b46e0ffb94727`. The source run used three
  previously authorized tasks / 75 Runway credits; this closure created no replacement or retry.
- The Owner's explicit human review is stored only in ignored
  `outputs/reviews/LALA-VIDEO-20260820-075843-MOTION-V7-001-review.csv` (SHA-256
  `2b6a4b028526d0ccd51042530508f7d383b4a9e3e724f852c069206f99330cea`). V7-A Stability First is
  PASS and the unique P1-1 winner; V7-B is FAIL; V7-C is formally FAIL and retained as reserve.
  V7-A records human PASS for Camera Lock (`background`), Framing (`body_proportions`), Identity,
  Eyes, Mouth, Motion, technical export, overall decision, and MTL readiness. Authority is HUMAN
  from the explicit Owner decision; automatic Human QA is false. The append-only parent
  `review.csv` remains blank and byte-unchanged at SHA-256
  `1188628ec6ec759a3f001d30a4779d5ff4bb68de1aba61b2481772f531637a88`.
- The existing P1-2 motion prerequisite gate now accepts a successful canonical three-candidate
  `motion_v7_live` parent only when the external review has exactly one fully passing/MTL-ready
  candidate, all three rows have human attribution, B/C have explicit overall FAIL, and every
  request/task/media/hash fact is intact. It selects only V7-A's prompt/keyframe provenance.
  Ambiguity, provenance mismatch, incomplete review, and media drift reject before provider
  construction. Legacy single-result `motion_smoke` behavior remains supported.
- Offline readiness proof `LALA-VIDEO-20260820-084806-MOTION-GENERATE-001` wrote the standard 13
  artifacts, reported `P1_2_LIVE_READY`, selected V7-A, planned three calls / 75 credits, and made
  zero provider constructions, submissions, task IDs, HTTP requests, or paid calls. P1-2 Live was
  not executed and still independently requires its explicit live command, permission, credential,
  input, count, and budget guards.
- Diagnostics remain honestly
  `P1_1_V7_DIAGNOSTICS_POST_LIVE_DIAGNOSTIC_ENTRYPOINT_NOT_AVAILABLE`: the existing Subject Lock
  entrypoint is legal only for one-result `motion_smoke` packages. Human PASS is authoritative.
  Algorithm modified: NO; thresholds modified: NO; V6 baseline modified: NO; fabricated V7
  diagnostics: NO.
- The original pre-human-review ZIP remains byte-unchanged at SHA-256
  `268842f10553856b821496f8d76662bee2419069b443aeb55f48c7781fcb25ef`. The separate deterministic
  closure ZIP is
  `outputs/packages/P1-1-V7-LALA-VIDEO-20260820-075843-MOTION-V7-001-human-qa-closure.zip`, SHA-256
  `9a33f122fb80877df020b98fea8ea5a1ba6169b7af201974b7bcfd0b4630c3d4`; all 33 checksummed files
  and 34 ZIP members passed integrity, and 31 package text files passed secret scan.
- Feature traceability lives in `specs/007-p1-1-v7-human-qa-closure/`. Focused V7/review/P1-2/
  Subject Lock regression is **38 passed**; full offline suite is **233 passed**; compileall,
  `video validate` (`paid_calls: 0`), `git diff --check`, package verification, and a 337-file
  high-confidence repository/runtime secret scan passed. All 26 approved-source files retained
  their pre-closure SHA-256 values and all five approved-anchor hashes match Checkpoint 1.
- Canonical closure state is `P1_1_V7_LIVE_BATCH_EXECUTED`,
  `P1_1_V7_LIVE_MEDIA_VALIDATED`, `P1_1_V7_HUMAN_QA_PASS`,
  `P1_1_V7_SELECTED_CANDIDATE_V7_A`, `P1_1_MTL_READY`, `P1_2_OFFLINE_READY`, and
  `P1_2_LIVE_READY`, while the diagnostics-entrypoint gap remains retained.
- Provider accounting for this closure: new Runway paid tasks **0**, replacement/retry generation
  **0**, HeyGen **0**, voice **0**, talking **0**, assembly **0**, P1-2 provider calls **0**, other
  paid provider calls **0**. No P1-2 Live command was run.
## Phase 1 Character Switch Checkpoint 1 — Foundational domain and registry

- Added the optional Streamlit extra, runtime character storage boundaries, immutable versioned
  profile/build models, bounded image upload validation, role-specific safe errors, exclusive
  source/profile writes, and a filesystem-locked single-active registry with revision CAS.
- Checked in the `lala-v1` compatibility profile and revision-zero registry. The profile points
  directly to the existing approved face/full-body bytes; it does not copy the shared scene or
  invent a three-quarter source. Synthetic test projects bootstrap their own hash-bound seed.
- Registry mutation validates both the current and proposed immutable profile snapshots before the
  atomic fsync/replace boundary. Simulated stale revisions, invalid target profiles, and write
  failure leave the original registry bytes unchanged.
- Verification: foundational character tests **9 passed**; complete network-blocked offline suite
  **238 passed** (the prior 229 plus 9 new tests); package import and compileall passed.
- Approved-source changes: **none**. Real paid/provider calls in this checkpoint: Runway **0**,
  HeyGen **0**, and all other providers **0**.

## Phase 1 Character Switch Checkpoint 2 — Complete mocked lifecycle, UI, and CLI

- Implemented collision-safe import/build, explicit → active → legacy resolution, deterministic
  baseline/home/medium/product reference policies, optional character provenance on the unchanged
  static provider contract, and eight-artifact static evidence with profile/source hashes.
- Offline preview records zero calls and no fake media. The live adapter preflights static and motion
  authorization before any submission; static is one three-reference result and motion is one
  five-second `gen4_turbo` preview capped at 25 credits. A provider task ID is submitted once and
  then only polled/downloaded. Fake operations verify real local image/video evidence without
  network access; Subject Lock remains diagnostic-only.
- Activation revalidates sources and both previews, copies exact source bytes into the approved
  character authority, writes immutable old/new snapshots, and atomically switches the registry.
  Rejection retains evidence; stale revision and simulated registry-write failure preserve the old
  active ID; `lala-v1` reactivation uses the same transaction.
- Added the shared character CLI and optional one-page Streamlit UI. Streamlit AppTest rendered
  title `人物更换` with **0 exceptions**; the module uses absolute package imports and lazy Streamlit
  loading. Focused character/static/video/reporting suite: **42 passed**.
- Real provider accounting: Runway HTTP requests **0**, Runway tasks **0**, HeyGen **0**, other
  providers **0**, paid calls **0**. All generated media in tests came from local fixtures/fakes.

## Phase 1 Character Switch Checkpoint 3 — Final convergence and delivery

- Architecture: `CharacterService` is the sole UI/CLI application boundary. It composes bounded
  upload validation, collision-safe profile building, immutable YAML snapshots, strict profile/
  source hash validation, a locked revision-CAS registry, explicit/active/legacy resolution,
  deterministic character-plus-scene references, preview-only static/motion adapters, copy-only
  authority promotion, rejection, and `lala-v1` rollback. Provider SDK translation remains inside
  provider adapters; new static fields are optional provider-neutral provenance.
- Convergence: audited FR-001–FR-034, SC-001–SC-010, all 21 acceptance scenarios, nine design
  decisions, and five constitution principles. No remaining missing, partial, contradictory, or
  unrequested finding was found; all **58/58** implementation tasks are complete.
- Verification: full network-blocked suite **265 passed in 41.57s**; compileall and
  `git diff --check` passed. Focused character/static/video suite **36 passed**. Streamlit AppTest
  rendered seven required/optional upload controls with **0 exceptions**. `character list` and
  `character show lala-v1` returned revision 0, one ACTIVE character, and integrity PASS.
- Static validation passed. Dry runs retained exactly eight artifacts and recorded active
  `lala-v1` provenance: baseline identity **10** requests
  (`LALA-RUNWAY-20260820-110625-BASELINE-IDENTITY-001`), home decor **5**
  (`LALA-RUNWAY-20260820-110626-HOME-DECOR-001`), and product page clean **5**
  (`LALA-RUNWAY-20260820-110626-PRODUCT-PAGE-CLEAN-001`). All made zero submissions/outputs.
- Goal 2 validation remains valid. Product-page, tooltip, and homepage dry runs retained exactly
  thirteen artifacts at `LALA-VIDEO-20260820-110640-PRODUCT-PAGE-001`,
  `LALA-VIDEO-20260820-110640-TOOLTIP-001`, and
  `LALA-VIDEO-20260820-110641-HOMEPAGE-001`; they planned 10/4/13 provider calls, generated no
  candidates or human QA decisions, and made zero submissions. Existing QA/promotion gates pass
  the unchanged regression suite.
- Secret/evidence scans found no credential values, Bearer tokens, authorization headers, signed
  query strings, data URIs, or absolute developer paths in character/new run evidence. README
  credential strings are explicit `set-locally-do-not-commit` examples; `.env` test values remain
  synthetic fixtures.
- Approved-source integrity: all 18 authoritative non-placeholder files are byte-identical to the
  isolated pre-change workspace. Approved-anchor baseline remains face
  `b33743fb7a4ec88ca178bb2393cdc99ebe20bf96071c0d8e332496b6ff97ac1b`, full body
  `512dade3fe0762ac778da050c613f30250b5d4b6a270188bd85b807fddc331d9`, scene
  `ab53d9d0551bcf926a41072567493cf640815d99ff92503d9bc111ec3ce7b9ca`, wardrobe B
  `174aaec2242d096e4c465a8dce1a96048017d8f3ea72582316c106b41891f074`, and character sheet
  `427006aee23b59bdaec4ae2b97d4640b7088bc12e1a0d3105d0c13f83913409d`. The approved keyframe/
  provenance, three scripts, and eight canonical voice WAV hashes also exactly match the captured
  pre-change values; no approved-source byte was rewritten.
- Paid/provider accounting for the entire feature: Runway HTTP requests **0**, Runway tasks **0**,
  HeyGen **0**, voice/talking/video **0**, other providers **0**, paid calls **0**. Live character
  preview remains externally blocked because this task supplied no separate owner authorization;
  it additionally requires exact static/video permission flags, the motion-smoke flag, a local
  Runway credential, one result per stage, and the fixed at-most-25-credit motion cap.
- Phase 1 limitations: it does not generate missing views/expressions/poses, infer identity or
  creative quality, auto-approve keyframes/videos/MTL readiness, provide authentication/multi-user
  workflow, deploy to cloud/Shopify, migrate old evidence, or replace existing production review
  and promotion gates.

## Phase 1 Character Switch Checkpoint 4 — Non-technical preview blocker message

- Fixed the local UI leaking the operational error
  `motion preview requires exact VIDEO_ALLOW_LIVE_CALLS=true` to ordinary users. All
  `PreviewUnavailableError` instances now retain precise internal/CLI diagnostics while exposing a
  stable Chinese UI message that explains the preview is temporarily unavailable, confirms the
  profile is saved, recommends retry/contact, and confirms the active character is unchanged.
- Added a regression assertion that the user-facing message contains neither the environment
  variable name nor its required value. Focused UI/preview suite **7 passed**; Streamlit AppTest
  rendered with **0 exceptions**; compileall and `git diff --check` passed; full offline suite
  **266 passed in 43.88s**.
- Real provider accounting for this fix: Runway **0**, HeyGen **0**, other providers **0**, paid
  calls **0**. No approved-source or generated-media file was changed.

## Goal 2 Product Page pilot preflight remediation

- Corrected the external Talking Smoke reviewed copy reviewer placeholder to the stable existing
  human identifier `Project owner (explicit human decision)` without changing the Owner PASS,
  timezone-aware `reviewed_at`, or immutable run-local blank review. The reviewed-copy SHA-256 is
  `06f1dc9e23c46299ab0ebf17988e4549284352c0dba0a1c78d52d77da7452d84`; the original run review
  remains `8e57c24fc38855fd481975193a004e83f83c4c40aa1d1d2f091b520bdd89bfcb`.
- Added the explicit post-TTS `--max-talking-duration-seconds` workflow gate with a configured
  60-second safety ceiling. Dry-run now preserves exact unknown HeyGen totals, records known unit
  rates and `TOTAL_EXACT_UNKNOWN_UNTIL_TTS`, and distinguishes a duration-limit projection from an
  actual-duration estimate. Live code requires the explicit gate for cloned voice, measures the
  WAV after the one TTS result, recalculates cumulative cost and remaining budget, and blocks all
  Talking/Runway submissions if either the duration or Owner USD cap is exceeded. The evidence
  states that HeyGen does not provider-enforce the TTS duration limit.
- General Goal 2 preview/live generation now shares the existing canonical motion-prerequisite
  resolver: legacy one-result motion smoke remains compatible, while a V7 parent requires one
  unique human-reviewed/MTL-ready winner plus intact review, task, keyframe, media, and hash
  provenance. The selected request is rebound to the current approved keyframe before provider
  construction. The canonical V7 run still uniquely resolves `v7-a-stability-first`.
- New Product Page dry-run `LALA-VIDEO-20260821-014037-PRODUCT-PAGE-001` retained thirteen
  artifacts and zero submissions. It records one Starfish request, one Avatar IV request, two
  four-second `gen4_turbo` requests, 40 Runway credits / USD 0.40, a 45-second voice projection of
  USD 0.030015, Talking projection of USD 2.25, combined projection USD 2.680015, exact total
  unknown until TTS, and `accept_unknown_provider_cost=false`. Talking and V7 review hashes are
  embedded in request/resolved evidence.
- Verification: focused preflight tests **10 passed**; broader focused video tests **54 passed**;
  complete offline suite **288 passed in 49.86s**; compileall, Goal 2 validation, and
  `git diff --check` passed. Approved-source and historical V7 evidence hashes remain unchanged.
  Provider accounting for this remediation: Runway HTTP **0**, HeyGen HTTP **0**, provider
  submissions **0**, paid calls **0**. No Product Page Live was executed.

## Goal 2 K2 candidate intake audit and talking-keyframe parity

- Audited three owner-supplied K2 images under `tmp/k2_candidates/` without copying them into an
  approved-source directory or fabricating generation/human-review provenance. The current CLI has
  no external-keyframe candidate import/review/promotion contract: static promotion requires a
  genuine Goal 1 run/request/result/prompt chain, while `owner_supplied_legacy_asset` is an audited
  already-approved source-package path and cannot represent an unreviewed candidate.
- Talking workflows for Product Page, Tooltip, and Homepage now require an independently approved
  `talking_medium_closeup` role in both dry-run and live modes. Missing-role checks run before run
  allocation and before real provider construction, including when a provider mapping is injected
  by tests; the full-body home-context keyframe no longer satisfies any talking entry point.
- Focused Product Page/dry-run/generation tests **25 passed** and the complete offline suite
  **290 passed in 50.95s**. Direct Product Page dry-run and live fail-closed checks both exited 4
  with run count unchanged at 10. Provider accounting: Runway HTTP **0**, HeyGen HTTP **0**,
  submissions **0**, paid calls **0**.

## Goal 2 external K2 workflow — documentation continuation

- Recovered the interrupted Track B session and completed the active Spec Kit design set under
  `specs/008-external-k2-workflow/`: explicit scope/NFRs, architecture and multi-file failure
  boundaries, security/privacy rules, compatibility, evidence, rollback, full data schemas, CLI
  contracts, runnable Owner handoff, dependency-ordered tasks, and FR/NFR/SC traceability.
- Documentation deliberately records the feature as implementation-in-progress. The focused
  external-keyframe/pilot/dry-run command currently reports **18 passed, 8 failed**; failures cover
  duplicate K2 fixture authority, resolver fixture/order conflicts, V7/talking keyframe parity,
  and one promotion fixture collision. T003–T016 remain unchecked until independent verification
  is green.
- The real candidate was not imported through the new workflow, no review value was filled, no
  promotion ran, and no approved source or manifest was changed by this documentation checkpoint.
  Ordered approved-source hash-list digest remains
  `b39392cd134ac80470c259419510d8dfd763b2c776a5ef48f0f8875169b1e908`.
  Provider accounting: Runway HTTP **0**, Runway tasks **0**, HeyGen HTTP **0**, provider
  submissions **0**, paid calls **0**.

## Goal 2 external K2 workflow — implementation and pending Owner review

- Implemented `video keyframe import-candidate` and `promote-candidate` with dedicated external
  provenance, exact-byte exclusive staging/promotion, bounded PNG/JPEG validation, source/review/
  staged symlink and traversal rejection, one-row versioned blank Human QA, candidate/hash-bound
  review validation, timezone-aware attribution, collision protection, and handled-failure cleanup.
- Split pilot keyframe authority end to end: Product Page/Tooltip/Homepage talking resolves unique
  `talking_medium_closeup` K2, while motion/B-roll/V7 resolves unchanged `pilot_home_context` K1
  (with `establishing_keyframe` fallback). New request/resolved evidence records both independently;
  historical single-keyframe readers remain compatible.
- Focused external/media/preflight/dry-run suites passed **39 tests**; broader video coverage passed
  **68 tests**; complete offline suite passed **302 tests in 53.60s**. Compileall, Goal 2 validation,
  `git diff --check`, requirement traceability, and precise credential/signed-URL scans passed.
- Imported real candidate `k2-owner-20260821-01` by exact bytes only. Source and staged SHA-256 are
  both `111811f7d501850e0ddd2cd4dca1cf4f595453e68c83a987f52c96ecbb488ea6`; candidate provenance SHA
  is `4807befaa7eb3f35d8f8051baf6cf9eb3b57ef737e9f4bbe69175f2451ce2082`; blank review SHA is
  `fb02a32ddaad51a4f78c2e9ff93cda377ce8283d206062bdb52f0d6886c36bd4`, with one row and zero
  nonblank Human fields. Status is `READY_FOR_K2_HUMAN_REVIEW`.
- The unapproved-candidate Product Page dry-run failed closed with exit 4 before run allocation;
  run count stayed 10. No review PASS was supplied, no promotion ran, and keyframe manifest SHA
  remains `8b9e4eb1eea4222eb20b6b97bdd7f697f9d096573274b706bd6732064ca3a7b5`.
- Approved-source ordered digest remains
  `b39392cd134ac80470c259419510d8dfd763b2c776a5ef48f0f8875169b1e908`.
  Provider accounting: Runway HTTP **0**, Runway tasks **0**, HeyGen HTTP **0**, submissions **0**,
  paid calls **0**. Promotion and Product Page ready dry-run await explicit Owner Human review.
