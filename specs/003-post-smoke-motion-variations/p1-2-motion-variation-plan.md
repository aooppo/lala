# P1-2 Motion Variations — Owner Review Plan

**Status:** planning and dry-run only; no Runway Live authorization.

**Baseline smoke:** `LALA-VIDEO-20260820-040258-MOTION-SMOKE-001`
**Smoke QA state:** passed per the owner instruction in the 2026-08-20 task request. The
original run and its external review copy remain immutable and unchanged; this statement is a
planning attestation, not a rewrite of human QA fields.
**Source keyframe:** `pilot_home_context` → `assets/approved_keyframes/lady-lala-home-context-v0.7.png`
**Smoke model / duration / ratio:** `gen4_turbo` / `5s` / `1280:720`
**Smoke prompt:** `prompts/home-broll-v3.txt` (SHA-256 recorded in the smoke run)

## Invariants and prohibitions

Every candidate uses the same approved keyframe, identity, apparent age, hairstyle, wardrobe,
jewelry, room decor, color palette, lighting, scale, and framing. The camera stays locked off and
the subject remains fully visible. No walking, stepping, moving toward camera, leaving frame,
large body rotation, speaking/lip-sync, camera push-in, tracking, zoom, reframing, or scene
transition is permitted.

The exact candidate prompts are versioned at `prompts/motion-variation-v1.txt` through `v3.txt`.
They are design candidates only; the existing Smoke prompt and smoke evidence are not changed.

## Controlled variation matrix

| variation_id | purpose | prompt | UTF-16 units | model | duration | ratio | estimated credits | expected risk | QA acceptance criteria |
|---|---|---|---:|---|---:|---|---:|---|---|
| `MOTION-VAR-001` | Lowest-risk natural presence cue | `prompts/motion-variation-v1.txt` (`2a62b84d…`) | 959 | `gen4_turbo` | 5s | 1280:720 | 25 | Low | Identity, apparent age, hair, wardrobe, jewelry, background and framing unchanged; feet stay fixed; breathing/blink/head movement are subtle and return to baseline; no forbidden motion; technical export is 5s, 1280×720 MP4. |
| `MOTION-VAR-002` | Test attention toward room decor without body travel | `prompts/motion-variation-v2.txt` (`31feb46e…`) | 985 | `gen4_turbo` | 5s | 1280:720 | 25 | Low–medium | All identity/environment/framing checks pass; gaze shift is small, singular and reversible; head follows by only a few degrees; no torso/feet/camera movement; no lip motion; technical export passes. |
| `MOTION-VAR-003` | Add a restrained product/room presentation cue | `prompts/motion-variation-v3.txt` (`023d1b1b…`) | 997 | `gen4_turbo` | 5s | 1280:720 | 25 | Medium | All identity/environment/framing checks pass; one hand moves only a few inches at waist height and returns; elbow stays close; no pointing/waving, body rotation, crop, camera motion, or speaking; technical export passes. |

## Budget

Runway pricing evidence in `configs/providers.yaml` is 5 credits/second for `gen4_turbo`.
Therefore each 5-second candidate is estimated at **25 credits**; the three-candidate design is
**75 credits**. A single 25-credit Live authorization can request only one candidate, not all
three. No retries, concurrency increase, or replacement submission is implied by this estimate.

## Recommendation and gate

Recommend first real generation of `MOTION-VAR-001`: it is the smallest motion delta and gives the
cleanest identity/framing regression signal after the passing smoke. If the Owner permits exactly
one 25-credit Live call, choose `MOTION-VAR-001` for the same reason.

P1-2 is **not Live-executable yet**. Technical planning inputs are present, but execution still
requires Owner approval of this variation plan, an explicit `--live` authorization, exact
`VIDEO_ALLOW_LIVE_CALLS=true`, a local `RUNWAYML_API_SECRET`, and the immutable reviewed smoke
evidence accepted by the production gate. This task performs none of those paid actions.
