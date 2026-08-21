# CLI Contract: External K2 and Dual Keyframes

## Import

```bash
uv run python -m lala_workflow video keyframe import-candidate \
  --source PATH --candidate-id ID --role talking_medium_closeup \
  --source-reference TEXT
```

Returns ID, `READY_FOR_K2_HUMAN_REVIEW`, staged path/hash, provenance, and blank review. Creates no approved authority/provider call.

`ID` is a safe lowercase slug. `PATH` may be a project-relative local path or explicit local
absolute path, but a relative path containing `..`, a direct symlink, invalid/oversized image,
extension/MIME mismatch, duplicate candidate directory, or any target collision is rejected. The
stored source identity is only the basename; bytes are never transformed. `created_by` is the
stable owner source declaration emitted by the workflow and is not an approval or a CLI-supplied
reviewer.

## Promote

```bash
uv run python -m lala_workflow video keyframe promote-candidate \
  --candidate-id ID --review-file outputs/reviews/ID-review.csv
```

Exclusively creates exact approved bytes/provenance and registers the role. Failure leaves no partial authority. Do not run for the real candidate in this delivery.

The review must be a regular non-symlink copy under `outputs/reviews/`, retain the exact ordered
`external-k2-review/v1` header and candidate identity, contain one row, literal `PASS` in all eleven
decision columns, a non-empty reviewer, and timezone-aware ISO-8601 `reviewed_at`. The immutable
candidate-local review must still be blank. Promotion rejects drift, wrong role/source type,
duplicate K2 authority, or any approved media/provenance/manifest collision.

## Pilot

```bash
uv run python -m lala_workflow video generate --preset product_page \
  --talking-keyframe K2_ID --motion-keyframe pilot_home_context --dry-run
```

Selectors may be omitted only when each required role is unique. Explicit selections still require matching roles. Talking Smoke uses `--keyframe` for K2; motion-only commands use K1.

Product Page, Tooltip, and Homepage talking paths all require K2. Motion/B-roll and the canonical
V7 prerequisite retain K1. New evidence writes the two authorities independently. Missing or
ambiguous authority blocks before run allocation and provider construction; dry-run never grants
Live authorization.

## Current delivery gate

The import interface is verified and the real candidate is staged at
`READY_FOR_K2_HUMAN_REVIEW`. Promotion remains blocked until the Owner supplies a complete reviewed
copy. Dry-run remains blocked until promotion creates approved K2 authority; neither pending status
nor candidate existence satisfies the production role gate.
