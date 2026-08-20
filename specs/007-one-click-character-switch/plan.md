# Implementation Plan: One-Click Character Switch

**Branch**: `codex/phase1-character-switch` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-one-click-character-switch/spec.md`

## Summary

Add a provider-neutral character-management layer in front of the current static and video
workflows. It imports three required photos into character-isolated immutable staging storage,
maintains versioned profile snapshots and a concurrency-safe single-active registry, adapts a
selected character plus the existing scene into the legacy `AnchorManifest` contract, creates
explicit preview-only static and motion evidence, and switches production identity only after one
final human Approve & Activate action. A one-page optional Streamlit UI and character CLI share the
same application service. Existing prompts, providers, production promotion gates, run schemas,
and legacy evidence remain compatible.

## Technical Context

**Language/Version**: Python 3.11+ (tested with the repository's current Python 3.13 environment)

**Primary Dependencies**: Pillow, PyYAML, existing Runway/HTTP dependencies; optional
`streamlit>=1.49,<2` UI extra; standard-library `fcntl`, `os`, `pathlib`, `hashlib`, `uuid`

**Storage**: Versioned YAML profile snapshots and registry; immutable upload bytes under
`assets/characters/`; copy-only activated sources under `assets/approved_anchors/characters/`;
character build/preview/provenance evidence under `outputs/characters/`

**Testing**: pytest unit and mocked integration tests with the existing autouse socket prohibition,
Pillow fixtures, fake image/motion providers, and local FFmpeg only where media verification needs it

**Target Platform**: Local macOS or Linux filesystem; Streamlit browser UI served locally

**Project Type**: Existing single Python package with CLI, optional local web UI, and file-backed
application services

**Performance Goals**: Validate/import three ordinary photos and persist a profile in under five
seconds excluding provider work; deterministic registry/reference operations complete in under one
second; no unbounded scans, retries, or provider work

**Constraints**: Offline by default; zero automated network/paid calls; approved sources immutable;
no database; one active character; atomic/concurrency-safe activation; existing eight- and
thirteen-artifact production evidence contracts preserved; no automatic human QA

**Scale/Scope**: One local screen, one local operator with possible concurrent sessions, tens to
hundreds of character profiles, three required references plus a small optional set, existing three
static and three video presets

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

- **I. Approved Sources Are Immutable Truth — PASS**: `lala-v1` points to existing bytes. Candidate
  uploads stay immutable under staging storage. Activation copies exact bytes into the existing
  authoritative `assets/approved_anchors/characters/` root using exclusive creation and hash
  verification; no derived preview enters approved directories. Before/after full approved-source
  hashes are mandatory.
- **II. Provider-Neutral, Reproducible Core — PASS**: Character domain, storage, resolver,
  selection, service, and preview orchestration depend on provider-neutral models/protocols. Static
  integration adapts to current `AnchorManifest`/`GenerationRequest`; motion preview constructs the
  current provider-neutral `MotionVideoRequest`. Provider SDK objects remain in adapters. New
  evidence records exact profile/reference/prompt/media hashes.
- **III. Paid Calls Are Explicit, Staged, and Bounded — PASS**: Character creation never calls a
  provider. Preview defaults offline and returns `READY_FOR_GENERATION`. Live preview delegates to
  existing exact env/credential/smoke/budget/count/retry/timeout/task-ID gates; tests use fakes only.
- **IV. Offline Tests and Deterministic Editing Gate Delivery — PASS**: New domain, security,
  registry, resolver, reference, static/video preview, activation, CLI, UI-service, and compatibility
  behavior has unit/mocked coverage under the global network block. Existing local media validators
  remain the evidence authority.
- **V. Human Approval and Staged Video Delivery — PASS**: Preview evidence and Subject Lock are
  explicitly diagnostic/preview-only. No existing review CSV is filled. Character activation has a
  separate explicit local-user event and does not promote a production keyframe/video or infer MTL
  readiness.

**Post-design re-check**: PASS. The profile-snapshot plus atomic-registry design avoids a multi-file
partial active-state transaction; the authoritative source promotion is copy-only; the dedicated
preview evidence type cannot satisfy existing production keyframe validation.

## Architecture and Data Flow

```text
Streamlit UI / character CLI
           |
           v
    CharacterService
      |      |      \
      |      |       -> PreviewCoordinator -> existing static runner adapter
      |      |                              -> preview-only motion runner
      |      -> ReferenceSelector -> CharacterResolver + existing scene
      -> CharacterProfileBuilder -> CharacterStorage
                                  -> CharacterRegistryStore (lock + revision CAS)

Approve & Activate:
revalidate staging bytes + previews
 -> copy exact sources into assets/approved_anchors/characters/<id>/
 -> write new immutable profile snapshots for old/new states
 -> atomic registry compare-and-swap
 -> append activation provenance
```

### Registry transaction boundary

Profiles are immutable, versioned snapshots. A state transition writes candidate snapshots first,
then performs one locked, revision-checked atomic replacement of `registry.yaml` that points to the
new snapshots. Readers therefore see either the old registry or the new registry, never an
intermediate combination. Orphan snapshots or approved copies from a failed final replace remain
recoverable evidence and are not made active. The registry file is the sole current-state pointer.

### Source authority boundary

- `assets/characters/<id>/source/`: exclusive-write immutable raw uploads used only while staging.
- `assets/approved_anchors/characters/<id>/`: exact copy-only activated character sources. These
  are authority inputs, never derived media.
- `outputs/characters/<id>/`: builds, static/motion previews, technical checks, and append-only
  events. Production promotion code never scans this tree.
- Existing face/full-body/scene anchors are never copied or changed for `lala-v1`; its compatibility
  profile points directly to them.

### Preview boundary

Static preview requests use the existing static runner with explicit `character_id` and a staging
resolver flag. Their normal run evidence gains optional backward-compatible character provenance.
The selected output is copied into character preview storage as a `STAGING_KEYFRAME_CANDIDATE`.
Motion preview uses that exact candidate with the existing bounded Runway motion request and prompt,
but writes `CHARACTER_PREVIEW_ONLY` evidence under character outputs. It is not added to
`configs/keyframe-manifest.yaml`, `assets/approved_keyframes/`, or production promotion inputs.
Offline preview writes only a plan/status and cannot set `READY_FOR_APPROVAL`.

## Project Structure

### Documentation (this feature)

```text
specs/007-one-click-character-switch/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── service.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
configs/characters/
├── registry.yaml
└── profiles/
    └── lala-v1-v001.yaml

assets/characters/                         # runtime staging sources (gitignored by contents)
assets/approved_anchors/characters/        # activated exact source copies
outputs/characters/                        # runtime build and preview evidence

src/lala_workflow/
├── characters/
│   ├── __init__.py
│   ├── domain.py
│   ├── errors.py
│   ├── storage.py
│   ├── validation.py
│   ├── registry.py
│   ├── builder.py
│   ├── resolver.py
│   ├── references.py
│   ├── preview.py
│   └── service.py
├── ui/
│   ├── __init__.py
│   └── app.py
├── config.py                         # optional character-aware manifest adaptation
├── domain.py                         # optional character provenance on static requests/config
├── runner.py                         # explicit character selection and run evidence
├── reporting.py                      # backward-compatible character summary/provenance
├── cli.py                            # character commands and --character
└── video/runner.py                   # preview-only staging motion entry point

tests/
├── characters/
│   ├── test_domain.py
│   ├── test_validation.py
│   ├── test_registry.py
│   ├── test_resolver.py
│   ├── test_references.py
│   ├── test_preview.py
│   ├── test_service.py
│   └── test_cli.py
├── integration/test_character_static.py
├── test_character_video_preview.py
└── existing regression suite
```

**Structure Decision**: Keep one Python package and add a focused `characters` domain/application
layer plus a thin optional `ui` adapter. Existing static/video modules receive narrow integration
points rather than being rewritten. Runtime character data is file-backed and isolated by project
root so tests can use temporary repositories.

## Verification Strategy

1. Capture all approved-source SHA-256 before changes and compare after each material checkpoint.
2. Use TDD per task phase: domain/serialization, upload security, registry CAS, resolver/selector,
   static provenance, preview-only motion, lifecycle service, CLI, then UI adapter.
3. Run focused tests after each phase and the full network-blocked suite before completion.
4. Run `compileall`, `git diff --check`, secret/signed-URL scan, `validate`, and static 10/5/5 dry runs.
5. Run Goal 2 validation and representative previews in offline mode; inspect blocker/run-count
   behavior where authority inputs are unavailable.
6. Inspect one fake-provider character lifecycle: upload -> build -> static -> motion -> approve ->
   activate, plus reject and rollback, verifying exact hashes and one active record.
7. Launch/import the Streamlit module without UI extras during normal CLI tests, and run a manual
   one-page UI smoke with the UI extra installed if available. No live provider call is authorized.

## Migration and Rollback

- Ship a deterministic `lala-v1` profile and registry pointing at the existing face/full-body
  anchors; keep the shared scene exclusively in the legacy scene manifest.
- Existing commands with no character option resolve registry active; if character configuration is
  absent, fall back to the exact legacy manifest. Old run files are read without rewrite and may be
  labeled `legacy/lala-v1` only in read-time summaries.
- Rollback is `character activate lala-v1`; source/history for newer characters is retained.
- If new character configuration is removed, legacy fallback restores pre-feature behavior without
  changing approved source bytes or historical evidence.

## Observability and Error Handling

- Every build has an append-only event log and a status summary under its character output tree.
- Registry writes record revision, expected/previous/new active IDs, event type, actor source, time,
  and profile hashes; they never include credentials or provider response URLs.
- Low-level decode/config/locking errors are normalized to role-specific Chinese/English UI messages;
  advanced details contain redacted technical codes only.
- Build/profile failures persist a safe FAILED snapshot only after a valid character exists; upload
  validation failure before registration creates no profile.

## Complexity Tracking

No constitution violation or exception is required. Versioned profile snapshots add a small number
of files but are the simplest way to keep atomic active-state switching while preserving immutable
profile provenance without a database.
