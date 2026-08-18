# Lady LaLa Static Image Workflow — Agent Instructions

## Purpose

This repository builds reproducible Lady LaLa static-image candidates and promotes only
human-reviewed images to approved video keyframes. Static images are the complete scope of this
project. Do not add talking avatars, voice cloning, lip sync, final video generation/editing,
ComfyUI, Coze, Shopify, automatic face scoring, or automatic MTL approval.

## Immutable approved anchors

`assets/approved_anchors/` is the sole authoritative visual-identity source. Never overwrite,
rename, move, crop, resize, redraw, recompress, transform, or delete any file in that directory.
Do not create derived files there. Update `configs/anchor-manifest.yaml` when mapping existing
filenames; do not change source files to fit configuration.

Before and after material work, compute SHA-256 for every approved source and compare it with the
baseline in `PROGRESS.md`. Store derived files under `assets/derived/`, runtime candidates under
`outputs/<run_id>/`, and promoted copies under `outputs/approved_keyframes/`.

## Architecture boundaries

- Batch, storage, CLI, and reporting code depend only on provider-neutral types and
  `ImageProvider` from `src/lala_workflow/providers/base.py`.
- Provider SDK objects and request translation stay inside `src/lala_workflow/providers/`.
- Runway request fields must be supported by current official API documentation recorded in
  `specs/001-lala-static-images/research.md`. Do not infer API behavior from the Runway web UI.
- Long prompts live in versioned `prompts/*-vN.txt` files. Do not hardcode them in Python.
- Run records are append-only evidence. Do not silently rewrite past runs or generated outputs.
- Human review fields start blank. Never fabricate identity, MTL, or keyframe approval.
- Promotion copies the source and records provenance; it never moves or replaces the generated
  image.

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
```

Run targeted tests while implementing, then run the full suite before checkpoint completion. Tests
must not contact Runway or any other network service.

## Paid-call restrictions

Paid calls are disabled by default. A Runway live call requires all of the following at execution
time:

1. Explicit `--live`.
2. Exact environment permission `RUNWAY_ALLOW_LIVE_CALLS=true`.
3. A non-empty local `RUNWAYML_API_SECRET`.

When `RUNWAY_LIVE_SMOKE_TEST=true`, the requested count must be exactly one. Never run a live test
automatically, paste/print a secret, commit `.env`, serialize credentials/authorization headers, or
increase count/concurrency/retries/timeouts beyond configured bounds without owner review. Do not
resubmit a task after a provider task ID exists.

## Testing requirements

Maintain unit and mocked integration coverage for configuration, manifest/image validation,
hashes, duplicate role/tag rejection, prompt version/hash/tags, run IDs, dry-run isolation,
provider validation/translation, polling and total timeouts, submission/download retries, secret
redaction, result serialization, exact QA rows, report behavior, and keyframe promotion. All
automated provider clients/downloaders are fakes and make zero paid calls.

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
