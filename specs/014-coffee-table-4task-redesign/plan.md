# Implementation Plan: Coffee Table Four-Task Redesign

**Branch**: `codex/lady-lala-pilot-live` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

## Summary

Create append-only, dry-run-only planning evidence for a four-shot 20-second Coffee Table commercial. Use versioned prompts and a human-readable/JSON review package; do not construct a Provider or alter historical media/accounting.

## Technical Context

**Language/Version**: Data-only JSON/CSV/Markdown and prompt text; repository runtime remains Python 3.11
**Primary Dependencies**: Existing approved-source hashing and current Coffee Table evidence
**Storage**: New versioned prompts, `specs/014-*`, and append-only `outputs/reviews/coffee-table-4task-dryrun/`
**Testing**: JSON parsing, schema/invariant assertions, hash comparison, diff/secret scans
**Target Platform**: Local offline review
**Project Type**: Reproducible media workflow
**Constraints**: Zero network/live/provider calls; no retries/replacements; preserve dirty work and all history
**Scale/Scope**: Four tasks × five seconds, one 20-second 16:9 storyboard

## Constitution Check

- Immutable sources: PASS — only read and hash approved inputs.
- Provider-neutral/reproducible evidence: PASS — prompts, references, contracts, hashes, and decisions are inspectable.
- Paid calls staged/bounded: PASS — all current authorization and counters are zero.
- Offline validation: PASS — structural and integrity checks require no network.
- Human approval: PASS — all Owner decision fields remain blank.

Post-design re-check: PASS. No exception or complexity waiver is required.

## Project Structure

```text
prompts/coffee-table-task-0*-v*.txt
specs/014-coffee-table-4task-redesign/
outputs/reviews/coffee-table-4task-dryrun/<package-id>/
PROGRESS.md
README.md
```

**Structure Decision**: Keep creative contracts in versioned prompt files, governance/design in the feature spec, and append-only review evidence under outputs.
