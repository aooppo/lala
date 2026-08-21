# Quickstart: Candidate 16 Keyframe Publish

## 1. Verify implementation offline

```bash
uv run pytest -q tests/test_candidate16_keyframe_sets.py tests/test_coffee_table_campaign.py
uv run python -m compileall -q src tests
git diff --check
```

Expected: all tests pass and fake/guard assertions prove zero provider construction.

## 2. Validate the real Owner review package

After recording only the explicit Owner decisions in the existing V2 `review.csv`:

```bash
uv run python -m lala_workflow video keyframe validate-review-package --package outputs/reviews/candidate16-keyframes-v2
```

Expected: exactly K1-V2-002, K2-002, and K3-V2-002 are selected with role-applicable PASS fields and actual-file hashes matching the manifest.

## 3. Promote, build, publish, and bind

Run the commands from [contracts/cli-and-evidence.md](contracts/cli-and-evidence.md) in order. After each promotion, compare staged and approved SHA-256. After publish, verify the set manifest and publish event hashes before binding.

## 4. Preflight and conditional Coffee Table preview

```bash
uv run python -m lala_workflow video keyframe-set preflight
```

If current historical V7 evidence remains bound to legacy Lady LaLa K1, expected state is `READY_FOR_OWNER_CANDIDATE16_V7_EXECUTION`; stop without a paid call until separately authorized Candidate 16 V7 evidence exists.

After recording the separately authorized Candidate 16 V7-B review:

```bash
uv run python -m lala_workflow video motion-v7-register-review --package outputs/reviews/candidate16-v7
uv run python -m lala_workflow video keyframe-set preflight
```

Expected: V7-B is the unique reviewed winner, all split-run provenance/hash gates pass, preflight returns `GOAL2_READY`, and provider activity remains zero. Then run:

```bash
uv run python -m lala_workflow video campaign coffee-table --dry-run
```

Expected: 20-second motion-only plan, planned 1:1 and 9:16 delivery, zero provider submissions, and zero paid calls.
The terminal state is `READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION`; do not execute Live.

## 5. Completion verification

```bash
uv run pytest -q
uv run python -m compileall -q src tests
git diff --check
uv run python -m lala_workflow validate
```

Recompute the approved-source list and confirm every pre-existing path retains its baseline hash; only explicitly promoted approved keyframes and their new provenance records may be added.
