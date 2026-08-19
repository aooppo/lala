# Implementation Plan: Reproducible Lady LaLa Video Pipeline

**Branch**: `fix/goal2-production-readiness` | **Date**: 2026-08-19 | **Spec**:
[spec.md](spec.md)

**Input**: Feature specification from `specs/002-lala-video-pipeline/spec.md`

## Summary

Extend the existing provider-neutral static-image CLI with a separate, reproducible video domain.
The video workflow validates immutable genuine Goal 1 promotions or a narrowly audited
`owner_supplied_legacy_asset` keyframe, approved voice/audio, canonical voice-cloning sources, and
byte-exact MTL scripts; resolves bounded talking and motion shot plans; supports zero-call dry
runs; performs guarded asynchronous provider work; assembles selected media deterministically with
FFmpeg; and writes append-only request, hash, event, result, edit, cost, QA, and summary evidence.

HeyGen v3 is the default first talking-shot adapter because its documented image subject accepts
the approved keyframe and approved audio directly. A Runway `gwm1_avatars` talking adapter is also
supported when configuration maps the keyframe hash to a previously approved custom avatar ID.
Runway `gen4_turbo` remains the default motion/B-roll model, with `gen4.5` configurable for higher-
cost motion. Voice Mode A (existing approved WAV) remains preferred. Mode B uses the owner-supplied
HeyGen Starfish voice only after read-only verification, advances it no further than approved-for-
smoke without human QA, and retains the provider-neutral voice protocol. Independent Runway motion
smoke, explicit pre-construction budgets, technical contact sheets, and deterministic local brand
graphics are added before a minimal tooltip candidate can be assembled.

## Technical Context

**Language/Version**: Python 3.11 or newer

**Primary Dependencies**: Pillow, PyYAML, `python-dotenv`, `runwayml==5.15.0`, HTTPX, local
FFmpeg/FFprobe

**Storage**: Immutable approved inputs under `assets/`; keyframe provenance beside approved
keyframes; canonical voice-source manifests under `assets/voice/metadata/`; append-only
JSON/YAML/JSONL/CSV/Markdown run records under `runs/<run_id>/`; derived media under categorized
`outputs/` paths

**Testing**: pytest unit tests, fake-provider integration tests, fake-command FFmpeg tests, and one
local FFmpeg export smoke test when FFmpeg is installed; all automated network access blocked

**Target Platform**: macOS and Linux operator CLI with Python and FFmpeg available

**Project Type**: Single Python package and command-line application

**Performance Goals**: Complete a valid dry run within 60 seconds; live provider concurrency is one
by default; metadata writes complete incrementally before external work advances

**Constraints**: No source mutation, script rewriting, fabricated QA/costs, automatic approval,
networked automated tests, or paid calls without all guards and an explicit provider budget;
provider task IDs are never resubmitted; talking and motion first-smoke scopes remain independent
one-result workflows

**Scale/Scope**: Three offline presets, one five-second motion smoke, one eight-to-twelve-second
talking smoke, at most three talking and three motion alternatives per applicable shot, at most
two final edits, and paid end-to-end remediation limited to the tooltip preset

## Constitution Check

*GATE: PASS before research; PASS after design.*

- **Approved sources**: PASS. Inputs are read-only, directory-contained, content-validated, and
  hashed. The legacy-keyframe branch requires package-level provenance and forbids generated-run
  fields; ordinary Goal 1 promotion checks remain unchanged. Provider-derived avatars and every
  generated file remain outside approved directories.
- **Provider-neutral reproducibility**: PASS. Video orchestration depends only on talking, motion,
  and voice protocols plus normalized domain types. SDK/HTTP payloads remain in adapters.
- **Paid-call staging**: PASS. Dry run cannot instantiate providers. Live work requires `--live`,
  `VIDEO_ALLOW_LIVE_CALLS=true`, provider-specific smoke/full flags, credentials, explicit budgets,
  bounded limits, and prior-stage evidence. Motion smoke is independent from talking approval.
- **Offline tests and deterministic editing**: PASS. Providers and downloads are faked in tests;
  deterministic editing uses logged FFmpeg commands with no-overwrite semantics.
- **Human approval**: PASS. QA decisions start blank, shot selections are explicit inputs, and
  promotion requires a reviewed candidate, copies it with provenance, and rejects draft graphics.
- **Official provider behavior**: PASS. Request fields, API version, model names, limits, and dated
  pricing sources are recorded in `research.md` and configuration.
- **Delivery evidence**: PASS. Requirements trace through `tasks.md`; completion includes dry runs,
  artifact inspection, source-hash comparison, tests, secret scans, and convergence.

Post-design re-check: the provider contracts keep Runway, HeyGen, local editing, storage, and CLI
boundaries separate. No constitution exception or complexity waiver is required.

## Project Structure

### Documentation (this feature)

```text
specs/002-lala-video-pipeline/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── configuration.md
│   ├── providers.md
│   └── run-artifacts.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
assets/
├── approved_anchors/              # unchanged Goal 1 authority
├── approved_keyframes/            # Goal 1 promotions or audited owner-supplied copies + provenance
├── voice/
│   ├── source/
│   ├── approved/
│   └── metadata/                  # hash-pinned canonical clone-source manifests
└── scripts/                       # owner-supplied immutable MTL copy

configs/
├── anchor-manifest.yaml
├── brand-assets.yaml
├── keyframe-manifest.yaml
├── script-manifest.yaml
├── voice-profile.yaml
├── video-presets.yaml
└── providers.yaml

prompts/
├── talking-motion-v1.txt
├── home-broll-v1.txt
└── product-broll-v1.txt

src/lala_workflow/
├── env.py
├── audio/
│   ├── __init__.py
│   └── validation.py
├── editing/
│   ├── __init__.py
│   └── ffmpeg.py
├── video/
│   ├── __init__.py
│   ├── assembly.py
│   ├── cli.py
│   ├── config.py
│   ├── costing.py
│   ├── downloads.py
│   ├── domain.py
│   ├── execution.py
│   ├── graphics.py
│   ├── naming.py
│   ├── planning.py
│   ├── promotion.py
│   ├── prompts.py
│   ├── reporting.py
│   ├── review.py
│   ├── runner.py
│   ├── selection.py
│   ├── scripts.py
│   ├── storage.py
│   ├── validation.py
│   └── voice.py
├── providers/
│   ├── talking_base.py
│   ├── motion_base.py
│   ├── voice_base.py
│   ├── heygen_talking.py
│   ├── heygen_voice.py
│   ├── runway_talking.py
│   └── runway_video.py
└── cli.py

runs/                               # ignored runtime evidence
outputs/
├── audio/
├── talking_shots/
├── broll/
├── graphics/
├── edits/
├── final/
└── approved_videos/

tests/
├── fixtures/video/
├── integration/
└── unit/
```

**Structure Decision**: Keep Goal 1 modules and commands intact. New video domain, storage, and
providers are namespaced so image batch/storage/reporting code continues to depend only on
`ImageProvider`. Shared primitives are limited to hashing, redaction, and serialization. The CLI
adds a `video` command group rather than changing existing command meanings.

## Implementation Phases

### Phase A — Immutable inputs and configuration

Create normalized source directories, strict generated-promotion and narrowly separate
owner-supplied legacy-keyframe validation, hash-pinned canonical voice-source manifest validation,
script byte preservation and source attribution, voice Mode A/Mode B resolution, and bounded
preset/provider loading. Canonical clone-source WAVs remain registered source material and never
stand in for per-script narration or profile approval.

### Phase B — Domain, planning, and dry-run evidence

Add provider-neutral requests/results, deterministic run and candidate identifiers, per-preset
shot-plan expansion, smoke-test reduction, call/cost preview, thirteen-file run initialization,
blank QA schemas, and CLI validation/dry-run paths that never instantiate a network client.

### Phase C — Provider adapters and live safety

Implement HeyGen image-plus-audio translation and polling, HeyGen Starfish exact-script speech to
derived PCM WAV, approved-mapping Runway avatar video translation, Runway image-to-video motion
translation, normalized retries/downloads, task-ID non-resubmission, exact live guards, one-result
first smoke, and immutable reviewed-smoke validation before up-to-three talking alternatives.
HeyGen asset/video mutations use documented idempotency; Starfish speech has no documented
idempotency parameter in the current operation and is therefore never automatically replayed.
Tests use HTTPX capturing transports or injected official-SDK fakes and downloaders only.

### Phase D — Editing, review, report, and promotion

Validate media with FFprobe, build no-overwrite FFmpeg commands, assemble explicitly selected or
single-shot sources, record commands and output hashes, generate exact QA rows and costs, report
runs read-only, and copy reviewed candidates into approved versions with provenance.

### Phase E — Verification and handoff

Run targeted and full tests, real local FFmpeg fixture assembly, project validation, all three
input-backed dry runs when authoritative inputs exist, safe missing-input validation otherwise,
artifact/QA/cost inspection, secret scans, pre/post package-member and approved-source hash
comparisons, Spec Kit analysis and convergence, and documentation/progress updates. Copy the
owner-supplied keyframe, three exact-byte scripts, and eight canonical voice sources only after
their package hashes pass. Live work remains blocked until the owner-supplied voice is verified,
credentials and environment permission are present, explicit budgets pass, and each required
human review has occurred.

### Phase F — Production-readiness remediation

Load project-local environment values safely; verify the exact owner-supplied voice read-only;
stage the voice profile as approved-for-smoke; repair HeyGen multipart, failure, idempotency,
capability, and run-local asset reuse contracts; make Runway motion smoke independent; enforce
pre-construction USD/credit budgets; capture actual Runway terminal cost; expand FFprobe evidence
and generate verification frames/contact sheets; turn local graphic shots into hashed approved or
explicit draft edit inputs; block draft promotion; add deterministic crop candidates and CI; then
run the complete offline and staged-live audit without enabling any live flag on the owner's behalf.
For `gen4_turbo`, keep prompt text optional per the pinned official SDK while still supplying a
versioned non-empty prompt for the configured smoke preset.

## Complexity Tracking

No constitution violations require justification.
