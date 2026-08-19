# Provider Contracts

## Provider-neutral protocols

```python
class TalkingVideoProvider(Protocol):
    def validate_request(self, request: TalkingVideoRequest) -> None: ...
    def submit(self, request: TalkingVideoRequest) -> str: ...
    def wait(self, task_id: str, timeout_seconds: float) -> VideoTaskResult: ...
    def download_results(
        self, result: VideoTaskResult, output_dir: Path, output_stem: str,
        timeout_seconds: float, max_retries: int
    ) -> tuple[MediaArtifact, ...]: ...

class MotionVideoProvider(Protocol):
    def validate_request(self, request: MotionVideoRequest) -> None: ...
    def submit(self, request: MotionVideoRequest) -> str: ...
    def wait(self, task_id: str, timeout_seconds: float) -> VideoTaskResult: ...
    def download_results(
        self, result: VideoTaskResult, output_dir: Path, output_stem: str,
        timeout_seconds: float, max_retries: int
    ) -> tuple[MediaArtifact, ...]: ...

class VoiceProvider(Protocol):
    def synthesize(self, request: VoiceRequest) -> MediaArtifact: ...
```

Domain, CLI, storage, planning, editing, and reporting modules import these protocols and domain
types only. SDK/HTTP objects never leave adapters.

## HeyGen talking translation

1. Upload local approved keyframe/audio with `POST /v3/assets` when no already-approved provider
   asset mapping exists. Use a stable idempotency key per upload request.
2. Submit `POST /v3/videos` with:
   - `type: image`
   - `image: {type: asset_id, asset_id: ...}`
   - exactly one of `audio_asset_id` or `audio_url`
   - configured `aspect_ratio`, `resolution`, optional motion prompt/expressiveness
3. Persist `data.video_id` immediately.
4. Poll `GET /v3/videos/{video_id}`. Normalize `completed` to success and `failed` to failure.
5. Download `video_url` before expiry and content-validate the media.

Authentication uses local `HEYGEN_API_KEY` in `X-Api-Key`; it is never serialized. Uploads accept
PNG/JPEG and WAV/MP3, with documented maximum 32 MB. First live smoke uses image + approved audio,
not script/TTS.

## HeyGen voice translation

Only an explicitly approved `heygen_voice` / `starfish` Mode B profile can reach this adapter.
Submit synchronous `POST /v3/voices/speech` with the exact UTF-8 script text, approved private
`voice_id`, `input_type: text`, approved/default speed, and optional language. Persist the returned
`data.request_id`, download `data.audio_url` within the shared overall timeout and retry bound,
and convert the derived result to mono PCM WAV at the configured sample rate. Record the request
ID, script hash, voice ID, reported duration, validated WAV hash, and a query-redacted source URL.
The adapter never writes into an approved-source directory and never changes approval status.

Authentication uses the same local `HEYGEN_API_KEY` in `X-Api-Key`; it is redacted from failures
and never serialized. Current self-serve Starfish pricing is USD 0.000667 per output second and is
recorded as an estimate until provider/billing evidence supplies an actual. The current speech
operation does not document `Idempotency-Key`; synthesis is therefore submitted at most once per
run attempt and an ambiguous response fails closed without automatic replay.

## Runway talking translation

Requires an approved configuration mapping `{keyframe_sha256 -> custom_avatar_id}`. Submit
`POST /v1/avatar_videos` through SDK 5.15.0 with:

```text
model = gwm1_avatars
avatar = {type: custom, avatarId: UUID}
speech = {type: audio, audio: HTTPS | runway URI | data URI}
```

The adapter does not create/update/delete avatars during a talking run. It polls the common task
endpoint and normalizes/downloads outputs. A keyframe hash mismatch rejects the request.

## Runway motion translation

Submit `POST /v1/image_to_video` with documented model-specific fields:

- `gen4_turbo`: model, first-frame prompt image, `1280:720`, duration two-to-ten seconds,
  optional prompt text and seed.
- `gen4.5`: model, first-frame prompt image, prompt text, `1280:720`, duration two-to-ten seconds,
  optional seed, MP4 output.

The adapter records submission `estimatedCost.credits`, persists task ID, polls
`GET /v1/tasks/{id}`, and downloads output URLs. It sends `X-Runway-Version: 2024-11-06` through
the SDK. A submitted task is never recreated after its ID is known.

## Retry and timeout contract

- Submission retries are bounded and occur only before any task ID is received.
- Synchronous voice submission is not automatically replayed; only its derived-audio download and
  conversion may retry within the configured bound and overall deadline.
- Provider reads and downloads may retry transient failures within the request deadline.
- A lost/ambiguous submission response fails closed; it is not blindly retried unless the provider
  supports an idempotency key that proves replay safety.
- Rate-limit retry honors `Retry-After` without extending the overall timeout.
- Terminal failure/cancellation/timeouts are normalized and never resubmitted.
- All exceptions and payloads pass through recursive redaction before persistence or display.
