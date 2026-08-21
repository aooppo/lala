# CLI and Runtime Contract

## Command

```bash
VIDEO_ALLOW_LIVE_CALLS=true uv run python -m lala_workflow video campaign coffee-table \
  --live \
  --execution-manifest outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json \
  --execution-manifest-sha256 ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea \
  --confirm-owner-authorized-live \
  --max-runway-credits 100 \
  --max-provider-cost-usd 1.00
```

The Live mode is mutually exclusive with dry-run and manifest preparation. All arguments above are required and exact; lower/higher alternate values do not create a different plan.

## Success response

Returns run ID/path, exact manifest identity, four task IDs/raw artifact identities, lineage identity, master/local delivery identities, zero retries/replacements, cost facts, and status `READY_FOR_OWNER_REVIEW`.

## Failure response

Returns a nonzero exit with an append-only run when allocation already occurred. The run records the exact stop state and all known durable task IDs/artifacts. It never submits a later/replacement task.

## Evidence

The run stores authorization/request, task events, provider results, Task 04 lineage, assembly commands, delivery manifest, cost, blank review CSV, and summary. Signed output URLs and credentials are redacted or omitted.
