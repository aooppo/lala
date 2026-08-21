# Data Model: Candidate 16 Keyframe Publish

## Review Package

| Field | Rule |
|---|---|
| schema/status | Exact supported V2 values; status starts review-ready |
| character | Active Candidate 16 ID, profile hash/version, registry revision |
| candidates | Exactly the manifest candidates; unique ID/path/hash and formal role |
| review | Same seven identity rows; selected rows have only applicable PASS fields plus attribution |

Role-required QA:

- K1 `pilot_home_context`: identity/age/hair/eyes/mouth/body/wardrobe/jewelry/hands/scene/product geometry/product finish/wine glass/no extra people/no text-logo/video readiness.
- K2 `pilot_talking_medium_closeup`: identity/age/hair/eyes/mouth/body/wardrobe/jewelry/no extra people/no text-logo/video readiness.
- K3 `pilot_product_present`: same complete scene/product/interaction field set as K1.

## Approved Role Authority

| Field | Rule |
|---|---|
| candidate ID / formal role | Must be one of the Owner selection and match package evidence |
| character ID/profile hash | Must match the active package character at mutation time |
| staged/approved path and SHA | Project-relative; approved copy is exact-byte identical |
| package manifest/review path and SHA | Immutable provenance references |
| source run/task | Truthful generated/retained source provenance from V2 manifest |
| reviewer/approved time | Non-empty and timezone-aware |

State: `REVIEWED` to `PROMOTED`; any gate failure leaves the candidate unpromoted.

## Keyframe Set

| Field | Rule |
|---|---|
| set ID/version | Safe unique ID and positive version |
| character | Exactly the sole active character |
| members | Exactly K1/K2/K3, each unique by candidate, role, path, hash |
| provenance | Promotion record and review hashes for every member |
| member digest | Deterministic digest of the normalized three-member payload |
| created time | Timezone-aware |

State: immutable `BUILT`; publication is represented separately.

## Publish Event and Registry

Publish event fields: schema, event ID, event type, set ID, manifest path/hash, member digest, character, reviewer authority reference, prior/new revision, timezone-aware time.

Registry fields: schema, revision, current set ID/path/hash, character, publish event path/hash, updated time. Transition is `absent/revision N` to `revision N+1`; the event and immutable set must validate before replacement.

## Goal 2 Binding

Fields: schema, revision, active character/profile, published registry revision, set/path/hash, K1/K2/K3 candidate/path/hash/role, V7 classification, bound time. Preflight returns either `GOAL2_READY` or a precise blocker.

## Coffee Table Preview

Fields: run ID, dry-run status, character and set binding, product/PDP, wardrobe, room semantics, performance constraints, six storyboard beats totaling 20 seconds, talking/TTS/lip-sync booleans all false, ratio strategies, recommended/fallback live projections, provider submissions 0, paid calls 0, creation time.

## Candidate 16 V7 Human Review and Registration

Review fields use the exact video QA schema. V7-B has all Owner-supplied applicable decisions true, `mtl_review_ready=true`, explicit reviewer, timezone-aware review time, and winner notes. V7-A/V7-C preserve exact provenance, `mtl_review_ready=false`, reviewer/time, and supplied non-selection reasons; non-applicable audio/lip-sync fields remain blank.

Registration fields: schema/status, character and K1 identity/hash, parent and recovery run IDs, reviewed-copy path/hash, winner candidate/media/task/prompt evidence, all three canonical candidate task/media/prompt facts, parent/recovery relationship, registration time, provider submissions 0, paid calls 0. State transition is `READY_FOR_OWNER_CANDIDATE16_V7_REVIEW` → `CANDIDATE16_V7_HUMAN_QA_PASS` → `GOAL2_READY`.
