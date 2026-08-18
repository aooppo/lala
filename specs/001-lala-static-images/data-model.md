# Data Model: Reproducible Lady LaLa Static Images

## ApprovedAnchor

Represents one configured immutable source image.

| Field | Type | Rules |
|-------|------|-------|
| `name` | string | Unique logical name: `face`, `full_body`, or `scene` for required anchors |
| `path` | project-relative path | Must resolve under `assets/approved_anchors/`, exist, be readable, and be a regular file |
| `role` | string | Unique non-empty authority role |
| `tag` | string | Unique; 3–16 lowercase letters/digits/underscores; starts with a letter |
| `priority` | integer | Positive; controls deterministic reference order |
| `generation_input` | boolean | True for the three authority anchors; false by default for QA references |
| `sha256` | 64-character hex | Calculated from source bytes, never user-authored |
| `mime_type` | string | Supported image MIME type derived from verified content |
| `width`, `height` | positive integer | Read from the image decoder; both must be greater than zero |

## AnchorManifest

| Field | Type | Rules |
|-------|------|-------|
| `project` | string | Must be `lady-lala` for this repository |
| `anchor_set_version` | string | Required immutable-set version included in every run/promotion |
| `status` | string | Must be `approved` for generation |
| `anchors` | map of `ApprovedAnchor` | Must contain exactly one configured authority for each required logical name |
| `qa_references` | map of `ApprovedAnchor` | Optional; never selected unless a preset explicitly names it |

## PromptTemplate

| Field | Type | Rules |
|-------|------|-------|
| `path` | project-relative path | Must resolve under `prompts/` and be a readable text file |
| `filename` | string | Preserved in metadata |
| `version` | string | Parsed from terminal `-vN.txt` naming convention |
| `text` | string | Non-empty; <= 1000 UTF-16 code units for supported Runway models |
| `sha256` | 64-character hex | Hash of exact UTF-8 file bytes |
| `referenced_tags` | ordered string list | Every `@tag` must resolve to a selected anchor tag |

## GenerationPreset

| Field | Type | Rules |
|-------|------|-------|
| `name` | string | Unique across all preset files |
| `purpose` | string | Human-readable production purpose |
| `references` | ordered logical-name list | Two or three for required presets; no duplicates |
| `prompt_file` | project-relative path | Versioned prompt file |
| `default_count` | integer | Baseline 10; home/product 5; never above global maximum |
| `default_ratio` | string | Exact provider dimension token; also exposed as resolution |

## ProviderCapabilities

| Field | Type | Rules |
|-------|------|-------|
| `provider` | string | Adapter identifier |
| `api_version` | string | Version recorded from official API contract |
| `sdk_version` | string | Pinned SDK release |
| `models` | set of strings | Only models whose selected schemas were verified |
| `ratios` | map model -> set | Exact accepted dimensions per supported model |
| `min_references`, `max_references` | map model -> integer | Model-specific limits |
| `supports_seed` | map model -> boolean | Never assume across providers |
| `seed_min`, `seed_max` | integer/nullable | Present only where documented |
| `tag_pattern`, `tag_min`, `tag_max` | constraints | Validated before submission |
| `prompt_utf16_max` | integer | Model/API-specific maximum |
| `data_uri_max_chars` | integer | Used before local-file translation |
| `poll_interval_seconds` | number | At least 5 for Runway |

## GenerationRequest

One provider-neutral single-candidate request.

| Field | Type | Rules |
|-------|------|-------|
| `run_id` | string | Parent run identifier |
| `output_id` | string | Unique within run, deterministic from candidate index |
| `preset` | string | Resolved preset name |
| `provider` | string | Selected adapter |
| `model` | string | Capability-validated |
| `ratio` | string | Capability-validated exact dimension |
| `resolution` | string | Equal to resolved ratio for the current Runway adapter |
| `prompt` | string | Resolved prompt text |
| `prompt_file`, `prompt_version`, `prompt_sha256` | provenance | Immutable prompt metadata |
| `references` | ordered `ReferenceImage` list | Path, logical name, role, tag, SHA-256, MIME type |
| `seed` | integer/nullable | Base seed + candidate index when supplied; otherwise null |
| `output_count` | integer | Always 1 for current Runway adapter |

## ResolvedRunConfig

| Field | Type | Rules |
|-------|------|-------|
| `run_id`, `preset`, `provider`, `model`, `ratio`, `resolution` | scalar | Final values after preset and CLI overrides |
| `count` | integer | 1 through `max_outputs_per_run` |
| `concurrency` | integer | 1 through `max_concurrency` |
| `max_retries` | integer | 0 through configured cap; additional attempts after initial |
| `poll_timeout_seconds` | positive number | Per-task bound |
| `overall_timeout_seconds` | positive number | Must be >= poll timeout |
| `live` | boolean | False unless explicitly selected |
| `allow_live_calls` | boolean | True only from exact environment permission |
| `estimated_credits_per_output` | number/nullable | Operator-supplied estimate; not provider billing fact |
| `max_estimated_credits` | number/nullable | Optional fail-closed ceiling |
| `api_version`, `sdk_version`, `anchor_set_version` | string | Reproducibility versions |

## ProviderTaskResult

| Field | Type | Rules |
|-------|------|-------|
| `provider_task_id` | string | Returned by provider submission |
| `status` | enum | `SUCCEEDED`, `FAILED`, `CANCELLED`, or `TIMED_OUT` after `wait` |
| `output_urls` | string list | Non-empty only for success; treated as expiring |
| `error_code`, `error_message` | nullable string | Recursively redacted |
| `started_at`, `completed_at` | UTC timestamp | ISO 8601 |
| `events` | ordered event list | Status observations and retries |

## OutputArtifact

| Field | Type | Rules |
|-------|------|-------|
| `output_id` | string | Matches request/review row |
| `provider_task_id` | string | Provenance |
| `file` | project-relative path | Must resolve outside approved anchors |
| `sha256` | hex string | Hash after complete download |
| `size_bytes` | non-negative integer | Recorded after complete download |
| `source_url_redacted` | string | URL stripped of query/fragment credentials or omitted |

## GenerationResult

| Field | Type | Rules |
|-------|------|-------|
| `run_id`, `provider`, `model` | string | Run provenance |
| `status` | enum | `DRY_RUN`, `SUCCEEDED`, `PARTIAL`, or `FAILED` |
| `started_at`, `completed_at`, `duration_seconds` | timing | Completed even on failure |
| `requests` | request summary list | No base64 data or secrets |
| `tasks` | normalized task summary list | One per submitted candidate |
| `outputs` | `OutputArtifact` list | One entry per downloaded file |
| `errors` | redacted error list | Candidate-scoped |

## ReviewRow

One row per downloaded output. Provenance fields are populated from the result. All of the
following human fields start as empty strings: `face_identity_pass`, `age_pass`, `hair_pass`,
`body_proportions_pass`, `wardrobe_pass`, `jewelry_pass`, `hands_pass`, `scene_pass`,
`no_extra_people_pass`, `no_text_logo_pass`, `video_keyframe_ready`, `mtl_review_ready`,
`reviewer`, `reviewed_at`, and `notes`.

## PromotionRecord

| Field | Type | Rules |
|-------|------|-------|
| `source_run_id`, `source_output_id`, `source_image` | string/path | Must identify one run review row and result output |
| `image_sha256` | hex string | Recomputed and must match result before copy |
| `approved_anchor_version` | string | Copied from resolved run config |
| `prompt_version` | string | Copied from request provenance |
| `provider`, `model` | string | Copied from run |
| `reviewer` | string | Required non-empty human value |
| `approval_date` | ISO timestamp | Copied from valid `reviewed_at` |
| `approved_keyframe` | path | New copy under `outputs/approved_keyframes/`; never replaces source |

## State Transitions

```text
NEW
  -> VALIDATED
  -> DRY_RUN_COMPLETE

VALIDATED
  -> SUBMITTING
  -> TASK_PENDING | TASK_THROTTLED | TASK_RUNNING
  -> TASK_SUCCEEDED -> DOWNLOADED
  -> TASK_FAILED | TASK_CANCELLED | TASK_TIMED_OUT

DOWNLOADED
  -> AWAITING_HUMAN_REVIEW
  -> KEYFRAME_READY (human CSV edit)
  -> PROMOTED
```

Terminal provider states never transition back to submission automatically. Promotion does not
change or delete the `DOWNLOADED` source artifact.
