# Implementation Plan: Post-Smoke Motion Variations

## Technical Context

Python 3.11 package; existing provider-neutral video domain, Runway motion adapter, append-only
`VideoRunStorage`, review-copy parser, and CLI routing are reused. Motion-only workflows load
configuration without requiring voice/script approval because they do not consume those inputs.

## Design

- Keep separate `motion-smoke-test` and `motion-generate` CLI parsers and typed motion options;
  smoke is always one `gen4_turbo`/five-second result with a cap no greater than 25 credits.
- Build a single-shot motion plan from the exact smoke prompt and create independent
  `MotionVideoRequest` objects for each post-smoke variation. The configured maximum is five;
  two additional variations are the recommended first request.
- Validate smoke evidence, immutable review copy, keyframe/prompt hashes, provider capability,
  historical-schema compatibility, variation limit, explicit cap, owner live permission, and
  Runway credential before provider construction.
- Reuse bounded `execute_provider_request` and `VideoRunStorage`; write the standard thirteen
  artifacts with motion-specific not-applicable script/audio evidence.
- Keep smoke guard implementation independent from pilot/talking guards. No HeyGen, talking, voice,
  or full-pilot provider is constructed on this path.

## Verification

Use fake providers only. Cover failed smoke/review/keyframe/prompt/cap/variation guards, zero-call
preview, exact smoke bounds, modern and historical review schemas, complete bundles, and
Runway-only live submission. Run the full offline suite and `git diff --check`; do not run a paid
provider call automatically. The real smoke run's review copy remains blank and therefore remains
an intentional `BLOCKED_EXTERNAL` gate.

## P1-2 planning checkpoint

The owner-requested P1-2 design is captured in `p1-2-motion-variation-plan.md`, with exact prompt
files under `prompts/motion-variation-v1.txt` through `v3.txt` and the derived schema in
`contracts/p1-2-evidence-schema.md`. The dry-run uses an explicit planning-only
`--motion-smoke-qa-attested` flag; it validates smoke/keyframe/output provenance, records the
owner instruction without editing the review copy, plans three Runway requests at 75 credits, and
submits zero calls. This flag is rejected by every Live path.
