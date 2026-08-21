# Research: Coffee Table Execution Manifest

## Decision 1: Supplement rather than replace the parent plan

**Decision**: Bind a new execution manifest to the existing plan path and SHA without changing or regenerating `plan.json`.

**Rationale**: The parent correctly freezes business authority while the supplement freezes missing provider-request and assembly details.

**Alternatives considered**: Re-running the dry-run would create a new plan identity and violate the Owner's no-replanning boundary.

## Decision 2: Four independent image-to-video requests

**Decision**: Use K1 for establishing/walk start and K3 for walk completion/placement, product detail, and sit/hero.

**Rationale**: K1 provides the widest stable room composition. K3 puts Candidate 16, the glass, table, and sofa in the strongest interaction-safe composition. K2 is portrait talking media and unsuitable for the frozen 16:9 motion-only contract.

**Alternatives considered**: Using K2 would add composition drift; deriving a later task's source from a prior Live output would make its source SHA unknowable before Owner authorization.

## Decision 3: Preserve exact timeline with local hold

**Decision**: Use Task 1 `[0,5)`, Task 2 `[0,5)`, Task 3 `[0,3)`, Task 4 `[0,5)`, then hold Task 4's terminal frame for two seconds.

**Rationale**: It preserves all six beats and the exact twenty-second master while keeping four paid five-second tasks. The static hero hold is deterministic, local, and commercially appropriate.

**Alternatives considered**: Time-stretching motion risks visible artifacts; a fifth task exceeds authority; pretending four independent tasks provide continuous split actions is not reproducible.

## Decision 4: Preparation-only CLI

**Decision**: Add an explicit offline manifest-preparation mode but no provider execution mode.

**Rationale**: Current authority ends at manifest review. A later change can consume the approved manifest SHA for Live without weakening this checkpoint.

**Alternatives considered**: Adding a dormant Live path now would exceed this authorization and complicate proof that provider construction is impossible.

## Decision 5: Existing official Runway evidence remains authoritative

**Decision**: Freeze `gen4_turbo`, 16:9, five seconds, and 25 credits per task as already supported by project research/configuration; do not introduce new pricing or API claims.

**Rationale**: The parent plan already records four tasks and one hundred credits/$1.00, and repository provider configuration/tests already validate the request fields.

**Alternatives considered**: Provider web UI behavior is not acceptable evidence under project governance.

## Decision 6: Remove both held-glass resets

**Decision**: Replace Task 03's K3 source with the frozen product-only PDP image and Task 04's K3 source with Task 02's last valid decoded frame.

**Rationale**: This preserves the causal state established by glass placement: the glass remains on the table and Candidate 16's hands remain empty through sitting and the hero ending.

**Alternatives considered**: A K3 cutaway still visibly resets the glass; choosing a frame aesthetically at runtime is nondeterministic; adding a fifth provider task exceeds authority.

## Decision 7: Runtime-bound hashes are gates, not omissions

**Decision**: Freeze the exact upstream task, artifact, frame selector, extraction commands, and validation sequence while representing the future MP4 and extracted-frame SHA fields as `RUNTIME_BOUND`.

**Rationale**: Those bytes do not exist before Live. Deterministic lineage is reviewable now, while actual hashes must be written and verified after Task 02 succeeds and before Task 04 submits.

**Alternatives considered**: Inventing hashes is invalid; selecting timestamp 4.8 seconds can diverge from the last decoded frame across real container durations.
