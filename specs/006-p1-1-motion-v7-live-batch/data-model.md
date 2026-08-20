# Data Model: P1-1 Motion V7 Controlled Live Batch

## V7 Live Batch Plan

| Field | Validation |
|---|---|
| `run_id` | One unique parent video run ID |
| `run_type` | `P1-1 Motion V7` |
| `authoritative_code_commit` | Non-empty current repository commit |
| `provider` | Exactly `runway` |
| `candidate_count` | Exactly 3 |
| `planned_submissions` | Exactly 3 |
| `estimated_credits` | Known finite positive total; currently 75 |
| `max_runway_credits` | Explicit finite cap greater than or equal to estimate |
| `live_authorization` | Both CLI confirmations and exact environment permission true |
| `source` | Approved keyframe path, SHA-256, and provenance |
| `candidates` | Exact unique A/B/C executions in canonical order |

## V7 Candidate Execution

| Field | Validation / state |
|---|---|
| `candidate_id` | Exact canonical ID; unique |
| `experiment_level` | Exact rung from canonical manifest |
| `prompt_path` | Exact authoritative versioned mapping; unique |
| `prompt_sha256` | Exact prompt bytes |
| `prompt_utf16_units` | 1..999 |
| `estimated_credits` | Known; currently 25 |
| `submission_state` | `planned` → `submitted` / `failed`; unvisited candidates become `not_submitted` |
| `submission_attempts` | 0 or 1 |
| `provider_task_id` | Null until returned; never replaced |
| `provider_status` | Terminal normalized status or null |
| `output_references` | Zero or more validated derived media records |
| `error_code/message` | Sanitized failure evidence or null |

## State Transitions

```text
prepare all → validate all → write plan → verify plan
    → submit A → submit B → submit C → complete
                  ↘ failure → mark remaining not_submitted → stop
```

Any transition before `submit A` can fail only with zero submissions. Every submission has exactly one attempt. A task ID, once returned, is immutable and cannot be replaced.

## Human QA and Subject Lock

The parent run always has three review rows using the existing schema. Camera Lock/Framing equivalents and all other human fields, including Identity, Eyes, Mouth, Motion, MTL Ready, reviewer, and timestamp, start blank. Subject Lock retains `measurement_scope=color_region_proxy`, `human_qa_authority=not_automatic`, and V7/delta `PENDING` until separate real-media diagnostics exist.
