# Data Model: Reviewed External K2 Workflow

## ExternalKeyframeCandidate

Schema `external-keyframe-candidate/v1` contains:

- identity: unique 3–80 character lowercase slug, exact role `talking_medium_closeup`, source type
  `owner_supplied_external_candidate`;
- source evidence: non-empty source reference, sanitized basename only, source SHA-256;
- staged evidence: project-relative staged path, staged SHA-256 equal to source, byte size from
  1–20 MiB, decoded `image/png` or `image/jpeg`, width, and height;
- audit state: UTC creation time, stable `created_by` source declaration, and exact status
  `PENDING_HUMAN_REVIEW`.

State transition: absent -> pending. Candidate identity and bytes are immutable after import.

## ExternalK2Review

Schema `external-k2-review/v1` is exactly one CSV row. Immutable columns are schema, candidate ID,
role, candidate file, candidate SHA-256, and source type. Human columns are
`face_identity_pass`, `age_pass`, `hair_pass`, `eyes_pass`, `mouth_pass`,
`body_proportions_pass`, `wardrobe_pass`, `jewelry_pass`, `no_extra_people_pass`,
`no_text_logo_pass`, `video_keyframe_ready`, `reviewer`, `reviewed_at`, and `notes`.

The candidate-local baseline keeps every human column blank. A reviewed copy under
`outputs/reviews/` must preserve identity columns, use literal `PASS` for all eleven decision
columns, contain a non-empty reviewer, and contain timezone-aware ISO-8601 `reviewed_at`. Notes are
optional and never confer approval. Blank, lowercase aliases, `N/A`, partial decisions, extra or
missing columns, multiple rows, hash drift, and naive timestamps do not authorize promotion.

## ExternalKeyframePromotion

Schema `external-keyframe-promotion/v1` records source/candidate/staged facts, review path/hash,
reviewer/time, approved path/hash, role, and provenance type
`owner_supplied_external_promotion`. Provider/task/model/prompt/generated-run fields are
prohibited. Source SHA-256 = staged SHA-256 = approved SHA-256. Transition is pending -> approved
only; no overwrite or reverse transition exists.

## DualKeyframeResolution

Schema `dual-keyframe-evidence/v1` contains independent `talking_keyframe` and `motion_keyframe`
objects, each with ID, project-relative path, roles, SHA-256, provenance type/record, review digest,
reviewer, and approval time when applicable. Talking uniquely resolves `talking_medium_closeup`.
Motion uniquely resolves `pilot_home_context`, otherwise unique `establishing_keyframe`. Ambiguity
or absence blocks; no fallback crosses the talking/motion boundary.
