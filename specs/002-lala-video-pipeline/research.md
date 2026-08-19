# Research: Reproducible Lady LaLa Video Pipeline

**Verified**: 2026-08-19

Only current official provider documentation and official package/release metadata are treated as
API evidence. Web-application controls are not used as evidence.

## Decision 1 — Talking-video provider strategy

**Decision**: Use HeyGen v3 image-plus-approved-audio as the default first talking-shot provider.
Support Runway `gwm1_avatars` only when configuration supplies a human-approved custom avatar ID
whose mapping includes the exact approved keyframe hash.

**Rationale**: HeyGen documents `POST /v3/videos` with `type: image`, an image supplied by URL,
asset ID, or base64, and exactly one `audio_url` or `audio_asset_id`. This maps directly to the
required one-keyframe-plus-one-approved-audio smoke test. The response returns `video_id`; the
workflow polls `GET /v3/videos/{video_id}` until `completed` or `failed` and downloads `video_url`.

Runway now documents `POST /v1/avatar_videos` with model `gwm1_avatars`, an avatar reference, and
audio or text speech. A custom avatar must first be created via `POST /v1/avatars`, which requires
`name`, `referenceImage`, `personality`, and a preset/custom voice, and may process the image.
That persistent setup makes a raw keyframe-to-approved-audio smoke test less direct. An approved
custom avatar mapping is therefore supported but never created implicitly during generation.

**Official sources**:

- `https://developers.heygen.com/audio-to-video`
- `https://developers.heygen.com/reference/create-video`
- `https://developers.heygen.com/reference/get-video`
- `https://developers.heygen.com/reference/upload-asset`
- `https://docs.dev.runwayml.com/api/#tag/Avatar-Videos`
- `https://docs.dev.runwayml.com/api/#tag/Avatars`

**Alternatives considered**:

- Runway-only talking path: supported by the current API but rejected as the default because it
  requires prior custom-avatar creation and a voice/personality configuration unrelated to the
  selected approved WAV.
- Runway Act-Two: rejected for this flow because it requires a three-to-thirty-second driving
  performance video, not only the approved audio.
- Text-driven speech: retained as Mode B but not selected for MVP because approved WAV should
  bypass unnecessary synthesis.

## Decision 2 — Runway motion/B-roll adapter

**Decision**: Use Runway `POST /v1/image_to_video` as the motion abstraction. Default to
`gen4_turbo` for bounded shot alternatives; allow configured `gen4.5` for owner-reviewed quality
tests.

**Rationale**: API version `2024-11-06` documents both models with first-frame `promptImage`,
provider-contained `promptText`, supported landscape ratio `1280:720`, optional seed, and two-to-
ten-second durations. `gen4.5` requires prompt text, image, ratio, duration, and model.
`gen4_turbo` requires image, ratio, and model and accepts the same bounded motion fields. Both
return an asynchronous task ID and an estimated credit object.

**Official sources**:

- `https://docs.dev.runwayml.com/api/#tag/Start-generating/paths/~1v1~1image_to_video/post`
- `https://docs.dev.runwayml.com/guides/pricing/`
- `https://docs.dev.runwayml.com/api-details/versions/2024-11-06/`

**Alternatives considered**:

- `gen4.5` as default: rejected because its documented rate is more than twice `gen4_turbo`; shot-
  level review should prove whether the quality difference is valuable before increasing spend.
- Runway product/multi-shot recipes: rejected for the core because they collapse planning and
  assembly responsibilities that must remain reproducible and provider-neutral.
- Act-Two for B-roll: rejected because it is a performance-transfer model, not general camera or
  environment motion from a keyframe.

## Decision 3 — Provider versions and pricing evidence

**Decision**: Pin `runwayml==5.15.0`, record API version `2024-11-06`, and encode dated pricing
metadata rather than hardcoded totals. Use verified formulas only when all required duration and
model inputs are known.

**Rationale**: PyPI and the official Runway SDK repository report 5.15.0 as the current Python SDK
release on 2026-08-18. Runway states one credit costs USD 0.01; `gen4_turbo` is five credits per
output second and `gen4.5` is twelve. HeyGen self-serve pricing lists Avatar IV Photo Avatar at
USD 0.05 per output second for 720p/1080p. Provider responses and actual billing evidence override
static estimates when available. Unknown voice, storage, avatar-setup, or ambiguous costs remain
null.

**Official sources**:

- `https://pypi.org/project/runwayml/`
- `https://github.com/runwayml/sdk-python/releases/tag/v5.15.0`
- `https://docs.dev.runwayml.com/guides/pricing/`
- `https://developers.heygen.com/docs/pricing`

**Alternatives considered**:

- Continue SDK 5.14.0: rejected because 5.15.0 is the current official release used to verify the
  new video surfaces.
- Fabricated zero or aggregate estimates: rejected; unavailable components remain null.
- Real-time pricing lookups in dry run: rejected because dry run must remain offline and zero-call.

## Decision 4 — Voice handling

**Decision**: Prefer an approved WAV matched to the exact selected script. For optional Mode B,
use the provider-neutral `VoiceProvider` boundary with a concrete HeyGen Starfish adapter only
when configuration supplies an approved reusable private voice ID and profile.

**Rationale**: Mode A preserves the already-approved voice and avoids cost and identity drift.
Script and audio hashes are recorded together. HeyGen documents synchronous Starfish speech at
`POST /v3/voices/speech`, accepting exact text, `voice_id`, `input_type`, optional speed, and
language/locale, and returning an `audio_url`, duration, and request ID. Private cloned voices are
discoverable through the voice-list endpoint with `type=private` and `engine=starfish`. The adapter
downloads the result to a derived path, converts it to validated PCM WAV, and records the provider
request ID and script hash; it never treats generated audio as an approved source. The approved
voice profile remains a human-owned prerequisite, and Mode A still takes precedence whenever a
script-matched WAV exists.

**Official sources**:

- `https://developers.heygen.com/reference/generate-speech`
- `https://developers.heygen.com/reference/list-voices`

**Alternatives considered**:

- Always re-synthesize: rejected because it adds cost and voice variation without product value.
- Treat a provider voice ID as approval: rejected; configuration metadata is not human approval.
- Store credentials in the voice profile: rejected by constitution and security requirements.

## Decision 5 — Deterministic editing

**Decision**: Use local FFmpeg/FFprobe through an injectable command runner. Normalize selected
shots to the preset canvas, frame rate, pixel format, and codec; preserve exact speech by using
the selected approved audio as the final audio source; refuse overwrite; and record shell-escaped
commands before execution.

**Rationale**: Concatenation, trimming, scaling, letterboxing, transitions, audio normalization,
replacement, and export do not require a generative provider. FFprobe supplies media evidence;
FFmpeg 8.0 is available in the current workspace. An injected runner makes automated tests
offline and platform-safe.

**Alternatives considered**:

- Generative editing: rejected as costly and non-deterministic.
- MoviePy: rejected because it adds a Python media stack while ultimately relying on FFmpeg.
- Blind concatenation: rejected because mismatched streams and durations can create invalid or
  desynchronized exports.

## Decision 6 — Append-only storage and staged orchestration

**Decision**: Initialize exactly thirteen video run artifacts once, append task events as JSONL,
write terminal provider and cost facts once per run stage, and never revise past media. Shot
generation and final assembly are separate commands/stages joined by explicit selections.

**Rationale**: A provider task ID must survive interruptions without resubmission. Separate stages
allow MTL to select shot alternatives before full assembly and keep paid generation counts small.
Promotion copies a hash-verified candidate to a monotonically versioned approved filename and
adds provenance without altering either source.

**Alternatives considered**:

- One command that regenerates and assembles everything: rejected because review cannot intervene
  before expensive work.
- Rewriting a run record after review: rejected because it destroys evidence; the run's review CSV
  remains blank, and human decisions live in a separate hash-recorded copy under `outputs/reviews/`.
- Moving selected files: rejected because candidates are evidence and must remain intact.

## Decision 7 — Authoritative package import and remaining voice dependency

**Decision**: Import the owner-supplied package keyframe, three exact-byte MTL scripts, and eight
canonical voice-cloning WAVs into the existing source locations. Because repository inspection
found no genuine Goal 1 promoted keyframe, register the package keyframe through a narrow
`owner_supplied_legacy_asset` provenance branch. Keep the voice profile pending until a real
approved HeyGen Starfish/private Lady LaLa profile or approved per-script narration is supplied.

**Rationale**: `lala-goal2-authoritative-inputs-v1.0.0.zip` passed archive safety, member checksum,
and pre-copy validation. The keyframe is byte-identical to the existing approved home-decor scene
anchor, but an anchor is not generated-promotion provenance; the owner explicitly approved this
existing package asset for the pilot. The scripts are authoritative MTL Appendix A source copies.
The eight WAVs are explicitly clone-source material and cannot be relabeled as narration.

The legacy branch records the actual received ZIP SHA-256, package-relative source path,
keyframe/member digest, provenance sidecar, and owner decision reference while rejecting Goal 1
run/output, provider/model/prompt, reviewer, and approval-time claims. The historical generated
promotion branch remains unchanged and fully strict.

**Alternatives considered**:

- Fabricating a Goal 1 run or promotion: rejected because no such evidence exists.
- Treating the matching approved anchor as automatically promoted: rejected because identity and
  video-keyframe approval semantics differ.
- Using the canonical source WAVs as script narration: rejected because they are not matched to any
  of the three exact scripts.
- Creating a Starfish voice automatically: rejected because it would be a paid call and would
  invent an approval boundary.
