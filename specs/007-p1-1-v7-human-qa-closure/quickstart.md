# Quickstart: P1-1 V7 Human QA Closure

## Preconditions

- Worktree baseline and approved-source hashes are recorded.
- Fixed run `LALA-VIDEO-20260820-075843-MOTION-V7-001` has three successful canonical results.
- Original evidence ZIP SHA-256 is `268842f10553856b821496f8d76662bee2419069b443aeb55f48c7781fcb25ef`.
- No live command or provider environment permission is used.

## Focused validation

```bash
uv run pytest -q tests/test_video_motion_variations.py tests/test_video_review.py tests/test_motion_v7_live.py
```

Expected: V7-A reviewed selection is accepted for the prerequisite, invalid/ambiguous evidence is rejected before provider construction, and existing motion-smoke behavior remains green.

## Offline P1-2 readiness proof

Use the existing `video motion-generate` dry-run with:

- keyframe `pilot_home_context`;
- smoke run ID set to the fixed V7 parent run;
- smoke review file set to its external reviewed copy;
- three variations and a 75-credit planning cap;
- `--dry-run`, never `--live`.

Expected: three planned calls, zero submissions, zero task IDs, zero provider construction, and selected baseline provenance points to V7-A.

## Package validation

Verify both packages independently:

```bash
shasum -a 256 outputs/packages/P1-1-V7-LALA-VIDEO-20260820-075843-MOTION-V7-001-evidence.zip
unzip -t outputs/packages/P1-1-V7-LALA-VIDEO-20260820-075843-MOTION-V7-001-evidence.zip
unzip -t outputs/packages/P1-1-V7-LALA-VIDEO-20260820-075843-MOTION-V7-001-human-qa-closure.zip
```

Recompute every closure `SHA256SUMS.txt` entry from the package root and run the repository secret patterns against the unpacked closure package.

## Full validation

```bash
uv run pytest -q
uv run python -m compileall src tests
git diff --check
```

Recompute approved-source hashes, confirm `tmp/` is untouched, confirm the original run review and original ZIP retain their starting hashes, and report zero provider calls.
