# Implementation Plan: Candidate 16 Keyframe Publish

**Branch**: `codex/lady-lala-pilot-live` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-candidate16-keyframe-publish/spec.md`

## Summary

Add a provider-neutral, offline-first authority layer that validates the immutable Candidate 16 V2 review package, exact-byte promotes one Owner-approved candidate per formal role, builds and publishes one immutable three-role set, binds Goal 2 to its current revision, validates and registers the later split-run Candidate 16 V7-B Owner decision, and produces a zero-call motion-only Coffee Table preview. The implementation extends the existing video CLI and keyframe validation without replacing historical manifests, media, or run evidence.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Python standard library, PyYAML, Pillow through existing image inspection helpers

**Storage**: Collision-safe local JSON/YAML/CSV files, immutable approved media, append-only event files, atomic current-state YAML pointers

**Testing**: pytest unit and mocked integration tests with network/provider construction blocked

**Target Platform**: macOS/Linux CLI and local filesystem

**Project Type**: Existing single-package Python CLI

**Performance Goals**: Validate and promote seven review rows and three images in one local operator session; bounded O(number of package candidates) work

**Constraints**: Zero network/provider calls for review, promotion, set operations, preflight, and dry-run; no overwrite; exact-byte copy; active-character consistency; timezone-aware attribution; preserve dirty worktree and historical evidence

**Scale/Scope**: One Candidate 16 V2 package, three role authorities, one published set version, one current Goal 2 binding, one three-candidate split-run V7 review/registration, and one six-beat Coffee Table preview

## Constitution Check

*GATE: Passed before research and re-checked after design.*

- **I. Approved Sources Are Immutable Truth**: PASS. Existing approved sources remain read-only; promotion adds exact copies plus provenance through the authorized approved-keyframe write path. Derived sets, events, bindings, and campaign previews live outside approved-source directories.
- **II. Provider-Neutral, Reproducible Core**: PASS. New services operate on local domain records and evidence only. Provider/model facts in source provenance and cost plans are data, not SDK dependencies.
- **III. Paid Calls Are Explicit, Staged, and Bounded**: PASS. Every new command is offline; Coffee Table accepts dry-run only and does not construct providers. Live projection is informational and bounded.
- **IV. Offline Tests and Deterministic Editing Gate Delivery**: PASS. TDD tasks cover schema, hashes, exact bytes, collisions, rollback, pointer revisions, preflight, V7 classification, CLI, and zero-call evidence.
- **V. Human Approval and Staged Video Delivery**: PASS. Only the explicit Owner selections are recorded; role-inapplicable and non-selected subjective fields stay blank. Build/publish require review provenance and never auto-approve media.
- **Delivery Workflow**: PASS. Spec, plan, tasks, analysis, implementation, convergence, full tests, source hashes, secret scan, and PROGRESS traceability are planned.

Post-design re-check: PASS. No constitution exception or complexity waiver is required.

## Project Structure

### Documentation (this feature)

```text
specs/009-candidate16-keyframe-publish/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
src/lala_workflow/video/
├── cli.py
├── runner.py
├── domain.py
├── validation.py
├── keyframe_sets.py
└── campaigns.py

configs/
├── keyframe-manifest.yaml
├── keyframe-set-registry.yaml
└── goal2-binding.yaml

outputs/
├── keyframe-sets/
└── campaign-previews/

tests/
├── test_candidate16_keyframe_sets.py
└── test_coffee_table_campaign.py
```

**Structure Decision**: Keep orchestration in focused provider-neutral video modules and use the existing CLI/runner only as a thin interface. Authoritative approved media and registry pointers remain separate from immutable build/event evidence.

## Design Decisions

1. Validate the seven-row V2 package with an explicit schema and formal per-role required-field map; do not adapt the one-row external K2 schema or invent `NOT_SELECTED`.
2. Promote each selected package candidate with a new truthful provenance type that records package, manifest, review, character, run/task, staged, and approved hashes. Existing external K2 promotion behavior remains backward-compatible.
3. Treat the keyframe set manifest as immutable build evidence. Its file SHA-256 is the set manifest SHA used by publish/binding records; a deterministic member digest inside the manifest covers the role-member payload.
4. Store each publish event as a new collision-safe file, then atomically replace one revisioned registry only after revalidating the set and active character.
5. Goal 2 binding is explicit and revisioned rather than inferred from legacy keyframe manifest status. Preflight validates both registry and binding against live bytes and the active character.
6. Historical V7 evidence remains character-bound when its request keyframe SHA differs from the published Candidate 16 K1 SHA. Methodology/prompt rules may be reused, but media approval does not transfer.
7. Coffee Table is a separate motion-only dry-run contract so existing talking presets remain unchanged. A real repository run is allowed only when Goal 2/V7 preflight is ready; fixture tests prove the plan independently.
8. Candidate 16 V7 closure validates inherited A from the partial parent plus recovered B/C from the recovery run, records the exact Owner review in the external package only, writes a new exclusive registration record, and makes Goal 2 classification prefer this validated registration over legacy evidence.

## Verification Strategy

- Capture approved-source and V1/V2 ordered hash baselines before mutation and compare all pre-existing paths afterward.
- Run focused tests before and after implementation, then `uv run pytest -q`, compileall, diff check, and project validation.
- Exercise CLI help and real review validation/promotion/build/publish/bind/preflight commands in dependency order.
- Before the later V7 authorization, stop on `READY_FOR_OWNER_CANDIDATE16_V7_EXECUTION`; after the explicit V7-B review, validate/register that evidence, run the real Coffee Table dry-run, and stop at `READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION`.
- Verify review and registration paths construct no provider and add zero submissions, task IDs, HTTP calls, or paid calls.
- Scan tracked source/evidence for credentials, Bearer values, authorization headers, and signed query strings.

## Complexity Tracking

No constitution violations.
