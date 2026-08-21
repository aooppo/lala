# Research: Coffee Table Failed-Task Recovery

## Deterministic local product cutaway

**Decision**: Use a fixed center crop from 1280x1280 to 1280x720 followed by a center-anchored optical push from 1.000 to 1.035 over exactly 72 frames at 24 fps. Encode silent H.264/yuv420p with metadata removed, bit-exact flags, and one encoder thread.

**Rationale**: The source inspection confirms the entire table fits within the centered 16:9 crop. A fixed expression prevents runtime reframing, 72 frames gives exactly three seconds, and constrained encoding removes avoidable sources of byte drift while matching repository local-delivery conventions.

**Alternatives considered**: Letterboxing would preserve excess white space and reduce product emphasis; a hand-tuned crop would violate the frozen automatic framing boundary; provider generation and content-aware reframing are unauthorized; scaling the square image directly would distort product geometry.

## TASK-04 recovery source

**Decision**: Extract exactly zero-based decoded frame 96 from the fixed TASK-02 MP4 using a frame-index selector, then validate the PNG and record exact argv and hashes.

**Rationale**: The Owner supplied the frame index and source hash after visual review. The source has 121 decoded 24 fps frames, so index 96 exists near four seconds. Fixed selection is reproducible and cannot drift into aesthetic search.

**Alternatives considered**: The previous last-valid-frame rule leaves the candidate near/outside the right edge; time-based seeking can vary with timestamps/keyframes; automatic visual search or another manual selection is prohibited.

## Append-only recovery identity

**Decision**: Create a new recovery namespace and manifest, reference the exact parent manifest and failed run, and snapshot/reverify original evidence hashes without editing either original JSON file.

**Rationale**: Historical provider states are audit facts. A separate hashed contract lets later authorization refer to recovery without changing the contract or results that governed the failed paid run.

**Alternatives considered**: Adding fields to the original run would violate append-only evidence; rewriting TASK-03 as unsubmitted would erase a durable failed provider task; mutating the V2 manifest would invalidate its Owner-approved SHA.

## Offline-only authorization boundary

**Decision**: Expose recovery preparation as a CLI mode with no live flag, credential requirement, provider factory, or provider request construction. Record zero submissions/calls/retries/replacements as structural manifest facts.

**Rationale**: The current prompt authorizes local preparation only. Keeping provider types out of the recovery module makes accidental submission materially harder and directly testable.

**Alternatives considered**: Reusing the Live executor with a skip list risks provider construction and task-state ambiguity; auto-submitting TASK-04 would exceed authorization; retrying TASK-03 would violate its task-ID idempotency boundary.

## Failure and collision handling

**Decision**: Validate all immutable inputs before allocation, create new targets exclusively, and on failure remove only newly allocated recovery outputs. Never overwrite or repair an existing target.

**Rationale**: This preserves user/live evidence, makes retries explicit, and prevents partially completed recovery artifacts from being mistaken for a reviewed contract.

**Alternatives considered**: In-place overwrite can destroy evidence; retaining an unhashed partial manifest creates ambiguity; cleaning the original run would be destructive and unauthorized.

## Recovery V2 authorized Live boundary

**Decision**: Use a dedicated V2 coordinator selected by `--live --recovery-live`. Require exact `VIDEO_ALLOW_LIVE_CALLS=true`, a non-empty `RUNWAYML_API_SECRET`, Owner confirmation, and exact 25-credit/USD 0.25 caps. Keep the Runway adapter's SDK submission retries at zero and download retries at zero.

**Rationale**: The repository's formal Goal 2 video guard is `VIDEO_ALLOW_LIVE_CALLS`; `RUNWAY_ALLOW_LIVE_CALLS` belongs to Goal 1 static generation, and no `COFFEE_TABLE_ALLOW_LIVE_CALLS` contract exists. A distinct coordinator prevents the Owner-approved V2 manifest from entering the historical four-task executor and makes one-submit accounting structural.

**Alternatives considered**: Reusing the original executor would expose TASK-01/02/03 submission paths; inventing new environment gates would silently change the current contract; SDK retries could create submission ambiguity.

## Durable one-submit lifecycle

**Decision**: Persist PREPARED and SUBMITTING events before submit, fsync the provider task ID through the adapter sink before submit returns, then record SUBMITTED and terminal state. A submit exception without a known ID is `BLOCKED_SUBMISSION_UNKNOWN`; a known ID is polled without resubmission.

**Rationale**: The task ID is the provider idempotency boundary. This ordering preserves the strongest available proof after process/transport failures and prevents an automatic replacement.

**Alternatives considered**: Retrying an ambiguous submit can create a second paid task; stopping after a known sink ID without polling wastes a recoverable accepted task; writing only a terminal summary loses crash evidence.

## Master hold and guarded ratios

**Decision**: Decode-count TASK-04, extract exactly its last valid frame, and concatenate eight explicit 24-fps segments to a 480-frame master. Because V2 contains no objective machine-safe-area geometry or subject boxes, record both 1:1 and 9:16 as `BLOCKED_SAFE_AREA` and create no crops.

**Rationale**: The explicit PNG proves which frame supplies the two-second hold. Center cropping alone cannot prove preservation of Candidate 16, Coffee Table, wine glass, and action context, so fail-closed behavior is the only evidence-compatible result.

**Alternatives considered**: `tpad` clone hides the decoded-frame identity; fixed timestamp extraction can miss the last decoded frame; visual guessing or AI scoring would fabricate an approval gate; native-ratio generation is unauthorized.
