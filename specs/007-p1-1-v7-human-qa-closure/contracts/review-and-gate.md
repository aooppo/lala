# Contract: V7 Review and P1-2 Gate

## Accepted parent evidence

The P1-2 motion prerequisite accepts either:

- the existing successful one-result `motion_smoke` contract; or
- a successful `motion_v7_live` parent with the canonical A/B/C candidates and exactly one artifact per candidate.

The V7 path must validate request/result/keyframe consistency, task IDs, media containment, and current SHA-256 before provider construction.

## Human selection contract

- Review file is an existing external copy under `outputs/reviews`.
- Parent run `review.csv` remains exact-schema and human-field blank.
- External review contains exactly one provenance-matching row per canonical V7 candidate.
- Exactly one row has every required motion closure decision true and `mtl_review_ready=true`.
- Every other row has explicit overall `mtl_review_ready=false`, reviewer, and timezone-aware review time; detailed dimension fields may remain blank when the owner supplied only an overall failure.
- The selected request returned to P1-2 is the request whose `shot_id` equals the unique passing row's `video_id`.

## Rejection contract

Reject before provider construction if any of the following holds:

- parent action/status/candidate set is wrong;
- review is missing, outside `outputs/reviews`, schema-incompatible, duplicated, blank, ambiguous, or provenance-mismatched;
- no candidate or more than one candidate passes;
- a rejected row lacks explicit overall failure or human attribution;
- task ID, artifact path, candidate identity, media containment, or SHA-256 is missing or mismatched;
- selected prompt or keyframe provenance no longer matches current immutable inputs.

## Readiness semantics

Successful validation establishes:

```text
P1_1_V7_HUMAN_QA_PASS
P1_1_V7_SELECTED_CANDIDATE_V7_A
P1_1_MTL_READY
P1_2_OFFLINE_READY
P1_2_LIVE_READY
```

It does not establish `P1_2_LIVE_EXECUTED` and does not perform a Provider request.
