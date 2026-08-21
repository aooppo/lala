# Research: Reviewed External K2 Workflow

## External provenance

**Decision**: Use `owner_supplied_external_candidate` pending evidence and `owner_supplied_external_promotion` approved authority.

**Rationale**: Goal 1 requires real generation facts; legacy provenance is already-approved package evidence. Neither fits an unreviewed external file.

**Alternatives considered**: Fake Goal 1 run, legacy package schema, and derived crop schema; all misstate provenance.

## Staging

**Decision**: Require regular non-symlink file, bounded slug, PNG/JPEG decode/extension agreement, 20 MiB maximum, streaming hash, exclusive exact-byte copy, and post-copy equality.

**Rationale**: Prevents indirection, confusion, overwrite, transformation, and TOCTOU drift.

## Review

**Decision**: Dedicated `external-k2-review/v1`; candidate-local baseline stays blank, human decisions come only from a bound copy under `outputs/reviews/`.

**Rationale**: Preserves append-only evidence without weakening old schemas.

## Promotion

**Decision**: Exclusively create approved media/provenance, verify bytes, then atomically replace manifest; clean new targets and restore manifest on failure.

**Rationale**: No dangling or partial authority.

## Dual resolution

**Decision**: Talking uses K2, motion/V7 uses K1, and nested evidence preserves both while top-level legacy evidence remains readable.

**Rationale**: Separate composition authorities preserve reviewed V7-A.

**Alternatives considered**: Reusing K1 for talking, replacing K1 with K2, or storing one ambiguous
`keyframe_sha256`; each either weakens composition, breaks V7 authority, or destroys traceability.

## Failure semantics

**Decision**: Define handled-operation atomicity precisely: exclusive approved targets, verified
bytes, manifest replace last, and best-effort cleanup/manifest restoration for in-process failures.

**Rationale**: Local files do not provide a portable multi-file transaction. Precise semantics are
safer than claiming crash-proof atomicity that the implementation cannot guarantee.

**Alternatives considered**: Overwrite-in-place, manifest-first publication, or silent orphan
repair; all can expose unverified authority or destroy evidence.

## Compatibility

**Decision**: Add nested dual-keyframe evidence and additive CLI selectors while retaining legacy
single-keyframe readers and command meanings.

**Rationale**: Historical run evidence is immutable and existing smoke/motion commands must remain
readable without making their K1 keyframe valid for new talking work.

**Alternatives considered**: Rewrite historical records or reinterpret legacy `--keyframe` for all
commands; both introduce provenance ambiguity.
