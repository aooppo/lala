# Quickstart: External K2 Workflow

## Prerequisites

- Worktree: `/Users/tj/Documents/ChatGPT/lala-lady-lala-pilot-live`
- Branch: `codex/lady-lala-pilot-live`
- Run every command without `--live`; no provider credential is needed.
- Do not proceed to real import until focused and full offline tests are green.

## Verification before real import

```bash
uv run pytest -q tests/test_video_external_keyframes.py \
  tests/test_video_pilot_preflight.py tests/test_video_dry_run.py
uv run pytest -q
uv run python -m compileall -q src tests
uv run python -m lala_workflow video validate
git diff --check
```

Expected: all tests pass, validation succeeds or reports only a precise authoritative-input
`BLOCKED_EXTERNAL`, no run/provider object is created by failed preflight, and all provider/paid
counts remain zero. Compare the ordered approved-source digest to the baseline below before and
after material work.

## Real candidate import — only after green verification

```bash
uv run python -m lala_workflow video keyframe import-candidate \
  --source tmp/k2_candidates/k2_candidate_01.png \
  --candidate-id k2-owner-20260821-01 \
  --role talking_medium_closeup \
  --source-reference "Owner-supplied external K2 candidate, 2026-08-21"
```

Expected source/staged SHA-256:
`111811f7d501850e0ddd2cd4dca1cf4f595453e68c83a987f52c96ecbb488ea6`.
Expected status: `READY_FOR_K2_HUMAN_REVIEW`. Inspect the staged path, provenance path, and blank
review path printed by the command. Confirm every human review field is blank and no approved
keyframe or manifest entry was created.

## Owner review handoff

Copy, do not move or edit, the candidate-local blank baseline:

```bash
cp outputs/keyframes/candidates/k2-owner-20260821-01/review.csv \
  outputs/reviews/k2-owner-20260821-01-review.csv
```

The Owner fills only the review copy. All eleven `*_pass`/readiness fields require literal `PASS`;
`reviewer` must identify the human reviewer; `reviewed_at` must include a timezone such as
`2026-08-21T18:30:00+08:00`; `notes` is optional. The six identity fields and candidate-local blank
review remain unchanged. The workflow never supplies PASS values.

## Commands to display after Owner review — do not execute in this task

```bash
uv run python -m lala_workflow video keyframe promote-candidate \
  --candidate-id k2-owner-20260821-01 \
  --review-file outputs/reviews/k2-owner-20260821-01-review.csv

uv run python -m lala_workflow video generate \
  --preset product_page \
  --talking-keyframe k2-owner-20260821-01 \
  --motion-keyframe pilot_home_context \
  --dry-run
```

Promotion must prove candidate SHA = approved SHA and leave K1/V7 unchanged. The Product Page
dry-run additionally requires the repository's existing approved audio/script and reviewed motion
prerequisites; it records K2 talking and K1 motion separately and makes zero submissions.

## Current checkpoint

Implementation verification is complete. Focused suites passed with 39 tests; the complete offline
suite passed with 302 tests. The real candidate is staged at
`outputs/keyframes/candidates/k2-owner-20260821-01/candidate.png`; source and staged SHA-256 both
equal `111811f7d501850e0ddd2cd4dca1cf4f595453e68c83a987f52c96ecbb488ea6`. Its blank review has one
row and zero nonblank Human fields. Product Page dry-run remains correctly blocked before run
allocation until later explicit Owner review and promotion.

## Baseline captured before implementation

- HEAD: `201611f49b1fcdf26823aec90f5cae81fe69494b`
- Keyframe manifest: `8b9e4eb1eea4222eb20b6b97bdd7f697f9d096573274b706bd6732064ca3a7b5`
- K1 media: `ab53d9d0551bcf926a41072567493cf640815d99ff92503d9bc111ec3ce7b9ca`
- K1 provenance: `2866d1d68062e54f4eeab45cea6e1795994d6019bef6d241f585882e300cb96c`
- V7 keyframe evidence: `9c61d33ef4ad91907a8d85ba5dc88163f6daa6c09fc7046bd67b0270acd0c093`
- V7 provider results: `b935134b92ac074820d5044b98b11bc725222f2ce67c6a043bd768c782b7a19c`
- V7 reviewed copy: `2b6a4b028526d0ccd51042530508f7d383b4a9e3e724f852c069206f99330cea`
- Ordered 26-file approved-source hash-list digest: `b39392cd134ac80470c259419510d8dfd763b2c776a5ef48f0f8875169b1e908`
- Runtime candidate paths remain covered by the existing `outputs/*` ignore boundary; Python, environment, and generated runtime patterns are already present in `.gitignore`.
