# Lady LaLa Reproducible Media Workflow

This project implements two staged, reproducible workflows. Goal 1 validates approved Lady LaLa
anchors, generates bounded static candidates, and promotes reviewed images to approved video
keyframes. Goal 2 consumes those approved keyframes with an approved Lady LaLa voice and exact MTL
scripts to produce talking-shot alternatives, Runway motion/B-roll, deterministic FFmpeg edits,
blank human QA sheets, and review-gated approved video copies.

The workflow never rewrites MTL copy, auto-approves identity/voice/lip sync, or deploys to Shopify.
ComfyUI migration, Coze orchestration, unrelated website work, automatic creative approval, and
automatic MTL approval remain out of scope.

## Requirements and setup

- Python 3.11 or newer.
- macOS or Linux.
- Internet access only for installation, official documentation checks, and explicitly authorized
  live Runway calls. Validation, dry runs, and automated tests are offline-capable.

Using `uv`:

```bash
uv sync --extra dev
uv run python -m lala_workflow validate
```

Using a standard virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m lala_workflow validate
```

The production dependency is pinned to the verified official Python SDK `runwayml==5.15.0`.

## Goal 2 video pipeline

Goal 2 is provider-neutral by responsibility:

```text
Approved keyframe + exact MTL script + approved voice/audio
    -> talking/lip-sync alternatives
    -> optional Runway motion/B-roll
    -> human shot selection
    -> deterministic FFmpeg assembly and exact audio replacement
    -> blank candidate QA
    -> explicit MTL review and copy-only promotion
```

HeyGen v3 image-plus-audio is the default talking adapter because it accepts a local approved
keyframe and approved audio directly. Runway `gwm1_avatars` is available only when configuration
maps the exact keyframe SHA-256 to a previously human-approved custom avatar UUID; the workflow
never creates that avatar implicitly. Runway image-to-video (`gen4_turbo`, with configurable
`gen4.5`) is the motion/B-roll adapter. Ordinary edits stay local in FFmpeg.

### Required authoritative inputs

The owner-supplied `lala-goal2-authoritative-inputs-v1.0.0.zip` has been imported without changing
member bytes. The repository now contains:

```text
assets/approved_keyframes/lady-lala-home-context-v0.7.png
assets/approved_keyframes/lady-lala-home-context-v0.7.provenance.json
assets/voice/source/lady-lala-canonical-clip-00-v1.0.wav ... clip-07-v1.0.wav
assets/voice/metadata/canonical-source-manifest-v1.0.0.json
assets/scripts/product-page.txt
assets/scripts/tooltip.txt
assets/scripts/homepage.txt
```

No genuine Goal 1 promoted keyframe exists locally. The imported pilot keyframe therefore uses the
separate audited `owner_supplied_legacy_asset` branch with the package name/hash, package-relative
source path, keyframe hash, and owner-approval reference. It has no invented Goal 1 run/output ID,
provider/model/prompt claim, reviewer, or approval timestamp. Ordinary generated keyframes still
require the complete Goal 1 promotion schema.

The three scripts are exact-byte MTL Appendix A source copies with version `1.0.0`, SHA-256, and
per-script source references in `configs/script-manifest.yaml`. The eight WAVs are canonical Lady
LaLa voice-cloning source material only. They are not product-page, tooltip, or homepage narration
and do not satisfy the approved voice gate.

The owner-selected HeyGen voice ID `7a738e1ced454de6b92d2c76a6ccb8c0` is configured, but the
versioned profile remains `pending` until a read-only API verification proves that the current
account can read `Lady LaLa v1` as a private Starfish-compatible voice. A successful verification
may advance it only to `approved_for_smoke`; `production_approved` still requires human preview
and talking-QA decisions. Approved per-script narration WAVs remain an alternative and take
precedence when their exact script hashes match.

Configuration remains credential-free:

- `configs/keyframe-manifest.yaml`: approved path/hash and branch-specific provenance. Genuine Goal
  1 promotions use run/output/reviewer/time; the current legacy asset uses package audit fields.
- `configs/script-manifest.yaml`: MTL source, immutable policy, version, exact path, and SHA-256 for
  each script.
- `configs/voice-profile.yaml`: either `approved_audio` with one approved WAV/hash/script-hash
  mapping per script, or an approved `cloned_voice` provider/model/voice ID.
- `configs/video-presets.yaml`: bounded shot composition and provider/model selection.
- `configs/providers.yaml`: dated official capabilities, pricing sources, and safety maxima only.

Approved anchors, keyframes, voice files, and scripts are immutable. Derived audio/media goes only
under categorized `outputs/` paths. Until the configured voice is read-only verified as
`approved_for_smoke` (or approved per-script WAVs are supplied), talking validation and previews
stop before run allocation/provider construction with the sole blocker:

```text
BLOCKED_EXTERNAL: Goal 2 still requires a real approved HeyGen Starfish/private Lady LaLa voice profile or approved per-script Lady LaLa narration WAVs.
```

### Validate and preview without provider calls

The independent motion smoke preview does not require a voice, narration, or talking review:

```bash
uv run python -m lala_workflow video motion-smoke-test \
  --keyframe pilot_home_context --model gen4_turbo --duration 5 \
  --ratio 1280:720 --variations 1 --max-runway-credits 25 --dry-run
```

After verifying and approving the remaining voice profile/audio:

```bash
uv run python -m lala_workflow video validate
uv run python -m lala_workflow video talking-smoke-test \
  --preset tooltip --variations 1 --max-provider-cost-usd 1.00 --dry-run
uv run python -m lala_workflow video generate --preset product_page --dry-run
uv run python -m lala_workflow video generate --preset tooltip --dry-run
uv run python -m lala_workflow video generate --preset homepage --dry-run
```

Preview validates anchor/keyframe/script/audio/prompt hashes, resolves the shot plan and provider
capabilities, calculates call counts, estimates only supportable costs, and writes request evidence.
It never constructs a provider client. Defaults generate alternatives at shot level: up to three
talking takes, three motion takes per applicable shot, and two local final edits. Product-page and
homepage plans use one full-script talking performance and reuse its opening/closing deterministically
around selected B-roll, so the approved audio and script are not duplicated.

An accepted video run contains exactly:

```text
runs/<run_id>/
├── request.json
├── resolved-config.yaml
├── script.txt
├── script-hash.json
├── audio-hash.json
├── keyframe-hash.json
├── shot-plan.json
├── task-events.jsonl
├── provider-results.json
├── edit-commands.txt
├── review.csv
├── cost.json
└── summary.md
```

Every Goal 2 run artifact is append-only. The generated `review.csv` stays blank evidence; copy it
to `outputs/reviews/<run_id>-review.csv` before entering subjective decisions. Smoke approval and
promotion verify that the copy matches the run/candidate provenance and record its SHA-256.

### Staged live workflow

The project-root `.env` is loaded with `override=False`; an existing process value always wins.
Tests and CI disable developer `.env` loading. Inspecting environment status exposes only
`configured`/`missing` and value length, never values. A lowercase `voice_id` is not consumed;
explicitly migrate it with `video voice init-env`.

Verify the existing voice read-only before any speech/video call:

```bash
uv run python -m lala_workflow video voice verify \
  --voice-id-env HEYGEN_VOICE_ID
```

The result is `VERIFIED_FOR_SMOKE`, never automatic production approval. Optional preview audio
goes only under `outputs/audio/voice_preview/<run_id>/` and remains unreviewed.

Never run live commands without owner authorization, explicit provider budgets, and approved
inputs. The independent first Runway stage requires exact `VIDEO_MOTION_LIVE_SMOKE_TEST=true`,
one five-second `gen4_turbo` result, and at most 25 credits. It emits the MP4, FFprobe metadata,
first/middle/last frames, contact sheet, task ID, estimated/actual credits, hashes, and blank QA.

The first talking test is separately restricted to one 8–12-second result:

```bash
export VIDEO_ALLOW_LIVE_CALLS=true
export VIDEO_LIVE_SMOKE_TEST=true
export HEYGEN_API_KEY='set-locally-do-not-commit'
uv run python -m lala_workflow video talking-smoke-test \
  --preset tooltip --variations 1 --max-provider-cost-usd 1.00 --live
```

For the approved Runway-custom-avatar talking path, select `--provider runway_talking`, configure
the exact approved digest mapping, and provide `RUNWAYML_API_SECRET` instead. A task ID is persisted
immediately and is never resubmitted automatically. Polling/download retries, concurrency, total
timeout, and variation counts remain bounded.

Copy both smoke runs’ blank QA sheets and review only the copies. Full pilot generation requires
all talking/motion QA pass fields, MTL readiness, reviewer, and timezone-aware review time, plus
both immutable review copies. The motion copy is supplied with
`--motion-smoke-run-id` and `--motion-smoke-review-file`.

```bash
mkdir -p outputs/reviews
cp runs/LALA-VIDEO-SMOKE-RUN/review.csv \
  outputs/reviews/LALA-VIDEO-SMOKE-RUN-review.csv
# Fill only the copied CSV with a CSV-safe editor.
```

After that one result passes review, the talking-only validation can be expanded to three
sequential alternatives without weakening the first-live gate:

```bash
unset VIDEO_LIVE_SMOKE_TEST
uv run python -m lala_workflow video talking-smoke-test \
  --preset tooltip \
  --variations 3 \
  --smoke-run-id LALA-VIDEO-SMOKE-RUN \
  --smoke-review-file outputs/reviews/LALA-VIDEO-SMOKE-RUN-review.csv \
  --max-provider-cost-usd 1.00 \
  --live
```

### Runway motion smoke and post-smoke visual selection

Motion smoke is a separate Runway-only stage. Its live boundary is fixed at one `gen4_turbo`
result, exactly five seconds, and no more than 25 Runway credits:

Motion Smoke defaults to the bounded `prompts/home-broll-v3.txt`. v3 uses a locked-off camera,
keeps Lady LaLa stationary and fully visible, and stays within Runway's 1000 UTF-16-unit prompt
limit. Its external P1-1 review found camera/framing drift despite stable identity, age, and
wardrobe, so it is not human-QA approved. The v4 smoke solved camera/framing drift and retained
identity stability, but human QA failed eyes, mouth, and motion; it is not MTL-ready.
The v5 eye/mouth strategy corrected the prolonged eye closure and mouth opening, but external
review found global camera/framing translation, so v5 is not MTL-ready. `prompts/home-broll-v6.txt`
combines v4's pixel-position camera lock with v5's eye/mouth/subject lock; its single live smoke is
awaiting human QA. It does not change the default, homepage establishing shot, or P1-2
motion-variation prompts. The
older v1 and v2 prompts remain available for historical evidence; v2 is immutable and is not used
for new requests. The homepage establishing shot remains configured to use v3.

```bash
export VIDEO_ALLOW_LIVE_CALLS=true
export VIDEO_MOTION_LIVE_SMOKE_TEST=true
export RUNWAYML_API_SECRET='set-locally-do-not-commit'
uv run python -m lala_workflow video motion-smoke-test \
  --keyframe pilot_home_context --model gen4_turbo --duration 5 --ratio 1280:720 \
  --max-runway-credits 25 --live
```

Copy the smoke run's blank QA sheet to `outputs/reviews/`, fill the motion/technical pass fields,
MTL readiness, reviewer, and timezone-aware review time in that copy only. Then generate one to
five alternatives (start with two additional variations) from the same keyframe and exact smoke
prompt. For `gen4_turbo`, the estimate is five credits per second, so the cap must cover
`5 * duration_seconds * variations`. The command calls Runway only;
it does not invoke HeyGen, talking, voice, or the complete pilot:

```bash
uv run python -m lala_workflow video motion-generate \
  --keyframe pilot_home_context --model gen4_turbo --duration 5 --ratio 1280:720 \
  --variations 3 \
  --motion-smoke-run-id LALA-VIDEO-MOTION-SMOKE-... \
  --motion-smoke-review-file outputs/reviews/LALA-VIDEO-MOTION-SMOKE-...-review.csv \
  --max-runway-credits 75 --live
```

Every invocation writes the standard thirteen-artifact append-only bundle and blank `review.csv`.
Use `--dry-run` to validate the same smoke/review/hash/cap/variation gates with zero provider
submissions.

For the P1-2 planning checkpoint only, `motion-generate --dry-run` may add
`--motion-smoke-qa-attested`. This records the owner's supplied Smoke-QA status without changing
the blank review copy or authorizing Live; the flag is rejected on any Live invocation. The three
design candidates and exact prompt files are documented in
`specs/003-post-smoke-motion-variations/p1-2-motion-variation-plan.md`.

Mode B uses the same `HEYGEN_API_KEY` only when `configs/voice-profile.yaml` identifies an
explicitly approved `heygen_voice` / `starfish` private voice ID. Exact script bytes are submitted
to HeyGen speech generation, and the downloaded audio is converted to a derived PCM WAV with its
request ID and script hash recorded. An approved per-script WAV remains preferred whenever one is
configured.

```bash
export VIDEO_ALLOW_LIVE_CALLS=true
export HEYGEN_API_KEY='set-locally-do-not-commit'
export RUNWAYML_API_SECRET='set-locally-do-not-commit'
uv run python -m lala_workflow video generate \
  --preset product_page \
  --smoke-run-id LALA-VIDEO-SMOKE-RUN \
  --smoke-review-file outputs/reviews/LALA-VIDEO-SMOKE-RUN-review.csv \
  --motion-smoke-run-id LALA-VIDEO-MOTION-SMOKE-RUN \
  --motion-smoke-review-file outputs/reviews/LALA-VIDEO-MOTION-SMOKE-RUN-review.csv \
  --max-provider-cost-usd 1.00 \
  --max-runway-credits 100 \
  --live
```

Run the same command for `tooltip` and `homepage`. Multi-shot generation stops at
`AWAITING_SELECTION`; it never guesses preferred takes. Remove credentials/permission from the
shell after the authorized stage.

### Select, assemble, report, and promote

Create a human selection YAML outside the run record:

```yaml
source_run_id: LALA-VIDEO-...
reviewer: MTL reviewer name
selected_at: "2026-08-19T13:00:00+08:00"
selections:
  talking_performance: product_page-talking_performance-v001
  product_interaction: product_page-product_interaction-v001
  reward_visual: product_page-reward_visual-v001
```

Use artifact IDs from the source run’s `provider-results.json`; required shot IDs come from
`shot-plan.json`.

```bash
uv run python -m lala_workflow video assemble \
  --run-id LALA-VIDEO-SOURCE-RUN --selection-file selection.yaml --final-edits 2
uv run python -m lala_workflow video report --run-id LALA-VIDEO-ASSEMBLY-RUN
```

Assembly makes zero provider calls. It normalizes scale, letterboxing, frame rate, and codec;
trims/reuses the selected talking performance; intercuts chosen B-roll; replaces/normalizes audio
from the approved WAV; optionally crossfades the second edit; refuses overwrite; logs the exact
argument-safe FFmpeg commands; and validates/hashes final MP4s. Tooltip assembly resolves a real
reward graphic. If no approved brand source is configured, it creates a deterministic local PNG
under `outputs/graphics/`, overlays it in FFmpeg, marks it `DRAFT / NOT MTL APPROVED`, returns
`REVIEW_READY_DRAFT_ASSETS`, and blocks promotion. AI image generation is never used for exact
marketing text.

An unapproved talking crop can be derived without changing the approved keyframe:

```bash
uv run python -m lala_workflow video keyframe derive-talking-crop \
  --source pilot_home_context
```

The crop and provenance go under `outputs/keyframes/derived/`; no approval or manifest promotion
is inferred. Product-page/homepage live generation requires an independently approved
`talking_medium_closeup` role, while Tooltip smoke may use the original pilot hero.

After human review, copy the assembly run’s blank `review.csv` to `outputs/reviews/`, then set
`mtl_review_ready`, `reviewer`, and timezone-aware `reviewed_at` in the one matching row of that
copy. Promote with the reviewed copy as an explicit immutable input:

```bash
uv run python -m lala_workflow video promote \
  --run-id LALA-VIDEO-ASSEMBLY-RUN \
  --candidate lady-lala-product-page-candidate-v001.mp4 \
  --review-file outputs/reviews/LALA-VIDEO-ASSEMBLY-RUN-review.csv
```

Promotion copies to `outputs/approved_videos/lady-lala-<preset>-approved-vN.mp4`, refuses collisions,
keeps the source, run evidence, and reviewed copy unchanged, and writes adjacent provenance
covering sources, scripts, selected shots, providers/models, hashes, the review-copy digest,
reviewer, and dates.

Provider capability and pricing evidence is dated in
`specs/002-lala-video-pipeline/research.md`. Unknown voice, storage, or provider costs remain JSON
`null`; the workflow never fabricates zero or an aggregate. All Goal 2 automated provider clients,
downloads, clocks, and network behavior are fakes, while one test performs a real local FFmpeg
export.

## Approved anchors

The existing source package is mapped by `configs/anchor-manifest.yaml`:

| Logical role | Authoritative source |
|--------------|----------------------|
| Face identity, age, proportions, hair | `assets/approved_anchors/face/lala-face-front.png` |
| Body, red gown, jewelry, silhouette | `assets/approved_anchors/full_body/lala-red-gown-full-body.png` |
| Decorolala environment, lighting, palette | `assets/approved_anchors/scene/lala-home-decor-scene.png` |

The character-sheet exploration and wardrobe-B images are configured as QA-only references. They
are not sent to generation unless a future preset explicitly selects them.

Approved source files are immutable: do not rename, crop, resize, recompress, redraw, move, or
overwrite them. Derived files belong in `assets/derived/`, `runs/`, or `outputs/`.

## Configuration

- `configs/anchor-manifest.yaml`: approved paths, logical roles, tags, ordering, QA references, and
  anchor-set version.
- `configs/generation.yaml`: default provider/model, verified API/SDK versions, model capabilities,
  supported output dimensions, and cost/time/concurrency guardrails.
- `configs/look-presets.yaml`: baseline identity and product-page presets.
- `configs/scene-presets.yaml`: home-decor preset.
- `prompts/*-v1.txt`: versioned prompt sources. Their exact bytes and resolved text are hashed and
  recorded in every run.

Runway's current `ratio` field is an exact output dimension token such as `1080:1440`, not a free
aspect-ratio label. `--ratio` and `--resolution` are CLI aliases; if both are supplied, they must be
identical. Model and dimension overrides are rejected unless listed in verified capabilities.

## Environment variables and secrets

`.env.example` contains names and safe false/blank defaults only. The CLI loads only the parsed
project-root `.env` with `override=False`; it never searches parent directories.

| Variable | Purpose |
|----------|---------|
| `RUNWAYML_API_SECRET` | Runway API key; required only for live calls |
| `RUNWAY_ALLOW_LIVE_CALLS=true` | Exact explicit paid-call permission |
| `RUNWAY_LIVE_SMOKE_TEST=true` | Restricts live execution to exactly one output |
| `VIDEO_ALLOW_LIVE_CALLS=true` | Separate exact Goal 2 paid-call permission |
| `VIDEO_LIVE_SMOKE_TEST=true` | Restricts the first video test to one short talking result |
| `VIDEO_MOTION_LIVE_SMOKE_TEST=true` | Separately authorizes the first one-result Runway motion smoke |
| `VIDEO_FULL_PILOT_LIVE=true` | Separately authorizes reviewed full pilot shot generation |
| `HEYGEN_API_KEY` | HeyGen key; required only for selected live talking work |
| `HEYGEN_VOICE_ID` | Canonical owner-selected voice ID; lowercase `voice_id` is rejected |

Never commit or print real credentials. The CLI and run storage redact secret values, Bearer
tokens, authorization fields, and data-URI payloads from metadata and errors.

## Validate without a run

```bash
python -m lala_workflow validate
```

This verifies YAML, required roles/presets, approved path containment, image readability/content
and dimensions, unique roles/tags, hashes, prompt versions/tags/length, and provider versions and
capabilities. It creates no run and makes no network call.

## Dry run

Dry run is the default generation mode and can be made explicit:

```bash
python -m lala_workflow generate \
  --preset baseline_identity \
  --count 10 \
  --dry-run
```

Dry run validates all inputs, hashes anchors/prompts, resolves references, expands the batch into
single-output provider-neutral requests, validates Runway capabilities, and writes previews. It
does not construct a Runway client, submit a task, download an output, or consume credits.

When `--seed N` is supplied, candidate 001 uses `N`, candidate 002 uses `N+1`, and so on after the
complete range is validated. When no seed is supplied, seed metadata remains null because seed
behavior is provider-specific.

## Required presets

### Baseline identity

Default: 10 candidates, `1080:1440`, face + full-body anchors.

```bash
python -m lala_workflow generate --preset baseline_identity --count 10 --dry-run
```

The prompt requires the approved red gown, jewelry, hair, age, body proportions, complete figure,
neutral warm studio, empty hands, and no people/text/logo/props/redesign.

### Home decor

Default: 5 candidates, `1920:1080`, face + full-body + approved scene anchors.

```bash
python -m lala_workflow generate --preset home_decor --count 5 --dry-run
```

The prompt preserves identity and the approved look inside the warm-neutral premium Decorolala
environment with realistic commercial lighting and a slightly off-center complete figure.

### Product page clean

Default: 5 candidates, `1080:1440`, face + full-body anchors.

```bash
python -m lala_workflow generate --preset product_page_clean --count 5 --dry-run
```

The prompt produces clear subject separation on a clean warm-neutral background with no extra
people, text, logo, props, or objects in hands.

## Live generation and cost controls

Live execution is refused unless `--live`, explicit environment permission, and a non-empty key
are all present. Defaults cap a run at 10 outputs, concurrency at 2, retries at 3 additional
pre-task submission/download attempts, per-task polling at 900 seconds, and total run time at 1800
seconds. Once a provider task ID exists, failures are recorded and never automatically resubmitted.

The runner sends one Runway task per candidate because the verified Gen-4 Image schema has no batch
count field. It never invents an `output_count` API parameter.

An optional estimated-credit ceiling can be supplied with `--max-estimated-credits`. Because
pricing changes, no price is hardcoded. If a ceiling is set while
`estimated_credits_per_output` is null in configuration, live execution fails closed.

### One-image smoke test

Run only with valid credentials and explicit project-owner paid-call permission:

```bash
export RUNWAYML_API_SECRET='set-locally-do-not-commit'
export RUNWAY_ALLOW_LIVE_CALLS=true
export RUNWAY_LIVE_SMOKE_TEST=true
python -m lala_workflow generate --preset baseline_identity --count 1 --live
```

This is the only automated live test and is capped at exactly one output. Remove the temporary
environment values from the shell when finished. If credentials or permission are unavailable,
complete all offline checks and report:

```text
BLOCKED_EXTERNAL: Runway live smoke test requires valid credentials and explicit paid-call permission.
```

After an authorized smoke test succeeds, a full baseline/home/product live run uses the same
commands with `--live`; each is paid, so review count/concurrency and costs before execution.

## Run records and outputs

Every attempted dry or authorized live run has a unique directory:

```text
runs/<run_id>/
├── request.json
├── resolved-config.yaml
├── resolved-prompt.txt
├── anchor-hashes.json
├── task-events.jsonl
├── result.json
├── review.csv
└── summary.md
```

Live images are downloaded immediately from expiring provider URLs to `outputs/<run_id>/` and
hashed. Run records store only sanitized provider-neutral data and redacted URLs. Inspect a run
without changing it:

```bash
python -m lala_workflow report --run-id LALA-RUNWAY-YYYYMMDD-HHMMSS-PRESET-001
```

## Human QA

`review.csv` has one row per downloaded output. The workflow fills provenance and leaves all
identity, age, hair, body, wardrobe, jewelry, hands, scene, extra-people, text/logo, keyframe/MTL
readiness, reviewer, review time, and notes fields blank. It never fabricates approval.

Review the image, then edit the row using a CSV-safe tool. For keyframe promotion:

- set `video_keyframe_ready` to `true` (also accepted: `yes`, `1`, `approved`, or `pass`);
- fill `reviewer`;
- fill timezone-aware ISO 8601 `reviewed_at`, such as `2026-08-18T22:00:00+08:00`.

MTL readiness remains an independent human field and is not set by promotion.

## Promote an approved keyframe

```bash
python -m lala_workflow promote \
  --run-id LALA-RUNWAY-YYYYMMDD-HHMMSS-PRESET-001 \
  --output-id output-001
```

Promotion verifies the review row, source path, result record, and SHA-256. It copies—not moves—the
source to `outputs/approved_keyframes/`, refuses to overwrite an existing target, and writes an
adjacent JSON record containing source run/image, hash, anchor version, prompt version,
provider/model, reviewer, and approval date.

## Provider abstraction

The runner depends on `ImageProvider` only:

```python
class ImageProvider(Protocol):
    def validate_request(self, request): ...
    def submit(self, request): ...
    def wait(self, task_id, timeout_seconds): ...
    def download_results(self, result, destination, output_id, timeout_seconds, max_retries): ...
```

To add Coze or ComfyUI in a future goal, implement this protocol, add documented capabilities and
a provider factory entry, and reuse the runner/storage/reporting tests. Do not leak provider SDK
objects into domain results or rewrite the batch engine.

## Verified Runway behavior

Implementation evidence is recorded in `specs/001-lala-static-images/research.md`. As verified on
2026-08-18:

- Static endpoint: `POST /v1/text_to_image`.
- API version: `2024-11-06`.
- Implemented models: `gen4_image` and `gen4_image_turbo`.
- References: up to 3 (`gen4_image`), 1–3 (`gen4_image_turbo`).
- Tag syntax: lowercase 3–16 characters matching `^[a-z][a-z0-9_]+$`; prompt use is `@tag`.
- Seed: optional integer 0–4,294,967,295; same seed gives similar rather than guaranteed identical
  output.
- Polling: `GET /v1/tasks/{id}`, no faster than once every 5 seconds.
- Success output: expiring URL list downloaded to owned storage.

Official sources:

- [Runway Text/Image to Image API](https://docs.dev.runwayml.com/api/#tag/Start-generating/paths/~1v1~1text_to_image/post)
- [Runway API Getting Started](https://docs.dev.runwayml.com/guides/using-the-api/)
- [Runway Task Detail API](https://docs.dev.runwayml.com/api/#tag/Task-management/paths/~1v1~1tasks~1%7Bid%7D/get)

## Testing

```bash
uv run pytest
```

All provider clients, task states, clocks, downloads, and images in automated tests are local
fakes. An automatic socket guard makes any attempted network connection fail the test immediately,
so the suite makes zero generation and paid calls.

## Troubleshooting

- **Missing/invalid anchor**: run `validate`; restore the approved source at the configured path or
  correct the manifest mapping. Never alter the image to satisfy validation.
- **Duplicate role/tag**: every manifest role/tag must be unique, including QA references.
- **Prompt tag not selected**: ensure every `@tag` belongs to a reference selected by that preset.
- **Unsupported model/dimension**: choose a value listed under the provider's verified capabilities;
  research the current official model schema before expanding the list.
- **Live call blocked**: supply all three guards. Exact lowercase `true` is required for permission.
- **Smoke test count rejected**: `RUNWAY_LIVE_SMOKE_TEST=true` requires `--count 1`.
- **Timeout/failure**: inspect `task-events.jsonl`, `result.json`, and `summary.md`. Provider terminal
  failures are not automatically resubmitted.
- **Successful task but missing image**: output URLs expire; the live runner downloads immediately.
  A failed download is bounded and recorded.
- **Promotion rejected**: verify `video_keyframe_ready`, reviewer, timezone-aware `reviewed_at`,
  source file existence, and unchanged source hash.
