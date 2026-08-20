# Research: P1-1 V7 Human QA Closure

## Decision: Extend the existing P1-2 prerequisite validator

**Rationale**: P1-2 already has a strict pre-provider motion review gate. Extending it to recognize a successful V7 parent keeps a single authorization boundary and makes the recorded `P1_2_LIVE_READY` state executable in later separately authorized work.

**Alternatives considered**:

- Record readiness only in a package manifest: rejected because the production gate would still reject the V7 parent.
- Rewrite V7-A as a synthetic single-result motion-smoke run: rejected because it would fabricate provenance and replace the actual parent evidence model.
- Add a second P1-2 live command or bypass flag: rejected because it would create a weaker parallel authorization path.

## Decision: Select by unique passing reviewed row

**Rationale**: The parent contains three successful provider outputs but only the human-reviewed winner may become the P1-2 baseline. Requiring exactly one fully passing, MTL-ready row makes selection explicit and collision-safe without adding a schema field.

**Alternatives considered**:

- Assume the first candidate is selected: rejected because ordering is not human authorization.
- Read winner selection only from free-form notes: rejected because it is not a reliable gate field.
- Add a new selected column to the shared QA schema: rejected because the owner required the existing exact schema and a schema migration is unnecessary.

## Decision: Use established QA mappings and explicit notes

**Rationale**: The exact shared schema has no Camera Lock or Framing columns. Existing motion validation maps background stability to `background` and framing/proportions to `body_proportions`. Explicit notes preserve the human meaning without introducing incompatible fields.

**Alternatives considered**:

- Add ad hoc columns: rejected because the parser requires the exact header.
- Store these decisions only outside the CSV: rejected because the closure requires them in formal human QA evidence.

## Decision: Preserve diagnostics gap independently from Human PASS

**Rationale**: The only formal subject-lock entrypoint supports one-result `motion_smoke`, not a V7 parent. Human review remains authoritative, so the honest state is both Human PASS and `POST_LIVE_DIAGNOSTIC_ENTRYPOINT_NOT_AVAILABLE`.

**Alternatives considered**:

- Run the single-result command against V7-A: rejected because it would misrepresent the parent package contract.
- Modify algorithms, thresholds, or the V6 baseline: rejected by owner scope and governance.
- Create proxy diagnostics manually: rejected as fabricated formal evidence.

## Decision: Produce a new closure package

**Rationale**: The original ZIP is pre-human-review evidence with a fixed hash. A separately named final package can join that evidence with the later review and state transition while preserving chronology.

**Alternatives considered**:

- Overwrite the existing package directory/ZIP: rejected because it would destroy the pre-review evidence hash.
- Commit runtime evidence: rejected because repository policy ignores runs, reviews, and packages.
