# CLI and Evidence Contract: P1-1 Motion V7 Live Batch

## Command

```bash
uv run python -m lala_workflow video motion-v7-live \
  --keyframe <approved-id-or-path> \
  --execute-live \
  --confirm-v7-batch \
  --max-runway-credits <finite-positive-cap> \
  --project-root .
```

The environment must additionally contain exact `VIDEO_ALLOW_LIVE_CALLS=true` and a non-empty local `RUNWAYML_API_SECRET`. The command exposes no candidate selection, subset, skip, or range options.

## Preflight Contract

Before the first provider submission, the command validates the complete A/B/C matrix, approved keyframe, provider settings, final neutral requests, known credit estimates/cap, live authorization, and evidence destination. It writes then verifies immutable request, configuration, keyframe, shot-plan, review, and cost evidence. Any failure produces zero submissions.

## Parent Evidence Contract

Existing thirteen run artifacts are retained. `request.json` and `shot-plan.json` carry the immutable authorized plan and candidate provenance. `provider-results.json` carries:

- parent status and timestamps;
- actual submission attempt/count totals;
- task IDs as a separate list;
- Runway HTTP request count plus a known/unknown flag;
- one ordered result row per A/B/C candidate, including `not_submitted` rows;
- provider status, sanitized error, and validated output references.

`review.csv` contains exactly three rows and every human field is blank. `resolved-config.yaml` records `P1_2_LIVE_BLOCKED_PENDING_P1_1_HUMAN_PASS`. No secret value is serialized.

## Exit Semantics

- Successful A/B/C batch: exit 0, status `SUCCEEDED`, three task IDs.
- Partial/fail-stop batch: non-zero workflow exit, status `PARTIAL` or `FAILED`, preserved evidence, no retry/replacement.
- Preflight/authorization failure: non-zero before provider submission; no paid task.
