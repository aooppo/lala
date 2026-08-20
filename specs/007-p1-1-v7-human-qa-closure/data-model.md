# Data Model: P1-1 V7 Human QA Closure

## V7 Review Row

Uses the exact existing video QA header.

| Field group | Validation |
|---|---|
| Provenance | `run_id`, `video_id`, `preset`, and `candidate` exactly match one blank parent-run row |
| Motion closure | Identity, face/age/hair stability, framing/proportions, wardrobe, jewelry, mouth, eyes, camera/background lock, motion, and technical export are explicit human decisions |
| Overall decision | `mtl_review_ready` is explicit true for the winner and false for rejected candidates |
| Authority | `reviewer` is non-empty and `reviewed_at` is timezone-aware for every decided row |
| Notes | Records Camera Lock/Framing mappings, explicit human authority, and reserve status where applicable |

## V7 Selected Candidate

| Field | Rule |
|---|---|
| `candidate_id` | Exactly one canonical V7 ID with a fully passing review; for this closure it is `v7-a-stability-first` |
| `provider_task_id` | Non-empty and equal to the parent provider result |
| `media_path` | Existing file under the fixed run's `outputs/broll` directory |
| `media_sha256` | Equals both parent result evidence and current file bytes |
| `request` | The canonical V7 request with the same shot ID, prompt provenance, keyframe hash, model, duration, and ratio |

## P1-2 Gate Evidence

| Field | Rule |
|---|---|
| `source_run_id` | Fixed successful `motion_v7_live` parent or supported legacy `motion_smoke` run |
| `selected_candidate_id` | V7 unique passing candidate; absent only for single-result legacy smoke |
| `review.path` / `review.sha256` | Immutable external reviewed copy under `outputs/reviews` |
| `status` | `P1_2_LIVE_READY` only after all human/provenance/media checks pass |
| `live_executed` | False during closure and preview |

## Closure Manifest

| Section | Contents |
|---|---|
| Source | Run ID, original package filename/hash, reviewed-copy filename/hash |
| Candidates | All A/B/C IDs, original task IDs, media names/hashes, human outcomes |
| Selection | V7-A winner and explicit HUMAN authority |
| Canonical states | P1-1 live/media/human/selection/MTL states plus P1-2 offline/live readiness |
| Diagnostics | Retained entrypoint-unavailable state and unchanged algorithm/threshold/V6 flags |
| Provider accounting | Zero new tasks/calls for every provider category during closure |

## State Transitions

```text
V7_LIVE_SUCCEEDED + MEDIA_VALID + HUMAN_REVIEW_PENDING
  -> V7_A_HUMAN_PASS + V7_B_FAIL + V7_C_FAIL_RESERVE
  -> P1_1_SELECTED_V7_A + P1_1_MTL_READY
  -> P1_2_LIVE_READY
```

`P1_2_LIVE_READY` is a prerequisite state only. It does not imply `P1_2_LIVE_EXECUTED` and does not satisfy command, credential, environment, input, count, or budget guards.
