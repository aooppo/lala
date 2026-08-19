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

`request.json` also records the operator-supplied USD/credit ceilings and whether one unknown-cost
call was accepted. Budget checks occur before provider construction and before each upload,
speech, talking-video, or Runway submission. Local editing cost is never mixed into provider cost.

## QA CSV header

```csv
run_id,video_id,preset,candidate,visual_identity,face_stability,age_stability,hair_stability,body_proportions,wardrobe,jewelry,lip_sync,mouth,teeth,eyes,background,motion,audio_identity,pronunciation,script_match,audio_video_sync,technical_export,mtl_review_ready,reviewer,reviewed_at,notes
```

The first four fields are populated. All remaining fields are empty for each new candidate. The
system never infers a pass or approval.

Smoke provider results also reference FFprobe evidence (container, duration, dimensions, codecs,
pixel format, average frame rate, audio presence, sample rate, channels, and bit rate) plus hashes
for first/middle/last frames and a contact sheet. Provider source URLs are query-stripped; partial
downloads are never renamed to final artifacts.

## Deterministic names

Candidates use:

```text
lady-lala-tooltip-candidate-v001.mp4
lady-lala-product-page-candidate-v001.mp4
lady-lala-homepage-candidate-v001.mp4
```

Approved copies use `lady-lala-<preset>-approved-vN.mp4`. Allocation scans existing files and
chooses the next positive version; existing files are never overwritten.
