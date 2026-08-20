# Lady LaLa Reproducible Media Workflow — Agent Instructions

## Purpose

This repository has two staged scopes: Goal 1 builds reproducible static-image candidates and
promotes human-reviewed images to approved video keyframes; Goal 2 consumes approved keyframes,
approved Lady LaLa voice inputs, and exact MTL scripts to produce reviewable talking shots,
motion/B-roll, deterministic edits, and final video candidates. Do not add Shopify deployment,
ComfyUI migration, Coze orchestration, automatic face/voice scoring, creative approval, or
automatic MTL approval.

Phase 1 character switching is limited to local import, staging previews, one explicit activation,
rejection, rollback, and compatible static provenance. It does not generate missing character
views, auto-score identity, auto-promote keyframes/videos, or weaken Goal 1/Goal 2 human gates.

## Immutable approved sources

`assets/approved_anchors/` remains the sole authoritative visual-identity source. Goal 2 also
treats `assets/approved_keyframes/`, `assets/voice/source/`, `assets/voice/approved/`, and
`assets/scripts/` as immutable approved-source directories. Never overwrite, rename, move, crop,
resize, redraw, recompress, transform, normalize, rewrite, or delete a source to make it fit code
or configuration. Do not create derived files in any approved-source directory.

Before and after material work, compute SHA-256 for every approved source and compare approved
anchors with the baseline in `PROGRESS.md`. Goal 1 derived files belong under `assets/derived/`,
`outputs/<run_id>/`, or `outputs/approved_keyframes/`. Goal 2 derived files belong under the
categorized `outputs/audio/`, `talking_shots/`, `broll/`, `edits/`, `final/`, or
`approved_videos/` directories. Promotion always copies and records provenance.

Character uploads are immutable staging evidence under `assets/characters/<id>/source/`. Activation
may copy exact validated bytes into `assets/approved_anchors/characters/<id>/`; this is the only
approved character-authority write path and must use exclusive creation plus hash verification.
Character previews stay under `outputs/characters/` and are never production-approved evidence.

## Architecture boundaries

- Batch, storage, CLI, and reporting code depend only on provider-neutral types and
  `ImageProvider` from `src/lala_workflow/providers/base.py`.
- Video planning, storage, execution, editing, and reporting depend only on provider-neutral video
  domain types plus `TalkingVideoProvider`, `MotionVideoProvider`, and `VoiceProvider`.
- Provider SDK objects and request translation stay inside `src/lala_workflow/providers/`.
- Provider request fields and pricing claims must be supported by current official API evidence in
  `specs/001-lala-static-images/research.md` or `specs/002-lala-video-pipeline/research.md`. Never
  infer behavior from a provider web UI.
- Long prompts live in versioned `prompts/*-vN.txt` files. Do not hardcode them in Python.
- Exact MTL copy lives only in `assets/scripts/` with version, attribution, immutable policy, and
  SHA-256 metadata. Never create replacement copy or normalize line endings/punctuation.
- Goal 2 run records are append-only evidence. Keep their `review.csv` blank and copy it to
  `outputs/reviews/` for human decisions; smoke approval and video promotion read the explicit
  reviewed copy without rewriting the run.
- Human review fields start blank. Never fabricate identity, voice, lip-sync, script, keyframe,
  video, MTL-readiness, reviewer, or approval decisions.
- A provider task ID is an idempotency boundary. Poll or download that task within configured
  limits; never create an automatic replacement submission after an ID exists.
- The character registry is the sole current-state pointer. Profile snapshots are immutable;
  activation requires lock/revision CAS, prevalidated source and preview hashes, and one atomic
  registry replacement that always exposes exactly one active character.
- UI and character CLI commands call `CharacterService`; Streamlit imports remain lazy and optional.

Substantial requirement changes use the active Spec Kit lifecycle and keep `spec.md`, `plan.md`,
`tasks.md`, tests, and `PROGRESS.md` traceable and current.

## Commands to run

Install and test:

```bash
uv sync --extra dev
uv run pytest
```

Offline validation and representative previews:

```bash
uv run python -m lala_workflow validate
uv run python -m lala_workflow generate --preset baseline_identity --count 10 --dry-run
uv run python -m lala_workflow generate --preset home_decor --count 5 --dry-run
uv run python -m lala_workflow generate --preset product_page_clean --count 5 --dry-run
uv run python -m lala_workflow character list
uv run python -m lala_workflow character show lala-v1
```

Goal 2 validation and previews, after authoritative inputs are supplied:

```bash
uv run python -m lala_workflow video validate
uv run python -m lala_workflow video talking-smoke-test --preset tooltip --dry-run
uv run python -m lala_workflow video generate --preset product_page --dry-run
uv run python -m lala_workflow video generate --preset tooltip --dry-run
uv run python -m lala_workflow video generate --preset homepage --dry-run
```

When inputs are absent, these commands must return a precise `BLOCKED_EXTERNAL` message and create
no run; never fill pending manifests with invented content.

Run targeted tests while implementing, then run the full suite before checkpoint completion. Tests
must not contact Runway or any other network service.

## Paid-call restrictions

Paid calls are disabled by default. A Goal 1 Runway live call requires all of the following at
execution time:

1. Explicit `--live`.
2. Exact environment permission `RUNWAY_ALLOW_LIVE_CALLS=true`.
3. A non-empty local `RUNWAYML_API_SECRET`.

When `RUNWAY_LIVE_SMOKE_TEST=true`, the requested count must be exactly one. Never run a live test
automatically, paste/print a secret, commit `.env`, serialize credentials/authorization headers, or
increase count/concurrency/retries/timeouts beyond configured bounds without owner review. Do not
resubmit a task after a provider task ID exists.

A Goal 2 video call additionally requires explicit video `--live`, exact
`VIDEO_ALLOW_LIVE_CALLS=true`, every selected provider credential, approved inputs, and the staged
review prerequisite. The first video-provider call also requires exact
`VIDEO_LIVE_SMOKE_TEST=true`, one approved keyframe, 8–12 seconds of approved audio, and exactly one
talking result. Full pilot generation requires the ID of a successful, explicitly reviewed smoke
run. Defaults are three talking/motion variations, two final edits, concurrency one, two retries,
and a 1,800-second provider timeout. Do not run any live video call automatically.

Post-smoke motion selection is a separate Runway-only path. `video motion-smoke-test --live` remains
strictly one `gen4_turbo` variation at exactly five seconds and at most 25 Runway credits. After a
successful, manually reviewed motion smoke, `video motion-generate` may request 1–5 variations
(bounded by `max_motion_variations_per_shot`) only with the same approved keyframe and prompt, an
explicit `--max-runway-credits` cap, exact `VIDEO_ALLOW_LIVE_CALLS=true`, and the Runway credential.
It never constructs HeyGen or talking/voice providers.

## Testing requirements

Maintain unit and mocked integration coverage for configuration, manifest/image validation,
hashes, duplicate role/tag rejection, prompt version/hash/tags, run IDs, dry-run isolation,
provider validation/translation, polling and total timeouts, submission/download retries, secret
redaction, result serialization, exact QA rows, report behavior, and keyframe promotion. All
automated provider clients/downloaders are fakes and make zero paid calls.

Goal 2 coverage also includes exact script/audio/keyframe hashes, pending inputs, shot plans,
HeyGen talking/Starfish voice and Runway request translation, approved custom-avatar mappings,
the exact one-result first smoke and reviewed up-to-three talking validation, live/stage guards,
task-ID-aware recovery, video downloads, FFmpeg commands and real local assembly, costs, exact QA
rows, final naming, reporting, selection, and video promotion. Tests must block network access.

## Definition of Done

Work is done only when:

- The active specification's acceptance criteria are implemented and traced to completed tasks.
- Approved-anchor hashes exactly match the recorded baseline.
- All offline unit and mocked integration tests pass.
- All three presets complete dry runs with the expected 10/5/5 request counts and eight artifacts.
- Run metadata, blank human QA rows, reporting, and keyframe promotion have inspected evidence.
- Secret scans find no credentials, Bearer values, or authorization headers in source, fixtures,
  logs, or run metadata.
- `README.md`, this file, and `PROGRESS.md` reflect current behavior and paid-call count.
- A one-image live smoke test succeeds only when valid credentials and explicit owner permission
  are available. Otherwise report the exact external blocker and do not treat it as a code failure.
- Goal 2 source manifests validate approved keyframe provenance, approved audio or an approved
  cloned-voice profile, and all three exact MTL scripts without changing their bytes.
- All three Goal 2 presets complete zero-call previews and can produce bounded shot alternatives
  under simulated providers; a reviewed selection can produce deterministic final MP4 candidates.
- Every accepted Goal 2 run has exactly thirteen artifacts, known/unknown cost facts, content hashes,
  and one blank QA row per generated candidate.
- Final-video promotion is explicit, review-gated, copy-only, collision-safe, and provenance-complete.
- Approved anchor hashes remain identical to the `PROGRESS.md` baseline; secret scans find no
  credentials, Bearer values, signed query strings, or authorization headers in source or evidence.
- An actual Goal 2 smoke/full candidate stage runs only when its authoritative inputs, credentials,
  budget permission, and preceding human review are present. Otherwise report the precise external
  blocker; absence of external approval is not a code failure.
- Character import/build/preview/activate/reject/rollback tests prove one-active invariants,
  copy-only exact bytes, stale-session/write-failure safety, optional UI loading, deterministic
  character references, preview-only isolation, and legacy static/video compatibility.
