# Research: Coffee Table Live Execution

## Decision 1 — Reuse the existing Runway motion adapter

**Decision**: Reuse `RunwayMotionProvider` through the provider-neutral `MotionVideoProvider` protocol.

**Rationale**: Existing official-API-backed configuration freezes API version `2024-11-06`, `gen4_turbo`, 1280:720, five credits per output second, SDK retry count zero, task polling, validated MP4 download, and redaction. Four five-second tasks therefore project to exactly 100 credits / USD 1.00.

**Alternatives considered**: Direct SDK calls in campaign code were rejected because they would cross provider boundaries and duplicate validation/redaction.

## Decision 2 — Treat durable task IDs as the idempotency boundary

**Decision**: Persist `SUBMITTING` before the call and persist any returned provider task ID immediately through the adapter sink. Never replay submission automatically.

**Rationale**: The existing Goal 2 research and V7 recovery establish that a task ID must survive wait/download failures. A no-ID exception cannot prove non-acceptance and must be classified as ambiguous.

**Alternatives considered**: Retrying no-ID errors was rejected because it could create a fifth or duplicate paid task.

## Decision 3 — Freeze final decoded frame extraction

**Decision**: Use FFprobe `-count_frames` and select zero-based `frame_count - 1` with FFmpeg exactly as the approved manifest states.

**Rationale**: Container duration may not equal the final frame timestamp. Decoded-frame indexing is deterministic and avoids aesthetic choice.

**Alternatives considered**: Timestamp `4.8s`, literal `5.0s`, or manual selection were rejected as drift-prone or ambiguous.

## Decision 4 — Assemble and reframe locally

**Decision**: Use FFmpeg for manifest trims, concat, terminal hold, and local center-crop derivatives; validate every created MP4 with FFprobe.

**Rationale**: This preserves the no-native-regeneration boundary and produces replayable command evidence.

**Alternatives considered**: Provider-side ratio generation and nonlinear-editor/manual assembly were rejected as unauthorized or non-deterministic.

## Decision 5 — Fail closed while preserving evidence

**Decision**: On any provider/runtime failure, write a stopped summary and retain completed artifacts/task IDs; do not delete or resume automatically.

**Rationale**: Evidence preservation is necessary to prevent accidental paid duplication and to distinguish a failed task from ambiguous submission state.

**Alternatives considered**: Cleanup-and-rerun was rejected because it erases the idempotency boundary.
