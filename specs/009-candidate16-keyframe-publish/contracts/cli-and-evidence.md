# CLI and Evidence Contract: Candidate 16 Keyframe Publish

## Review and promotion

```bash
uv run python -m lala_workflow video keyframe validate-review-package --package outputs/reviews/candidate16-keyframes-v2
uv run python -m lala_workflow video keyframe promote-reviewed --package outputs/reviews/candidate16-keyframes-v2 --candidate-id K1-V2-002
```

Validation returns selected IDs by formal role, review/manifest hashes, character evidence, and `paid_calls: 0`. Promotion returns staged and approved paths/hashes plus exact-byte status. The same promotion command applies to K2-002 and K3-V2-002. Unsupported or non-selected IDs fail.

## Set build, publish, and Goal 2 binding

```bash
uv run python -m lala_workflow video keyframe-set build --set-id candidate16-keyframe-set-v1 --review-package outputs/reviews/candidate16-keyframes-v2
uv run python -m lala_workflow video keyframe-set publish --set-id candidate16-keyframe-set-v1
uv run python -m lala_workflow video keyframe-set bind-goal2 --set-id candidate16-keyframe-set-v1
uv run python -m lala_workflow video keyframe-set preflight
```

Build is immutable and collision-safe. Publish records an append-only event and advances one revision. Binding snapshots the current set. Preflight makes no run/provider allocation and returns `GOAL2_READY` only if all gates, including character-aware V7 status, pass.

Expected V7 blocker in the current real repository is `READY_FOR_OWNER_CANDIDATE16_V7_EXECUTION` because the approved historical V7 request used legacy SHA `ab53d9...`, not Candidate 16 K1.

After the separately executed Candidate 16 V7 parent/recovery batch and explicit Owner review:

```bash
uv run python -m lala_workflow video motion-v7-register-review --package outputs/reviews/candidate16-v7
uv run python -m lala_workflow video keyframe-set preflight
```

Registration validates exact split-run/task/media/prompt/keyframe/review provenance, writes an exclusive `registration.json`, reports V7-B as the winner, and makes zero calls. Preflight then returns `GOAL2_READY` with the selected Candidate 16 V7-B evidence.

## Coffee Table dry-run

```bash
uv run python -m lala_workflow video campaign coffee-table --dry-run
```

The command accepts no live flag. It refuses to create preview evidence unless Goal 2 preflight is ready. On success it creates a collision-safe preview directory and reports `provider_submissions: 0`, `paid_calls: 0`, exact character/set/product semantics, six storyboard beats, ratio plans, and bounded non-executed live options.

Successful output state is exactly `READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION`. No command in this feature executes Coffee Table Live.

## Error behavior

- Integrity mismatch: `BLOCKED_KEYFRAME_INTEGRITY` or `BLOCKED_PROMOTION_INTEGRITY`.
- Set/publish/binding mismatch: precise fail-closed validation error, no partial current pointer.
- Legacy character-bound V7: `READY_FOR_OWNER_CANDIDATE16_V7_EXECUTION` and estimated three tasks / 15 generated seconds / at most 75 Runway credits; no call.
- Talking-only preset mismatch: `BLOCKED_PRESET_SEMANTIC_MISMATCH`; no call.
