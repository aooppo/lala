# Lady LaLa Reproducible Static Image Workflow

This project validates approved Lady LaLa anchor images, builds controlled static-image requests,
generates bounded Runway batches when explicitly authorized, records complete reproducibility
metadata, creates human QA sheets, and promotes reviewed images to approved video keyframes.

The current scope ends at approved static keyframes. It does not implement talking video, voice
cloning, lip sync, final video editing, ComfyUI, Coze, Shopify, face-recognition approval, or
automatic MTL approval.

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

The production dependency is pinned to the verified official Python SDK `runwayml==5.14.0`.

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

`.env.example` contains names only. This CLI reads the process environment and does not
automatically load `.env` files.

| Variable | Purpose |
|----------|---------|
| `RUNWAYML_API_SECRET` | Runway API key; required only for live calls |
| `RUNWAY_ALLOW_LIVE_CALLS=true` | Exact explicit paid-call permission |
| `RUNWAY_LIVE_SMOKE_TEST=true` | Restricts live execution to exactly one output |

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
