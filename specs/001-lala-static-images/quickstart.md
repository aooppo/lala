# Quickstart Validation Guide

## Prerequisites

- Python 3.11 or newer.
- The existing approved-anchor files remain at their current paths.
- No provider credential is needed for setup, validation, dry runs, or tests.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Validate immutable inputs

```bash
python -m lala_workflow validate
```

Expected: the three authority anchors and their SHA-256 hashes, three presets, Runway API version
`2024-11-06`, SDK version `5.14.0`, and no network/provider task.

## Preview all presets

```bash
python -m lala_workflow generate --preset baseline_identity --count 10 --dry-run
python -m lala_workflow generate --preset home_decor --count 5 --dry-run
python -m lala_workflow generate --preset product_page_clean --count 5 --dry-run
```

For each printed run ID, verify `runs/<run_id>/` contains:

```text
request.json
resolved-config.yaml
resolved-prompt.txt
anchor-hashes.json
task-events.jsonl
result.json
review.csv
summary.md
```

Expected: request counts 10, 5, and 5; zero output rows/files; status `DRY_RUN`; no paid calls.

## Run offline verification

```bash
pytest
```

Expected: unit and mocked integration suites pass without network access.

## One-image live smoke test

Run this only after the project owner explicitly authorizes a paid call and supplies a valid key in
the local environment:

```bash
export RUNWAYML_API_SECRET='set-locally-do-not-commit'
export RUNWAY_ALLOW_LIVE_CALLS=true
export RUNWAY_LIVE_SMOKE_TEST=true
python -m lala_workflow generate --preset baseline_identity --count 1 --live
```

Expected: exactly one provider task, at most one downloaded image, one review row with subjective
fields blank, and a complete run bundle. If credentials or permission are unavailable, record
`BLOCKED_EXTERNAL` and do not repeatedly attempt the call.

## Human review and promotion

1. Open `runs/<run_id>/review.csv`.
2. Review identity, age, hair, body, wardrobe, jewelry, hands, scene, extra people, text/logo,
   keyframe readiness, and MTL readiness.
3. Enter human decisions. To promote, set `video_keyframe_ready` to `true`, provide `reviewer`, and
   provide an ISO 8601 `reviewed_at` timestamp.
4. Promote the selected row:

```bash
python -m lala_workflow promote --run-id RUN_ID --output-id OUTPUT_ID
```

Expected: original output unchanged; copied keyframe and JSON provenance under
`outputs/approved_keyframes/`.

## Completion evidence

- All offline tests pass.
- Representative dry-run artifacts match [the CLI contract](contracts/cli.md).
- Provider behavior matches [the provider contract](contracts/provider.md).
- Approved-anchor hashes equal the baseline recorded in `PROGRESS.md`.
- No secret sentinel or authorization header appears in project/runtime metadata.
