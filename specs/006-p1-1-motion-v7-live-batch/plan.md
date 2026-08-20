# Implementation Plan: P1-1 Motion V7 Controlled Live Batch

**Branch**: `fix/p1-1-motion-v7-live-batch` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-p1-1-motion-v7-live-batch/spec.md`

## Summary

Add a dedicated `motion-v7-live` command that uses the existing immutable V7 candidate loader and provider-neutral motion protocol. The runner prepares all requests, validates every candidate and request, writes and verifies append-only parent plan evidence, then executes A/B/C sequentially with one submission attempt each. Any invalid preflight produces zero submissions; any execution failure stops later candidates. Existing dry-run, Subject Lock, human QA, and P1-2 gates remain unchanged.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing Python standard library, PyYAML, Runway SDK adapter, FFmpeg/FFprobe evidence helpers

**Storage**: Existing ignored `runs/` append-only 13-artifact records and categorized `outputs/broll/`

**Testing**: pytest with fake motion providers and blocked network access

**Target Platform**: macOS/Linux CLI with FFmpeg

**Project Type**: Python CLI and library

**Performance Goals**: Complete all local validation and durable evidence writes before the first provider submission; keep live execution sequential

**Constraints**: Exactly three fixed requests; fewer than 1,000 UTF-16 units each; known 75-credit estimate under current config; explicit confirmations/env/cap; zero automatic task-creation retries; no prompt or approved-source mutation; no real calls during implementation

**Scale/Scope**: One parent run, exactly three five-second `gen4_turbo` motion candidates at `1280:720`, maximum three new Runway task submissions

## Constitution Check

- **I Approved Sources**: PASS. Full preflight validates the selected approved keyframe and records its digest; all generated media and evidence remain outside approved directories.
- **II Provider-Neutral Core**: PASS. Orchestration depends on `MotionVideoProvider` behavior and neutral request/result entities. Real SDK construction remains in the Runway adapter path.
- **III Paid Calls**: PASS. Canonical config remains disabled; the command requires two explicit flags, exact environment permission, credential, known estimate, explicit cap, sequential execution, and zero task-creation retries.
- **IV Offline Tests**: PASS. All new execution coverage injects fakes; no test constructs the real adapter or reads a real credential. Full-batch preflight and evidence ordering are asserted.
- **V Human Approval**: PASS. The parent run creates blank review rows, diagnostics remain pending, and no provider outcome changes P1-2 authorization.

No constitutional exception is requested.

## Project Structure

### Documentation (this feature)

```text
specs/006-p1-1-motion-v7-live-batch/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli-and-evidence.md
└── tasks.md
```

### Source Code (repository root)

```text
src/lala_workflow/
├── providers/
│   └── runway_video.py        # provider-specific request/HTTP accounting only
└── video/
    ├── cli.py                 # fixed live command interface
    ├── motion_v7.py           # candidate/batch entities and invariants
    └── runner.py              # preflight, evidence-first, sequential orchestration

tests/
└── test_motion_v7_live.py     # fake live path, failures, isolation, CLI guards

README.md
PROGRESS.md
```

**Structure Decision**: Extend the existing single-package video workflow. Keep V7-specific invariants in `motion_v7.py`, shared run orchestration/evidence in `runner.py`, and Runway-specific counters inside its adapter.

## Design

1. Add frozen V7 batch/candidate execution evidence entities and reuse `load_v7_candidates` for exact canonical validation. Strengthen it to reject duplicate prompt mappings and authoritative prompt-hash drift.
2. Add a fixed CLI command with required `--keyframe`, `--execute-live`, `--confirm-v7-batch`, and `--max-runway-credits`; provide no candidate-selection arguments.
3. The live runner validates flags, exact environment permission/credential, sequential configuration, selected keyframe provenance, all three candidate/provider settings, unique mappings, known estimates, total cap, and all three neutral requests before constructing or submitting through a real provider.
4. Allocate one parent run only after non-provider preflight succeeds. Validate all three requests through the injected/real provider, write the plan side of all existing artifacts, then read back request/plan/review/cost evidence and assert the expected hashes, counts, order, blank QA, and estimate before emitting `preflight_evidence_verified`.
5. Submit requests sequentially through a V7-specific no-retry executor. Preserve any durable task ID if wait/download fails, record one failed/not-submitted row for the remaining candidates, and never compensate.
6. Complete `provider-results.json`, cost facts, summary, and events after success or partial failure. Dynamic state lives in provider results while preflight plan artifacts remain immutable.
7. Record task submission attempts and IDs exactly. Record adapter HTTP request count separately when available; otherwise mark it unknown rather than inventing a value.

## Verification Strategy

- TDD tests first for authorized fake A/B/C order and prompt hashes, provider isolation, all required zero-submission preflight failures, missing CLI confirmations, and A-success/B-error fail-stop.
- Assert the actual runner writes plan evidence before the fake's first `submit` call and produces exactly thirteen run artifacts with three blank QA rows.
- Re-run existing V7 dry-run, Motion Smoke, Subject Lock/review-package, P1-2 gate, provider preflight, and secret/package tests.
- Run `python -m compileall .`, `uv run pytest -q`, `git diff --check`, approved-source hash comparison, and credential/Bearer/authorization scans.

## Post-Design Constitution Check

All five principles remain satisfied. The live path is more tightly bounded than general motion generation: it has a fixed request count/order, an evidence-before-submit checkpoint, one attempt per candidate, fail-stop execution, provider isolation, blank review evidence, and no downstream gate mutation.

## Complexity Tracking

No violations or complexity exceptions.
