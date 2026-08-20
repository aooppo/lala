# Research: Subject Lock Diagnostics

## Decision 1: Use an existing-dependency local color-region proxy

**Decision**: Implement a deterministic Pillow-based connected color-region tracker on bounded downsampled frames, tuned to the visually distinctive red-gown region, and label its scope `color_region_proxy`.

**Rationale**: The project declares Pillow but not OpenCV or NumPy. V6 and approved keyframes contain a distinctive red gown, while synthetic rectangles can exercise exact translation/scale. This provides useful subject-position evidence with no model, download, or network dependency.

**Alternatives considered**: OpenCV Haar face detection (new dependency and face-only scope); YOLO/SAM/cloud vision (prohibited); pure template matching (more expensive across scale); no real tracker (safe but unnecessarily weak for the available color cue).

## Decision 2: Fail closed on coverage and endpoints

**Decision**: Require the configured tracking-success rate and reliable first/last sampled observations for within/outside-threshold classification. Otherwise return `INSUFFICIENT_EVIDENCE` with nullable drift/scale metrics.

**Rationale**: Missing observations cannot truthfully be represented as zero drift. Endpoint availability is necessary for first-to-last metrics.

**Alternatives considered**: Interpolating missing endpoints risks hiding disappearance; middle-frame-only classification cannot prove a lock.

## Decision 3: Keep diagnostics outside the thirteen-artifact run bundle

**Decision**: Write subject-lock artifacts to the derived motion review package, not the append-only run directory.

**Rationale**: Existing accepted Goal 2 runs have an exact thirteen-artifact contract and are immutable. Review packages already hold visual evidence and ZIP/checksum material.

**Alternatives considered**: Adding run artifacts breaks the exact bundle; embedding summary in review.csv violates blank human-field rules.

## Decision 4: Separate dry-run provenance from live approval

**Decision**: Dry-run requires valid immutable smoke/output/keyframe provenance but does not require human PASS. It records the review copy's state without translating it to approval. Live uses the existing strict passing-review validator before provider construction.

**Rationale**: Offline planning is safe and explicitly allowed after V6 FAIL; live generation remains a paid, human-gated boundary.

**Alternatives considered**: Requiring PASS for dry-run blocks safe work; `passed_by_owner_instruction` conflicts with the archived V6 failure.

## Decision 5: Deterministic package integrity

**Decision**: Recompute a sorted checksum manifest, create ZIP entries with stable ordering, verify every checksum and ZIP member, and scan text artifacts for credential/header/signed-query patterns.

**Rationale**: Subject evidence needs the same reviewability and safety guarantees as existing manually assembled packages.

**Alternatives considered**: Appending manifest lines retains stale entries; unverified ZIP creation is insufficient handoff evidence.
