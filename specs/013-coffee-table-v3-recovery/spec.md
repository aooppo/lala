# Feature Specification: Coffee Table V3 Semantic Recovery

**Created**: 2026-08-21
**Status**: Offline recovery planning only

## User Scenarios & Testing

### User Story 1 — Record the Owner rejection (Priority: P1)

As the Owner, I can see an append-only decision record that rejects the existing 20-second master for `SOFA_SEATING_CONTRACT_VIOLATION`, without changing the original blank review package or generated media.

**Acceptance**: The new evidence states `REJECT`, preserves the correction that wine glass is required and correct, and hashes both the reviewed copy and original package.

### User Story 2 — Review reusable source frames (Priority: P1)

As the Owner, I can review 5–10 exact TASK-02 frames after glass placement, with the wine-glass/table/sofa relationship described and no automatic frame selection.

**Acceptance**: Each PNG has a zero-based index, timestamp, SHA-256, visibility/reachability observations, recommendation, and blank decision fields.

### User Story 3 — Approve only the smallest future recovery (Priority: P1)

As the Owner, I receive a V3 contract that recommends `TASK-04 ONLY` only when TASK-01, TASK-02, and LOCAL-TASK-03 can be reused, and that requires separate frame and Live authorization.

**Acceptance**: The manifest fixes all V3 spatial hard gates, preserves 75 credits/USD 0.75 historical accounting, records zero cost for this run, blocks 1:1/9:16, and grants no paid authorization.

## Requirements

- **FR-001**: No Provider client, network request, paid generation, retry, replacement, promotion, commit, push, or PR may occur.
- **FR-002**: Historical TASK-01/02/03/04 task IDs, media bytes, manifests, master bytes, and accounting are immutable protected inputs.
- **FR-003**: The Owner decision must be `REJECT` / `SOFA_SEATING_CONTRACT_VIOLATION`; wine glass must be recorded as correct per Henry's source requirement.
- **FR-004**: Coffee Table remains the foreground hero table, never a chair/bench/stool; Lady LaLa must sit with hips and body weight on sofa cushions; fireplace stays background and wine glass remains on tabletop.
- **FR-005**: The reviewed frame list contains exactly seven deterministic TASK-02 candidates and no selected frame.
- **FR-006**: The V4 prompt includes all table/sofa hard negatives and preserves a stemmed wine glass containing wine.
- **FR-007**: The dry-run manifest can recommend only `TASK-04 ONLY`, `TASK-02 + TASK-04`, or `WIDER RECOVERY REQUIRED`; it must contain explicit zero-credit authorization for this run.
- **FR-008**: 1:1 and 9:16 remain `BLOCKED_SAFE_AREA`; no crop or native-ratio regeneration is made.
- **FR-009**: Tests validate append-only evidence, protected source aggregate, zero provider calls, blank selection, and V3 task reuse result.

## Success Criteria

- **SC-001**: Every protected SHA and the 35-file approved-source aggregate matches its historical baseline before and after preparation.
- **SC-002**: The V3 package contains one Owner-decision JSON, one reviewed-copy CSV, seven source PNGs, a blank-selection CSV, a source-frame manifest, and a hashed recovery manifest.
- **SC-003**: `provider_calls = 0`, `paid_calls = 0`, and `maximum_authorized_credits = 0` are inspectable in V3 evidence.
- **SC-004**: The terminal state is exactly `READY_FOR_OWNER_COFFEE_TABLE_V3_RECOVERY_REVIEW`.

## Scope Boundaries

This feature performs no Live execution. It neither chooses a frame nor submits/replaces TASK-04. The future Live decision remains exclusively with the Project Owner.
