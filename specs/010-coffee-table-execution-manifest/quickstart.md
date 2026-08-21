# Quickstart: Coffee Table Execution Manifest

## Focused offline verification

```bash
uv run pytest -q tests/test_coffee_table_campaign.py tests/test_coffee_table_execution_manifest.py
```

Expected: all tests pass with no network/provider client.

## Prepare the real review manifest

```bash
uv run python -m lala_workflow video campaign coffee-table \
  --prepare-execution-manifest \
  --parent-plan outputs/campaign-previews/COFFEE-TABLE-DRY-20260821-071433-640204/plan.json \
  --parent-plan-sha256 ed30e4984dd488cde79188e7e327bc4472ab0c331125a0c600d739a0d388ac5f \
  --confirm-owner-authorized-manifest-preparation
```

Expected terminal state: `READY_FOR_OWNER_COFFEE_TABLE_EXECUTION_MANIFEST_REVIEW`.

## Inspect evidence

Verify the returned V2 manifest SHA, V1 rejection/supersession, Task 03 PDP SHA, Task 04 runtime lineage, four tasks, six-beat assembly, blank review fields, and all four zero-call counters. Do not set Live permission variables and do not execute a provider command in this checkpoint.
