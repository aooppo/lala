# CLI Contract

The existing top-level static-image commands remain unchanged. Video operations live under the
`video` group.

## Validate

```bash
python -m lala_workflow video validate [--project-root PATH]
```

Validates configuration, directories, manifests, approved keyframes, scripts, voice profile,
prompts, provider capability declarations, and FFmpeg availability. It makes zero provider calls.
Missing production inputs are reported together with paths and required metadata.

## Talking smoke test

```bash
python -m lala_workflow video talking-smoke-test \
  --preset PRESET (--dry-run | --live) \
  [--provider NAME] [--audio PATH] [--keyframe ID] [--variations N] \
  [--smoke-run-id RUN_ID] [--smoke-review-file PATH]
```

- `--dry-run` resolves at most three alternatives but submits none.
- `--live` always reduces the first unapproved smoke run to exactly one result and requires
  `VIDEO_LIVE_SMOKE_TEST=true` in addition to all live guards.
- After that result passes every required QA field in an immutable external review copy,
  `--smoke-run-id` plus `--smoke-review-file` permits a separate, sequential validation run of up
  to three talking-only alternatives. This expanded stage does not require
  `VIDEO_LIVE_SMOKE_TEST`, but it retains the general live permission, credential, duration, and
  concurrency guards.
- Audio duration must be eight to twelve seconds for the live technical validation.
- The output is a video run ID and evidence path.

## Generate shot alternatives

```bash
python -m lala_workflow video generate \
  --preset {tooltip,product_page,homepage} (--dry-run | --live) \
  [--single-shot] [--smoke-run-id RUN_ID] [--smoke-review-file PATH] \
  [--talking-variations N] [--motion-variations N]
```

Live generation requires a passing smoke run ID and a matching human-reviewed copy under
`outputs/reviews/`; the original run QA stays blank. Multi-shot generation stops after downloaded
alternatives and writes `AWAITING_SELECTION`; it does not guess preferred shots.
`--single-shot` permits the configured MVP fallback.

## Assemble selected shots

```bash
python -m lala_workflow video assemble \
  --run-id RUN_ID --selection-file PATH [--final-edits N]
```

Validates selection identities/hashes, invokes deterministic local editing, records commands,
produces at most two final candidates, and creates one blank QA row per candidate. It makes zero
provider calls.

## Report

```bash
python -m lala_workflow video report --run-id RUN_ID
```

Read-only summary of sources, stage/status, providers, outputs, costs, and review artifact.

## Promote

```bash
python -m lala_workflow video promote \
  --run-id RUN_ID --candidate CANDIDATE_ID --review-file PATH
```

Requires explicit MTL readiness, reviewer, and reviewed time in a matching external QA copy under
`outputs/reviews/`; verifies run, candidate, and review hashes; copies only to the next approved
version; refuses gaps and overwrite.

## Common exit codes

| Code | Meaning |
|---|---|
| 0 | Completed requested offline or successful live operation |
| 2 | Invalid configuration/input/selection or integrity failure |
| 3 | Provider task/download failure or partial live result |
| 4 | External blocker: missing authoritative input, credential, permission, or prior approval |

All error output is secret-redacted. No command prints provider credentials or authorization
headers.
