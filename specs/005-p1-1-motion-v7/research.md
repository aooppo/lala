# Research: P1-1 Motion V7 Targeted Fix

## Decision: Use a dedicated dry-run-only V7 batch command

**Rationale**: Existing Motion Smoke accepts one prompt, while existing P1-2 variation generation intentionally reuses a reviewed smoke prompt and has a later live path. V7 needs three distinct prompts in one record and must not become live-authorizing.

**Alternatives considered**:

- Run three independent Motion Smoke previews: rejected because it produces three run IDs and cannot provide a single comparable A/B/C record.
- Extend P1-2 generation: rejected because that stage is specifically guarded by P1-1 Human PASS and is not the V7 controlled experiment.

## Decision: Preserve the 13-artifact run contract

**Rationale**: Candidate matrix and pending comparison fit existing JSON run artifacts. Adding a fourteenth file would violate current run integrity validation.

**Alternatives considered**:

- Add a standalone comparison file to every run: rejected because dry-run no-media evidence does not need a new artifact class and current invariant is authoritative.

## Decision: Keep diagnostic values pending in dry-run

**Rationale**: The only authoritative V7 measurements can come from actual future media analyzed by the existing Subject Lock path.

**Alternatives considered**:

- Estimate or copy V6 values into V7 columns: rejected as fabricated diagnostic evidence.

## Decision: Reuse existing configured credit estimation and UTF-16 preflight

**Rationale**: `configs/providers.yaml` supplies verified Runway limits/pricing and current runner preflight occurs before any provider construction.

**Alternatives considered**:

- Hard-code 25/75 credits or a second prompt counter: rejected because they can drift from provider configuration and existing validation.
