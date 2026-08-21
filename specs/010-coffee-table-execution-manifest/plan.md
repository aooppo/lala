# Implementation Plan: Coffee Table Execution Manifest

**Branch**: `010-coffee-table-execution-manifest` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-coffee-table-execution-manifest/spec.md`

## Summary

Revise the rejected V1 contract into V2 without changing business authority or cost: Task 03 binds the frozen product-only PDP image, while Task 04 freezes a runtime dependency on Task 02's deterministically extracted last valid frame. The offline command validates all static hashes, records unknown future hashes as runtime-bound gates, and stops with zero provider construction at Owner manifest review.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Standard library, existing `lala_workflow` domain/configuration/hashing modules

**Storage**: Append-only JSON evidence under `outputs/campaign-execution-manifests/`; versioned text under `prompts/`

**Testing**: pytest with temporary projects and network/provider construction prohibited

**Target Platform**: Local macOS/Linux CLI

**Project Type**: Python CLI workflow

**Performance Goals**: Complete offline preparation in under one second excluding image hashing

**Constraints**: Zero provider/network calls; exact parent SHA; immutable approved sources; four tasks; 5 seconds each; 100 credits; $1.00; concurrency 1; retries/replacements 0

**Scale/Scope**: One frozen parent plan, one rejected V1 identity, four prompt files, three static inputs plus one runtime-derived input, four future requests, one exact twenty-second assembly map, one V2 manifest per invocation

## Constitution Check

- **I. Approved Sources Are Immutable Truth**: PASS. K1/K2/K3 and the frozen PDP source are read and hashed only; new prompts and evidence remain outside approved directories.
- **II. Provider-Neutral, Reproducible Core**: PASS. The campaign module emits plain provider-neutral evidence; no SDK object enters planning.
- **III. Paid Calls Are Explicit, Staged, and Bounded**: PASS. This feature has no Live path and constructs no provider. It records stricter future bounds for later review.
- **IV. Offline Tests and Deterministic Editing Gate Delivery**: PASS. Tests cover exact hashes, failure atomicity, zero calls, and deterministic assembly instructions.
- **V. Human Approval and Staged Video Delivery**: PASS. The manifest is review-pending, has blank human fields, and cannot approve or execute media.

Post-design re-check: PASS. No constitutional exception or complexity waiver is required.

## Project Structure

### Documentation (this feature)

```text
specs/010-coffee-table-execution-manifest/
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
├── coffee-table-task-01-establish-walk-v1.txt
├── coffee-table-task-02-walk-place-v1.txt
├── coffee-table-task-03-product-detail-v1.txt
└── coffee-table-task-04-sit-hero-v1.txt

src/lala_workflow/video/
├── campaigns.py
├── cli.py
└── runner.py

tests/
└── test_coffee_table_execution_manifest.py
```

**Structure Decision**: Keep preparation beside the existing Coffee Table dry-run planner, expose it through the current video campaign CLI, and isolate exact prompt prose in versioned prompt files.

## Design Decisions

1. Preparation takes an explicit parent path and expected SHA, but accepts only the repository's one approved parent identity.
2. Task 1 uses K1; Task 2 uses K3; Task 3 uses frozen product-only PDP `02.jpg`; Task 4 uses no static keyframe and instead depends on Task 02's last valid decoded frame. K2 remains hash-validated but unused.
3. `LAST_VALID_FRAME` is deterministic: count decodable video frames locally, select exactly zero-based index `frame_count - 1`, extract one PNG with logged FFprobe/FFmpeg commands, then record both upstream MP4 and extracted PNG hashes before Task 04 eligibility. The final two-second local hold likewise selects Task 04's last valid decoded frame rather than assuming a literal 5.000-second timestamp. No aesthetic frame choice is allowed.
4. Task 3 generates five seconds but only `[0,3)` is authorized for the master. Task 4 contributes `[0,5)` followed by a two-second local terminal-frame hold. This yields exactly twenty seconds without a fifth paid task.
5. Manifest serialization is canonical repository JSON (`indent=2`, sorted keys, newline), written exclusive and fsynced before its SHA is returned.
6. No code path in this feature imports or constructs `RunwayMotionProvider`.
