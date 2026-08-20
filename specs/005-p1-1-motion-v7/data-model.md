# Data Model: P1-1 Motion V7 Targeted Fix

## V7 Candidate

| Field | Description | Validation |
|---|---|---|
| `candidate_id` | Canonical experiment identifier | Exactly one of the ordered A/B/C identifiers; unique |
| `prompt_file` | Versioned project-relative prompt source | Under `prompts/`; accepted by existing prompt loader |
| `experiment_level` | Motion ladder rung | `stability_first`, `natural_micro_motion`, or `controlled_upper_bound` |
| `motion_intent` | Human-readable bounded movement description | Non-empty |
| `provider` | Planned provider | `runway` |
| `model` | Planned provider model | Supported configured motion model |
| `duration_seconds` | Planned duration | Supported configured duration |
| `ratio` | Planned output ratio | Supported configured ratio |
| `live_allowed` | Authorization state | Must be exactly `false` |

## Subject Lock Comparison

| Field | V6 baseline | V7 before real video |
|---|---:|---|
| `x_drift_px` | -14.0 | null / PENDING |
| `y_drift_px` | 10.0 | null / PENDING |
| `width_change_pct` | -8.641975 | null / PENDING |
| `height_change_pct` | -3.496503 | null / PENDING |
| `max_scale_change_pct` | 13.580247 | null / PENDING |
| `tracking_success_rate_pct` | 100.0 | null / PENDING |
| `diagnostic_status` | OUTSIDE_THRESHOLD | null / PENDING |

The comparison always includes `human_qa_authority: not_automatic` and cannot write review fields.

## V7 Dry-Run Record

One normal video run containing exactly three planned `MotionVideoRequest` records, candidate metadata, pending comparison, zero provider result rows, exactly three blank review rows, and estimator-derived known/unknown cost facts.
