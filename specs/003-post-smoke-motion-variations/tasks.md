# Tasks: Post-Smoke Motion Variations

## Phase 1: Specification and safety

- [X] T001 Add post-smoke motion variation specification, plan, and traceability artifacts.
- [X] T002 Raise configured motion variation ceiling to five without changing default pilot count.

## Phase 2: CLI and orchestration

- [X] T003 Add bounded motion smoke and post-smoke motion-generate CLI options.
- [X] T004 Implement motion smoke strict guards and motion-only provider orchestration.
- [X] T005 Implement smoke/review/hash/cap/variation validation and complete run bundles.

## Phase 3: Verification and handoff

- [X] T006 Add fake-provider tests for all live guards, dry-run isolation, and Runway-only calls.
- [X] T007 Run targeted/full offline tests, static checks, and record paid-call count and blockers.
- [X] T008 Preserve PR #1's complete test baseline while repairing Python 3.13 protocol
  introspection compatibility; add no collection filters or weakened gates.
- [X] T009 Add explicit historical motion-review schema compatibility and incomplete-review
  provider-zero-call tests; retain blank original run QA fields.
- [X] T010 Verify the real smoke review copy remains byte-identical and blank, and exercise CLI
  help, smoke dry-run, synthetic reviewed dry-run, and real-review fail-closed behavior.

## Verification checkpoint — 2026-08-20

- `origin/main` collected 179 node IDs but stopped at the Python 3.13 provider-protocol import
  error; repairing that compatibility restores the two provider-contract tests, giving the
  recorded 181-test production baseline. This branch keeps those 181 tests and adds seven motion
  variation tests, for 188 collected/passing tests.
- `uv run pytest -q`: 188 passed with network blocking active.
- Motion slice: `tests/test_video_motion_variations.py`: 7 passed; fake live submissions were
  Runway-only and dry-run submission count was zero.
- `uv run python -m compileall -q src tests` and `git diff --check`: passed.
- A production motion smoke preview wrote a complete thirteen-artifact bundle with `paid_calls: 0`.
- Existing real smoke evidence `LALA-VIDEO-20260819-154007-MOTION-SMOKE-001` is recognized, but its
  current copied review CSV is blank; live post-smoke generation therefore fails closed with the
  precise manual-QA blocker. No live credentials or owner live permission were present; new paid
  calls in this task: 0.
