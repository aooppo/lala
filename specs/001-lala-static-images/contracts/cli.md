# CLI Contract

Commands are invoked as `python -m lala_workflow ...` after installation.

## `validate`

```text
python -m lala_workflow validate [--project-root PATH]
```

Validates all configuration files, required presets, prompt files, anchor source paths/content,
hash generation, and provider capabilities. It does not create a run and never contacts Runway.

On success, prints the anchor-set version, validated logical anchors with hashes, available
presets, supported provider models, API version, and SDK version.

## `generate`

```text
python -m lala_workflow generate
  --preset {baseline_identity,home_decor,product_page_clean}
  [--count N]
  [--provider NAME]
  [--model NAME]
  [--ratio WIDTH:HEIGHT]
  [--resolution WIDTH:HEIGHT]
  [--seed N]
  [--concurrency N]
  [--retries N]
  [--timeout SECONDS]
  [--overall-timeout SECONDS]
  [--max-estimated-credits NUMBER]
  [--dry-run | --live]
  [--project-root PATH]
```

- If neither mode flag is supplied, generation defaults to dry-run.
- `--dry-run` and `--live` are mutually exclusive.
- `--ratio` and `--resolution` are aliases for the provider's exact output dimension. If both are
  supplied they must be identical.
- When a base seed is supplied, candidate `001` receives it and later candidates receive
  sequential values after range validation.
- Success prints the run ID, run directory, mode, request/output counts, and final status.
- A dry run creates all eight required run files with an empty review body and makes zero network
  calls.

Live mode additionally requires `RUNWAY_ALLOW_LIVE_CALLS=true` and `RUNWAYML_API_SECRET`. The
command refuses a live count above one when `RUNWAY_LIVE_SMOKE_TEST=true` is set.

## `report`

```text
python -m lala_workflow report --run-id RUN_ID [--project-root PATH]
```

Validates the run ID/path and prints the sanitized existing `summary.md`. It never contacts a
provider and never mutates the run.

## `promote`

```text
python -m lala_workflow promote
  --run-id RUN_ID
  --output-id OUTPUT_ID
  [--project-root PATH]
```

Reads `review.csv`, `result.json`, and resolved run metadata. It succeeds only when the selected row
has a recognized truthy `video_keyframe_ready` value plus non-empty `reviewer` and valid
`reviewed_at`. It verifies source existence/hash, copies to `outputs/approved_keyframes/` without
overwriting, and writes adjacent promotion metadata JSON.

## Exit Status

| Code | Meaning |
|------|---------|
| `0` | Command completed successfully |
| `2` | CLI usage, configuration, validation, or promotion precondition error |
| `3` | Provider submission, task, timeout, or download failure |
| `4` | Live mode blocked by missing explicit permission or credentials |

All user-facing errors are sanitized before printing.
