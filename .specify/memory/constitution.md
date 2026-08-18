<!--
Sync Impact Report
- Version change: template (unratified) -> 1.0.0
- Added principles:
  - I. Approved Anchors Are Immutable Visual Truth
  - II. Provider-Neutral, Reproducible Core
  - III. Paid Calls Are Explicit and Bounded
  - IV. Offline Tests Gate Delivery
  - V. Human Approval and Static-Image Scope
- Added sections:
  - Architecture and Security Constraints
  - Delivery Workflow and Evidence
- Removed sections: none (template placeholders replaced)
- Follow-up TODOs: none
-->
# Lady LaLa Static Image Pipeline Constitution

## Core Principles

### I. Approved Anchors Are Immutable Visual Truth
Files under `assets/approved_anchors/` are the sole authoritative source for Lady LaLa's
identity, body proportions, approved wardrobe, jewelry, hairstyle, and environment. The
workflow MUST NOT overwrite, rename, redraw, crop, transform, or otherwise modify these files.
Any derived asset MUST be stored outside that directory. Every run MUST validate configured
anchor paths and record SHA-256 hashes so unchanged source identity can be proven.

### II. Provider-Neutral, Reproducible Core
Workflow, domain, storage, and reporting code MUST depend on provider-neutral request and result
models plus the `ImageProvider` protocol. Provider-specific translation MUST remain inside the
provider adapter. Every run MUST preserve the resolved configuration, prompt text and hash,
anchor hashes, provider/model identity, task events, normalized results, and review artifact.
Adding a future provider MUST NOT require rewriting the batch runner or reporting layer.

### III. Paid Calls Are Explicit and Bounded
Paid generation MUST be disabled by default. A live Runway call requires all three controls:
an explicit `--live` invocation, `RUNWAY_ALLOW_LIVE_CALLS=true`, and a non-empty
`RUNWAYML_API_SECRET`. Output count, concurrency, retries, polling, and overall execution MUST be
bounded. Tests MUST never make paid calls, and an automated live smoke test MUST generate at most
one image. Secrets and authorization headers MUST NOT be committed, logged, serialized, or
included in errors.

### IV. Offline Tests Gate Delivery
Configuration, manifest and anchor validation, hashes, prompt resolution, request translation,
timeouts, retry limits, secret redaction, serialization, dry-run behavior, review generation,
and keyframe promotion MUST have unit or mocked integration coverage. All offline tests MUST pass
before a checkpoint is complete. External provider behavior MUST be mocked in automated tests;
network or paid generation is not acceptable test setup.

### V. Human Approval and Static-Image Scope
Subjective identity, quality, MTL readiness, and video-keyframe approval MUST remain explicit
human decisions. Review fields MUST start blank; the system MUST NOT fabricate approval or an
identity score. This project is limited to static-image candidates and approved static
keyframes. Voice cloning, talking avatars, lip sync, final video generation/editing, ComfyUI,
Coze orchestration, Shopify integration, and automatic MTL approval are outside the scope.

## Architecture and Security Constraints

- Python 3.11 or newer is the supported runtime for the MVP.
- Long prompts MUST live in versioned files under `prompts/`, not in Python source.
- Actual Runway request fields, model names, reference syntax, limits, ratios, polling, and output
  behavior MUST be based on current official Runway API documentation and recorded in project
  research/configuration; web-UI behavior is not evidence for API behavior.
- Provider inputs MUST be validated before submission and normalized results MUST not expose
  provider SDK objects outside the adapter.
- Live failures MUST stop after configured retry/timeout limits and MUST NOT trigger an
  uncontrolled paid-call loop.
- Generated outputs and runtime run records MUST be stored outside approved anchors and excluded
  from version control except deliberate sanitized fixtures.

## Delivery Workflow and Evidence

Substantial features use Spec Kit artifacts in dependency order: specification, implementation
plan, dependency-ordered tasks, implementation, and convergence audit. Requirements MUST trace to
tasks and verification evidence. Each implementation checkpoint MUST update `PROGRESS.md` with
files changed, tests executed, results, blockers, and paid-call count. Before handoff, reviewers
MUST verify approved-anchor hashes, run the complete offline test suite, exercise a representative
dry run, inspect metadata and QA artifacts, review secret redaction, and compare delivery against
the active specification's acceptance criteria. A live one-image smoke test is required only when
valid credentials and explicit paid-call permission are available; otherwise it is recorded as
an external blocker, not an implementation failure.

## Governance

This constitution governs all project specifications, plans, tasks, code, tests, and reviews.
Amendments require a documented rationale, an updated Sync Impact Report, and approval from the
project owner. Versioning follows semantic versioning: MAJOR for incompatible principle changes
or removals, MINOR for new principles or materially expanded governance, and PATCH for
non-semantic clarifications. Every plan MUST include a constitution check before and after design,
and every completion audit MUST cite evidence for each applicable principle. Complexity or an
exception to a MUST rule requires written justification in the active feature plan and explicit
project-owner approval.

**Version**: 1.0.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-18
