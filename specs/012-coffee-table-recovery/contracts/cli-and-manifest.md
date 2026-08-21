# CLI and Recovery Manifest Contract

## Preparation command

```bash
uv run python -m lala_workflow video campaign coffee-table \
  --prepare-recovery \
  --execution-manifest outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json \
  --execution-manifest-sha256 ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea \
  --failed-live-run LALA-VIDEO-20260821-082100-COFFEE-TABLE-LIVE-001
```

`--prepare-recovery` is mutually exclusive with dry-run, execution-manifest preparation, and Live. It accepts no live confirmation, credential, TASK-04 submit flag, retry flag, alternate frame index, alternate product source, or native-ratio option.

## Success response

Returns recovery ID, status `READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW`, parent manifest SHA, failed run ID, local TASK-03 path/SHA/media facts, TASK-04 frame index/path/SHA, prompt path/SHA, recovery manifest path/SHA, actual/projected costs, provider submissions zero, and paid calls zero.

## Failure response

Returns a nonzero offline validation error. No provider is constructed or called. No recovery manifest remains. Only newly allocated partial recovery outputs may be removed; original manifest, original run, provider results, successful raw media, source image, prompts, and approved sources remain untouched.

## Recovery manifest

The JSON document uses schema `candidate16-coffee-table-recovery-manifest/v1` and includes:

- exact parent manifest path/SHA and failed run ID;
- original manifest/provider-results byte hashes;
- historical TASK-01/TASK-02 reuse, real TASK-03 failure, and TASK-04 not-submitted facts;
- LOCAL-TASK-03 source/transformation/media/hash/cost evidence;
- TASK-02 frame-96 extraction and PNG lineage;
- frozen TASK-04 v3 prompt and future request proposal;
- eight exact contiguous timeline segments totaling twenty seconds;
- 16:9 master and guarded-local-only 1:1/9:16 policy;
- actual and projected credit/USD arithmetic;
- zero submission/call/retry/replacement counters;
- separate Owner authorization gate and terminal recovery-review status.

The file is exclusively created, canonically formatted with sorted keys and a trailing newline, then hashed. Any later TASK-04 authorization must identify this exact SHA; preparation itself never submits TASK-04.

## Owner-authorized Recovery V2 Live command

```bash
uv run python -m lala_workflow video campaign coffee-table \
  --live \
  --recovery-live \
  --execution-manifest outputs/campaign-recovery-manifests/COFFEE-TABLE-RECOVERY-20260821-204901-001/coffee-table-recovery-manifest-v2.json \
  --execution-manifest-sha256 e97ea0d34f4ea541ab07e6898083e7a35c3b82502030f8f40a06d58fb43e6cc3 \
  --confirm-owner-authorized-live \
  --max-runway-credits 25 \
  --max-provider-cost-usd 0.25
```

The command is valid only with exact `VIDEO_ALLOW_LIVE_CALLS=true` and a non-empty local `RUNWAYML_API_SECRET`. It accepts no alternate task, frame, prompt, model, duration, ratio, retry, replacement, or native-ratio option.

Success returns the operation/run ID, one provider task ID, TASK-04 artifact and actual/unknown cost facts, master and final-frame evidence, both safe-area outcomes, review-package path/SHA, one submission, zero automatic retries/replacements, and `READY_FOR_OWNER_REVIEW`.

An unknown submit acceptance returns `BLOCKED_SUBMISSION_UNKNOWN`; a terminal/invalid TASK-04 returns `BLOCKED_TASK04_PROVIDER`. Neither state permits another submit. Integrity or environment failure occurs before provider construction and returns the corresponding blocker.
