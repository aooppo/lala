# Data Model: Subject Lock Diagnostics

## SubjectLockThresholds

- `max_center_drift_px`: positive number; maximum Euclidean displacement from the first tracked center.
- `max_scale_change_pct`: positive number; maximum absolute width/height percentage change.
- `min_tracking_success_rate`: greater than zero and at most one.

Thresholds classify diagnostics only.

## SubjectBox

- Non-negative `x`, `y`; positive `width`, `height` within its frame.
- Derived `center_x`, `center_y`, and `area`.

## SubjectObservation

- `frame_index`, `timestamp_seconds`.
- Optional `SubjectBox`; absent means tracking failure.
- `tracking_confidence` in `[0,1]`.
- Derived displacement and scale changes relative to the first tracked observation; absent when no box exists.

## SubjectLockResult

- Measurement scope, sampled/tracked counts, success rate.
- First-to-last and maximum position metrics.
- First-to-last width/height changes and maximum absolute scale change.
- `diagnostic_status`: `WITHIN_THRESHOLD`, `OUTSIDE_THRESHOLD`, or `INSUFFICIENT_EVIDENCE`.
- Exact thresholds and ordered observations.

State rules:

```text
insufficient coverage or missing reliable endpoints -> INSUFFICIENT_EVIDENCE
otherwise any center/scale metric exceeds threshold -> OUTSIDE_THRESHOLD
otherwise -> WITHIN_THRESHOLD
```

## MotionReviewPackage

- Source motion MP4 and existing visual/run evidence.
- Blank original review copy.
- Subject JSON, trajectory CSV, overlay PNG, sorted checksum manifest, and deterministic adjacent ZIP.

## P1_2GateEvidence

- Mode (`DRY_RUN` or `LIVE`), immutable smoke/output/keyframe/prompt provenance, optional review path/hash/state, and live authorization derived only from explicit human PASS plus existing guards.
- Dry-run never emits provider construction, submission, task ID, or paid-call evidence.
