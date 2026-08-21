# Feature Specification: Coffee Table Failed-Task Recovery

**Feature Branch**: `012-coffee-table-recovery`

**Created**: 2026-08-21

**Status**: Owner authorized Recovery Manifest V2 for exactly one TASK-04 Live submission, then local delivery review preparation

**Input**: Preserve the stopped Coffee Table Live run and its immutable provider history, reuse the deterministic local TASK-03 replacement, execute exactly one Owner-authorized TASK-04 from TASK-02 frame 92 and frozen prompt v3, then create the exact twenty-second local master, guarded delivery variants, and a blank Human Review Package before stopping at Owner review.

## User Scenarios & Testing

### User Story 1 - Preserve the Failed Live History (Priority: P1)

As the Owner, I can prepare recovery without changing the original execution contract or rewriting what actually happened in the failed Live run.

**Why this priority**: Provider task IDs and outcomes are audit facts and form idempotency boundaries; losing or reclassifying them could cause an unauthorized retry.

**Independent Test**: Run recovery preparation from fixtures that contain two successful provider tasks, one failed provider task, and one unsubmitted task, then verify the original evidence bytes are unchanged and the new recovery record refers to all four states accurately.

**Acceptance Scenarios**:

1. **Given** the exact parent manifest and stopped Live run, **When** recovery preparation begins, **Then** TASK-01 and TASK-02 are reused, TASK-03 remains a real failed provider task, and TASK-04 remains unsubmitted.
2. **Given** the failed TASK-03 has a durable provider task ID, **When** recovery is prepared, **Then** no provider retry, replacement submission, or status rewrite occurs.
3. **Given** the original execution manifest and provider results, **When** recovery evidence is written, **Then** both originals retain their exact prior bytes and hashes.

---

### User Story 2 - Build the Local Product Cutaway (Priority: P1)

As the Owner, I receive a reproducible three-second local product shot that preserves the approved Coffee Table appearance and substitutes for the failed TASK-03 without a paid call.

**Why this priority**: The local cutaway restores the missing beat while keeping the recovery bounded, reviewable, and free of provider regeneration.

**Independent Test**: Prepare the cutaway twice from the exact product source and verify both runs use the frozen center framing and subtle optical push, satisfy the media contract, and produce identical evidence and output bytes.

**Acceptance Scenarios**:

1. **Given** the exact 1280x1280 product source with its required SHA-256, **When** recovery preparation runs, **Then** it creates one three-second, 1280x720, 24 fps, silent product cutaway with the Coffee Table centered and complete.
2. **Given** a source whose path, dimensions, or hash differs, **When** preparation runs, **Then** it stops before creating recovery evidence or making any provider call.
3. **Given** a valid source, **When** the cutaway is produced, **Then** evidence records the exact local transformation rule, input and output hashes, frame count, duration, dimensions, and zero provider cost.

---

### User Story 3 - Freeze the Proposed TASK-04 Input (Priority: P1)

As the Owner, I can review a fixed TASK-04 source frame and exact prompt before separately authorizing the remaining provider call.

**Why this priority**: The prior final-frame recommendation no longer provides a controlled sit composition, and no new paid work is authorized during recovery preparation.

**Independent Test**: Extract zero-based frame 96 from the exact TASK-02 video twice, verify the same PNG hash and source lineage, and prove preparation stops without constructing or invoking a provider.

**Acceptance Scenarios**:

1. **Given** the exact successful TASK-02 MP4 and required SHA-256, **When** recovery preparation runs, **Then** it extracts exactly zero-based frame 96 and records the deterministic extraction rule, PNG properties, and PNG hash.
2. **Given** frame 96 cannot be deterministically obtained from the exact TASK-02 MP4, **When** extraction is attempted, **Then** recovery stops and does not select another frame.
3. **Given** the extracted frame, **When** the proposed TASK-04 recovery contract is frozen, **Then** it preserves the supplied sit-and-hero business semantics and prohibitions in one exact versioned prompt with a recorded hash.
4. **Given** recovery preparation completes, **When** its terminal state is inspected, **Then** TASK-04 remains unsubmitted and awaits separate Owner authorization of the recovery manifest hash.

---

### User Story 4 - Review a Complete Recovery Contract (Priority: P1)

As the Owner, I receive one append-only recovery manifest that binds the parent contract, failed run, historical spend, local replacement, future TASK-04 proposal, and exact twenty-second assembly plan.

**Why this priority**: A single hashed contract is required before any separate authorization can safely refer to the proposed recovery.

**Independent Test**: Validate a generated recovery manifest and prove its parent/run bindings, task histories, local artifacts, timeline, guarded ratio policy, budget figures, and terminal state are complete and internally consistent.

**Acceptance Scenarios**:

1. **Given** all local preparation succeeds, **When** the manifest is created, **Then** it is a new append-only artifact that references the exact parent manifest SHA and failed Live run ID.
2. **Given** the recovery timeline, **When** it is validated, **Then** it totals exactly twenty seconds using the frozen TASK-01, TASK-02, local TASK-03, future TASK-04, and local hold intervals.
3. **Given** delivery policies, **When** the manifest is inspected, **Then** 16:9 remains the master and 1:1/9:16 remain guarded local reframes only, with native-ratio provider generation blocked.
4. **Given** the recorded budget, **When** it is validated, **Then** historical actual spend is 50 credits / USD 0.50, local recovery spend is zero, projected additional Live spend is 25 credits / USD 0.25, and projected final spend is 75 credits / USD 0.75.

---

### User Story 5 - Execute the Authorized TASK-04 Once (Priority: P1)

As the Owner, I can execute only the TASK-04 request bound by Recovery Manifest V2, with durable provider identity evidence and no automatic retry or replacement.

**Why this priority**: This is the only newly authorized paid operation and the final provider dependency for the Coffee Table delivery.

**Independent Test**: Run the executor with a fake provider and the exact V2 contract, then verify one request uses frame 92 and prompt v3, all lifecycle states are durable, and every failure path stops without a second submission.

**Acceptance Scenarios**:

1. **Given** Recovery Manifest V2 SHA `e97ea0d34f4ea541ab07e6898083e7a35c3b82502030f8f40a06d58fb43e6cc3`, exact live permission, credential, and 25-credit/USD 0.25 caps, **When** execution starts, **Then** it submits only TASK-04 using frame 92, `gen4_turbo`, five seconds, `1280:720`, and prompt v3.
2. **Given** the provider returns a task ID, **When** control returns to the coordinator, **Then** the ID is already durably recorded and the executor only polls/downloads that task.
3. **Given** submission acceptance is ambiguous and no task ID is known, **When** submission raises, **Then** the run stops at `BLOCKED_SUBMISSION_UNKNOWN` and never submits again.
4. **Given** the task fails or returns invalid media, **When** the terminal result is processed, **Then** the run stops with provider evidence and no replacement, assembly, or additional provider request.

---

### User Story 6 - Assemble the Exact Twenty-Second Master (Priority: P1)

As the Owner, I receive a deterministic 16:9 master that exact-byte reuses historical TASK-01, TASK-02, LOCAL-TASK-03, and the successful TASK-04 according to the approved timeline.

**Why this priority**: The master is the primary delivery candidate and must preserve the approved recovery sequence without creative or timing changes.

**Independent Test**: Assemble synthetic inputs with distinct frames and verify eight ordered intervals, exactly 480 frames at 24 fps, a final two-second hold from TASK-04's last decoded frame, and complete command/hash evidence.

**Acceptance Scenarios**:

1. **Given** one valid TASK-04 output, **When** local assembly runs, **Then** the master contains the exact eight V2 timeline intervals and targets twenty seconds at 1280x720 without audio.
2. **Given** TASK-04's decoded frame count, **When** the terminal hold is created, **Then** the selected frame is exactly the last valid zero-based decoded frame and its extracted PNG hash is recorded.
3. **Given** any input hash or media fact drifts, **When** assembly preflight runs, **Then** it stops without changing historical media or creating a substitute.

---

### User Story 7 - Prepare Guarded Deliveries and Blank Human Review (Priority: P1)

As the Owner, I receive safe local delivery variants only when objective safe-area evidence permits them, plus a review package whose subjective decisions are all blank.

**Why this priority**: Alternate ratios must not silently remove Candidate 16, the Coffee Table, wine glass state, or interaction context, and machine validation cannot replace Owner approval.

**Independent Test**: Verify that absent an Owner-approved machine-safe-area contract, 1:1 and 9:16 are explicitly blocked without provider regeneration, while the valid 16:9 master and complete blank checklist still reach `READY_FOR_OWNER_REVIEW`.

**Acceptance Scenarios**:

1. **Given** no objective safe-area contract can prove a proposed crop preserves all required subjects, **When** delivery preparation runs, **Then** the ratio is `BLOCKED_SAFE_AREA` and no local crop or native provider generation is created.
2. **Given** the 16:9 master is valid even when alternate ratios are blocked, **When** the review package is produced, **Then** it contains all four raw sources, the master, evidence, costs, safe-area results, and the complete Owner checklist with blank human fields.
3. **Given** all machine checks pass, **When** the workflow finishes, **Then** it stops at `READY_FOR_OWNER_REVIEW` without `PASS`, `APPROVED`, `FINAL`, `MTL_READY`, or delivery approval decisions.

### Edge Cases

- The parent manifest path or bytes differ even though the expected SHA is supplied.
- The original stopped run is missing, has a different task ID/status/error/cost, or its immutable evidence changed during preparation.
- Existing successful TASK-01 or TASK-02 artifacts have incorrect hashes or invalid media properties.
- The product source has the expected filename but wrong bytes or dimensions.
- Local media creation succeeds but its duration, frame count, dimensions, frame rate, codec, pixel format, or audio state violates the contract.
- TASK-02 has fewer than 97 decoded frames, frame 96 extraction fails, or output PNG validation fails.
- The recovery target already exists, a partial prior attempt exists, or an output path would collide.
- Any provider client construction, network access, submission, retry, or credential serialization occurs during preparation.
- Recovery Manifest V2, its Owner frame-review evidence, frame-92 PNG, prompt v3, historical media, or LOCAL-TASK-03 bytes drift before the sole submission.
- Submission raises before a durable task ID can be proven, or a task ID is persisted immediately before the submit call raises.
- TASK-04 succeeds but yields zero, multiple, short, wrong-resolution, non-decodable, or unsupported media outputs.
- The final decoded frame cannot be counted or extracted deterministically.
- A requested local crop has no objective Owner-approved safe-area rule capable of proving that Candidate 16, the Coffee Table, wine glass, and action context remain visible.

## Requirements

### Functional Requirements

- **FR-001**: Recovery MUST accept only parent execution manifest SHA `ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea` and failed run `LALA-VIDEO-20260821-082100-COFFEE-TABLE-LIVE-001`.
- **FR-002**: Recovery MUST NOT modify the original execution manifest or original provider results.
- **FR-003**: Recovery MUST preserve TASK-01 as succeeded with task ID `43da0f57-b584-4738-bbf1-05c33f653a3f`, output SHA `2c61cb10a6563d9d4c1e43811be17ef06c3244fc6eb2356d349f064cff6ffd4b`, and actual cost 25 credits.
- **FR-004**: Recovery MUST preserve TASK-02 as succeeded with task ID `a7bb1630-21ff-4a2e-8d40-c3c9085d45ac`, output SHA `9565691a30e312518cc867792063194ae2a667b70d586fbee06d821cc9b7413f`, and actual cost 25 credits.
- **FR-005**: Recovery MUST preserve TASK-03 as failed with task ID `03b195ab-98b0-4631-a845-03843656cbc5`, error `INTERNAL.BAD_OUTPUT.CODE01`, and actual cost zero; it MUST NOT classify that task as unsubmitted, rejected before submission, or zero-task.
- **FR-006**: Recovery preparation MUST leave original TASK-04 unsubmitted and MUST make zero new provider submissions, retries, replacements, or paid calls; later Live work requires the separate V2 authorization in FR-020–FR-033.
- **FR-007**: Recovery MUST validate the exact local product source `outputs/reviews/candidate16-keyframes-v2/references/02.jpg`, SHA `4bf6e13b82f9c9c4d4525180aa412ebc22e4ca6c541e6d9c33c905271814b5c5`, and 1280x1280 dimensions before producing local media.
- **FR-008**: The local TASK-03 replacement MUST be exactly three seconds, 1280x720, 24 fps, H.264, yuv420p, and silent, using a frozen center composition and subtle center-anchored optical push while adding no generated or modified content.
- **FR-009**: Local TASK-03 evidence MUST record the exact transformation invocation and expression, input hash, output hash, frame count, duration, dimensions, frame rate, codec, pixel format, audio state, and zero provider/paid calls.
- **FR-010**: Recovery MUST validate the exact TASK-02 MP4 hash before extracting exactly zero-based frame 96; it MUST NOT search for, score, or substitute another frame.
- **FR-011**: TASK-04 source evidence MUST record TASK-02 lineage, source hash, frame index 96, exact deterministic extraction invocation, validated PNG properties, and extracted PNG hash.
- **FR-012**: Recovery MUST freeze the Owner-supplied TASK-04 business semantics and prohibitions as exact versioned prompt bytes and record their SHA-256.
- **FR-013**: Recovery MUST create a new append-only manifest bound to the parent manifest SHA and failed run ID, and MUST fail closed on target collision or any source/evidence drift.
- **FR-014**: The recovery assembly contract MUST total exactly twenty seconds: TASK-01 `[0,3)` and `[3,5)`, TASK-02 `[0,2)` and `[2,5)`, local TASK-03 `[0,3)`, future TASK-04 `[0,4)` and `[4,5)`, then a two-second local hold of future TASK-04's last valid frame.
- **FR-015**: Delivery MUST keep a 16:9 master; 1:1 and 9:16 MUST remain guarded local reframes only; native-ratio provider regeneration MUST remain unauthorized.
- **FR-016**: Recovery evidence MUST report historical actual spend of 50 credits / USD 0.50, projected additional Live spend of 25 credits / USD 0.25, projected final spend of 75 credits / USD 0.75, and automatic retry/replacement counts of zero.
- **FR-017**: Recovery preparation MUST finish only at `READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW` and MUST require separate Owner authorization of the new manifest SHA before TASK-04 submission.
- **FR-018**: Automated recovery tests MUST block network access and prove zero provider calls during all preparation and failure paths.
- **FR-019**: Approved-source hashes MUST be unchanged before and after recovery implementation and execution.
- **FR-020**: Live recovery MUST accept only Recovery ID `COFFEE-TABLE-RECOVERY-20260821-204901-001`, its exact V2 path, and SHA-256 `e97ea0d34f4ea541ab07e6898083e7a35c3b82502030f8f40a06d58fb43e6cc3`; V1 and all pre-final manifests MUST be rejected.
- **FR-021**: Live recovery MUST revalidate the exact historical TASK-01/TASK-02 media, historical TASK-03 failure, LOCAL-TASK-03 media, Owner frame-review evidence, frame-92 PNG, prompt v3, parent execution manifest, original provider results, historical recovery manifest, and approved-source aggregate before provider construction and again after completion.
- **FR-022**: The only new provider request MUST be TASK-04 using zero-based frame 92 SHA `95f68fa1f9bd3dcf6db94c2298511a224484c85c1fc5f278c3c67aa72e765e2e`, prompt SHA `e73cc7844806f8a25249c22da261e57df67ba7c3762172746b33a3b45b24f669`, Runway `gen4_turbo`, five seconds, and `1280:720`.
- **FR-023**: Execution MUST require explicit Live invocation, exact Owner confirmation, the current formal video permission gate, a non-empty local Runway credential, exact maximum 25 new credits and USD 0.25, one submission, and zero automatic paid retries or replacements.
- **FR-024**: Execution MUST persist PREPARED and SUBMITTING before submission, persist a returned provider task ID immediately, then record SUBMITTED and the terminal state append-only; a task ID is the idempotency boundary.
- **FR-025**: An ambiguous submission without a known task ID MUST stop at `BLOCKED_SUBMISSION_UNKNOWN`; a known task ID MUST never be replaced or resubmitted.
- **FR-026**: Successful TASK-04 media MUST be exactly one non-empty, decodable MP4 of approximately five seconds at 1280x720 with supported video codec, and MUST record operation/task IDs, timestamps, media facts, SHA-256, credits, USD, and cost status.
- **FR-027**: A failed/cancelled/timed-out/invalid TASK-04 MUST stop before assembly, preserve all available task/error/cost evidence, and MUST NOT retry, replace, change source/prompt, or create another provider task.
- **FR-028**: Local assembly MUST exact-byte reuse TASK-01, TASK-02, LOCAL-TASK-03, and TASK-04 and MUST render the exact eight-segment V2 timeline to a twenty-second, 1280x720, 24 fps, H.264/yuv420p, silent master.
- **FR-029**: The final two seconds MUST be created from TASK-04's deterministically extracted last decoded frame, recording decoded frame count, selected zero-based index, extraction command, and PNG SHA-256.
- **FR-030**: 1:1 and 9:16 outputs MUST be local-only and MUST be created only when objective safe-area gates can prove all Owner-required subjects/context survive; otherwise each ratio MUST be `BLOCKED_SAFE_AREA` with no output and no provider generation.
- **FR-031**: The final review package MUST copy the four raw media sources and master, any permitted variants, manifest/evidence/cost/safe-area records, and a complete Owner checklist whose decision, notes, reviewer, and reviewed-at fields are blank.
- **FR-032**: A successful master MUST finish exactly at `READY_FOR_OWNER_REVIEW`, including when either guarded ratio is blocked, and MUST NOT fabricate any subjective approval or MTL readiness decision.
- **FR-033**: Tests MUST cover exact V2 rejection gates, one-submit lifecycle, known/unknown submit failure handling, provider failure, output validation, exact timeline/last-frame hold, safe-area blocking, blank review package, accounting, secret redaction, and protected-hash stability with fake providers and no network.

### Key Entities

- **Recovery Manifest**: Append-only contract binding the parent manifest, failed run, immutable history, local replacement, proposed future task, timeline, delivery policy, costs, and review stop.
- **Historical Task Record**: Exact provider task identity, terminal state, output/error evidence, and actual credits preserved from the failed run.
- **Local Product Cutaway**: Deterministic replacement media plus exact source, transformation, validation, and cost evidence.
- **TASK-04 Source Lineage**: Exact TASK-02 artifact identity, fixed frame index, extraction rule, extracted frame properties, and content hash.
- **Frozen TASK-04 Proposal**: Exact versioned prompt, input lineage, provider request boundary, and projected cost awaiting separate approval.
- **Recovery Timeline**: Ordered source intervals totaling exactly twenty seconds, including the future final-frame hold.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Recovery preparation performs exactly zero provider submissions, retries, replacements, network calls, and paid calls.
- **SC-002**: Original execution-manifest and provider-results bytes remain unchanged, while all three historical task IDs and outcomes are reproduced exactly in the new recovery evidence.
- **SC-003**: Repeated local TASK-03 preparation from the exact source produces a validated 72-frame, three-second, 1280x720, 24 fps, silent result and identical recorded hashes.
- **SC-004**: Repeated extraction of TASK-02 zero-based frame 96 produces the same validated PNG hash without examining or selecting any other frame.
- **SC-005**: The recovery manifest validates a twenty-second timeline and exact 50-credit actual / 75-credit projected-final budget with no arithmetic or lineage discrepancy.
- **SC-006**: Focused and full offline tests pass, secret scans find no credentials or authorization material, and every approved-source SHA remains unchanged.
- **SC-007**: Recovery preparation evidence preserves its historical `READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW` / Manifest V2 review checkpoints unchanged while the separately authorized Live stage writes new append-only evidence.
- **SC-008**: The authorized Live stage creates no more than one new provider task and never submits TASK-01, TASK-02, historical TASK-03, a replacement TASK-04, or any native-ratio task.
- **SC-009**: Every lifecycle interruption leaves enough durable evidence to prove whether a provider task ID is known; no repeated invocation can silently create a second TASK-04.
- **SC-010**: A successful local master has eight contiguous approved intervals, exactly 480 frames at 24 fps within encoding tolerance, and a two-second terminal hold sourced from the recorded last decoded TASK-04 frame.
- **SC-011**: Alternate-ratio outputs are either objectively gate-approved local files or explicit `BLOCKED_SAFE_AREA` records; absence of a variant never causes a provider regeneration.
- **SC-012**: The final Owner package exposes all required media and evidence with every subjective checklist field blank, while protected source/evidence hashes remain unchanged and secret/signed-URL scans pass.

## Assumptions

- The existing stopped Live run and its successful raw TASK-01/TASK-02 media are the authoritative historical evidence supplied by the Owner.
- The existing repository deterministic local-delivery conventions remain applicable to the local replacement and fixed-frame extraction.
- The Owner authorization supplied on 2026-08-21 approves only the exact Recovery Manifest V2 TASK-04 request and the subsequent local delivery work described above.
- Missing, drifted, invalid, or colliding local evidence is a hard stop; recovery does not repair sources or choose substitutes automatically.
- No Owner-approved geometric/subject-detection safe-area contract currently exists; unless such an objective contract is already implemented and passes, 1:1 and 9:16 remain blocked rather than guessed from visual content.
