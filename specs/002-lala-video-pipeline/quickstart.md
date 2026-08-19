# Quickstart: Reproducible Lady LaLa Video Pipeline

## 1. Install and verify local tooling

```bash
uv sync --extra dev
uv run pytest
ffmpeg -version
ffprobe -version
```

Tests block network access and make zero paid calls.

## 2. Verify immutable inputs and the owner-supplied voice

The owner package has already been imported without altering bytes. It provides:

```text
assets/approved_keyframes/lady-lala-home-context-v0.7.png
assets/approved_keyframes/lady-lala-home-context-v0.7.provenance.json
assets/voice/source/lady-lala-canonical-clip-00-v1.0.wav ... clip-07-v1.0.wav
assets/voice/metadata/canonical-source-manifest-v1.0.0.json
assets/scripts/product-page.txt
assets/scripts/tooltip.txt
assets/scripts/homepage.txt
```

The keyframe uses audited `owner_supplied_legacy_asset` provenance because the repository has no
genuine Goal 1 promoted keyframe. The canonical WAVs are clone-source inputs, not per-script
narration. Never rename or rewrite any imported source to fit configuration.

The owner supplied HeyGen voice ID `7a738e1ced454de6b92d2c76a6ccb8c0` (`Lady LaLa v1`) for
read-only verification and bounded smoke use. It is not production-approved merely because it is
configured. Do not recreate, delete, or replace it, copy canonical clips into
`assets/voice/approved/`, or add clone-source clips to `script_audio`.

The CLI safely loads only the project-root `.env` with process values taking precedence. It never
prints secret values or records the file path. If the file contains only lowercase `voice_id`, run
the explicit migration command; the lowercase name is never silently consumed:

```bash
uv run python -m lala_workflow video voice init-env
```

With `HEYGEN_API_KEY` and canonical `HEYGEN_VOICE_ID` configured, run the read-only check:

```bash
uv run python -m lala_workflow video voice verify \
  --voice-id-env HEYGEN_VOICE_ID
```

Expected success is `VERIFIED_FOR_SMOKE` with safe metadata and a query-stripped preview URL, not
`PRODUCTION_APPROVED`. Only after its real verification run ID/time is recorded may the profile
advance to `approved_for_smoke`.

## 3. Validate

```bash
uv run python -m lala_workflow video validate
```

Until the voice has real read-only verification evidence, this exits 4 without creating a run:

```text
BLOCKED_EXTERNAL: Goal 2 requires verified owner-supplied HeyGen voice evidence or approved per-script narration WAVs.
```

After smoke approval is configured, it reports validated hashes, scripts, audio mode, presets,
provider evidence dates, and FFmpeg availability without provider calls.

## 4. Preview the independent motion smoke

```bash
uv run python -m lala_workflow video motion-smoke-test \
  --keyframe pilot_home_context \
  --model gen4_turbo \
  --duration 5 \
  --ratio 1280:720 \
  --variations 1 \
  --max-runway-credits 25 \
  --dry-run
```

Expected: one five-second request, 25 estimated credits, zero provider calls, and no HeyGen,
voice, narration, or talking-review dependency.

## 5. Preview the short talking validation

```bash
uv run python -m lala_workflow video talking-smoke-test \
  --preset tooltip \
  --variations 1 \
  --max-provider-cost-usd 1.00 \
  --dry-run
```

Expected: one run directory with thirteen artifacts, one approved keyframe/audio/script hash set,
resolved request previews, expected call counts/cost evidence, blank QA decisions, and zero paid
calls.

## 6. Preview all pilot workflows

```bash
uv run python -m lala_workflow video generate --preset tooltip --dry-run
uv run python -m lala_workflow video generate --preset product_page --dry-run
uv run python -m lala_workflow video generate --preset homepage --dry-run
```

Inspect `shot-plan.json`, `cost.json`, and `summary.md` for bounded talking/motion alternatives and
at most two final edits. No provider client is constructed in dry run.

## 7. Run live stages only when their existing flags and budgets authorize them

Required local environment state:

```text
VIDEO_ALLOW_LIVE_CALLS=true
VIDEO_LIVE_SMOKE_TEST=true
HEYGEN_API_KEY=<non-empty local secret>
HEYGEN_VOICE_ID=7a738e1ced454de6b92d2c76a6ccb8c0
```

Then, and only with explicit owner authorization:

```bash
uv run python -m lala_workflow video talking-smoke-test \
  --preset tooltip \
  --variations 1 \
  --max-provider-cost-usd 1.00 \
  --live
```

This first live invocation must request exactly one eight-to-twelve-second talking result. Copy
the run's blank QA evidence, then review visual identity, face, hair, wardrobe, jewelry, lip sync,
mouth/teeth, eyes, background, motion, audio, and synchronization in the copy. Never edit the run:

```bash
mkdir -p outputs/reviews
cp runs/SMOKE_RUN_ID/review.csv outputs/reviews/SMOKE_RUN_ID-review.csv
```

After all required fields in the copied CSV pass, optionally validate three talking-only
alternatives before the broader pilots:

```bash
unset VIDEO_LIVE_SMOKE_TEST
uv run python -m lala_workflow video talking-smoke-test \
  --preset tooltip \
  --variations 3 \
  --smoke-run-id SMOKE_RUN_ID \
  --smoke-review-file outputs/reviews/SMOKE_RUN_ID-review.csv \
  --max-provider-cost-usd 1.00 \
  --live
```

For approved cloned-voice Mode B, configure provider `heygen_voice`, model `starfish`, the approved
private voice ID/version, output format `wav`, and any approved language/speed/sample-rate values
in `configs/voice-profile.yaml`. The workflow sends the exact immutable script and records the
generated WAV's provider request ID and provenance. Prefer Mode A's approved script-matched WAV
when available.

An independent Runway live smoke additionally requires `VIDEO_MOTION_LIVE_SMOKE_TEST=true`, a
non-empty `RUNWAYML_API_SECRET`, and the explicit 25-credit cap. It is not gated by talking QA.
Never turn any live flag on merely to make an acceptance command pass.

## 8. Generate, select, and assemble

```bash
uv run python -m lala_workflow video generate \
  --preset tooltip \
  --smoke-run-id SMOKE_RUN_ID \
  --smoke-review-file outputs/reviews/SMOKE_RUN_ID-review.csv \
  --motion-smoke-run-id MOTION_SMOKE_RUN_ID \
  --motion-smoke-review-file outputs/reviews/MOTION_SMOKE_RUN_ID-review.csv \
  --talking-variations 1 \
  --motion-variations 1 \
  --max-provider-cost-usd 1.00 \
  --max-runway-credits 25 \
  --live

uv run python -m lala_workflow video assemble \
  --run-id RUN_ID \
  --selection-file selections.json
```

Generate product-page and homepage alternatives only after tooltip review. Assembly makes no paid
provider calls and records every FFmpeg command.

If approved brand assets are absent, assembly creates deterministic derived graphics visibly
marked `DRAFT / NOT MTL APPROVED` and reports `REVIEW_READY_DRAFT_ASSETS`. Such a candidate may be
reviewed but cannot be promoted.

## 9. Report and promote

```bash
uv run python -m lala_workflow video report --run-id RUN_ID
uv run python -m lala_workflow video promote \
  --run-id RUN_ID \
  --candidate CANDIDATE_ID \
  --review-file outputs/reviews/RUN_ID-review.csv
```

Promotion succeeds only after explicit MTL readiness, reviewer, and reviewed time are present in
the matching external review copy. It copies the candidate and records the review digest and
provenance; it never mutates run evidence, moves media, skips versions, or overwrites files.

## 10. Completion checks

- Recompute all approved-anchor/keyframe/voice/script hashes and compare baselines.
- Run the full offline test suite and the three production-input dry runs.
- Inspect exactly thirteen artifacts per run and one blank-human-field QA row per candidate.
- Scan versioned files and run/output evidence for credentials, Bearer values, and authorization
  headers.
- Record paid-call count and any missing live authority/input as an external blocker in
  `PROGRESS.md`.
