# Feature Specification: Reviewed External K2 Workflow

**Feature Branch**: `codex/lady-lala-pilot-live`
**Created**: 2026-08-21
**Status**: Implemented; `READY_FOR_K2_HUMAN_REVIEW`
**Input**: Safely ingest, human-review, and exact-byte promote an owner-supplied talking-medium-closeup candidate while separating talking K2 authority from existing K1 motion/V7 authority.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stage an External K2 Candidate (Priority: P1)

As the production operator, I can import an owner-supplied Lady LaLa image as a pending talking-medium-closeup candidate without claiming provider generation or human approval.

**Why this priority**: Truthful immutable candidate evidence is required before review.

**Independent Test**: Import one valid image and verify exact bytes, truthful provenance, blank review, and zero approved-source/provider changes.

**Acceptance Scenarios**:

1. **Given** a valid local PNG/JPEG and unique ID, **When** it is imported, **Then** a collision-safe exact-byte staged copy, matching hashes, external-source provenance, and blank pending review are created.
2. **Given** a symlink, traversal, invalid/unsupported/oversized media, duplicate ID, or existing target, **When** import is attempted, **Then** it fails without partial acceptance.
3. **Given** an imported candidate, **When** evidence is inspected, **Then** it contains no generated run/provider/task/model/prompt or approval claim.

---

### User Story 2 - Human Review and Exact-Byte Promotion (Priority: P1)

As the Owner, I can review a candidate-bound blank QA record and promote K2 only after every required decision passes with attributable timezone-aware human authority.

**Why this priority**: Production may trust the role only after complete human review and integrity validation.

**Independent Test**: Review and promote a fixture, proving source/staged/approved bytes match, while incomplete, mismatched, stale, or unattributed reviews fail closed.

**Acceptance Scenarios**:

1. **Given** blank/incomplete review, **When** promotion is attempted, **Then** it is rejected with no approved or manifest change.
2. **Given** a fully passing exact-candidate review, reviewer, and timezone-aware time, **When** promotion runs, **Then** exact bytes and truthful provenance are approved and the K2 role is registered without changing K1.
3. **Given** drift, wrong role, candidate mismatch, or collision, **When** promotion runs, **Then** it fails atomically without overwrite or partial manifest mutation.

---

### User Story 3 - Resolve Talking K2 Separately from Motion K1 (Priority: P1)

As the video operator, I can validate Product Page, Tooltip, and Homepage talking work against K2 while retaining K1 and reviewed V7-A for motion/B-roll.

**Why this priority**: A shared keyframe either weakens talking composition or invalidates established motion evidence.

**Independent Test**: With approved K1/K2 fixtures, preview Product Page and verify talking uses K2 while motion/V7 uses K1; without K2, verify dry/live block before run/provider construction.

**Acceptance Scenarios**:

1. **Given** approved K1/K2, **When** a pilot resolves, **Then** talking uses K2, motion uses K1, and evidence records both separately.
2. **Given** existing K1/V7-A, **When** K2 is added, **Then** all K1/V7 bytes and provenance remain unchanged and valid.
3. **Given** no approved K2, **When** Product Page dry/live runs, **Then** it blocks before run allocation, HTTP, or paid submission.
4. **Given** approved K2 and valid K1/V7, **When** dry-run validates, **Then** it is ready with zero paid calls while live authority remains separate.

### Edge Cases

- Source changes between validation and staging; staged/provenance bytes drift later.
- Review alters immutable identity fields, omits headers, or has naive time.
- Duplicate promotion or approved target collision.
- Multiple approved records advertise one unique role.
- Historical evidence contains only a legacy single-keyframe field.
- Old Talking Smoke used K1 while the new talking authority is K2.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Import MUST accept one local owner-supplied PNG/JPEG using exact bytes and a unique safe ID.
- **FR-002**: Import MUST reject symlinks, traversal, mismatched/invalid/unsupported/oversized media, duplicates, and collisions.
- **FR-003**: Provenance MUST record candidate ID, role, external source type/reference, sanitized source identity, source/staged hashes, creation time, owner declaration, and `PENDING_HUMAN_REVIEW`.
- **FR-004**: Source/staged hashes MUST match; import MUST NOT transform, overwrite, or invent provider/generation provenance.
- **FR-005**: Import MUST create a versioned blank review bound to candidate ID/path/hash; all subjective/attribution fields start blank.
- **FR-006**: Review MUST include face identity, age, hair, eyes, mouth, body-proportions applicability, wardrobe, jewelry, extra people, text/logo, keyframe readiness, reviewer, review time, and notes.
- **FR-007**: Promotion MUST require literal `PASS` for every required QA/readiness field, including `body_proportions_pass`, plus a non-empty reviewer and timezone-aware review time. `notes` MAY remain blank and is never an approval signal.
- **FR-008**: Promotion MUST reject incomplete QA, missing attribution, naive time, schema/candidate/hash/path mismatch, drift, wrong role/type, and collisions.
- **FR-009**: Promotion MUST exact-byte copy an approved keyframe, write truthful provenance, and safely register `talking_medium_closeup` without changing K1.
- **FR-010**: Promotion MUST be non-overwriting and atomic across media, provenance, and manifest, cleaning partial work on failure.
- **FR-011**: Talking resolution MUST uniquely select K2; motion/B-roll MUST uniquely select K1 home-context/establishing authority.
- **FR-012**: New evidence MUST record talking and motion keyframe identity/path/role/hash/provenance separately while historical single-keyframe readers remain compatible.
- **FR-013**: Talking Smoke MUST match K2 and canonical motion prerequisite MUST match K1; K2 MUST NOT change K1/V7-A.
- **FR-014**: Missing/ambiguous K2 MUST block relevant dry/live workflows before run/provider/HTTP/paid work.
- **FR-015**: Valid dry-run MUST make zero paid calls; live and reviewed-smoke authority remain separate.
- **FR-016**: Historical evidence, approved sources, Owner decisions, and candidate bytes MUST remain unchanged.
- **FR-017**: The real candidate may be imported after tests, but review stays blank and promotion MUST NOT execute in this task.

### Non-Functional Requirements

- **NFR-001**: Import and promotion MUST be bounded local operations over a single file no larger than 20 MiB and MUST make zero network or provider calls.
- **NFR-002**: Every rejected operation MUST fail closed without overwriting an existing candidate, review, approved keyframe, promotion record, manifest entry, run, or historical evidence.
- **NFR-003**: User-facing evidence and errors MUST contain no credential, authorization header, signed download URL, fabricated provider field, or unsanitized absolute source path.
- **NFR-004**: Filesystem updates MUST use exclusive creation and hash verification. The manifest becomes authoritative only after media and promotion evidence exist; recoverable in-process failures MUST restore the pre-operation manifest and remove newly created targets.

### Out of Scope

- Generating, cropping, resizing, enhancing, re-encoding, or auto-scoring the owner candidate.
- Automatically filling Human QA, promoting the real K2, authorizing Live, or making Runway/HeyGen calls.
- Replacing or rewriting K1, canonical V7-A, historical run evidence, or existing approved roles.
- Generalizing the workflow to arbitrary keyframe roles or implementing the rest of Track B.

### Key Entities

- **External Keyframe Candidate**: Staged exact bytes, identity, intended role, source reference, hashes, status, and provenance.
- **External K2 Review**: Versioned blank baseline and human review copy bound to one candidate/hash.
- **External Keyframe Promotion**: Exact approved copy and provenance created from complete human authority.
- **Talking/ Motion Keyframe Authorities**: Unique K2 talking and existing K1 motion records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One command stages valid K2 with identical source/staged hashes and one blank review.
- **SC-002**: Every unsafe import/review case is rejected with zero approved-source changes.
- **SC-003**: A reviewed fixture promotes with identical source/staged/approved hashes; duplicate promotion adds zero files.
- **SC-004**: Product Page dry-run uses K2 talking and unchanged K1 motion/V7, records both, and makes zero calls.
- **SC-005**: Missing K2 blocks dry/live before provider construction and without creating a run.
- **SC-006**: Full offline verification and source/security checks pass with all provider accounting zero.
- **SC-007**: Real K2 ends `READY_FOR_K2_HUMAN_REVIEW` with staged path/hash/blank review and unexecuted promotion command.
- **SC-008**: Requirement-to-task traceability covers every FR, NFR, and buildable SC, and incomplete verification remains visibly unchecked.

## Assumptions

- Candidate IDs are bounded lowercase ASCII slugs.
- Owner source reference is an audit statement, not approval.
- A dedicated versioned K2 review schema avoids weakening generated-output review.
- Pending candidates live outside approved sources; approved K2 uses the immutable approved-keyframe boundary.
- K1/V7 remains motion authority; K2 Talking Smoke requires later separate Owner authorization/review.
