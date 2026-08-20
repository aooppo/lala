# Implementation Plan: Subject Lock Diagnostics

**Branch**: `feat/p1-1-subject-lock-control` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

## Summary

Add deterministic local subject-position/scale diagnostics based on a provider-neutral tracker contract, extend motion review packages and reports with diagnostic-only evidence, and separate P1-2 offline/dry-run permission from the existing strict live human-review gate. Analyze V6 from local media only. No prompt version, provider call, human-QA automation, stabilization pipeline, or approved-source mutation is included.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Existing Pillow, PyYAML, FFmpeg/FFprobe; Python standard library
**Storage**: Existing append-only `runs/` evidence and ignored `outputs/review-packages/` runtime packages
**Testing**: pytest with deterministic synthetic images/videos and fake providers; sockets blocked by the existing suite
**Target Platform**: macOS/Linux with FFmpeg
**Performance Goals**: Analyze 11 samples from a five-second 1280x720 motion clip locally without network access; favor bounded downsampling for deterministic tracking
**Constraints**: No OpenCV/NumPy currently declared; no new heavyweight dependency or model; no overwrite of approved/run/review evidence; no automatic QA; no paid/live calls
**Scale/Scope**: One subject proxy, one motion candidate at a time, three P1-2 candidate plans

## Constitution Check

- **I Approved Sources**: PASS. Analysis reads derived video/keyframe evidence only and writes under `outputs/`; pre/post hashes cover all approved sources.
- **II Provider-Neutral Core**: PASS. `SubjectTracker` and diagnostic domain models live under video QA; no provider SDK is involved.
- **III Paid Calls**: PASS. All implementation and verification are offline. Live negative tests use fake providers and must reject before construction/submission.
- **IV Offline Tests**: PASS. Synthetic translation/scale/loss, package integrity, report, and gate cases are required.
- **V Human Approval**: PASS. Diagnostic states are explicitly distinct from QA and never write review fields.

No constitutional exception is requested.

## Project Structure

### Documentation

```text
specs/004-subject-lock-diagnostics/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── subject-lock-evidence.md
└── tasks.md
```

### Source

```text
configs/video-qa.yaml
src/lala_workflow/video/qa/
├── __init__.py
├── subject_lock.py
└── review_package.py
src/lala_workflow/video/cli.py
src/lala_workflow/video/reporting.py
src/lala_workflow/video/runner.py
tests/test_subject_lock.py
tests/test_subject_lock_review_package.py
tests/test_video_motion_variations.py
tests/test_video_reporting.py
```

**Structure Decision**: Add a focused provider-neutral `video.qa` package. Keep run storage's exact thirteen artifacts unchanged; subject evidence belongs to the separate review package. Extend the current `video report` response only when a subject-lock artifact is available for the run/package.

## Design

1. Define immutable `SubjectBox`, `SubjectObservation`, `SubjectLockThresholds`, and `SubjectLockResult` types plus a `SubjectTracker` protocol.
2. Implement a bounded Pillow-based color-region proxy. It detects the dominant red-gown region on a downsampled frame, tracks the component nearest the first reliable box, and returns no observation for invalid/low-confidence regions. Evidence declares `measurement_scope=color_region_proxy`.
3. Extract 11 evenly spaced video samples with local FFmpeg into a temporary directory, preserving frame indices/timestamps. Synthetic tests call the same analyzer with in-memory frames and a deterministic tracker.
4. Aggregate displacement and scale relative to the first tracked observation. If the tracked/sample ratio is below the configured minimum or endpoints are missing, return `INSUFFICIENT_EVIDENCE`; never substitute zero values for missing observations.
5. Store thresholds in `configs/video-qa.yaml` and validate positive center/scale limits plus a success rate in `(0,1]`.
6. Generate JSON, CSV, and overlay artifacts without changing source media or review CSV. Review-package finalization recomputes `SHA256SUMS.txt`, creates a deterministic ZIP containing every package member, verifies hashes/archive, and scans text evidence for secret patterns.
7. Add a local-only CLI to diagnose/finalize an existing package and allow `video report` to discover the corresponding subject summary by run ID. No provider construction exists on this path.
8. Refactor P1-2 validation into a mode-aware gate: dry-run validates immutable smoke/output/keyframe provenance while accepting a blank or failing review as non-authorizing context; live continues to call the strict passing-review validator before any provider is created. Remove the planning-only attestation's misleading pass status while keeping backward-compatible CLI parsing if needed.

## Verification Strategy

- TDD: add synthetic perfect-lock, translation, scale, and loss tests before implementation.
- Package tests verify exact artifacts, checksums, ZIP membership/integrity, secret scanning, and review byte identity.
- Reporting tests verify diagnostic fields and `human_qa=NOT_SET` without interpreting diagnostic status as QA.
- Gate tests use a failed modern review: three-candidate dry-run succeeds with zero submissions; live fails before a provider factory/fake receives any call.
- Run V6 local analysis and require `OUTSIDE_THRESHOLD` with material drift/scale or `INSUFFICIENT_EVIDENCE`.
- Run compileall, focused suites, full pytest, three-candidate canonical dry-run, pre/post approved-source hashes, secret scans, and `git diff --check`.

## Post-Design Constitution Check

All five principles remain satisfied. The color tracker is an explicitly limited diagnostic proxy, not automatic identity/quality scoring; package evidence remains derived; provider and paid-call boundaries are unchanged or stricter.

## Complexity Tracking

No violation or complexity exception.
