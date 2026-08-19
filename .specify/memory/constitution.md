<!--
Sync Impact Report
- Version change: 1.0.0 -> 2.0.0
- Modified principles:
  - I. Approved Anchors Are Immutable Visual Truth -> I. Approved Sources Are Immutable Truth
  - II. Provider-Neutral, Reproducible Core -> II. Provider-Neutral, Reproducible Core
  - III. Paid Calls Are Explicit and Bounded -> III. Paid Calls Are Explicit, Staged, and Bounded
  - IV. Offline Tests Gate Delivery -> IV. Offline Tests and Deterministic Editing Gate Delivery
  - V. Human Approval and Static-Image Scope -> V. Human Approval and Staged Video Delivery
- Modified sections:
  - Architecture and Security Constraints
  - Delivery Workflow and Evidence
- Added sections: none
- Removed sections: none
- Follow-up TODOs: none
-->
# Lady LaLa Reproducible Media Pipeline Constitution

## Core Principles

### I. Approved Sources Are Immutable Truth
Files under `assets/approved_anchors/`, `assets/approved_keyframes/`, and approved voice source
directories are the sole authoritative sources for Lady LaLa's visual and voice identity. MTL
script files are the sole authoritative copy source. The workflow MUST NOT overwrite, rename,
redraw, crop, transform, move, or otherwise modify these files or their content. Derived media
MUST be stored outside approved-source directories. Every applicable run MUST validate configured
source paths and record SHA-256 hashes so unchanged identity, audio, and exact script copy can be
proven.

### II. Provider-Neutral, Reproducible Core
Workflow, domain, storage, editing, and reporting code MUST depend on provider-neutral request and
result models plus focused image, talking-video, motion-video, and voice protocols. Provider-
specific request translation and SDK objects MUST remain inside provider adapters. Every run MUST
preserve resolved configuration, exact prompts and scripts with hashes, input hashes,
provider/model identity, task events, normalized results, deterministic editing commands, cost
evidence, and review artifacts. Adding or replacing a provider MUST NOT require rewriting the
orchestration, editing, or reporting layers.

### III. Paid Calls Are Explicit, Staged, and Bounded
Paid generation MUST be disabled by default. A live call requires an explicit `--live`
invocation, the exact provider-appropriate permission environment variable, and a non-empty local
provider credential. Output count, generated duration, concurrency, retries, polling, and overall
execution MUST be bounded. Tests and dry runs MUST make zero paid calls. The first call for a new
video provider or workflow MUST be one short result from one approved input; broader generation
MUST wait for human review of that smoke test. Secrets and authorization headers MUST NOT be
committed, logged, serialized, or included in errors.

### IV. Offline Tests and Deterministic Editing Gate Delivery
Configuration, source validation, hashes, immutable script handling, prompt and shot-plan
resolution, provider translation, timeouts, retry limits, secret redaction, serialization,
dry-run behavior, cost and review generation, deterministic naming, and promotion MUST have unit
or mocked integration coverage. Automated tests MUST use fake provider clients and make no
network or paid calls. Shot assembly, trimming, scaling, transitions, audio replacement,
normalization, synchronization, and final encoding MUST use a logged deterministic local tool
such as FFmpeg where practical. All offline tests MUST pass before a checkpoint is complete.

### V. Human Approval and Staged Video Delivery
Subjective visual identity, voice identity, lip sync, mouth and teeth quality, eye motion,
wardrobe, jewelry, background, MTL readiness, and final approval MUST remain explicit human
decisions. Review fields MUST start blank; the system MUST NOT fabricate approval, quality
scores, or MTL decisions. Video work MUST proceed from approved keyframes, approved voice inputs,
and exact MTL scripts through a short talking-shot validation, shot-level alternatives, local
assembly, and reviewable candidates. Approved outputs MUST be copied with provenance and MUST NOT
replace their source candidates. Talking-video, motion/B-roll, and voice responsibilities MUST
remain separable; no provider may be assigned unsupported capabilities.

## Architecture and Security Constraints

- Python 3.11 or newer is the supported runtime.
- Long prompts MUST live in versioned files under `prompts/`, not in Python source.
- MTL scripts MUST live in immutable source files with version, source attribution, exact content,
  and SHA-256 evidence; the workflow MUST NOT rewrite, shorten, expand, or paraphrase them.
- Actual provider request fields, model names, limits, ratios, duration controls, polling, output
  behavior, and pricing evidence MUST be based on current official API documentation recorded in
  project research/configuration; web-UI behavior is not API evidence.
- Runway is preferred for supported image-to-video, camera/environment motion, and B-roll work.
  Talking or lip-sync work MUST use a dedicated provider when current official Runway APIs do not
  provide a suitable supported capability.
- Provider inputs MUST be validated before submission and normalized results MUST not expose
  provider SDK objects outside adapters.
- A provider task that has returned a task ID MUST NOT be resubmitted automatically. Live failures
  MUST stop after configured retry/timeout limits and MUST NOT trigger an uncontrolled paid-call
  loop.
- Approved audio MAY bypass synthesis and feed the talking-video layer directly. Voice synthesis
  MUST remain optional and provider-neutral.
- Generated outputs and append-only run records MUST be stored outside approved sources and
  excluded from version control except deliberate sanitized fixtures.

## Delivery Workflow and Evidence

Large features and architecture changes use Spec Kit artifacts in dependency order:
constitution, specification, clarification, implementation plan, dependency-ordered tasks,
consistency analysis, implementation, and convergence audit. Requirements MUST trace to tasks
and verification evidence. Each implementation checkpoint MUST update `PROGRESS.md` with files
changed, tests executed, results, blockers, and paid-call count. Before handoff, reviewers MUST
verify every approved-source hash, run the complete offline test suite, exercise representative
dry runs, inspect resolved shot plans, metadata, costs, editing commands, and blank-human-field QA
artifacts, perform secret scans, and compare delivery against the active specification's
acceptance criteria. Live smoke tests and candidate generation occur only with valid credentials,
explicit paid-call permission, and the required preceding human approval; absent authority or
inputs are external blockers, not implementation failures.

## Governance

This constitution governs all project specifications, plans, tasks, code, tests, and reviews.
Amendments require a documented rationale, an updated Sync Impact Report, and approval from the
project owner. Versioning follows semantic versioning: MAJOR for incompatible principle changes
or removals, MINOR for new principles or materially expanded governance, and PATCH for
non-semantic clarifications. Every plan MUST include a constitution check before and after design,
and every completion audit MUST cite evidence for each applicable principle. Complexity or an
exception to a MUST rule requires written justification in the active feature plan and explicit
project-owner approval.

**Version**: 2.0.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-18
