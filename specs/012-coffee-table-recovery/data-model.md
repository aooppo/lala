# Data Model: Coffee Table Failed-Task Recovery

## RecoveryPreparation

Fields: recovery ID, created timestamp, parent manifest path/SHA, failed run ID, original evidence path/hash snapshots, status, provider-call counters, and output locations.

States: `VALIDATING → PREPARING_LOCAL_MEDIA → WRITING_MANIFEST → READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW`. Any failure ends without a manifest and removes only paths allocated by that attempt.

Validation: exact parent/run identity; no prior reviewed recovery for the same binding; original manifest/results bytes unchanged before and after; all counters zero.

## HistoricalTaskRecord

Fields: logical task ID, provider task ID, status, artifact path/SHA or provider error, actual credits, and reuse/retry policy.

Validation: TASK-01 and TASK-02 are `SUCCEEDED` with exact IDs, hashes, and 25 credits each; TASK-03 is `FAILED` with exact ID/error and zero credits; TASK-04 is `NOT_SUBMITTED`. Historical TASK-03 never becomes a local task or unsubmitted state.

## LocalProductCutaway

Fields: local task ID, semantic purpose, product identity, source path/SHA/dimensions, output path/SHA/size, duration, frame count/rate, dimensions, codec, pixel format, audio state, filter expression, exact argv, provider calls, and cost.

Validation: source is exact IN3725 PDP reference; output is 72 frames, 3.000 seconds, 1280x720, 24 fps, H.264/yuv420p, silent; provider calls and cost are zero.

## Task04SourceLineage

Fields: source task/provider task ID, source MP4 path/SHA, fixed zero-based frame index, extraction selector/argv, PNG path/SHA/size/dimensions/mode, and provider calls.

Validation: source is exact successful TASK-02; index equals 96; PNG decodes at 1280x720; source and PNG hashes match current bytes; provider calls are zero.

## FrozenTask04Proposal

Fields: status, semantic purpose, source lineage reference, prompt path/text/SHA/UTF-16 length, provider/model/ratio/duration, projected credits/USD, submission gate, and prohibitions.

Validation: status remains `FUTURE_NOT_SUBMITTED`; prompt bytes and extracted PNG match recorded hashes; submission requires a separate Owner authorization of the recovery manifest SHA.

## RecoveryTimeline

Fields: ordered segments, master interval, source ID, source interval, role, duration, and derivation policy.

Validation: eight contiguous master segments exactly cover `[0,20)` with total duration 20 seconds; last segment is a local hold of future TASK-04's last valid frame.

## RecoveryBudget

Fields: historical actual credits/USD, local recovery credits/USD, future projected credits/USD, final projected credits/USD, retry count, replacement count.

Validation: actual 50 / 0.50; local 0 / 0; future 25 / 0.25; projected final 75 / 0.75; retries/replacements zero.

## RecoveryManifest

Fields: schema version, status, recovery preparation, historical task records, local cutaway, TASK-04 lineage/proposal, timeline, delivery policy, budget, zero-call facts, and review gate.

Validation: every referenced file hash matches current bytes; parent/original evidence remains unchanged; no secrets, URLs, credentials, authorization headers, or subjective approval fields are present.

## RecoveryLiveRun

Fields: operation/run ID, V2 path/SHA, authorization/cap facts, protected-hash snapshot, task lifecycle events, provider result, TASK-04 artifact, assembly evidence, safe-area results, costs, review-package identity, and terminal state.

States: `PREPARED → SUBMITTING → TASK_ID_DURABLE → SUBMITTED → SUCCEEDED → ASSEMBLING → READY_FOR_OWNER_REVIEW`. A no-ID submit ambiguity ends at `BLOCKED_SUBMISSION_UNKNOWN`; provider/validation failure ends at `BLOCKED_TASK04_PROVIDER`; integrity failure before submission creates no run and ends externally as `BLOCKED_INTEGRITY`.

Validation: exactly one logical/provider task, one submit attempt, zero automatic paid retries/replacements, exact V2 contract/caps, no secret or signed URL serialization, and no prior Live authorization record for the same manifest SHA.

## Task04LiveArtifact

Fields: provider task ID, request binding, submission/completion timestamps, output path/SHA/size, duration, dimensions, codec, pixel format, frame rate, audio state, estimated/actual credits, USD, and cost status.

Validation: exactly one non-empty decodable MP4; approximately five seconds; 1280x720; supported video codec; request bytes match frame 92 and prompt v3 evidence.

## FinalFrameHold

Fields: source TASK-04 path/SHA, decoded frame count, selected zero-based index, PNG path/SHA/dimensions/mode, ffprobe argv, ffmpeg argv, and hold duration.

Validation: selected index equals decoded frame count minus one; PNG is decodable 1280x720; hold is exactly 48 frames at 24 fps and makes zero provider calls.

## DeliveryAndReviewPackage

Fields: exact eight-segment assembly argv/input hashes, master media/hash facts, 1:1/9:16 gate status/reasons, exact-byte copied raw/master items, evidence files, Owner checklist rows, and package manifest SHA.

Validation: master is 480 frames/20 seconds at 1280x720, 24 fps, H.264/yuv420p, silent; absent objective safe-area geometry yields `BLOCKED_SAFE_AREA`; all human decision/notes/reviewer/timestamp cells are blank; terminal state is `READY_FOR_OWNER_REVIEW`.
