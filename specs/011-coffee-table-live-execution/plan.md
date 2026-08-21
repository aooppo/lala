# Implementation Plan: Coffee Table Live Execution

**Branch**: `011-coffee-table-live-execution` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-coffee-table-live-execution/spec.md`

## Summary

Add one manifest-bound Coffee Table Live CLI mode. It validates the exact Owner-approved V2 identity before allocation/provider construction, persists each submission boundary and task ID, executes four requests serially with fail-stop semantics, deterministically derives Task 04 from Task 02, produces local review media, and leaves blank Human QA at `READY_FOR_OWNER_REVIEW`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing provider-neutral video domain, `RunwayMotionProvider`, Pillow, FFmpeg/FFprobe, standard library

**Storage**: Append-only run evidence under `runs/`; raw media under `outputs/broll/`; derived delivery under `outputs/final/` and `outputs/reviews/`

**Testing**: pytest with injected fake providers/command runners and network-blocked full suite

**Target Platform**: Local macOS/Linux CLI

**Project Type**: Python CLI media workflow

**Performance Goals**: Preflight completes before any network call; local assembly completes within the existing 1,800-second media timeout

**Constraints**: Exact manifest SHA; four sequential tasks; 100 credits / USD 1.00; zero paid retries/replacements; durable task IDs; no native-ratio generation; no automatic Human decisions

**Scale/Scope**: One approved campaign manifest, four Runway tasks, four raw MP4s, one master, up to two local derivatives, one review package

## Constitution Check

- **I. Approved Sources Are Immutable Truth**: PASS. All approved files are read/hash-only; runtime inputs and outputs are derived elsewhere.
- **II. Provider-Neutral, Reproducible Core**: PASS. Orchestration consumes `MotionVideoProvider`; SDK translation stays in the existing adapter.
- **III. Paid Calls Are Explicit, Staged, and Bounded**: PASS. Exact Owner SHA and live flags gate four tasks; no retries or replacements.
- **IV. Offline Tests and Deterministic Editing Gate Delivery**: PASS. Fake-provider tests and logged FFmpeg/FFprobe commands precede Live.
- **V. Human Approval and Staged Video Delivery**: PASS. Review rows stay blank and completion stops at Owner review.

Post-design re-check: PASS. No exception is required.

## Project Structure

### Documentation (this feature)

```text
specs/011-coffee-table-live-execution/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli-and-runtime.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/lala_workflow/video/
├── campaigns.py
├── coffee_table_live.py
├── cli.py
└── runner.py

tests/
└── test_coffee_table_live.py
```

**Structure Decision**: Keep immutable planning validation in `campaigns.py`; isolate stateful paid execution and local delivery in a dedicated module; expose only one manifest-bound campaign CLI entry.

## Design Decisions

1. Live takes both manifest path and expected SHA and accepts only the hard-coded approved V2 identity. It also requires `--live`, an exact Owner authorization flag, exact live environment permission, and credential presence.
2. A runtime run directory is allocated only after every static preflight gate passes. Authorization evidence is stored without secrets.
3. Requests are reconstructed from manifest fields and validated immediately before each submit. Provider construction occurs only after preflight and run allocation.
4. Before `submit`, a durable `SUBMITTING` event is fsynced. The adapter's task-created sink immediately persists the returned ID. An exception with no ID becomes `SUBMISSION_AMBIGUOUS` and stops the run; it is never retried.
5. Tasks run strictly 01→02→03→04. Each task must succeed and its MP4 must validate before continuation. Planned credits reserve the remaining budget before every submission.
6. After Task 02, FFprobe counts decoded frames and FFmpeg extracts index `frame_count - 1`; both MP4/PNG hashes and exact argv are recorded in `task-04-source-lineage.json`, then reverified before Task 04.
7. Local assembly uses explicit trim/setpts/concat/tpad filters and fixed H.264/yuv420p output. Center-crop derivatives are local-only and validated; a derivative failure is recorded without provider fallback.
8. Raw, master, delivery, cost, provider, lineage, event, and blank review evidence are written collision-safely. Success is `READY_FOR_OWNER_REVIEW`; failures preserve evidence with precise stopped status.

## Verification Strategy

- Contract/failure tests cover exact SHA/path, flags, provider non-construction, source/prompt drift, budget, ordering, task-ID persistence, ambiguous submission, failure stop, lineage, deterministic assembly, blank review, and zero replacements.
- Real local synthetic-media test validates the FFprobe/FFmpeg selectors and 20-second assembly.
- Run focused tests, full offline tests, compileall, video validation, diff check, secret scan, and approved-source before/after hashes before paid execution.
- Immediately before Live, rehash the approved manifest and required sources; after Live, repeat approved-source comparison and inspect run evidence.
