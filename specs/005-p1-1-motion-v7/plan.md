# Implementation Plan: P1-1 Motion V7 Targeted Fix

**Branch**: `fix/p1-1-motion-v7` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

## Summary

Add a deterministic, offline-only V7 batch dry-run for three named motion candidates. Store their versioned prompt provenance, UTF-16 measurements, cost estimates, live-disabled metadata, blank human QA rows, and a V6-to-pending-V7 Subject Lock comparison in the existing append-only 13-artifact run format. Reuse existing provider preflight, Runway credit estimator, review package, and P1-2 gate; do not add a V7 live execution path.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing Python standard library, PyYAML, Pillow, FFmpeg/FFprobe

**Storage**: Existing ignored `runs/` records and `outputs/review-packages/` evidence

**Testing**: pytest with fake providers and blocked network access

**Target Platform**: macOS/Linux with FFmpeg

**Performance Goals**: Resolve three local prompts and write one dry-run record without constructing a provider or network client

**Constraints**: Prompt limit is strictly fewer than 1,000 UTF-16 code units; no provider calls; no V2/V3 or approved-source mutation; no fabricated V7 diagnostics; run records retain exactly thirteen artifacts

**Scale/Scope**: Exactly three 5-second `gen4_turbo` candidates at `1280:720`, one V6 baseline, and a future-only comparison scaffold

## Constitution Check

- **I Approved Sources**: PASS. The implementation only reads approved-keyframe provenance and writes derived prompts/configuration/run evidence outside approved sources; approved-anchor hashes are checked before and after work.
- **II Provider-Neutral Core**: PASS. Candidate planning is a local domain helper and reuses the existing neutral `MotionVideoRequest` evidence; no provider SDK appears outside its adapter.
- **III Paid Calls**: PASS. The new CLI is dry-run only, has no live flag, and performs no provider construction. Existing preflight and P1-2 live gate are retained.
- **IV Offline Tests**: PASS. Candidate, UTF-16, comparison, review-blankness, package, and gate regressions receive local or fake-provider coverage.
- **V Human Approval**: PASS. Comparison data is labelled diagnostic-only; V7 metrics are pending without video and review fields stay blank.

No constitutional exception is requested.

## Project Structure

```text
configs/motion-v7.yaml
prompts/
├── p1-1-motion-v7-a-v1.txt
├── p1-1-motion-v7-b-v1.txt
└── p1-1-motion-v7-c-v1.txt
src/lala_workflow/video/
├── cli.py
├── motion_v7.py
└── runner.py
tests/
└── test_motion_v7.py
specs/005-p1-1-motion-v7/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── dry-run-evidence.md
└── tasks.md
```

## Design

1. Keep the three long prompts in new versioned text files. Each contains shared positive camera/framing/identity/eyes/background constraints and a small rung-specific motion paragraph.
2. Add a compact YAML candidate manifest containing the canonical ordered identifiers, prompt files, experiment metadata, Runway model/duration/ratio, and a hard `live_allowed: false` value.
3. Add local V7 domain helpers that validate the exact candidate set/order, reject unsafe prompt paths or live-enabled configuration, load each prompt with the existing loader, validate its UTF-16 value with the existing Runway preflight, and obtain each estimate with the existing configured credits-per-second value.
4. Add a dry-run-only runner/CLI operation. It creates one normal video run, builds one planned request per candidate with its own prompt provenance, records candidate metadata and the comparison scaffold inside existing JSON artifacts, writes three blank review rows, writes estimator-derived cost evidence, and asserts the existing 13-artifact invariant.
5. Represent V6 values as fixed documented diagnostics. Represent every V7 measurement and delta as `null` with explicit `PENDING` status until later real media is diagnosed; do not create a Subject Lock artifact or review package in a no-video dry-run.
6. Keep all existing P1-2 validation untouched and test that it remains blocked for live execution after V7 planning.

## Verification Strategy

- Confirm prompt bytes for V2/V3 are unchanged and V7 A/B/C files each remain below the UTF-16 threshold.
- Test candidate manifest ordering, uniqueness, non-authorizing flag, prompt provenance, and estimator results.
- Test V7 dry-run output: one run, three planned calls, zero submission/task IDs/provider creation, 75 configured-estimator credits, and three blank review rows.
- Test fixed V6/pending V7 comparison and diagnostic-only labelling.
- Re-run Subject Lock/package and P1-2 gate suites to prove no human-QA or live-gate regression.
- Run `python -m compileall .`, full `uv run pytest -q`, approved-source hashes, secret scan, V7 CLI dry-run, and `git diff --check`.

## Post-Design Constitution Check

All principles remain satisfied. The only new runtime path is local dry-run planning; it does not construct a provider, submit a task, change approved material, or turn Subject Lock into QA authority.

## Complexity Tracking

No violation or complexity exception.
