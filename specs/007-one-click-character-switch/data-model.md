# Data Model: One-Click Character Switch

## CharacterStatus

String enum values:

- `DRAFT`
- `VALIDATING`
- `BUILDING`
- `READY_FOR_GENERATION`
- `READY_FOR_PREVIEW`
- `READY_FOR_APPROVAL`
- `ACTIVE`
- `INACTIVE`
- `FAILED`
- `REJECTED`

Allowed transitions:

```text
DRAFT -> VALIDATING -> BUILDING
BUILDING -> READY_FOR_GENERATION -> READY_FOR_PREVIEW -> READY_FOR_APPROVAL
BUILDING / READY_FOR_GENERATION / READY_FOR_PREVIEW -> FAILED
READY_FOR_APPROVAL -> ACTIVE | REJECTED
ACTIVE -> INACTIVE
INACTIVE -> ACTIVE
FAILED -> BUILDING
REJECTED -> BUILDING
```

Activation of a failed, rejected, building, ready-for-generation, or ready-for-preview character is
invalid. `lala-v1` is bootstrapped directly as ACTIVE compatibility data.

## CharacterReference

| Field | Type | Rule |
|---|---|---|
| logical_name | string | One of required/known optional logical roles |
| path | project-relative path | Must resolve inside allowed staging or approved root |
| sha256 | 64-char lowercase hex | Must match exact file bytes |
| role | string | Semantic identity role, not user-controlled filename |
| tag | string | Stable provider tag satisfying configured constraints |
| mime_type | string | `image/png`, `image/jpeg`, or `image/webp` |
| width | positive integer | Decoded width |
| height | positive integer | Decoded height |
| size_bytes | positive integer | At or below configured upload limit |
| source_filename | optional string | Display-only, sanitized/redacted; never a path |

Required logical references: `face`, `full_body`, `three_quarter`.

Optional logical references: `side`, `expression`, `product_pose`, `hair_accessory`.

## CharacterProfile

| Field | Type | Rule |
|---|---|---|
| schema_version | string | `1.0` |
| character_id | string | `character-YYYYMMDD-NNN`; `lala-v1` reserved legacy ID |
| display_name | optional string | UI label only; bounded and never used as path |
| profile_version | positive integer | Snapshot version, monotonic per character |
| status | CharacterStatus | Must agree with current registry entry for current snapshot |
| created_at | timezone-aware timestamp | Actual system time |
| created_by | string | `local_ui`, `cli`, or `legacy_migration` |
| references | mapping | Exactly one each required role; optional roles unique |
| attributes | mapping | Nullable hair/wardrobe/jewelry notes; no inferred facts |
| provenance | mapping | Source hashes/build ID/previous snapshot where present |
| profile_sha256 | derived string | Hash of canonical serialized snapshot excluding this field |

Profile snapshots are immutable. `configs/characters/profiles/<id>-vNNN.yaml` is created
exclusively. A later state writes another snapshot.

## CharacterRegistryEntry

| Field | Type | Rule |
|---|---|---|
| character_id | string | Must equal mapping key and profile ID |
| display_name | optional string | Convenience label |
| status | CharacterStatus | Exactly one entry must be ACTIVE |
| profile | project-relative path | Must be under character profiles root |
| profile_sha256 | hash | Must match loaded profile canonical hash |
| updated_at | timestamp | Actual transition time |

## CharacterRegistry

| Field | Type | Rule |
|---|---|---|
| registry_version | string | `1.0` |
| revision | non-negative integer | Incremented once per successful mutation |
| active_character | string | Existing entry whose status is ACTIVE |
| previous_active_character | optional string | Last active before current switch |
| characters | mapping | Unique entries; exactly one ACTIVE |
| last_event | mapping | Latest transition summary without secrets |

Registry readers validate the whole object plus referenced current snapshots. Registry writers hold
the filesystem lock and require expected revision plus expected active character when activating.

## CharacterBuild

| Field | Type | Rule |
|---|---|---|
| build_id | string | Unique per attempt |
| character_id | string | Existing non-active profile |
| character_profile_version/hash | integer/hash | Snapshot bound to attempt |
| status | string | Validating/building/ready/failed state |
| selected_references | ordered sequence | Exact logical name/role/tag/path/hash |
| static_preview | optional PreviewArtifact | Required before motion |
| motion_preview | optional PreviewArtifact | Required before activation |
| technical_checks | mapping | Objective PASS/FAIL/NOT_RUN only |
| subject_lock | optional mapping | Diagnostic status with human authority `not_automatic` |
| errors | sequence | Redacted normalized errors |
| events_path | path | Append-only event log under character output |

## PreviewArtifact

| Field | Type | Rule |
|---|---|---|
| kind | enum | `static` or `motion` |
| status | string | `STAGING_PREVIEW_ONLY_NOT_PRODUCTION_APPROVED` |
| path | project-relative path | Under `outputs/characters/<id>/previews/` |
| sha256 | hash | Exact file hash |
| mime_type | string | Validated media type |
| width/height | positive integer | Decoded media dimensions |
| duration_seconds | optional positive float | Required for motion |
| source_run_id | optional string | Real static/video run when generated |
| provider_task_id | optional string | Only when actually returned |
| provenance | mapping | Character/profile/reference/prompt/source-candidate hashes |

## ReferenceSelection

Ordered immutable tuple of `SelectedReference` values:

| Context | Preferred order |
|---|---|
| baseline/full-body | face, full_body |
| home | face, full_body, scene |
| medium/three-quarter | face, three_quarter, full_body |
| product | face, full_body, scene when requested and capacity allows |

Selection fails if required roles cannot fit or are absent. Optional scene is dropped only according
to explicit context policy, never directory order. Maximum is supplied from current provider model
capability.

## CharacterLifecycleEvent

Append-only evidence fields: event ID, event type (`created`, `build_started`, `preview_ready`,
`approved_and_activated`, `rejected`, `reactivated`, `failed`), character ID, build/profile hashes,
previous/new active IDs when relevant, expected/result registry revision, actual time, actor source,
and redacted error code/message. It does not claim MTL or production keyframe/video approval.
