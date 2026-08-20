# Feature Specification: P1-1 Motion V7 Controlled Live Batch

**Feature Branch**: `fix/p1-1-motion-v7-live-batch`

**Created**: 2026-08-20

**Status**: Ready for planning

**Input**: Add a guarded controlled live execution path for the existing immutable V7 A/B/C motion experiment without making a real provider call during implementation.

## User Scenarios & Testing

### User Story 1 - Execute One Fixed Authorized V7 Batch (Priority: P1)

As the P1-1 operator, I can explicitly authorize one complete V7 experiment so the three canonical candidates are submitted once each in A/B/C order with no candidate selection or automatic replacement.

**Why this priority**: The merged V7 workflow prepares reproducible dry-run evidence but cannot yet execute the controlled experiment that human review requires.

**Independent Test**: Use a fake Runway-compatible provider with both runtime confirmations and live permission present; verify exactly three submission attempts contain the canonical A/B/C prompts and no fourth attempt occurs.

**Acceptance Scenarios**:

1. **Given** valid authoritative inputs, fixed configuration, full runtime authorization, and a fake provider, **When** the live batch is requested, **Then** A, B, and C are each submitted exactly once in that order under one parent run.
2. **Given** either runtime confirmation or provider live permission is absent, **When** the live batch is requested, **Then** it fails before provider construction or submission.
3. **Given** the live command, **When** its interface is inspected, **Then** it offers no candidate, skip, subset, or range selection.

---

### User Story 2 - Fail Closed Before the First Submission (Priority: P1)

As the production owner, I can trust that every member of the batch, its source, cost, provider configuration, authorization, and plan evidence are validated before candidate A can incur a task.

**Why this priority**: Submitting A before discovering an invalid B or C would create a paid, scientifically incomplete experiment.

**Independent Test**: Independently invalidate A length, B length, C existence, candidate count, order, prompt mapping, authorization, and source input; every case must produce zero submissions.

**Acceptance Scenarios**:

1. **Given** any invalid candidate or mapping anywhere in the A/B/C batch, **When** preflight runs, **Then** all three are rejected together and provider submissions remain zero.
2. **Given** valid candidates but an invalid source, provider setting, unavailable estimate, missing authorization, or unavailable evidence destination, **When** preflight runs, **Then** no candidate is submitted.
3. **Given** a valid batch, **When** preflight completes, **Then** append-only plan evidence is written and verified before A submission begins.

---

### User Story 3 - Preserve Partial Failure Evidence and Human Authority (Priority: P1)

As a reviewer, I can inspect a complete parent record after success or partial failure, while all subjective QA stays blank and neither successful tasks nor diagnostics unlock P1-2 Live.

**Why this priority**: Durable task IDs are idempotency boundaries, and provider success is not a human P1-1 pass.

**Independent Test**: Make fake A submission succeed and B submission raise an error; verify A's task ID, B's failure, C's not-submitted state, two attempts, zero retries/replacements, three blank QA rows, pending V7 diagnostics, and the unchanged P1-2 gate.

**Acceptance Scenarios**:

1. **Given** A succeeds and B submission fails, **When** the batch executes, **Then** C is not submitted, no retry or replacement occurs, and the parent record preserves both A's task ID and B's error.
2. **Given** all three submissions complete, **When** evidence is inspected, **Then** it contains three correctly associated task IDs/results and exactly three blank human QA rows.
3. **Given** any provider result or Subject Lock diagnostic, **When** the record is produced, **Then** Camera Lock, Framing, Identity, Eyes, Mouth, Motion, and MTL Ready remain human-only and P1-2 Live remains blocked pending explicit human pass.

### Edge Cases

- A prompt becomes missing, duplicated, remapped, or reaches 1,000 UTF-16 units.
- The manifest has fewer or more than three candidates, duplicate IDs, or reordered candidates.
- The approved keyframe path or digest no longer matches its recorded provenance.
- Credit estimation is unknown, non-finite, exceeds the explicit cap, or the evidence destination cannot be prepared.
- Provider request validation fails for B or C after A was locally prepared; no submission may have occurred.
- A provider submission throws before returning a task ID; the failure is recorded once and later candidates remain not submitted.
- A durable task ID exists but polling, terminal processing, or download fails; no replacement submission is created.

## Requirements

### Functional Requirements

- **FR-001**: The workflow MUST expose one controlled V7 live-batch operation containing exactly `v7-a-stability-first`, `v7-b-natural-micro-motion`, and `v7-c-controlled-upper-bound` in fixed A/B/C order.
- **FR-002**: The live operation MUST NOT accept candidate, subset, skip, or range selection.
- **FR-003**: Canonical `configs/motion-v7.yaml` entries MUST remain `live_allowed=false`; execution MUST require both explicit command confirmations, exact video live permission, a non-empty Runway credential, and an explicit credit cap.
- **FR-004**: Before the first submission, the workflow MUST prepare and validate all three candidates, exact prompt mappings, unique IDs/mappings, prompt existence/hash/UTF-16 length, approved source existence/hash, Runway configuration, request validity, known per-candidate and total credit estimates, authorization, cap, and evidence destination.
- **FR-005**: If any full-batch preflight check fails, the workflow MUST make zero provider submissions and MUST NOT create a replacement or partial experiment.
- **FR-006**: Successful preflight MUST write and read back verifiable parent plan evidence before candidate A submission.
- **FR-007**: The live runner MUST attempt at most one new Runway task per candidate and at most three new tasks for the parent batch, with automatic task-creation retry disabled.
- **FR-008**: Submission processing MUST be sequential and fail-stop: an A failure skips B/C; a B failure after A skips C; a C failure preserves A/B and ends the batch.
- **FR-009**: A returned provider task ID MUST remain the idempotency boundary; polling or download MUST never trigger a replacement submission.
- **FR-010**: One append-only parent run MUST record run type, authoritative code commit, timestamps/status, source reference/hash, planned and actual submission counts, authorization state, provider, known estimates, HTTP accounting state, task IDs, and per-candidate prompt/result/output provenance without secrets.
- **FR-011**: The parent run MUST prepare exactly three review rows and leave every human QA and MTL-readiness field blank regardless of provider or diagnostic results.
- **FR-012**: V7 Subject Lock values MUST remain pending until actual diagnostics are separately produced; diagnostics remain `color_region_proxy` evidence and cannot fill Human QA.
- **FR-013**: V7 live implementation or provider/diagnostic success MUST NOT unlock P1-2 Live; only explicit later Human QA plus MTL readiness can satisfy that gate.
- **FR-014**: The V7 execution path MUST construct and call only the Runway motion provider; it MUST NOT invoke talking, voice, HeyGen, assembly, promotion, or P1-2 generation.
- **FR-015**: Existing `motion-v7-dry-run` behavior MUST remain unchanged at three planned submissions, zero actual submissions/task IDs/paid calls, 75 configured credits, and three blank QA rows.
- **FR-016**: Automated tests MUST exercise the actual live orchestration with fakes for authorized A/B/C success, every required preflight failure, partial submission failure, CLI guards, provider isolation, dry-run regression, Subject Lock, and P1-2 gates.
- **FR-017**: Implementation and tests for this feature MUST make zero real Provider HTTP requests, tasks, or paid calls.

### Key Entities

- **V7 Live Batch Plan**: The immutable, verified pre-submission parent plan containing the exact three candidates, source provenance, authorization evidence, estimates, cap, provider, and code commit.
- **V7 Candidate Execution**: Per-candidate state progressing from planned to submitted/failed/not-submitted with one prompt provenance record, at most one task ID, provider result, output references, and no automatic replay.
- **V7 Parent Run**: One append-only thirteen-artifact run containing plan, events, results, cost/accounting, pending diagnostics, and three blank review rows.

## Success Criteria

### Measurable Outcomes

- **SC-001**: An authorized fake batch produces exactly three submission attempts in A/B/C order, three correctly associated results, and no fourth attempt.
- **SC-002**: Each of the eight required preflight-failure scenarios produces exactly zero provider submissions, including an invalid B after a valid A.
- **SC-003**: In an A-success/B-submission-error scenario, exactly two attempts occur, A's task ID is retained, B is failed, C is not submitted, and retries/replacements are zero.
- **SC-004**: Every completed or partial live-batch record contains exactly thirteen run artifacts and three rows whose human QA fields are all blank.
- **SC-005**: The existing V7 dry-run retains three planned calls, zero submissions/task IDs/paid calls, and a 75-credit estimate.
- **SC-006**: All focused and full offline test suites pass with zero real Runway, HeyGen, voice, talking, assembly, promotion, P1-2, or other provider activity.

## Assumptions

- The existing three prompt files, their authoritative hashes, and canonical live-disabled manifest remain unchanged.
- The current configured estimate is 25 Runway credits per five-second candidate, 75 total; unknown estimates fail closed.
- Runtime authorization uses `--execute-live`, `--confirm-v7-batch`, exact `VIDEO_ALLOW_LIVE_CALLS=true`, a local `RUNWAYML_API_SECRET`, and `--max-runway-credits` at least the known batch estimate.
- Provider polling and download may make a provider-dependent number of HTTP requests; evidence records task submission attempts separately and marks total HTTP count unknown unless the adapter exposes an exact counter.
- A non-success terminal result stops the controlled batch as a conservative extension of the required submission-error fail-stop rule.
