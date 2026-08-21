# Feature Specification: Coffee Table Four-Task Redesign

**Feature Branch**: `codex/lady-lala-pilot-live`
**Created**: 2026-08-21
**Status**: Dry-run review package only

## User Scenarios & Testing

### User Story 1 — Review the complete Henry story (Priority: P1)

As Owner, I can review a 20-second, 16:9 storyboard split into four exact five-second tasks that begins by the fireplace with one stemmed wine glass, places it on the Coffee Table, and ends with Lady LaLa seated on the sofa.

**Independent Test**: Read the four task contracts in sequence and verify all required objects, actions, endpoints, and final relationships are explicit.

### User Story 2 — Verify product and transition continuity (Priority: P1)

As Owner, I can verify one locked Coffee Table, one locked room layout, one wine glass, and compatible terminal/opening states before authorizing any generation.

**Independent Test**: Compare every source-reference plan, continuity contract, negative, and acceptance gate in the manifest.

### User Story 3 — Control future staged Live execution (Priority: P1)

As Owner, I receive a sequential TASK-01 → review → TASK-02 → review → TASK-03 → review → TASK-04 → review strategy, with no current Live authority.

**Independent Test**: Confirm all current call/cost counters and authorization caps are zero and owner decisions remain blank.

## Edge Cases

- A task fails review if the table changes geometry/scale, the room changes, the glass changes state incorrectly, or a transition implies teleportation.
- TASK-03 fails even with an attractive table if it becomes a white-background/isolated PDP.
- TASK-04 fails unless the sofa visibly supports Lady LaLa's hips and body weight and the table remains physically separate.

## Requirements

### Functional Requirements

- **FR-001**: The plan MUST contain exactly four five-second 16:9 tasks covering `[0,20)` without gaps or overlap.
- **FR-002**: Every task MUST include summary, duration, prompt, source references, continuity contract, hard negatives, acceptance gates, composition, and review checklist.
- **FR-003**: Product, scale, spatial, transition, prop, identity/wardrobe, and final-state locks MUST apply globally.
- **FR-004**: TASK-01 MUST end beside the Coffee Table holding the glass; TASK-02 MUST place it and begin the sofa approach without exiting frame.
- **FR-005**: TASK-03 MUST be a same-room lifestyle beauty shot with table foreground, glass on tabletop, and fireplace background.
- **FR-006**: TASK-04 MUST end with Lady LaLa's hips/body weight visibly supported by the sofa, table foreground, glass on tabletop, and fireplace background.
- **FR-007**: The package MUST make zero Provider/network/paid calls and authorize zero retries, replacements, credits, or cost.
- **FR-008**: Historical artifacts, task IDs, hashes, and 75-credit/USD 0.75 accounting MUST remain unchanged.
- **FR-009**: Owner review decisions MUST remain blank and terminal status MUST be `READY_FOR_OWNER_4TASK_DRYRUN_REVIEW`.

### Key Entities

- **Dry-Run Manifest**: Immutable plan identity, four task contracts, reference lineage, locks, risks, accounting, and stopping state.
- **Task Contract**: One five-second shot's action, start/end state, prompt, references, negatives, gates, and review fields.
- **Continuity State**: Character position/orientation, glass custody, product/room geometry, and required handoff to the next task.

## Success Criteria

- **SC-001**: Exactly four tasks total exactly 20 seconds at 16:9.
- **SC-002**: All six global locks and all supplied hard negatives are represented in the package.
- **SC-003**: Each adjacent task pair has an explicit compatible transition contract.
- **SC-004**: Current Provider calls, submissions, task IDs, retries, replacements, credits, and USD cost are all zero.
- **SC-005**: Approved-source pre/post hash snapshots are identical and the terminal state is exact.

## Assumptions

- The current active Candidate 16/approved character and current Coffee Table references remain the future visual authority; this package does not approve a new image.
- Future provider-specific fields and budget require a separate Owner authorization after each preceding task review.
- Final delivery in this scope is 16:9 only.
