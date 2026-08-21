# Implementation Plan: Coffee Table Failed-Task Recovery

**Branch**: `012-coffee-table-recovery` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/012-coffee-table-recovery/spec.md`

## Summary

Preserve the completed recovery-preparation evidence, then add a dedicated V2-authorized Live path for exactly one TASK-04 request from Owner-selected TASK-02 frame 92. The path fails closed on any protected drift, durably records the one-submit lifecycle, downloads and validates one result, assembles the exact twenty-second 16:9 master with a decoded-last-frame hold, blocks alternate ratios unless objective safe-area gates exist, creates a blank Human Review Package, and stops at `READY_FOR_OWNER_REVIEW`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Standard library, Pillow, existing video inspection/hash helpers, FFmpeg/FFprobe

**Storage**: Read-only original/recovery evidence under `runs/` and existing output trees; one new append-only recovery Live run under `runs/`, TASK-04 under `outputs/broll/<run_id>/`, master under `outputs/final/<run_id>/`, and copies/evidence under `outputs/reviews/coffee-table-final/<run_id>/`

**Testing**: pytest with synthetic local media, injected command runners where useful, and network-blocked full suite

**Target Platform**: Local macOS/Linux CLI with FFmpeg/FFprobe

**Project Type**: Python CLI media workflow

**Performance Goals**: All static gates run before output allocation; local preparation completes within the existing 1,800-second media-operation bound

**Constraints**: Exact Recovery Manifest V2/path/SHA and all protected hashes; one TASK-04 submit/task only; SDK submission retries zero; 25 credits/USD 0.25 maximum; frame 92 and prompt v3 frozen; task-ID idempotency; deterministic 480-frame master and last-decoded-frame hold; objective safe-area gating; blank Human fields; no historical rewrite

**Scale/Scope**: One stopped run, two reused provider outputs, one historical failure, one exact-byte local cutaway, one reviewed source PNG, one new provider result, one master, zero-to-two guarded local variants, and one review package

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **I. Approved Sources Are Immutable Truth**: PASS. Recovery reads and hashes approved sources only; all derived media is written beneath `outputs/`.
- **II. Provider-Neutral, Reproducible Core**: PASS. Recovery contains no provider adapter or SDK object; exact local commands and hashes are evidence.
- **III. Paid Calls Are Explicit, Staged, and Bounded**: PASS. Preparation exposes no live flag and constructs no provider; future TASK-04 remains projected and separately gated.
- **IV. Offline Tests and Deterministic Editing Gate Delivery**: PASS. Fixed FFmpeg/FFprobe argv, strict media validation, synthetic tests, full offline tests, and source rehashes are required.
- **V. Human Approval and Staged Video Delivery**: PASS. Preparation records no subjective decision and stops for Owner review of the recovery manifest hash.

Post-design re-check: PASS. Atomic collision-safe creation and cleanup of only newly allocated recovery paths preserve append-only evidence without exceptions to the constitution.

Owner-authorized Live design re-check: PASS. The V2 path requires explicit `--live`, the formal video permission and credential, exact cost caps, one submission with SDK retries disabled, durable task-ID evidence, deterministic local editing, protected-source rehashes, and blank Human review fields. Safe-area uncertainty fails closed without provider regeneration.

## Project Structure

### Documentation (this feature)

```text
specs/012-coffee-table-recovery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli-and-manifest.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
prompts/
└── coffee-table-task-04-sit-hero-v3.txt

src/lala_workflow/video/
├── cli.py
├── coffee_table_live.py
├── coffee_table_recovery.py
├── coffee_table_recovery_live.py
└── runner.py

tests/
├── test_coffee_table_recovery.py
└── test_coffee_table_recovery_live.py
```

**Structure Decision**: Keep the paid historical executor unchanged. Place recovery-specific identities, validation, local derivation, and manifest creation in a separate provider-free module; add one mutually exclusive offline campaign mode to the existing CLI.

**Live Continuation Decision**: Keep the four-task historical executor unchanged and add a separate V2 recovery Live coordinator. `--live --recovery-live` selects it explicitly, preventing a V2 manifest from entering the original four-task path.

## Design Decisions

1. Recovery accepts the exact parent manifest path/SHA and failed run ID, then compares the current original execution-manifest and provider-results bytes against hashes captured before output allocation. It validates the full three-record historical facts rather than trusting only the run status.
2. TASK-01, TASK-02, and the PDP source are SHA/dimension/media-gated. TASK-03 is preserved as a historical failed provider record while `LOCAL-TASK-03` is a distinct local artifact with no provider task ID.
3. The local cutaway uses a fixed 1280x720 center crop from the 1280x1280 source, then a center-anchored optical push from 1.000 to 1.035 across exactly 72 frames. The logged encoder contract fixes frame rate, H.264, yuv420p, no audio, metadata removal, bit-exact flags, and one encoding thread.
4. TASK-02 zero-based frame 96 is extracted directly with a fixed selector. The source SHA is rechecked before and after extraction; no frame count–based aesthetic choice or fallback index is allowed.
5. TASK-04 v3 prompt is an immutable repository file. Preparation records path, exact text, UTF-16 code-unit count, and SHA, but creates no `MotionVideoRequest` and imports/constructs no provider.
6. A recovery ID is collision-safely allocated from the current timestamp and sequence. Media is prepared in a new output directory; the manifest directory and final JSON are exclusively created. Failure removes only the newly created recovery paths, never the original run or source evidence.
7. The manifest contains parent/original evidence hashes, historical task records, local media/extraction evidence, frozen TASK-04 proposal, exact eight-segment 20-second timeline, guarded-local ratio policy, budget facts, explicit zero-call counters, and the review terminal state.
8. After writing the manifest, original evidence and every referenced source/output hash are revalidated. CLI success reports the recovery ID, manifest path/SHA, local artifact identities, frame-96 identity, zero calls, costs, and review state.
9. The V2 Live preflight validates the exact manifest bytes and its complete transitive evidence before creating a run or provider. The current formal video contract is exact `VIDEO_ALLOW_LIVE_CALLS=true` plus a non-empty `RUNWAYML_API_SECRET`; Goal 1's `RUNWAY_ALLOW_LIVE_CALLS` is not part of this video path, and no new permission variable is invented.
10. The run writes PREPARED and SUBMITTING events before calling the provider. The provider task-created sink fsyncs the returned ID before `submit()` returns; a no-ID exception is `BLOCKED_SUBMISSION_UNKNOWN`, while a known ID is polled and never resubmitted.
11. TASK-04 uses only manifest-bound frame 92 and prompt v3. The adapter retains SDK `max_retries=0`, download retries are zero, provider count is one, and actual credits/cost remain explicit even when the provider omits a final cost value.
12. Assembly extracts TASK-04's last decoded frame to PNG, records count/index/hash, then concatenates eight explicit 24-fps segments to a silent H.264/yuv420p 1280x720 master targeting exactly 480 frames.
13. No objective machine-safe-area geometry is present in V2, so both 1:1 and 9:16 fail closed as `BLOCKED_SAFE_AREA`. The system does not generate crops merely because FFmpeg can center-crop them and never requests native-ratio provider work.
14. The review package exact-byte copies TASK-01, TASK-02, LOCAL-TASK-03, TASK-04, the master, and evidence. Its checklist contains every Owner item with blank decision/notes/reviewer/timestamp fields and never marks approval or MTL readiness.

## Verification Strategy

- Contract tests cover exact CLI mode, parent/run/source gates, immutable byte snapshots, historical TASK states and IDs, no TASK-03 retry, collision/failure cleanup, and provider-free imports/counters.
- A real local-media test runs cutaway generation twice and validates matching bytes, 72 frames, three seconds, 1280x720, 24 fps, H.264, yuv420p, and no audio.
- A real TASK-02 extraction test validates fixed index 96, exact source SHA, PNG dimensions/hash, and failure when the source drifts or lacks that frame.
- Manifest tests validate exact 20-second assembly segments, 50/25/75-credit cost arithmetic, local-only ratio policy, prompt SHA, source lineage, original evidence byte stability, and terminal state.
- Run focused tests, full offline tests, compileall, `git diff --check`, video validation, secret scan, and before/after approved-source SHA comparison. Execute recovery preparation only after these offline gates pass.
- V2 Live tests use a fake provider to cover exact one-request translation, PREPARED/SUBMITTING/task-ID/SUBMITTED/terminal ordering, ambiguous no-ID submission, known-ID continuation, task failure, invalid/multiple outputs, zero replacement, and exact accounting.
- Real local FFmpeg tests verify last-decoded-frame extraction, the eight segment order, 480 frames/20 seconds, codec/pixel format/no audio, explicit safe-area blocking, exact review copies, and blank Owner checklist fields.
