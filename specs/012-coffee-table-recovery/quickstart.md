# Quickstart: Validate Coffee Table Recovery Preparation

## Prerequisites

- Work from the repository root with the stopped Live run and its raw TASK-01/TASK-02 outputs present.
- Confirm FFmpeg and FFprobe are available.
- Do not set or use Live-call authorization for this workflow.

## 1. Run focused offline tests

```bash
uv run pytest tests/test_coffee_table_recovery.py
```

Expected: exact historical-state, source-hash, local-media, frame-96, timeline, budget, collision, and zero-provider-call tests pass.

## 2. Run repository gates

```bash
uv run pytest
uv run python -m compileall -q src tests
git diff --check
uv run python -m lala_workflow video validate
```

Expected: all offline tests pass; validation reports either ready authoritative inputs or the pre-existing precise external blocker without creating a run.

## 3. Prepare recovery

Use the exact command in [contracts/cli-and-manifest.md](contracts/cli-and-manifest.md).

Expected: one new local cutaway, one frame-96 PNG, and one append-only recovery manifest are created; the response reports `READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW`, zero provider submissions, and zero paid calls.

## 4. Inspect evidence

- Verify historical TASK-01/TASK-02 IDs, hashes, and credits.
- Verify TASK-03 retains its real failed provider ID/error and zero actual credits.
- Verify LOCAL-TASK-03 is three seconds, 1280x720, 24 fps, silent H.264/yuv420p with 72 frames.
- Verify TASK-04 source is exactly TASK-02 frame 96 and the PNG/prompt hashes match.
- Verify timeline duration is exactly twenty seconds and native-ratio generation is unauthorized.
- Rehash original manifest/provider results and every approved source; all must match the before snapshot.

## 5. Validate the authorized V2 continuation offline

```bash
uv run pytest tests/test_coffee_table_recovery_live.py
uv run pytest
uv run python -m lala_workflow validate
uv run python -m lala_workflow video validate
uv run python -m compileall -q src tests
git diff --check
```

Expected: exact one-submit fake-provider tests and real local assembly tests pass with zero network calls. Recompute the V2, historical media/evidence, prompt, frame 92, and approved-source aggregate hashes before any real submit.

## 6. Execute only the Owner-authorized request

With the formal local permission and credential configured, print the final execution plan and run the exact V2 command from [contracts/cli-and-manifest.md](contracts/cli-and-manifest.md). Never repeat the command if a recovery Live authorization/run record exists.

Expected on success: one TASK-04, one 20-second 16:9 master, guarded ratio results, one blank Human Review Package, and `READY_FOR_OWNER_REVIEW`. Do not approve or promote any output.
