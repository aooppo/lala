# Quickstart: Coffee Table Live Execution

## Offline verification

```bash
uv run pytest -q tests/test_coffee_table_execution_manifest.py tests/test_coffee_table_live.py
uv run pytest
uv run python -m lala_workflow video validate
```

Expected: all tests pass with fake providers and zero network/paid calls.

## Authorized Live

Run only the exact command in [contracts/cli-and-runtime.md](contracts/cli-and-runtime.md) after rehashing the approved V2 manifest. Do not add retry, replacement, ratio-generation, or alternative-source arguments.

## Handoff inspection

Verify four durable task IDs/raw MP4 hashes, Task 02 last-frame lineage, exact 20-second master, local delivery statuses, cost evidence, blank review fields, unchanged approved-source hashes, and final `READY_FOR_OWNER_REVIEW`.
