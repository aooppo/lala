# Research: Candidate 16 Keyframe Publish

## Decision 1: Add a role-complete package review contract

**Decision**: Use the existing V2 package manifest and CSV as immutable candidate identity evidence, with a new parser that validates all seven rows and a per-role required human-field map.

**Rationale**: The existing external K2 contract accepts one lowercase external candidate and only `talking_medium_closeup`. Candidate 16 has generated K1/K3 provenance, a retained K2, uppercase IDs, and three formal roles. Reusing K2 would either lose truthful provenance or weaken role semantics.

**Alternatives considered**: Import all images again; convert IDs; mark all fields PASS; create a new `NOT_SELECTED` value.

## Decision 2: Exact-byte promotion remains per-candidate and collision-safe

**Decision**: Each selected candidate is copied with exclusive creation, rehashed before/after copy, accompanied by an exclusive JSON promotion record, and atomically added to the existing approved keyframe manifest.

**Rationale**: This matches the existing approved-keyframe boundary and permits independent rollback of one failed promotion without transforming image bytes.

**Alternatives considered**: Put derived files under approved directories; overwrite the legacy authority; delay all manifest updates until three files exist.

## Decision 3: Immutable sets plus a revisioned publish registry

**Decision**: Store immutable set manifests and publish-event files under `outputs/keyframe-sets/`; store only the current set ID, manifest path/hash, character, event, and monotonically increasing revision in a small atomic YAML registry.

**Rationale**: Append-only history and current state have different semantics. A pointer can change atomically while prior manifests/events remain byte-for-byte stable.

**Alternatives considered**: Rewrite one set manifest to `PUBLISHED`; append records to YAML in place; derive current state from modification times.

## Decision 4: Explicit Goal 2 binding

**Decision**: Create a revisioned Goal 2 binding that snapshots the published set and role hashes, then require preflight to revalidate active character, registry revision, manifest hash, members, approved bytes, and review provenance.

**Rationale**: The legacy keyframe manifest can contain historical entries and has no current-character/set semantics. Explicit binding prevents stale legacy authority from silently resolving.

**Alternatives considered**: Delete the legacy Lady LaLa entry; infer the latest approval timestamp; use character registry alone.

## Decision 5: V7 methodology is reusable, V7 media is identity-bound

**Decision**: Reuse only V7 prompt methodology, stability rules, and recovery infrastructure. Treat a reviewed V7 run as character-bound whenever its request keyframe SHA differs from Candidate 16 K1.

**Rationale**: The existing V7 evidence was executed against SHA `ab53d9...`, the legacy Lady LaLa home-context image, before Candidate 16 activation. It cannot prove Candidate 16 identity stability.

**Alternatives considered**: Re-label old V7 as Candidate 16; ignore V7 entirely; automatically execute a new V7 batch.

## Decision 6: Separate motion-only Coffee Table preview

**Decision**: Add a dedicated offline Coffee Table campaign planner that emits six storyboard beats, 20 seconds total, Candidate 16/keyframe/product bindings, a 16:9 safe master plan, 1:1 and 9:16 reframe guards, and two non-executed live cost options.

**Rationale**: Existing Goal 2 presets require talking/TTS semantics. Extending them would add unauthorized dialogue and provider responsibilities.

**Alternatives considered**: Force `product_page`; auto-crop both ratios; submit native live ratio tasks now.

## Decision 7: Register split-run Candidate 16 V7 evidence

**Decision**: Validate the A-success parent and B/C-success recovery as one canonical Candidate 16 V7 evidence set, preserve the original package manifest, and write a separate exclusive registration record for the unique reviewed winner.

**Rationale**: The provider-safe recovery correctly avoided replacing the successful A task and produced B/C under a linked recovery run. Treating only one run as authoritative would either discard truthful A provenance or ignore recovered B/C. A separate registration preserves append-only execution evidence and human-review history.

**Alternatives considered**: Rewrite the parent into a synthetic three-success run; copy B/C results into the parent; relabel the legacy Lady LaLa V7 run; infer the winner from diagnostics.
