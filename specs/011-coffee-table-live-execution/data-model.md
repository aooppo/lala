# Data Model: Coffee Table Live Execution

## LiveAuthorization

Fields: manifest path/SHA, parent SHA, Owner decision text identity, authorized provider/model, max tasks/seconds/credits/USD, concurrency, retries, replacements, timestamp.

Validation: exact approved path/SHA only; limits equal V2; Live permission and local credential present; review in manifest remains blank.

## CampaignLiveRun

Fields: run ID/path, manifest identity, status, created/completed timestamps, ordered task records, stop reason, counters, cost totals, delivery artifacts.

States: `PREFLIGHTED → RUNNING → READY_FOR_OWNER_REVIEW`; any execution uncertainty transitions to a specific `STOPPED_*` state and cannot automatically re-enter running.

## TaskRuntimeRecord

Fields: task ID, request fingerprint/evidence, state, provider task ID, submission attempts, artifact metadata, estimated/actual credits, error.

States: `PENDING → SUBMITTING → SUBMITTED → POLLING → SUCCEEDED`; terminal alternatives are `SUBMISSION_AMBIGUOUS`, `FAILED`, `CANCELLED`, `TIMED_OUT`, or `VALIDATION_FAILED`. One submission attempt maximum.

## RuntimeLineage

Fields: source task, source MP4 path/SHA, decoded frame count, selected index, FFprobe argv, FFmpeg argv, extracted PNG path/SHA/dimensions, revalidation result, provider calls zero.

Validation: source is Task 02, status succeeded, index equals count minus one, hashes match current bytes, PNG decodes, and Task 04 request input hash equals extracted SHA.

## DeliveryArtifact

Fields: role (`RAW`, `MASTER_16_9`, `LOCAL_1_1`, `LOCAL_9_16`), path, SHA, bytes, duration, dimensions, codec/container, provenance, command identity.

Validation: raw count exactly four for success; master duration approximately 20 seconds and 1280×720; local derivative dimensions match target; every output is outside approved directories.

## HumanReviewRow

Fields: standard Goal 2 QA columns.

Validation: subjective fields, reviewer, reviewed timestamp, decision, and notes are blank at handoff.
