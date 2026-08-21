# Implementation Plan: Reviewed External K2 Workflow

**Branch**: `codex/lady-lala-pilot-live` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

## Summary

Add an offline external-keyframe service with exact-byte ingest, dedicated blank K2 review, atomic human-gated promotion, and role-based dual keyframe resolution so talking uses K2 while motion/V7 remains on K1. Preserve legacy readers and block before run/provider allocation.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib, Pillow, PyYAML, existing provider-neutral video domain
**Storage**: local files under `outputs/keyframes/candidates/`, `outputs/reviews/`, `assets/approved_keyframes/`, and atomic YAML manifest replacement
**Testing**: pytest with network blocked and fake providers
**Target Platform**: local macOS/Linux CLI
**Project Type**: Python CLI/library
**Performance Goals**: one bounded streaming local copy; preflight before run/provider allocation
**Constraints**: exact bytes, maximum 20 MiB, PNG/JPEG only, no symlink/traversal/collision, zero provider calls, immutable approved/historical evidence
**Scale/Scope**: 1–3 candidates, one K2 authority, existing K1/V7-A retained

## Constitution Check

- **Approved Sources**: PASS — pending files stay outside approved directories; promotion is copy-only, exclusive, hash-verified, human-gated.
- **Provider Neutrality**: PASS — external provenance omits inapplicable provider claims; resolver stays provider-neutral.
- **Paid Calls**: PASS — commands are local; tests block network/provider construction.
- **Offline Tests**: PASS — ingest/review/promotion/resolver/evidence failures receive coverage.
- **Human Approval**: PASS — blank baseline remains blank; only an external reviewed copy authorizes promotion.
- **Complexity**: PASS — a dedicated schema avoids corrupting Goal 1 provenance; no exception.

## Project Structure

```text
specs/008-external-k2-workflow/{spec,plan,research,data-model,quickstart,tasks}.md
specs/008-external-k2-workflow/contracts/keyframe-cli.md
src/lala_workflow/video/{domain,validation,config,keyframe_candidates,cli,runner}.py
tests/{test_video_external_keyframes,test_video_media_validation,test_video_pilot_preflight,test_video_dry_run,conftest}.py
```

**Structure Decision**: Extend the existing Python project and isolate candidate lifecycle from provider adapters.

## Design Decisions

1. Stage at `outputs/keyframes/candidates/<id>/candidate.<ext>` with `provenance.json` and blank `review.csv`.
2. Use `external-k2-review/v1`, with immutable identity columns followed by blank human fields.
3. Promotion reads only a copy under `outputs/reviews/`, verifies the local baseline remains blank, and exclusively copies to `assets/approved_keyframes/<id>.<ext>`.
4. Approved provenance type is `owner_supplied_external_promotion`; it records source/staged/review/approved hashes and human attribution but no provider fields.
5. Update the manifest with temp+fsync+atomic replace after exclusive media/provenance creation; restore and clean on failure.
6. Resolve unique `talking_medium_closeup` for talking and unique `pilot_home_context` (fallback `establishing_keyframe`) for motion.
7. Add `--talking-keyframe` and `--motion-keyframe`; legacy `--keyframe` stays on smoke/motion commands.
8. New evidence writes nested `talking_keyframe` and `motion_keyframe`; legacy top-level fields remain talking-compatible.

## Architecture and Interfaces

The candidate lifecycle is isolated in `video/keyframe_candidates.py`. CLI parsing and dispatch may
call that module, but provider adapters are never constructed. Existing configuration loading owns
approved-manifest validation; the pilot runner consumes only validated `ApprovedKeyframe` values.

```text
owner file -> import CLI -> pending candidate directory -> external review copy
                                                    |
                                                    v
approved bytes <- promotion CLI <- complete human review
       |
       +-> talking resolver (K2) -> HeyGen talking requests/evidence
K1 ----+-> motion resolver        -> V7/Runway requests/evidence
```

The public CLI and CSV contracts are defined in `contracts/keyframe-cli.md`. Candidate, review,
promotion, and dual-resolution schemas are defined in `data-model.md`. No provider SDK object or
provider-specific request is introduced by this feature.

## Integrity and Transaction Boundaries

- Import validates a regular non-symlink source, decoded MIME/extension agreement, size, and safe
  candidate slug before creating the candidate directory. It computes the source digest before the
  copy, streams exact bytes into an exclusive target, fsyncs, re-hashes source and target, then
  writes exclusive provenance and blank review files. Any in-process failure removes the new
  candidate directory.
- Promotion revalidates pending provenance, staged bytes, the immutable blank baseline, and one
  reviewed copy under `outputs/reviews/`. Approved media and promotion evidence use exclusive
  creation. Only then is a temporary fsynced manifest atomically replaced.
- "Atomic" means no partial authority remains after a handled in-process failure. It does not claim
  a multi-file filesystem transaction across sudden power loss. Startup validation must reject any
  orphaned media/evidence or manifest drift; repair is manual and never overwrites evidence.
- No target is reused. Duplicate candidate IDs, duplicate K2 role authority, existing approved
  media, existing promotion evidence, or manifest collisions fail before authority changes.

## Security and Privacy

- Accept project-relative input or an explicit local absolute path, reject relative `..` traversal
  and direct symlinks, and store only the sanitized basename as `source_identity`.
- Review files must resolve to a regular non-symlink file beneath `outputs/reviews/` and must match
  the exact ordered v1 header and single candidate row.
- Candidate provenance carries a stable owner-source declaration, not human approval. Provider,
  task, model, prompt, static-run, credential, and authorization fields are prohibited.
- Secret scanning covers changed source/docs/tests plus produced candidate/run evidence without
  printing local secret values.

## Compatibility and Migration

No data migration is performed. Existing K1 and V7-A remain byte- and provenance-identical.
Historical evidence readers continue accepting the legacy single-keyframe shape; newly written
pilot evidence uses `dual-keyframe-evidence/v1` and retains compatible top-level talking fields.
Explicit selectors are additive: legacy `--keyframe` remains for smoke/motion commands, while
general pilot generation adds `--talking-keyframe` and `--motion-keyframe`.

## Observability and Evidence

Import returns candidate ID, status, staged/provenance/review paths, SHA-256, and zero-call
accounting. Promotion returns the approved path/hash and promotion record. Pilot evidence records
independent talking and motion ID/path/role/hash/provenance. All blockers must identify the missing
or ambiguous authority before run allocation or provider construction.

## Verification Strategy

1. Run candidate import/review/promotion unit tests, including exact-byte and failure cleanup.
2. Run dual resolver, Product Page/Tooltip/Homepage preflight, V7 compatibility, and factory-zero
   tests with network blocked.
3. Run the complete offline suite, compileall, `video validate`, `git diff --check`, precise secret
   scans, and before/after approved-source hash comparison.
4. Only after all tests pass, import the real candidate locally. Verify its given SHA-256, staged
   equality, blank review, and `READY_FOR_K2_HUMAN_REVIEW`; do not promote it.
5. Record commands/results and provider accounting in `PROGRESS.md`, then create one local commit.

## Rollback

Before real promotion, rollback is deletion of no authority: the pending candidate remains review
evidence and is not consumed by production. A failed handled promotion restores the original
manifest bytes and removes only targets created by that invocation. Once a promotion succeeds,
approved-source immutability applies; reversal requires a separately specified copy-only authority
change and must never delete or overwrite the approved K2.

## Implementation Phases

- Phase 0: capture immutable baselines and settle external provenance/review contracts.
- Phase 1: implement and independently verify exact-byte ingest plus blank review.
- Phase 2: implement and independently verify human-gated exact-byte promotion.
- Phase 3: split talking K2 from motion K1 across resolver, requests, evidence, and preflight.
- Phase 4: run full gates, import the real candidate, stop for Owner review, and document handoff.

## Post-Design Constitution Check

All gates remain PASS: no byte transformation, inferred review, provider leakage, historical mutation, or paid call.

Implementation completion is gated by `tasks.md`; the presence of source files alone does not make
this plan complete. On 2026-08-21 all offline gates passed, the real candidate was imported as
exact-byte pending evidence, and execution stopped at `READY_FOR_K2_HUMAN_REVIEW` without review or
promotion.
