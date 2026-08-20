# Subject Lock Evidence Contract

## `subject-lock.json`

Required fields include `schema_version=subject-lock-v1`, measurement scope, sampled/tracked counts, tracking success rate, first-to-last X/Y drift, maximum absolute X/Y drift, maximum center distance, first-to-last width/height change, maximum absolute scale change, diagnostic status, and exact thresholds.

Drift/scale values are `null` when evidence is insufficient. Missing tracking is never serialized as zero.

## `subject-trajectory.csv`

Exact header:

```text
frame_index,timestamp_seconds,x,y,width,height,center_x,center_y,dx,dy,distance,width_change_pct,height_change_pct,area_change_pct,tracking_confidence
```

Rows exist for every sampled frame. Tracking-loss rows retain frame/timestamp/confidence and leave geometric fields blank.

## `subject-overlay.png`

Shows the first tracked frame, first and final tracked proxy boxes, center markers, trajectory, measurement-scope label, and diagnostic status. It never modifies source media.

## Integrity

All three files appear in sorted `SHA256SUMS.txt` and the adjacent ZIP. Verification rejects missing/mismatched files, unexpected ZIP membership, or unsafe archive paths. Human review fields remain blank and are outside diagnostic serialization.
