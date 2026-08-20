# Implementation Plan: P1-1 V7 Human QA Closure

**Branch**: `main` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-p1-1-v7-human-qa-closure/spec.md`

## Summary

Record the owner's explicit V7 A/B/C review in the immutable external reviewed copy, extend the existing P1-2 motion prerequisite validator to accept a provenance-valid `motion_v7_live` parent with exactly one fully passing selected candidate, prove the gate through the existing zero-call P1-2 preview, and create a separately named closure evidence package. The original run, original blank review, original ZIP, Subject Lock algorithm/thresholds, and V6 baseline remain unchanged.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Python standard library, PyYAML, existing `lala_workflow.video` domain/storage/runner modules

**Storage**: Append-only JSON/YAML/CSV filesystem evidence under ignored `runs/` and `outputs/`; tracked specification and progress Markdown

**Testing**: pytest with fake motion providers and network blocking; local archive/checksum/secret verification

**Target Platform**: Local macOS/Linux CLI with FFmpeg/FFprobe available

**Project Type**: Single Python CLI package

**Performance Goals**: Closure validation completes locally without network access; gate rejection occurs before provider construction

**Constraints**: Zero paid calls; no approved-source mutation; no run-evidence mutation; no original ZIP overwrite; exact three-candidate V7 provenance; no diagnostic fabrication; P1-2 Live remains separately guarded

**Scale/Scope**: One fixed V7 parent run, three reviewed candidates, one selected winner, one new closure package, and a small compatibility extension to the P1-2 prerequisite validator

## Constitution Check

*GATE: Passed before research and passed again after design.*

- **I Approved Sources**: PASS. Only ignored reviewed/package outputs and tracked code/tests/docs change; approved-source bytes are hashed before and after.
- **II Provider-Neutral Core**: PASS. Selection validation uses normalized run evidence and existing review/domain fields; no provider SDK type crosses into orchestration.
- **III Paid Calls**: PASS. Only read-only validation, tests with fakes, and dry-run preview are allowed; provider construction is asserted absent during gate tests.
- **IV Offline Tests**: PASS. New acceptance/rejection paths receive focused mocked coverage, followed by full offline regression, compileall, integrity, and secret checks.
- **V Human Approval**: PASS. The owner decision is copied verbatim into the reviewed copy; no automatic or diagnostic decision is generated.
- **Complexity/Exceptions**: None. The existing motion prerequisite function is extended rather than creating a parallel state or promotion system.

## Project Structure

### Documentation (this feature)

```text
specs/007-p1-1-v7-human-qa-closure/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── review-and-gate.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/lala_workflow/video/runner.py        # review normalization and P1-2 prerequisite gate
tests/test_video_motion_variations.py    # V7 selection/gate and zero-provider regressions
README.md                                # operator-visible closure/gate behavior
PROGRESS.md                              # checkpoint evidence and paid-call accounting

runs/<fixed-v7-run>/                     # append-only source evidence, unchanged
outputs/reviews/                         # explicit human reviewed copy
outputs/packages/                        # original package plus new closure package
```

**Structure Decision**: Reuse the current single-project CLI layout and the existing ignored runtime evidence policy. Do not add a new provider, promotion subsystem, state store, or approved-source output.

## Design

1. Preserve the existing single-result `motion_smoke` validator behavior unchanged.
2. For `motion_v7_live`, require successful parent evidence, the canonical three candidate IDs, matching keyframe/request/result provenance, one artifact per candidate, existing files under `outputs/broll`, and exact recorded hashes.
3. Load all three rows from the external review copy through the exact unified QA schema while verifying the corresponding run rows remain blank and provenance-equal.
4. Require exactly one row to pass all motion closure dimensions plus `mtl_review_ready`, reviewer, and timezone-aware timestamp. Require every non-selected row to contain explicit overall failure and human attribution without inventing dimension-level reasons.
5. Return only the selected V7 request as the P1-2 prompt/keyframe prerequisite so downstream planning references V7-A and never B/C.
6. Keep P1-2 live credential, environment, count, and budget guards in their existing order after the human prerequisite. Use the dry-run preview to demonstrate the new readiness without provider construction.
7. Create a new final closure directory/ZIP containing the original live evidence, copied reviewed CSV, canonical closure manifest, diagnostics status, and deterministic checksums; preserve the old ZIP unchanged.

## Verification Strategy

- Focused tests cover passing V7-A selection, unique-pass enforcement, incomplete/failing rows, provenance mismatch, media hash drift, and zero provider construction.
- Existing motion-smoke acceptance and failed-review P1-2 tests remain green.
- Execute the real reviewed V7 parent through `motion-generate --dry-run` for three planned variations and assert zero submissions/task IDs.
- Verify the original ZIP SHA-256 and integrity before and after closure; verify the new closure ZIP and every checksum.
- Scan tracked/runtime/package evidence for secrets while avoiding secret-value output.
- Run the full offline suite, compileall on `src` and `tests`, `git diff --check`, and approved-source pre/post hashes.

## Complexity Tracking

No constitution violations or additional complexity exceptions are required.
