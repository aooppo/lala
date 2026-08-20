# Research: P1-1 Motion V7 Controlled Live Batch

## Decision: Add a dedicated fixed live-batch command

**Rationale**: Motion Smoke is a one-prompt first-provider gate and P1-2 variation generation is review-gated downstream work. V7 needs three distinct prompts under one parent experiment without selecting candidates.

**Alternatives considered**:

- Reuse Motion Smoke three times: rejected because it creates independent runs and permits only one first-smoke result.
- Extend P1-2 motion generation: rejected because it would weaken the explicit P1-1 Human PASS gate.

## Decision: Require two CLI confirmations plus existing live environment guards and a credit cap

**Rationale**: `--execute-live` expresses paid execution intent, `--confirm-v7-batch` confirms the inseparable A/B/C experiment, exact `VIDEO_ALLOW_LIVE_CALLS=true` and the local credential follow repository convention, and a known capped estimate prevents accidental scope growth.

**Alternatives considered**:

- Change canonical `live_allowed` to true: rejected because configuration must stay fail-closed.
- Use only one generic `--live` flag: rejected because it does not separately attest the fixed three-task experiment.

## Decision: Validate all neutral requests and write verified plan evidence before submission

**Rationale**: Candidate parsing alone does not prove the selected source and provider request are acceptable. Validating every final request through the provider protocol, then writing and reading back immutable plan evidence, ensures B/C failures cannot occur merely because they were never preflighted.

**Alternatives considered**:

- Validate each candidate immediately before its submission: rejected because A could be submitted before B fails.
- Write evidence only after execution: rejected because an early provider failure could lose the exact authorized plan.

## Decision: Use a dedicated zero-retry sequential executor

**Rationale**: Shared execution supports explicitly idempotency-safe submission retries, while this experiment prohibits all automatic task-creation replay. A small provider-neutral executor preserves returned task IDs across wait/download errors and stops the batch on the first non-success.

**Alternatives considered**:

- Set `max_retries=0` but reuse the shared executor: rejected because download exceptions do not return its locally acquired task ID to the caller.
- Continue after a failed terminal task: rejected as a less conservative experiment and contrary to fail-stop intent.

## Decision: Preserve the 13-artifact contract

**Rationale**: Preflight plan, dynamic candidate results, QA, cost, and accounting fit the existing request/config/plan/events/results/review/cost/summary files. No new artifact class is necessary.

**Alternatives considered**:

- Add a separate preflight manifest: rejected because it would break the authoritative exact-artifact invariant.

## Decision: Keep HTTP accounting honest

**Rationale**: Task submissions and IDs are exactly countable in orchestration. Provider API HTTP calls can be counted inside the Runway adapter; if an injected provider cannot expose a reliable count, evidence must state unknown rather than infer from task attempts.

**Alternatives considered**:

- Treat submissions as total HTTP requests: rejected because polling and downloads are separate operations.
