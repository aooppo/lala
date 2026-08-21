# Data Model: Coffee Table Execution Manifest

## Parent Plan Identity

Fields: repository-relative path, SHA-256, schema version, run ID, status, Candidate 16 identity, keyframe-set identity, V7-B identity, product SKU, storyboard digest.

Validation: path and hash are exact constants; file is regular and inside the project; all frozen semantics match expected values.

## Execution Boundary

Fields: provider, model, task count/cap, duration per task, generated seconds, credit/USD caps, concurrency, retry/replacement counts, master ratio, prohibited capabilities, provider/paid counters.

Validation: exact equality with the Owner-authorized boundary; all counters remain zero.

## Execution Task

Fields: stable task ID, semantic purpose, ordered storyboard beat references, static source path/SHA or runtime source-lineage rule, prompt path/SHA/text length, model, duration, ratio, seed, output format, expected usable interval, projected credits.

Validation: exactly four ordered tasks; paths and hashes match; prompt length is within provider limit; durations and projected credits sum to the boundary.

## Runtime Source Lineage

Fields: source type, upstream task ID, required upstream status/artifact, runtime-bound upstream SHA, selector, frame-count rule, exact FFprobe/FFmpeg command templates, output format/path, runtime-bound extracted-frame SHA, provider-call count.

Validation: Task 04 only; upstream is Task 02; selector is `LAST_VALID_FRAME`; frame index is `frame_count - 1`; both hashes are absent until runtime evidence; extraction requires zero provider calls and gates Task 04 submission.

## Assembly Segment

Fields: segment ID, beat number/name, source task or terminal-frame hold, source interval, master interval, operation.

Validation: ordered, gap-free, non-overlapping coverage of `[0,20)`; beat names and durations match the parent storyboard exactly; only Task 4 terminal-frame hold may synthesize local duration.

## Review Gate

Fields: status, manifest SHA returned externally, human reviewer, human decision, Live authorized flag.

Validation: status is `READY_FOR_OWNER_COFFEE_TABLE_EXECUTION_MANIFEST_REVIEW`; human fields are blank; Live authorization is false.

## State Transition

`READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION` → offline validation/preparation → `READY_FOR_OWNER_COFFEE_TABLE_EXECUTION_MANIFEST_REVIEW`

No transition to Live or approval exists in this feature.
