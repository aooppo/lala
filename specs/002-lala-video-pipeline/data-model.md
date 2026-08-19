# Data Model: Reproducible Lady LaLa Video Pipeline

## ApprovedKeyframe

Represents one human-approved still image supplied either by genuine Goal 1 promotion or by the
narrow owner-supplied legacy import path.

| Field | Type | Rules |
|---|---|---|
| `keyframe_id` | string | Unique, stable logical name |
| `path` | project-relative path | Must remain inside `assets/approved_keyframes/` |
| `sha256` | 64-character hex | Must match current file bytes |
| `mime_type` | string | PNG or JPEG only |
| `width`, `height` | positive integer | Read from decoded image |
| `provenance_type` | enum | `goal1_promotion` or `owner_supplied_legacy_asset` |
| `provenance_record` | path | Must exist beside the approved keyframe and match its branch |
| `source_run_id`, `source_output_id` | string/null | Required only for genuine Goal 1 promotion |
| `reviewer`, `approved_at` | string/timestamp/null | Required only for genuine Goal 1 promotion |
| `source_package`, `source_package_sha256` | string/null | Required only for legacy import |
| `source_path` | string/null | Exact package-relative member path; required only for legacy import |
| `owner_approval_reference` | string/null | Auditable owner decision reference; required only for legacy import |

An anchor is not automatically a keyframe. A generated still becomes an approved keyframe only by
copy-based promotion with complete provenance. The legacy branch never accepts generated-run,
provider/model/prompt, reviewer, or timestamp claims and does not relax the promotion branch.

## ScriptRecord

Represents one immutable MTL copy source.

| Field | Type | Rules |
|---|---|---|
| `script_id` | enum | `product_page`, `tooltip`, `homepage` |
| `path` | project-relative path | Must remain inside `assets/scripts/` |
| `version` | non-empty string | Owner/MTL supplied |
| `sha256` | 64-character hex | Pinned before generation |
| `source` | constant | `MTL` |
| `source_reference` | non-empty string | Authoritative MTL/package and Appendix A reference |
| `modification_policy` | constant | `immutable` |
| `content` | exact bytes/text | Read-only; never normalized or rewritten |

Validation fails when the file, version, pinned hash, UTF-8 decoding, or non-empty content is
missing. Script capture in a run is byte-equivalent to the selected source.

## VoiceProfile

Describes the approved voice path without credentials.

| Field | Type | Rules |
|---|---|---|
| `voice_version` | string/null | Required when approved |
| `mode` | enum | `approved_audio`, `cloned_voice`, or `pending` |
| `provider`, `model`, `voice_id` | string/null | Required only for Mode B |
| `source_audio`, `approved_audio` | path/null | Must remain in matching voice directories |
| `canonical_source_manifest` | path/null | Hash-pinned manifest under `assets/voice/metadata/` |
| `canonical_sources` | validated record list | PCM WAVs under `assets/voice/source/`; clone inputs only |
| `script_hash` | hex/null | Approved audio must map to exact script when Mode A |
| `language`, `locale`, `gender`, `engine`, `type`, `created_at` | string/null | API or human facts only; never guessed |
| `accent` | string/null | Human-provided metadata only |
| `speed`, `style`, `stability`, `similarity` | scalar/null | Approved profile metadata; bounded speed may be sent in Mode B |
| `output_format` | string | WAV for approved/generated archival audio |
| `sample_rate` | integer/null | Verified from media when available |
| `approval_status` | enum | `pending`, `verified`, `approved_for_smoke`, `production_approved`, or `rejected` |
| `owner_supplied_voice_id` | boolean | Records provenance, not quality approval |
| `verification_run_id`, `verification_time` | string/timestamp/null | Required before `approved_for_smoke` |
| `voice_name`, `profile_version`, `approval_scope`, `owner_reference` | string/null | Safe versioned provenance; no API key |

Canonical voice sources may be present while `mode` and `approval_status` remain `pending`. They do
not populate `script_audio`, do not map to product-page/tooltip/homepage copy, and do not satisfy
the approved narration or reusable-profile gate. `approved_for_smoke` requires the exact expected
voice ID/name plus a successful read-only private/Starfish membership check and verification
evidence. Only human listening and talking QA may advance to `production_approved`.

## VideoPreset

Defines one pilot-video workflow.

| Field | Type | Rules |
|---|---|---|
| `name` | enum | `product_page`, `tooltip`, `homepage` |
| `script_id` | string | Must resolve to one ScriptRecord |
| `aspect_ratio`, `resolution` | string | Must be supported by selected providers/editor |
| `talking_provider`, `motion_provider` | string | Must resolve to configured capability records |
| `talking_model`, `motion_model` | string | Must be documented for the provider |
| `alternate_takes` | integer | One to configured maximum |
| `talking_shot_variations` | integer | Default and maximum three |
| `broll_variations` | integer | Default and maximum three |
| `final_edit_variations` | integer | Default and maximum two |
| `single_shot_fallback` | boolean | Allows MVP plan |
| `shots` | ordered ShotTemplate list | At least one talking shot |

## ShotTemplate and PlannedShot

`ShotTemplate` is configuration. `PlannedShot` is a run-specific expansion.

| Field | Type | Rules |
|---|---|---|
| `shot_id` | string | Unique within preset/run |
| `kind` | enum | `talking`, `motion`, `graphic`, `local` |
| `source_role` | string | Approved keyframe/scene/product or derived selection |
| `prompt_file` | path/null | Versioned prompt required for provider motion |
| `prompt_sha256` | hex/null | Recorded after resolution |
| `duration_seconds` | number/null | Within provider/preset bounds |
| `variation_count` | integer | Within kind-specific maximum |
| `selection_required` | boolean | True before final multi-shot assembly |
| `requests` | request ID list | Exactly one per provider variation |

State: `PLANNED -> GENERATED -> SELECTED -> ASSEMBLED`. A failure may occur after `PLANNED` or
`GENERATED`; selection never implies MTL approval.

## TalkingVideoRequest

Provider-neutral talking intent.

- Run/preset/shot/variation IDs.
- Provider and model.
- Approved keyframe path/hash and optional approved provider-avatar mapping.
- Approved audio path/hash and duration.
- Exact script path/version/hash for traceability; providers receive audio in Mode A.
- Output ratio/resolution and bounded timeout/retry metadata.
- No credentials, authorization headers, or provider SDK objects.

## MotionVideoRequest

Provider-neutral image-to-video intent.

- Run/preset/shot/variation IDs.
- Provider/model and keyframe/scene path/hash.
- Versioned prompt path/text/hash.
- Ratio, duration, optional seed, and output format.
- No voice/script content unless a documented motion model accepts reference audio and the preset
  explicitly enables it; the MVP keeps B-roll silent.

## VoiceRequest

Optional Mode B synthesis intent containing exact script identity/content, approved voice profile
identity, language/speed/output settings, bounded timeout/retries, and derived output path. It
excludes secrets. The normalized artifact records provider request ID and script/voice provenance;
a generated WAV remains derived and is never promoted implicitly.

## ProviderTask

| Field | Type | Rules |
|---|---|---|
| `request_id` | string | Joins one variation request |
| `provider_task_id` | string | Persist immediately; never resubmit after set |
| `provider`, `model` | string | Exact adapter identity |
| `status` | enum | `SUBMITTED`, `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`, `TIMED_OUT` |
| `attempts` | integer | Submission attempts before first task ID plus read/download retries |
| `output_urls` | redacted URI list | Ephemeral; never contains credentials |
| `estimated_cost` | CostComponent/null | From documented formula or response |
| `actual_cost` | CostComponent/null | Terminal provider fact; never replaced by an estimate |
| `error_code`, `error_message` | string/null | Sanitized |
| timestamps | timestamp/null | Ordered lifecycle evidence |

## MediaArtifact

Normalized downloaded or local result with artifact ID, kind, project-relative path, SHA-256,
byte size, MIME/container, width/height, duration, provider task or edit provenance, and redacted
source URL. Approved-source paths are forbidden.

## ShotSelection

Human-created mapping from every required `shot_id` to an artifact ID plus reviewer and selection
time. It selects edit inputs only; it does not approve identity, MTL readiness, or the final video.

## VideoRun

Append-only evidence aggregate with unique run ID, mode (`DRY_RUN`, `LIVE`, `ASSEMBLY`), preset,
stage, resolved configuration, source/script hashes, planned requests, ordered events, provider
results, outputs, edit commands, costs, review rows, and summary.

State transitions:

```text
INITIALIZED -> VALIDATED -> DRY_RUN_COMPLETE
                         -> SUBMITTED -> GENERATED -> AWAITING_SELECTION
                         -> ASSEMBLED -> REVIEW_READY
Any live stage may end FAILED or PARTIAL; a task ID is retained for recovery.
```

## CostRecord

Contains nullable voice, talking, motion, editing, storage, and total-provider cost components.
Each known component records provider, model, generated seconds, attempts, successes/failures,
amount, currency, `estimated` or `actual`, pricing URL, and pricing date. Total is null when known
components cannot form a complete total; zero is used only for verified local editing provider
cost.

## VideoReviewRow

One row per final candidate with the exact schema in `contracts/run-artifacts.md`. Provenance fields
are populated. All subjective pass fields, readiness, reviewer, reviewed time, and notes are empty
at creation. Human decisions are entered only in a separate immutable copy under
`outputs/reviews/`; the run row stays blank. Approval consumers hash and validate that copy against
run/candidate provenance.

## ApprovedVideo

A copy of one integrity-verified, explicitly reviewed final candidate with monotonically increasing
approved version and adjacent provenance. Required provenance includes source run/candidate/hash,
script version/hash, keyframe/audio hashes, selected shot artifacts, providers/models, reviewer,
and approval time. The source candidate remains unchanged.
