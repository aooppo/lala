# Run Artifact Contract

Every video run directory is `runs/<run_id>/` and contains exactly these thirteen required files:

```text
request.json
resolved-config.yaml
script.txt
script-hash.json
audio-hash.json
keyframe-hash.json
shot-plan.json
task-events.jsonl
provider-results.json
edit-commands.txt
review.csv
cost.json
summary.md
```

`task-events.jsonl` is append-only and includes monotonically ordered event timestamps. All other
artifacts are created once and never rewritten. `review.csv` is blank run evidence, not an edit
surface. A human copies it to `outputs/reviews/`, enters decisions in the copy, and passes that
path explicitly to smoke approval or promotion; provenance records the reviewed copy's SHA-256.

## Cost schema

```json
{
  "voice_cost": null,
  "talking_video_cost": null,
  "motion_video_cost": null,
  "editing_cost": 0,
  "storage_cost": null,
  "total_provider_cost": null,
  "currency": "USD",
  "components": []
}
```

Unknown values remain null. A known component includes provider, model, generated seconds,
attempts, successes/failures, amount, estimated/actual basis, currency, pricing URL, and pricing
date.

## QA CSV header

```csv
run_id,video_id,preset,candidate,visual_identity_pass,face_stability_pass,hair_pass,wardrobe_pass,jewelry_pass,lip_sync_pass,mouth_teeth_pass,eye_motion_pass,audio_quality_pass,audio_sync_pass,background_pass,motion_quality_pass,script_exact_match_pass,technical_export_pass,mtl_review_ready,reviewer,reviewed_at,notes
```

The first four fields are populated. All remaining fields are empty for each new candidate. The
system never infers a pass or approval.

## Deterministic names

Candidates use:

```text
lady-lala-tooltip-candidate-v001.mp4
lady-lala-product-page-candidate-v001.mp4
lady-lala-homepage-candidate-v001.mp4
```

Approved copies use `lady-lala-<preset>-approved-vN.mp4`. Allocation scans existing files and
chooses the next positive version; existing files are never overwritten.
