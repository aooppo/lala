# Tasks: Coffee Table V3 Semantic Recovery

## Phase 1 — Protected baseline

- [X] T001 Verify branch, historical task IDs/costs, final master, current review package, and protected SHA inputs in `outputs/` and `runs/`.
- [X] T002 Inspect TASK-01, TASK-02, and TASK-04 sampled frames and document the seating violation without changing media.

## Phase 2 — Owner evidence [US1]

- [X] T003 [US1] Implement append-only Owner rejection CSV/JSON evidence in `src/lala_workflow/video/coffee_table_v3_recovery.py`.
- [X] T004 [US1] Add rejection/root-cause and wine-glass-correction assertions in `tests/test_coffee_table_v3_recovery.py`.

## Phase 3 — Source-frame review [US2]

- [X] T005 [US2] Implement seven deterministic TASK-02 frame extractions and blank Owner selection in `src/lala_workflow/video/coffee_table_v3_recovery.py`.
- [X] T006 [US2] Add source-frame SHA, candidate list, and empty-selection tests in `tests/test_coffee_table_v3_recovery.py`.

## Phase 4 — V3 proposal [US3]

- [X] T007 [US3] Add V4 sofa-seating prompt in `prompts/coffee-table-task-04-sofa-hero-v4.txt`.
- [X] T008 [US3] Implement protected V3 dry-run manifest, hard gates, reuse analysis, and zero-cost authorization in `src/lala_workflow/video/coffee_table_v3_recovery.py`.
- [X] T009 [US3] Add a dedicated offline CLI mode in `src/lala_workflow/video/cli.py` and `src/lala_workflow/video/runner.py`.

## Phase 5 — Validation

- [X] T010 Execute the V3 dry-run against the current worktree and inspect output hashes.
- [X] T011 Run focused tests, full regression, validators, compile, diff check, secret scan, and protected-source verification.
- [X] T012 Update `PROGRESS.md` with this zero-call checkpoint and its evidence paths.
