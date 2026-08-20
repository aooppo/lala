# Feature Specification: Post-Smoke Motion Variations

**Feature Branch**: `feat/post-smoke-motion-variations`
**Feature Directory**: `003-post-smoke-motion-variations`
**Status**: Offline implementation complete; live variation path remains review-gated

The one-result motion smoke and the post-smoke variation stage are separate workflow stages.
Smoke establishes technical/provider evidence; post-smoke generation is unlocked only by an
immutable external review copy containing explicit human decisions. The system never fills those
decisions automatically.

## User Scenarios & Testing

### User Story 1 — Generate reviewed motion alternatives (P1)

As an MTL visual reviewer, I can generate one to five Runway motion alternatives from the same
approved keyframe and smoke prompt after a successful motion smoke and explicit manual review.

**Acceptance scenarios**

1. A passing motion smoke, immutable reviewed copy, matching keyframe and prompt digests, explicit
   credit cap, and bounded variation count allow only Runway submissions and produce one
   independent result per variation.
2. Missing/failed smoke, incomplete review, changed keyframe or prompt, absent/insufficient cap,
   unsupported model/duration/ratio, or over-limit variation count fails before provider submission.
3. Dry-run validates the same inputs, writes a complete run bundle, and performs zero submissions.
4. The motion smoke command remains one `gen4_turbo` result at exactly five seconds and at most 25
   Runway credits.

## Functional Requirements

- **FR-001**: `video motion-generate` MUST support keyframe, model, duration, ratio, variations,
  motion-smoke-run-id, motion-smoke-review-file, max-runway-credits, and live/dry-run options.
- **FR-002**: Live generation MUST require `VIDEO_ALLOW_LIVE_CALLS=true`, a successful motion smoke,
  a passing immutable manual review copy, matching keyframe and prompt SHA-256 values, an explicit
  cap, and variations within configured `max_motion_variations_per_shot` (1–5).
- **FR-003**: Motion generation MUST instantiate/call only the Runway motion provider; it MUST NOT
  call HeyGen, synthesize voice, run talking, or execute the complete pilot.
- **FR-004**: Every variation MUST use the same approved keyframe and exact smoke prompt while
  retaining independent task/output provenance and blank human QA rows.
- **FR-005**: Each invocation MUST create the existing thirteen-artifact append-only run bundle,
  including cost/cap evidence, task events, hashes, provider results, and review CSV.
- **FR-006**: Existing motion smoke live guards MUST remain strict: one variation, `gen4_turbo`,
  five seconds, and no more than 25 Runway credits.
- **FR-007**: The smoke stage and post-smoke stage MUST remain separate commands and run records;
  post-smoke live generation MUST require explicit owner authorization in addition to the reviewed
  external copy. The first recommended post-smoke request is two additional variations, while the
  configured hard maximum is five.
- **FR-008**: The implementation MUST accept the already-existing historical motion-review CSV
  schema only when its provenance fields match the smoke run and its supported motion decisions are
  explicit; an unknown or ambiguous schema MUST fail closed. The current unified QA schema remains
  strict and is not weakened for other video workflows.

## Success Criteria

- **SC-001**: All seven guard tests fail closed before a Runway submission when their prerequisite
  is absent or invalid.
- **SC-002**: A dry-run creates zero provider submissions and a complete thirteen-artifact bundle.
- **SC-003**: A bounded live fixture with three variations records three Runway submissions and
  three independently reviewable outputs without any HeyGen call.
- **SC-004**: For `gen4_turbo`, the estimate is `5 credits/second × duration_seconds × variations`;
  a five-second smoke therefore has a maximum estimate of 25 credits, and a post-smoke request is
  rejected before provider construction when its estimate exceeds the explicit cap.

## Assumptions

- Motion smoke evidence uses the existing video run schema and its output review row.
- Runway credit estimates use the verified per-second model pricing in `configs/providers.yaml`.
