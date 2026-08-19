# Configuration Contract

## `configs/keyframe-manifest.yaml`

```yaml
project: lady-lala
status: pending | approved
keyframes:
  LOGICAL_ID:
    path: assets/approved_keyframes/FILE.png
    sha256: 64_HEX
    provenance_type: goal1_promotion
    source_run_id: ID
    source_output_id: ID
    promotion_record: assets/approved_keyframes/FILE.json
    reviewer: NAME
    approved_at: ISO_8601
```

Production validation requires status `approved` and at least one complete entry. Pending/empty is
valid repository scaffolding but blocks a runnable production preset.

An owner-supplied external keyframe uses a separate schema and never impersonates Goal 1 output:

```yaml
    provenance_type: owner_supplied_legacy_asset
    provenance_record: assets/approved_keyframes/FILE.provenance.json
    source_package: lala-goal2-authoritative-inputs-v1.0.0.zip
    source_package_sha256: 64_HEX
    source_path: 01_keyframe/video_keyframe_candidate/FILE.png
    owner_approval_reference: NON_EMPTY_AUDIT_REFERENCE
```

The adjacent JSON record must match these values plus the imported keyframe path/hash. The legacy
branch rejects Goal 1 run/output IDs, provider task/model/prompt claims, reviewer names, and
approval timestamps. Omitting `provenance_type` retains the strict historical
`goal1_promotion` interpretation for existing generated promotions.

## `configs/script-manifest.yaml`

```yaml
source: MTL
modification_policy: immutable
scripts:
  product_page:
    path: assets/scripts/product-page.txt
    version: VERSION_OR_NULL
    sha256: HASH_OR_NULL
    source_reference: AUTHORITATIVE_MTL_REFERENCE
  tooltip:
    path: assets/scripts/tooltip.txt
    version: VERSION_OR_NULL
    sha256: HASH_OR_NULL
  homepage:
    path: assets/scripts/homepage.txt
    version: VERSION_OR_NULL
    sha256: HASH_OR_NULL
```

Null version/hash/source-reference values declare exact external blockers; they never authorize
automatic pinning or content creation.

## `configs/voice-profile.yaml`

Includes every user-requested profile field plus `mode`, `script_audio` mapping,
`canonical_source_manifest`, and staged `approval_status` (`pending`, `verified`,
`approved_for_smoke`, `production_approved`, `rejected`). Paths must remain under `assets/voice/`.
Secrets are forbidden. A canonical source manifest is hash-pinned under
`assets/voice/metadata/` and lists content-validated PCM WAVs under `assets/voice/source/`; these
records remain clone-source inputs only. Approved-audio mode requires an approved WAV and exact
script hash mapping. Cloned-voice mode requires an approved `heygen_voice` provider, `starfish`
model, private voice ID/version, WAV output, and optional approved language/speed/sample rate; it
produces a derived WAV. A script-matched approved WAV is preferred in either mode. Canonical
sources alone leave the profile pending and cannot populate `script_audio`. The owner-supplied ID
may be recorded while pending, but `approved_for_smoke` additionally requires a real read-only
verification run ID/time and the exact expected voice name. API-derived language, locale, gender,
engine, type, and creation time remain null until observed; accent/style are never guessed.

## `configs/brand-assets.yaml`

Defines approved or missing `decorolala_logo`, `lala_like_heart`, `five_lala_likes`,
`five_percent_off_coupon`, `club_lala`, and `end_card` roles. An approved record contains path,
SHA-256, version, approval status, reviewer, reviewed time, and source reference, and its path must
remain under `assets/brand/approved/`. Missing approved assets resolve to deterministic draft SVG/
PNG files under `outputs/graphics/`, visibly marked `DRAFT / NOT MTL APPROVED`; drafts are valid for
smoke assembly but make promotion fail closed.

## `configs/video-presets.yaml`

Defines `product_page`, `tooltip`, and `homepage`; exact script ID; 16:9 default; provider/model;
resolution/frame rate; three talking alternatives, three B-roll alternatives, two final edits;
single-shot fallback; and ordered shot templates. Values may only reduce configured maxima at CLI
time unless owner-reviewed configuration changes them.

## `configs/providers.yaml`

Contains no credentials. It records:

- `verified_on` and official documentation/pricing URLs.
- Runway API/SDK versions, endpoints, models, ratios, duration/prompt/seed limits, credit formulas,
  poll interval, and input byte/URI limits.
- HeyGen endpoints, image/audio source shapes, MIME/size limits, ratios/resolutions, terminal
  statuses, known per-second talking price, and Starfish speech endpoint/text/speed/output limits.
- Global live bounds: three variations, two final edits, concurrency one, retries two, timeout
  1800 seconds, `allow_live_calls: false`.

Runway `gen4_turbo` requires image/model/ratio and accepts optional prompt text and duration in the
pinned SDK; the configured smoke preset supplies both a non-empty versioned prompt and five-second
duration. `gen4.5` requires prompt text, image, ratio, and duration. Submission estimated credits
and terminal actual credits are separate nullable facts.

Every provider/model used by a preset must resolve to one documented capability record. Unknown or
unsupported fields are rejected before provider construction.
