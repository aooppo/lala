# Implementation Plan: Reproducible Lady LaLa Static Images

**Branch**: `001-lala-static-images` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-lala-static-images/spec.md`

## Summary

Build a Python CLI and library that validates immutable approved anchors, resolves versioned
presets/prompts into provider-neutral single-output requests, previews batches without network
access, and executes explicitly authorized bounded Runway tasks. Each run stores a sanitized,
reproducible artifact bundle, a blank-by-default human QA CSV, and promotion provenance for
reviewed keyframes. Runway-specific validation, data-URI translation, task polling, and download
behavior remain behind the `ImageProvider` protocol.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `runwayml==5.14.0`, PyYAML 6.x, Pillow 11/12.x; standard-library
`argparse`, `dataclasses`, `concurrent.futures`, `csv`, `hashlib`, `json`, and `urllib`

**Storage**: Local files: immutable PNG anchors, YAML configuration, text prompts, JSON/JSONL run
metadata, CSV review sheets, Markdown summaries, downloaded image outputs, and promotion JSON

**Testing**: pytest 8.x with fake provider/SDK clients; no network in automated tests

**Target Platform**: macOS and Linux command line; filesystem paths remain portable

**Project Type**: Single Python package and CLI

**Performance Goals**: All three preset dry runs finish in under 60 seconds on local inputs;
live runs process at most 10 outputs with default concurrency 2

**Constraints**: Approved anchors immutable; dry-run completely offline; paid calls disabled by
default; provider polling no faster than 5 seconds; bounded retries/poll and total timeout;
prompts <= 1000 UTF-16 code units for supported Runway models; references <= 3; local data URIs
<= provider limits; secrets fully redacted

**Scale/Scope**: Three required presets, five current source images (three generation authorities
plus two QA-only references), up to 10 candidates per run, one implemented provider, one CLI

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research gate

| Principle | Planned evidence | Status |
|-----------|------------------|--------|
| Immutable visual truth | Manifest paths are constrained under `assets/approved_anchors/`; tests and final audit compare SHA-256 baselines | PASS |
| Provider-neutral reproducibility | Domain dataclasses and `ImageProvider` protocol isolate Runway; every required run artifact is written | PASS |
| Explicit bounded paid calls | CLI flag + environment permission + secret required; max count/concurrency/retries/timeouts enforced | PASS |
| Offline tests gate delivery | Unit and fake-provider integration tests cover all named behaviors without network | PASS |
| Human approval/static scope | Review fields blank; promotion requires human fields; no video/audio modules | PASS |

### Post-design gate

The data model and contracts preserve all five principles. Runway translation accepts local paths
only until live submission, preventing data-URI expansion in stored previews. The runner expands a
batch into single-output provider requests because the verified `gen4_image` endpoint does not
define a batch count field; no invented parameter is sent. Promotion copies rather than moves the
source. No constitution exceptions or complexity justifications are required.

## Architecture

### Request flow

1. Load and validate YAML configuration and the approved-anchor manifest.
2. Resolve a preset, command-line overrides, prompt text/version/hash, and selected references.
3. Calculate source hashes and create a collision-safe run ID/directory.
4. Expand the requested count into provider-neutral requests with `output_count=1`; derive
   sequential seeds only when the operator supplied a base seed.
5. In dry-run mode, validate capabilities and serialize sanitized previews without constructing a
   provider client or making network calls.
6. In live mode, enforce all three paid-call guards and optional estimated-credit ceiling, then
   submit/wait/download through the protocol with bounded concurrency and retries.
7. Persist normalized results and one blank review row per actual output, even when sibling tasks
   fail; write a final summary.
8. Promote only a review row explicitly marked keyframe-ready with reviewer and review timestamp;
   verify the source hash and preserve the original.

### Provider boundary

`ImageProvider` exposes `validate_request`, `submit`, `wait`, and `download_results`. The domain
request stores local reference paths, tags, hashes, and prompt provenance. `RunwayImageProvider`
translates paths to base64 data URIs only inside `submit`, invokes the official SDK
`text_to_image.create`, polls `tasks.retrieve` with a minimum five-second interval, normalizes all
terminal states, and downloads expiring output URLs immediately. Runner/reporting code never
imports Runway SDK types.

### Retry and timeout semantics

- `max_retries` means additional attempts after the initial submission/download attempt.
- Provider task failure is terminal and is not resubmitted automatically, avoiding duplicate paid
  generations. Retries apply only to pre-task transient submission errors and downloads.
- Each task uses `poll_timeout_seconds`; the executor also enforces `overall_timeout_seconds` and
  stops scheduling further work when exceeded.
- Default polling interval is 5 seconds, matching official guidance that consumers should not
  expect updates more frequently than once every five seconds.

### Cost-estimate semantics

Current provider pricing is not hardcoded. An operator may configure both an estimated credits per
output and a maximum estimated-credit ceiling. If a ceiling is present but no estimate is present,
live validation fails closed. Estimates are recorded as operator-supplied planning metadata, not
claimed as actual provider billing.

## Project Structure

### Documentation (this feature)

```text
specs/001-lala-static-images/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── provider.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
.
├── AGENTS.md
├── PLAN.md
├── PROGRESS.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── assets/
│   ├── approved_anchors/
│   └── derived/
├── configs/
│   ├── anchor-manifest.yaml
│   ├── generation.yaml
│   ├── look-presets.yaml
│   └── scene-presets.yaml
├── prompts/
│   ├── baseline-identity-v1.txt
│   ├── home-decor-v1.txt
│   └── product-page-clean-v1.txt
├── src/lala_workflow/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── domain.py
│   ├── hashing.py
│   ├── prompts.py
│   ├── runner.py
│   ├── reporting.py
│   ├── storage.py
│   └── providers/
│       ├── __init__.py
│       ├── base.py
│       └── runway.py
├── tests/
│   ├── fixtures/
│   ├── integration/
│   └── unit/
├── runs/
└── outputs/
    └── approved_keyframes/
```

**Structure Decision**: A single `src`-layout Python package keeps the provider boundary explicit
without introducing services or deployment infrastructure. Configuration and prompts remain
operator-editable source artifacts; run/output directories hold runtime artifacts.

## Verification Strategy

- Unit-test configuration, manifest integrity, prompt/version/hash handling, run IDs, domain
  serialization, capability validation, redaction, review rows, retries/timeouts, and promotion.
- Mock-integrate the runner with a recording provider to prove dry-run isolation, request expansion,
  result/download persistence, normalized failures, and required artifact coverage.
- Run the CLI against all three presets in dry-run mode and inspect the resulting bundles.
- Compare all five pre-implementation approved-anchor hashes after tests and dry runs.
- Scan tracked/source/runtime fixture files for secret names, bearer headers, and configured test
  sentinel values.
- Do not run the one-image live smoke test without credentials and explicit paid-call permission.

## Migration and Rollback

There is no prior runtime schema or production deployment. Configuration is versioned and new run
directories are append-only. Rollback consists of reverting code/config/spec files while leaving
approved anchors and existing run/output evidence untouched. Promotion never replaces source
outputs, so an erroneous promotion can be reviewed and removed separately without losing the run.

## Observability

Each run records timestamped JSONL events for validation, dry-run completion, submission attempt,
task creation, polling state, retry, download, normalized failure, completion, and promotion. Logs
and serialized event payloads pass through recursive redaction. `summary.md` provides the concise
operator view; JSON/YAML/CSV remain authoritative machine-readable evidence.

## Complexity Tracking

No constitution violations or unapproved complexity are present.
