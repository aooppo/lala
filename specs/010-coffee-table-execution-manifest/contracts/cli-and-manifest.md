# CLI and Manifest Contract

## Command

```bash
uv run python -m lala_workflow video campaign coffee-table \
  --prepare-execution-manifest \
  --parent-plan outputs/campaign-previews/COFFEE-TABLE-DRY-20260821-071433-640204/plan.json \
  --parent-plan-sha256 ed30e4984dd488cde79188e7e327bc4472ab0c331125a0c600d739a0d388ac5f \
  --confirm-owner-authorized-manifest-preparation
```

The command is mutually exclusive with `--dry-run`. It has no `--live` flag and no provider factory input.

## Successful Result

The result contains:

- exact status `READY_FOR_OWNER_COFFEE_TABLE_EXECUTION_MANIFEST_REVIEW`;
- parent plan path and SHA;
- execution manifest path and SHA;
- Task 01–04 summaries;
- assembly summary;
- `provider_submissions: 0`, `provider_task_ids: 0`, `http_requests: 0`, and `paid_calls: 0`.

## Failure Contract

Every mismatch fails before output-directory creation. Existing output identities fail collision-safe. A write failure removes an empty/partial new directory where safe and never changes an existing manifest.

## Manifest Contract

The V2 JSON root contains `schema_version`, `status`, `supersedes`, `parent_plan`, `execution`, `tasks`, `assembly`, `delivery`, `review`, Owner review focus, and zero-call evidence. Task 03 binds the exact product-only PDP path/SHA. Task 04 embeds exact prompt text and a runtime source-lineage contract: Task 02 success/download/hash, `LAST_VALID_FRAME`, deterministic local FFprobe/FFmpeg extraction, extracted PNG hash recording, then eligibility. The final two-second local hold also selects Task 04's `LAST_VALID_FRAME` instead of assuming an exact 5.000-second timestamp. Unknown future hashes are exactly `RUNTIME_BOUND`; no aesthetic frame choice is permitted. Native generation and all paid/provider activity are unauthorized.
