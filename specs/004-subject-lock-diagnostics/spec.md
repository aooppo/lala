# Feature Specification: Subject Lock Diagnostics

**Feature Branch**: `feat/p1-1-subject-lock-control`

**Created**: 2026-08-20

**Status**: Implemented and offline-verified

**Input**: Archive the V6 human-QA failure, add quantitative provider-neutral subject-position and scale diagnostics to motion review packages, allow P1-2 offline/dry-run work, and keep P1-2 live blocked until P1-1 human MTL readiness passes. No real provider calls are authorized.

## User Scenarios & Testing

### User Story 1 - Quantify Subject Lock (Priority: P1)

As a motion reviewer, I can inspect reproducible measurements of a visible subject's position and apparent scale across sampled video frames so I can distinguish subject drift from camera/background drift without treating automation as human approval.

**Why this priority**: V1-V6 established that prompt-only locking and camera evidence do not reliably prove subject framing stability.

**Independent Test**: Analyze deterministic locked, translated, scaled, and lost-subject frame sequences and verify the reported trajectory, drift, scale, tracking coverage, and diagnostic state.

**Acceptance Scenarios**:

1. **Given** a consistently visible subject with unchanged position and scale, **When** diagnostics run, **Then** center and scale changes remain approximately zero and the result is within configured thresholds.
2. **Given** a subject translated 20 pixels horizontally and 30 pixels vertically, **When** diagnostics run, **Then** the first-to-last displacement is approximately 20/30 pixels and the result is outside threshold.
3. **Given** a subject whose reference region shrinks by approximately ten percent, **When** diagnostics run, **Then** the result records a material negative scale change and is outside threshold.
4. **Given** insufficient reliable subject observations, **When** diagnostics run, **Then** the result is `INSUFFICIENT_EVIDENCE`, never a passing or within-threshold result.

---

### User Story 2 - Package Diagnostic Evidence (Priority: P1)

As an owner reviewer, I receive subject-lock summary, trajectory, and visual overlay evidence in every motion-smoke review package so I can rapidly inspect measurements while retaining sole authority over QA decisions.

**Why this priority**: Measurements are useful only when preserved with the same integrity, archive, and secret-scan guarantees as existing motion evidence.

**Independent Test**: Build a review package from local fixture media and verify the three subject-lock artifacts, manifest hashes, archive members, integrity checks, report summary, and unchanged blank human review fields.

**Acceptance Scenarios**:

1. **Given** a local motion result, **When** its review package is built, **Then** it includes `subject-lock.json`, `subject-trajectory.csv`, and `subject-overlay.png` in its checksum manifest and archive.
2. **Given** a diagnostic result, **When** a report is displayed, **Then** it labels the values as diagnostic evidence and separately shows whether human QA is set.
3. **Given** package generation, **When** diagnostics complete or fail to track, **Then** neither the run review nor packaged review receives automatic human decisions.

---

### User Story 3 - Continue P1-2 Safely Offline (Priority: P1)

As a production operator, I can plan and dry-run all three P1-2 motion candidates after a failed P1-1 review while live provider execution remains blocked before provider construction.

**Why this priority**: A failed visual smoke should not stop safe offline engineering, but it must remain an effective paid-call boundary.

**Independent Test**: Use a failed immutable P1-1 review copy to run three-candidate dry-run planning and a simulated live attempt; verify three planned calls, zero submissions/tasks/HTTP calls, and pre-provider live rejection.

**Acceptance Scenarios**:

1. **Given** P1-1 human review FAIL, **When** P1-2 offline planning or dry-run is requested, **Then** three candidates are resolved with provenance, estimates, and blank QA without constructing a provider.
2. **Given** the same failed review, **When** P1-2 live is requested under mocks, **Then** execution is blocked before provider construction with zero HTTP requests, tasks, submissions, or paid calls.
3. **Given** a later immutable P1-1 review with all required human decisions and MTL readiness true, **When** the existing live gate is evaluated, **Then** the review may satisfy only that prerequisite; all other live permissions, credentials, and bounds still apply.

### Edge Cases

- The first frame has no reliable subject reference.
- Tracking succeeds initially but is lost for enough later samples to fall below the configured success rate.
- A tracker returns low-confidence or invalid/out-of-frame boxes.
- Scale change is directional: width and height differ or one grows while the other shrinks.
- A diagnostic artifact is missing or changed after checksum generation.
- Existing review packages are rebuilt from local media without modifying their original run evidence.
- P1-2 dry-run receives a blank or failing review copy; it must remain offline and must not reinterpret the copy as approval.

## Requirements

### Functional Requirements

- **FR-001**: The workflow MUST expose a provider-neutral subject-tracker contract and local deterministic implementation that requires no network or runtime model download.
- **FR-002**: The diagnostic MUST sample video frames and record frame index, timestamp, reference box, center, displacement from the first tracked frame, width/height changes, and tracking confidence.
- **FR-003**: The diagnostic summary MUST record sampled/tracked counts, success rate, first-to-last X/Y displacement, maximum absolute X/Y displacement, maximum center distance, first-to-last width/height changes, maximum absolute scale change, measurement scope, thresholds, and diagnostic status.
- **FR-004**: Invalid, unavailable, or insufficient tracking MUST yield `INSUFFICIENT_EVIDENCE` and MUST NOT be represented as zero drift or within threshold.
- **FR-005**: Center, scale, and minimum tracking thresholds MUST be configuration-controlled and MUST produce diagnostic-only states without filling or changing human QA.
- **FR-006**: The initial measurement scope MUST explicitly identify whether the reference is a face proxy or another limited subject proxy and MUST NOT claim full-body segmentation when it is not performed.
- **FR-007**: Motion-smoke review packages MUST include `subject-lock.json`, `subject-trajectory.csv`, and `subject-overlay.png` in checksum, archive, integrity, and secret-scan coverage.
- **FR-008**: Reports MUST summarize subject-lock scope, tracking coverage, position/scale changes, diagnostic state, and separately identify unset human QA.
- **FR-009**: Diagnostics MUST leave original media, approved sources, append-only run evidence, and every human review field byte-unchanged.
- **FR-010**: The V6 local regression analysis MUST report non-zero material drift or scale outside the specified acceptance bound, or `INSUFFICIENT_EVIDENCE`; it MUST NOT report perfect subject lock or `WITHIN_THRESHOLD` when tracking fails.
- **FR-011**: P1-2 offline planning and dry-run MUST remain available after P1-1 human QA fails and MUST construct no provider or network request.
- **FR-012**: P1-2 live execution MUST require a passing immutable P1-1 human review with MTL readiness true and MUST reject a failing review before provider construction.
- **FR-013**: The implementation MUST use existing lightweight local media dependencies and MUST NOT add cloud vision, runtime weight downloads, heavyweight ML frameworks, generated stabilization, or a new production prompt version.
- **FR-014**: Automated coverage MUST include locked, translated, scaled, and tracking-loss sequences; threshold configuration; review immutability; package artifacts/checksums; P1-2 failed-review dry-run allowance; and pre-provider live blocking.
- **FR-015**: All verification in this feature MUST be offline, with zero Runway, HeyGen, voice, talking, or other provider calls.

### Key Entities

- **Subject Observation**: One sampled frame's timestamp, proxy bounding box, center, confidence, and changes relative to the first reliable observation.
- **Subject Lock Summary**: Aggregated tracking coverage, drift and scale metrics, configured thresholds, scope, and diagnostic state.
- **Subject Lock Thresholds**: Maximum center displacement, maximum scale change, and minimum tracking success rate used only for diagnostic classification.
- **Motion Review Package**: Existing runtime evidence bundle extended with subject-lock artifacts while preserving blank human QA.
- **P1-2 Execution Gate**: Mode-aware policy that permits offline/dry-run planning but requires a passing immutable P1-1 human review before live provider construction.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Deterministic locked synthetic input reports approximately zero center and scale change.
- **SC-002**: Deterministic translation input reports displacement within a small test tolerance of 20 horizontal and 30 vertical pixels.
- **SC-003**: Deterministic ten-percent shrink input reports a material negative width or height change and an outside-threshold diagnostic.
- **SC-004**: One hundred percent of insufficient-tracking cases report `INSUFFICIENT_EVIDENCE`, and zero report within threshold.
- **SC-005**: Every newly built motion-smoke review package contains all three required subject-lock artifacts, includes their exact hashes in `SHA256SUMS`, and includes them in its ZIP.
- **SC-006**: The V6 offline analysis either detects at least 10 pixels X drift, 10 pixels Y drift, or 5 percent scale change, or reports `INSUFFICIENT_EVIDENCE`; it never reports `WITHIN_THRESHOLD` after tracking failure.
- **SC-007**: The canonical three-candidate P1-2 dry-run reports three planned calls, zero submissions, zero task IDs, zero provider construction, and zero paid calls while P1-1 remains failed.
- **SC-008**: One hundred percent of mocked P1-2 live attempts with failed P1-1 review stop before provider construction and make zero HTTP requests or tasks.
- **SC-009**: The full offline test suite remains at or above the 198-test baseline with no regression, approved-source hashes unchanged, and secret/integrity scans passing.

## Assumptions

- Subject measurements are diagnostic proxies, not biometric identity scoring or automatic creative approval.
- Human review remains the sole authority for P1-1 pass/fail and MTL readiness.
- Existing OpenCV, NumPy, Pillow, and FFmpeg capabilities are preferred; no dependency addition is expected.
- Runtime evidence under `runs/` and `outputs/` remains ignored and is not committed.
- Existing V6 media is the only real-video regression sample; no provider download or new generation is needed.
- Subject stabilization, compositing, inpainting, face replacement, and new V7/V8 prompts are out of scope.
