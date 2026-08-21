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
language/locale, and returning a required string `audio_url`, numeric duration, nullable string
`request_id`, and nullable word-timestamp array. A null request ID is preserved as null and never
fabricated; defensively, an omitted request ID is handled the same way. Neither state invalidates
an otherwise usable audio response. Private cloned voices are discoverable through the voice-list
endpoint with `type=private` and `engine=starfish`. The adapter downloads the result to a derived
path, converts it to validated PCM WAV, and records the provider request ID when present, its
presence/null state, and the script hash; it never treats generated audio as an approved source.
The approved voice profile remains a human-owned prerequisite, and Mode A still takes precedence
whenever a script-matched WAV exists.

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

## Decision 8 — 2026-08-19 production API contract refresh

**Decision**: Keep HeyGen v3 and Runway API version `2024-11-06`, but correct the implementation
to the current official contracts. HeyGen asset upload uses `multipart/form-data` field `file`, a
32 MB maximum, and `data.asset_id`. HeyGen mutation idempotency keys are 1–255 characters from
`[A-Za-z0-9_:.-]`, replay for 24 hours per endpoint/resource, and return `409
request_in_progress` while the original request is in flight. Video failures use `failure_code`
and `failure_message`. Arbitrary-image video requests use `type=image`, an asset input, exactly one
audio source, and only capability-supported optional fields. Runway `gen4.5` image-to-video
requires non-empty `promptText`, `promptImage`, ratio, integer duration 2–10, and may include a
seed. The pinned official SDK requires `promptImage`, model, and ratio for `gen4_turbo`, while its
prompt text and duration remain optional; this workflow still supplies a bounded duration and may
supply a versioned prompt without claiming either is universally required. Terminal tasks expose
final `cost.credits` while submissions/pending tasks expose `estimatedCost.credits`.

The current Starfish `POST /v3/voices/speech` OpenAPI operation does not declare the shared
`Idempotency-Key` parameter or a `409` response, unlike asset upload and video creation. Speech is
therefore submitted at most once per run attempt with no automatic mutation replay; an ambiguous
response fails closed and preserves unknown cost/submission evidence. The workflow MUST NOT send
or claim support for an undocumented idempotency header merely because other HeyGen mutations
support it.

**Rationale**: The 2026-08-19 official HeyGen reference explicitly documents multipart upload,
idempotency semantics, current failure fields, image/video unions, and voice query filters. The
official Runway API reference and generated Python SDK 5.15.0 distinguish required `gen4.5`
prompt text from optional `gen4_turbo` prompt text, limit data-URI images to 5 MB, and expose final
terminal credits separately from estimates. These sources supersede assumptions in the first Goal
2 implementation.

**Official evidence checked 2026-08-19**:

- `https://developers.heygen.com/reference/upload-asset`
- `https://developers.heygen.com/reference/create-video`
- `https://developers.heygen.com/reference/get-video`
- `https://developers.heygen.com/reference/get-voice`
- `https://developers.heygen.com/reference/list-voices`
- `https://developers.heygen.com/reference/generate-speech`
- `https://developers.heygen.com/docs/pricing`
- `https://docs.dev.runwayml.com/api/`
- `https://docs.dev.runwayml.com/guides/pricing/`
- official `runwayml==5.15.0` generated request/response type signatures installed from PyPI

**Alternatives considered**:

- Preserve the raw-body HeyGen upload: rejected because it cannot satisfy the documented file
  field and multipart boundary contract.
- Treat unknown cost as zero: rejected because estimates and final charges are distinct evidence.
- Make motion smoke depend on narration: rejected because Runway image-to-video needs neither
  HeyGen nor speech and must be reviewable as a separate capability.

## Decision 9 — Duration-dependent pilot budgeting and canonical motion prerequisites

**Decision**: Treat pre-TTS HeyGen totals as duration-dependent even though the Starfish and Avatar
IV unit rates are known. A complete cloned-voice pilot requires an explicit
`--max-talking-duration-seconds` workflow limit, capped by repository safety configuration.
Dry-run records the voice rate USD 0.000667/output-second, Avatar IV photo-avatar rate USD
0.05/output-second, Runway `gen4_turbo` five credits/output-second at USD 0.01/credit, the known
Runway amount, and a projection at the duration limit. It labels the state
`TOTAL_EXACT_UNKNOWN_UNTIL_TTS` and explicitly records that HeyGen does not enforce the duration
limit during synthesis. After TTS, local WAV inspection supplies the actual duration; the runner
recalculates the cumulative estimate and blocks before Talking or Runway submission if the WAV is
over the workflow limit or the projected total exceeds the owner ceiling.

General Goal 2 live generation also reuses the existing canonical motion-prerequisite resolver.
It accepts either the historical valid one-result motion smoke or a reviewed canonical V7 parent.
The V7 path retains its unique-winner, human attribution, MTL readiness, review provenance,
keyframe digest, provider task, downloaded media, and media digest checks, then resolves only the
selected request. The general runner separately binds that request to its currently selected
approved keyframe before any provider factory is constructed.

**Rationale**: Output duration is returned only after speech synthesis, so an exact pre-TTS total
would be fabricated. The staged gate exposes the dependency and limits the expensive downstream
work while preserving the single TTS result as append-only evidence. Reusing the existing V7
resolver avoids a second, weaker interpretation of the human gate and keeps legacy evidence
readable.

**Alternatives considered**:

- Treat the workflow duration limit as a HeyGen-enforced upper bound: rejected because the speech
  contract does not provide that guarantee.
- Continue emitting only generic `null`: rejected because it hides known unit rates, the exact
  dependency, and the actionable post-TTS enforcement stage.
- Use a words-per-minute estimate: rejected because it is not an executable provider constraint.
- Add a Product Page-only V7 parser: rejected because the P1-2 canonical resolver already performs
  the required validation and supports historical one-result evidence.
