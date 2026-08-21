# Lady LaLa Reproducible Media Workflow

This project implements two staged, reproducible workflows. Goal 1 validates approved Lady LaLa
anchors, generates bounded static candidates, and promotes reviewed images to approved video
keyframes. Goal 2 consumes those approved keyframes with an approved Lady LaLa voice and exact MTL
scripts to produce talking-shot alternatives, Runway motion/B-roll, deterministic FFmpeg edits,
blank human QA sheets, and review-gated approved video copies.

The workflow never rewrites MTL copy, auto-approves identity/voice/lip sync, or deploys to Shopify.
ComfyUI migration, Coze orchestration, unrelated website work, automatic creative approval, and
automatic MTL approval remain out of scope.

## Requirements and setup

- Python 3.11 or newer.
- macOS or Linux.
- Internet access only for installation, official documentation checks, and explicitly authorized
  live Runway calls. Validation, dry runs, and automated tests are offline-capable.

Using `uv`:

```bash
uv sync --extra dev
uv run python -m lala_workflow validate
```

Using a standard virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m lala_workflow validate
```

The production dependency is pinned to the verified official Python SDK `runwayml==5.15.0`.

## Phase 1 one-click character switch

The optional local screen lets a non-technical operator upload one clear front photo, one full-body
photo, and one three-quarter photo, review a static preview plus a five-second motion preview, then
make one final **Reject** or **Approve & Activate** decision. Creation and offline preview planning
never change the active character. Activation is the only production identity-switch boundary and
uses a filesystem lock, expected registry revision, immutable profile snapshots, and one atomic
registry replacement. Rollback uses the same operation to reactivate `lala-v1`.

Install and start the screen:

```bash
uv sync --extra dev --extra ui
uv run --extra ui streamlit run src/lala_workflow/ui/app.py
```

The UI dependency is optional; `uv sync --extra dev` and every existing CLI continue to work
without importing Streamlit. The equivalent technical workflow is:

```bash
uv run python -m lala_workflow character list
uv run python -m lala_workflow character show lala-v1
uv run python -m lala_workflow character import \
  --face /path/to/front.png \
  --full-body /path/to/full-body.png \
  --three-quarter /path/to/three-quarter.png \
  --name "Candidate 07"
uv run python -m lala_workflow character build CHARACTER_ID
uv run python -m lala_workflow character preview CHARACTER_ID --dry-run
```

The default preview is a zero-call plan and leaves the character `READY_FOR_GENERATION`; it does
not create fake media and cannot satisfy activation. A real preview additionally requires
`--live`, exact `RUNWAY_ALLOW_LIVE_CALLS=true`, `VIDEO_ALLOW_LIVE_CALLS=true`,
`VIDEO_MOTION_LIVE_SMOKE_TEST=true`, a local Runway credential, and a motion cap no greater than
25 credits. Static work is one result; motion is exactly one five-second `gen4_turbo` result. Both
gates are preflighted before the first paid call. No live call is part of installation, testing,
dry runs, or this delivery.

If static succeeds but motion is interrupted, never rerun the combined preview. Resume only with:

```bash
uv run python -m lala_workflow character motion-recover CHARACTER_ID \
  --max-runway-credits 25 --live
```

Character motion recovery stores an atomic runtime operation under
`outputs/characters/<id>/operations/`. Its deterministic request fingerprint binds the character
source hashes, reused static hash, prompt hash, model, duration, and ratio. A durable submitted task
is polled instead of resubmitted; a completed artifact is reused; and ambiguous submission state
returns `BLOCKED_SUBMISSION_UNKNOWN`. Provider SDK retries and automatic paid replacement
submissions remain disabled. The command never invokes static generation.

An exceptional `--owner-risk-override` is accepted only when the canonical operation remains
`SUBMISSION_UNKNOWN`. It preserves that legacy record and creates a separate audited
`owner-risk-override-001` operation capped at one new five-second `gen4_turbo` submission, 25
credits, USD 0.25, and zero automatic retries. Repeating the command resumes/reuses that override
operation; it can never create a second override submission.

After visually reviewing both preview-only artifacts:

```bash
uv run python -m lala_workflow character activate CHARACTER_ID
uv run python -m lala_workflow character reject CHARACTER_ID
uv run python -m lala_workflow character activate lala-v1  # rollback
```

Staging uploads are exact immutable copies under `assets/characters/<id>/source/`. Activation copies
those exact bytes into `assets/approved_anchors/characters/<id>/`; static/motion previews remain
under `outputs/characters/<id>/` and never become production keyframes or videos automatically.
New static evidence records character/profile/source/reference hashes while preserving the existing
eight-file run contract. If character configuration is absent, static generation falls back to the
unchanged legacy anchor manifest.

Phase 1 does not generate missing views, score identity automatically, approve creative/MTL/video
quality, provide multi-user authentication, deploy a cloud service, or migrate historical evidence.

## Goal 2 video pipeline

Goal 2 is provider-neutral by responsibility:

```text
Approved keyframe + exact MTL script + approved voice/audio
    -> talking/lip-sync alternatives
    -> optional Runway motion/B-roll
    -> human shot selection
    -> deterministic FFmpeg assembly and exact audio replacement
    -> blank candidate QA
    -> explicit MTL review and copy-only promotion
```

HeyGen v3 image-plus-audio is the default talking adapter because it accepts a local approved
keyframe and approved audio directly. Runway `gwm1_avatars` is available only when configuration
maps the exact keyframe SHA-256 to a previously human-approved custom avatar UUID; the workflow
never creates that avatar implicitly. Runway image-to-video (`gen4_turbo`, with configurable
`gen4.5`) is the motion/B-roll adapter. Ordinary edits stay local in FFmpeg.

### Required authoritative inputs

The owner-supplied `lala-goal2-authoritative-inputs-v1.0.0.zip` has been imported without changing
member bytes. The repository now contains:

```text
assets/approved_keyframes/lady-lala-home-context-v0.7.png
assets/approved_keyframes/lady-lala-home-context-v0.7.provenance.json
assets/voice/source/lady-lala-canonical-clip-00-v1.0.wav ... clip-07-v1.0.wav
assets/voice/metadata/canonical-source-manifest-v1.0.0.json
assets/scripts/product-page.txt
assets/scripts/tooltip.txt
assets/scripts/homepage.txt
```

No genuine Goal 1 promoted keyframe exists locally. The imported pilot keyframe therefore uses the
separate audited `owner_supplied_legacy_asset` branch with the package name/hash, package-relative
source path, keyframe hash, and owner-approval reference. It has no invented Goal 1 run/output ID,
provider/model/prompt claim, reviewer, or approval timestamp. Ordinary generated keyframes still
require the complete Goal 1 promotion schema.

The three scripts are exact-byte MTL Appendix A source copies with version `1.0.0`, SHA-256, and
per-script source references in `configs/script-manifest.yaml`. The eight WAVs are canonical Lady
LaLa voice-cloning source material only. They are not product-page, tooltip, or homepage narration
and do not satisfy the approved voice gate.

The owner-selected HeyGen voice ID `7a738e1ced454de6b92d2c76a6ccb8c0` is configured, but the
versioned profile remains `pending` until a read-only API verification proves that the current
account can read `Lady LaLa v1` as a private Starfish-compatible voice. A successful verification
may advance it only to `approved_for_smoke`; `production_approved` still requires human preview
and talking-QA decisions. Approved per-script narration WAVs remain an alternative and take
precedence when their exact script hashes match.

Configuration remains credential-free:

- `configs/keyframe-manifest.yaml`: approved path/hash and branch-specific provenance. Genuine Goal
  1 promotions use run/output/reviewer/time; the current legacy asset uses package audit fields.
- `configs/script-manifest.yaml`: MTL source, immutable policy, version, exact path, and SHA-256 for
  each script.
- `configs/voice-profile.yaml`: either `approved_audio` with one approved WAV/hash/script-hash
  mapping per script, or an approved `cloned_voice` provider/model/voice ID.
- `configs/video-presets.yaml`: bounded shot composition and provider/model selection.
- `configs/providers.yaml`: dated official capabilities, pricing sources, and safety maxima only.

Approved anchors, keyframes, voice files, and scripts are immutable. Derived audio/media goes only
under categorized `outputs/` paths. Until the configured voice is read-only verified as
`approved_for_smoke` (or approved per-script WAVs are supplied), talking validation and previews
stop before run allocation/provider construction with the sole blocker:

```text
BLOCKED_EXTERNAL: Goal 2 still requires a real approved HeyGen Starfish/private Lady LaLa voice profile or approved per-script Lady LaLa narration WAVs.
```

### Validate and preview without provider calls

The independent motion smoke preview does not require a voice, narration, or talking review:

```bash
uv run python -m lala_workflow video motion-smoke-test \
  --keyframe pilot_home_context --model gen4_turbo --duration 5 \
  --ratio 1280:720 --variations 1 --max-runway-credits 25 --dry-run
```

After verifying and approving the remaining voice profile/audio:

```bash
uv run python -m lala_workflow video validate
uv run python -m lala_workflow video talking-smoke-test \
  --preset tooltip --variations 1 --max-provider-cost-usd 1.00 --dry-run
uv run python -m lala_workflow video generate --preset product_page --dry-run
uv run python -m lala_workflow video generate --preset tooltip --dry-run
uv run python -m lala_workflow video generate --preset homepage --dry-run
```

Preview validates anchor/keyframe/script/audio/prompt hashes, resolves the shot plan and provider
capabilities, calculates call counts, estimates only supportable costs, and writes request evidence.
It never constructs a provider client. Defaults generate alternatives at shot level: up to three
talking takes, three motion takes per applicable shot, and two local final edits. Product-page and
homepage plans use one full-script talking performance and reuse its opening/closing deterministically
around selected B-roll, so the approved audio and script are not duplicated.

An accepted video run contains exactly:

```text
runs/<run_id>/
├── request.json
├── resolved-config.yaml
├── script.txt
├── script-hash.json
├── audio-hash.json
├── keyframe-hash.json
├── shot-plan.json
├── task-events.jsonl
├── provider-results.json
├── edit-commands.txt
├── review.csv
├── cost.json
└── summary.md
```

Every Goal 2 run artifact is append-only. The generated `review.csv` stays blank evidence; copy it
to `outputs/reviews/<run_id>-review.csv` before entering subjective decisions. Smoke approval and
promotion verify that the copy matches the run/candidate provenance and record its SHA-256.

### Staged live workflow

The project-root `.env` is loaded with `override=False`; an existing process value always wins.
Tests and CI disable developer `.env` loading. Inspecting environment status exposes only
`configured`/`missing` and value length, never values. A lowercase `voice_id` is not consumed;
explicitly migrate it with `video voice init-env`.

Verify the existing voice read-only before any speech/video call:

```bash
uv run python -m lala_workflow video voice verify \
  --voice-id-env HEYGEN_VOICE_ID
```

The result is `VERIFIED_FOR_SMOKE`, never automatic production approval. Optional preview audio
goes only under `outputs/audio/voice_preview/<run_id>/` and remains unreviewed.

Never run live commands without owner authorization, explicit provider budgets, and approved
inputs. The independent first Runway stage requires exact `VIDEO_MOTION_LIVE_SMOKE_TEST=true`,
one five-second `gen4_turbo` result, and at most 25 credits. It emits the MP4, FFprobe metadata,
first/middle/last frames, contact sheet, task ID, estimated/actual credits, hashes, and blank QA.

The first talking test is separately restricted to one 8–12-second result:

```bash
export VIDEO_ALLOW_LIVE_CALLS=true
export VIDEO_LIVE_SMOKE_TEST=true
export HEYGEN_API_KEY='set-locally-do-not-commit'
uv run python -m lala_workflow video talking-smoke-test \
  --preset tooltip --variations 1 --max-provider-cost-usd 1.00 --live
```

For the approved Runway-custom-avatar talking path, select `--provider runway_talking`, configure
the exact approved digest mapping, and provide `RUNWAYML_API_SECRET` instead. A task ID is persisted
immediately and is never resubmitted automatically. Polling/download retries, concurrency, total
timeout, and variation counts remain bounded.

Copy both smoke runs’ blank QA sheets and review only the copies. Full pilot generation requires
all talking/motion QA pass fields, MTL readiness, reviewer, and timezone-aware review time, plus
both immutable review copies. The motion copy is supplied with
`--motion-smoke-run-id` and `--motion-smoke-review-file`.

```bash
mkdir -p outputs/reviews
cp runs/LALA-VIDEO-SMOKE-RUN/review.csv \
  outputs/reviews/LALA-VIDEO-SMOKE-RUN-review.csv
# Fill only the copied CSV with a CSV-safe editor.
```

After that one result passes review, the talking-only validation can be expanded to three
sequential alternatives without weakening the first-live gate:

```bash
unset VIDEO_LIVE_SMOKE_TEST
uv run python -m lala_workflow video talking-smoke-test \
  --preset tooltip \
  --variations 3 \
  --smoke-run-id LALA-VIDEO-SMOKE-RUN \
  --smoke-review-file outputs/reviews/LALA-VIDEO-SMOKE-RUN-review.csv \
  --max-provider-cost-usd 1.00 \
  --live
```

### Runway motion smoke and post-smoke visual selection

Motion smoke is a separate Runway-only stage. Its live boundary is fixed at one `gen4_turbo`
result, exactly five seconds, and no more than 25 Runway credits:

Motion Smoke defaults to the bounded `prompts/home-broll-v3.txt`. v3 uses a locked-off camera,
keeps Lady LaLa stationary and fully visible, and stays within Runway's 1000 UTF-16-unit prompt
limit. Its external P1-1 review found camera/framing drift despite stable identity, age, and
wardrobe, so it is not human-QA approved. The v4 smoke solved camera/framing drift and retained
identity stability, but human QA failed eyes, mouth, and motion; it is not MTL-ready.
The v5 eye/mouth strategy corrected the prolonged eye closure and mouth opening, but external
review found global camera/framing translation, so v5 is not MTL-ready. `prompts/home-broll-v6.txt`
combines v4's pixel-position camera lock with v5's eye/mouth/subject lock. Its technical execution
succeeded, but Owner review failed framing, eyes, motion, and MTL readiness while passing camera
lock, identity, and mouth. Its archived status is `P1_1_V6_SMOKE_HUMAN_QA_FAILED`; P1-1 has not
passed. Prompt-only subject locking is not sufficient evidence for P1-1 acceptance. It does not
change the default, homepage establishing shot, or P1-2 motion-variation prompts. The
older v1 and v2 prompts remain available for historical evidence; v2 is immutable and is not used
for new requests. The homepage establishing shot remains configured to use v3.

### P1-1 Motion V7 targeted stability and guarded live batch

V7 is a controlled experiment for the V6 failures: Framing, Eyes, Motion, and the
`OUTSIDE_THRESHOLD` Subject Lock result. It provides three distinct motion rungs: Stability First,
Natural Micro Motion, and Controlled Upper Bound. The versioned V7 prompts preserve camera lock,
framing, identity, gaze, and background while increasing only the bounded natural micro-motion.
The stricter versioned filenames are `p1-1-motion-v7-a-v1.txt`, `p1-1-motion-v7-b-v1.txt`, and
`p1-1-motion-v7-c-v1.txt`; each is validated below Runway's 1,000 UTF-16-unit limit.

Prepare the single three-candidate review record locally:

```bash
uv run python -m lala_workflow video motion-v7-dry-run \
  --keyframe pilot_home_context --project-root .
```

This command intentionally has no `--live` option. It writes three planned calls, estimator-derived
credits, and three blank QA rows, but makes no provider construction, submission, task ID, or paid
call. Its V6 comparison is diagnostic evidence only: V6 values are fixed and V7/delta values stay
`PENDING` until a later real V7 video is analyzed. The V6 blank review SHA-256 remains
`c04e271773e31f81744f94602a9ed782b1a8b792bdbbdaa2e81c704a9b86fa31`; its separately archived
reviewed-copy SHA-256 remains `67ceedc5ce97a9436086fd6b4ff5a3cb8026bd56c68042ddcc4c56dd6eb7ab8e`.
V7 planning alone does not unlock P1-2 Live; an explicit human P1-1 pass and MTL readiness are
required.

The guarded `motion-v7-live` path always runs the complete fixed batch in A → B → C order; there is
no candidate/subset/skip selection. Canonical `configs/motion-v7.yaml` remains
`live_allowed: false`. Any separately owner-authorized execution requires
both `--execute-live` and `--confirm-v7-batch`, exact `VIDEO_ALLOW_LIVE_CALLS=true`, a non-empty
local `RUNWAYML_API_SECRET`, and an explicit credit cap covering the known full-batch estimate:

```bash
uv run python -m lala_workflow video motion-v7-live \
  --keyframe pilot_home_context \
  --execute-live --confirm-v7-batch --max-runway-credits 75 \
  --project-root .
```

Before candidate A can be submitted, the command prepares and validates all three prompt/source/
provider requests, confirms the 75-credit estimate under current configuration, writes the parent
plan evidence, and reads it back for verification. It permits at most one new task per candidate
and three per batch, disables automatic task-creation retries, and stops on the first failure while
preserving any durable task IDs. Human QA rows remain blank, Subject Lock remains diagnostic-only,
and provider or diagnostic success cannot unlock P1-2 Live.

The separately authorized fixed batch `LALA-VIDEO-20260820-075843-MOTION-V7-001` completed all
three original Runway tasks. Its append-only run review remains blank. The Owner's later explicit
review is stored only in
`outputs/reviews/LALA-VIDEO-20260820-075843-MOTION-V7-001-review.csv`: V7-A Stability First PASS,
V7-B Natural Micro Motion FAIL, and V7-C Controlled Upper Bound FAIL/reserve. V7-A is the unique
P1-1 winner and is explicitly MTL-ready. This is HUMAN authority; automatic Human QA is false.
The reviewed copy maps Camera Lock to `background` and Framing to `body_proportions` under the
existing exact schema.

P1-2's existing motion prerequisite now also accepts a successful canonical V7 parent only when
its external review contains exactly one fully passing, MTL-ready candidate, all three decisions
have human attribution, and every task/media/hash fact remains valid. It returns only the selected
candidate's prompt/keyframe provenance to downstream planning. Ambiguous, failing, mismatched, or
mutated V7 evidence is rejected before provider construction. This establishes
`P1_2_LIVE_READY`; it does not execute P1-2 or replace the independent live command, credential,
environment, count, and budget guards. The closure proof run
`LALA-VIDEO-20260820-084806-MOTION-GENERATE-001` planned three variations and made zero submissions,
task IDs, provider constructions, or paid calls.

The formal V7 diagnostics state remains `POST_LIVE_DIAGNOSTIC_ENTRYPOINT_NOT_AVAILABLE` because
the existing Subject Lock command accepts a single-result `motion_smoke` package, not a
three-candidate `motion_v7_live` parent. Human PASS remains authoritative; no Subject Lock
algorithm, threshold, V6 baseline, or V7 diagnostic value was changed or fabricated.

```bash
export VIDEO_ALLOW_LIVE_CALLS=true
export VIDEO_MOTION_LIVE_SMOKE_TEST=true
export RUNWAYML_API_SECRET='set-locally-do-not-commit'
uv run python -m lala_workflow video motion-smoke-test \
  --keyframe pilot_home_context --model gen4_turbo --duration 5 --ratio 1280:720 \
  --max-runway-credits 25 --live
```

Copy the smoke run's blank QA sheet to `outputs/reviews/`, fill the motion/technical pass fields,
MTL readiness, reviewer, and timezone-aware review time in that copy only. Then generate one to
five alternatives (start with two additional variations) from the same keyframe and exact smoke
prompt. For `gen4_turbo`, the estimate is five credits per second, so the cap must cover
`5 * duration_seconds * variations`. The command calls Runway only;
it does not invoke HeyGen, talking, voice, or the complete pilot:

```bash
uv run python -m lala_workflow video motion-generate \
  --keyframe pilot_home_context --model gen4_turbo --duration 5 --ratio 1280:720 \
  --variations 3 \
  --motion-smoke-run-id LALA-VIDEO-MOTION-SMOKE-... \
  --motion-smoke-review-file outputs/reviews/LALA-VIDEO-MOTION-SMOKE-...-review.csv \
  --max-runway-credits 75 --live
```

Every invocation writes the standard thirteen-artifact append-only bundle and blank `review.csv`.
Use `--dry-run` to validate the same smoke/review/hash/cap/variation gates with zero provider
submissions.

P1-2 planning, prompt loading, shot-plan and budget construction, offline tests, and dry-runs are
available. P1-2 live provider execution requires a separate human-reviewed P1-1 copy that
explicitly passes and records `mtl_review_ready=true`; technical success or diagnostic evidence
alone never opens the live gate. The reviewed V7-A copy now satisfies that P1-1 prerequisite, but
no P1-2 Live execution is authorized or performed by the closure.

Subject Lock diagnostics now quantify subject-proxy position and apparent scale independently
from camera/background lock. They use a deterministic local `color_region_proxy` for Lady LaLa's
red-gown region, require no network/model download, and produce `subject-lock.json`,
`subject-trajectory.csv`, and `subject-overlay.png`. The configured thresholds in
`configs/video-qa.yaml` classify only diagnostic evidence as `WITHIN_THRESHOLD`,
`OUTSIDE_THRESHOLD`, or `INSUFFICIENT_EVIDENCE`; they never populate human QA or MTL readiness.

To analyze and integrity-refresh an existing local Motion Smoke review package without any
provider construction or call:

```bash
uv run python -m lala_workflow video subject-lock \
  --run-id LALA-VIDEO-MOTION-SMOKE-... \
  --package-dir outputs/review-packages/P1-1-MOTION-SMOKE-...
```

`video report` includes the diagnostic summary when exactly one matching package exists and
reports the append-only run's human QA state separately. Prompt-only subject locking is not
considered sufficient evidence for P1-1 acceptance; human review remains authoritative.

For backward compatibility, `motion-generate --dry-run` may still accept
`--motion-smoke-qa-attested`, but dry-run no longer interprets it or any review copy as a pass.
Dry-run validates immutable smoke, output, keyframe, prompt, and review-copy provenance, records
the observed human review state, and authorizes no Live work. The flag is rejected on any Live
invocation. The three
design candidates and exact prompt files are documented in
`specs/003-post-smoke-motion-variations/p1-2-motion-variation-plan.md`.

Mode B uses the same `HEYGEN_API_KEY` only when `configs/voice-profile.yaml` identifies an
explicitly approved `heygen_voice` / `starfish` private voice ID. Exact script bytes are submitted
to HeyGen speech generation, and the downloaded audio is converted to a derived PCM WAV with its
request ID and script hash recorded. An approved per-script WAV remains preferred whenever one is
configured.

```bash
export VIDEO_ALLOW_LIVE_CALLS=true
export HEYGEN_API_KEY='set-locally-do-not-commit'
export RUNWAYML_API_SECRET='set-locally-do-not-commit'
uv run python -m lala_workflow video generate \
  --preset product_page \
  --smoke-run-id LALA-VIDEO-SMOKE-RUN \
  --smoke-review-file outputs/reviews/LALA-VIDEO-SMOKE-RUN-review.csv \
  --motion-smoke-run-id LALA-VIDEO-MOTION-SMOKE-RUN \
  --motion-smoke-review-file outputs/reviews/LALA-VIDEO-MOTION-SMOKE-RUN-review.csv \
  --talking-variations 1 \
  --motion-variations 1 \
  --max-talking-duration-seconds 45 \
  --max-provider-cost-usd 3.00 \
  --max-runway-credits 40 \
  --live
```

Run the same command for `tooltip` and `homepage`. Multi-shot generation stops at
`AWAITING_SELECTION`; it never guesses preferred takes. Remove credentials/permission from the
shell after the authorized stage.

### Select, assemble, report, and promote

Create a human selection YAML outside the run record:

```yaml
source_run_id: LALA-VIDEO-...
reviewer: MTL reviewer name
selected_at: "2026-08-19T13:00:00+08:00"
selections:
  talking_performance: product_page-talking_performance-v001
  product_interaction: product_page-product_interaction-v001
  reward_visual: product_page-reward_visual-v001
```

Use artifact IDs from the source run’s `provider-results.json`; required shot IDs come from
`shot-plan.json`.

```bash
uv run python -m lala_workflow video assemble \
  --run-id LALA-VIDEO-SOURCE-RUN --selection-file selection.yaml --final-edits 2
uv run python -m lala_workflow video report --run-id LALA-VIDEO-ASSEMBLY-RUN
```

Assembly makes zero provider calls. It normalizes scale, letterboxing, frame rate, and codec;
trims/reuses the selected talking performance; intercuts chosen B-roll; replaces/normalizes audio
from the approved WAV; optionally crossfades the second edit; refuses overwrite; logs the exact
argument-safe FFmpeg commands; and validates/hashes final MP4s. Tooltip assembly resolves a real
reward graphic. If no approved brand source is configured, it creates a deterministic local PNG
under `outputs/graphics/`, overlays it in FFmpeg, marks it `DRAFT / NOT MTL APPROVED`, returns
`REVIEW_READY_DRAFT_ASSETS`, and blocks promotion. AI image generation is never used for exact
marketing text.

An unapproved talking crop can be derived without changing the approved keyframe:

```bash
uv run python -m lala_workflow video keyframe derive-talking-crop \
  --source pilot_home_context
```

The crop and provenance go under `outputs/keyframes/derived/`; no approval or manifest promotion
is inferred. Product-page, Tooltip, and homepage talking workflows require an independently
approved `talking_medium_closeup` role in both dry-run and live modes; the full-body pilot hero
cannot satisfy that talking-keyframe gate.

The reviewed external K2 workflow is defined under `specs/008-external-k2-workflow/`. It stages an
owner-supplied PNG/JPEG byte for byte, creates a dedicated blank Human QA copy, and permits
exact-byte promotion only after every required K2 field is literal `PASS` with a named reviewer and
timezone-aware review time. K2 is talking authority only; K1 remains motion/V7 authority. The first
real candidate is staged at `READY_FOR_K2_HUMAN_REVIEW`; it is not approved and Product Page remains
blocked until the Owner supplies a complete reviewed copy and explicitly runs promotion.

Candidate-bound cutover generation also defines three unapproved static roles: K1
`pilot_home_context`, K2 `pilot_talking_medium_closeup`, and K3 `pilot_product_present`. Their
versioned presets are `pilot_home_keyframe`, `pilot_talking_keyframe`, and
`pilot_product_keyframe`; each defaults to three candidates and resolves references from the exact
active character profile. Generated files and blank QA remain staging evidence. Human review does
not itself promote media, build or publish a keyframe set, or rebind Goal 2.

K1 and K3 can additionally use explicit local PDP references through the role-aware three-slot
planner. K1 resolves `character face + character full body + scene/product reference`; K3 resolves
`character face + scene/product reference + product-only reference`. The local inputs must be
regular, non-symlink PNG/JPEG/WebP files inside the project, and both a clean HTTPS source URL and
SKU are required as provenance. The planner hashes and decodes every input, records slot order,
semantic role, path, dimensions, SHA-256, source type, URL, and SKU in run evidence, and fails before
run allocation if a required reference is missing, duplicated, unsafe, or exceeds the provider's
three-reference limit. Example zero-call inspection:

```bash
uv run python -m lala_workflow generate \
  --preset pilot_product_keyframe --count 3 --character character-20260821-001 \
  --scene-reference tmp/candidate16-henry-pdp/01-hero.jpg \
  --product-reference tmp/candidate16-henry-pdp/02.jpg \
  --reference-source-url https://decorolala.com/products/in3725 \
  --reference-sku IN3725 --retries 0 --dry-run
```

After human review, copy the assembly run’s blank `review.csv` to `outputs/reviews/`, then set
`mtl_review_ready`, `reviewer`, and timezone-aware `reviewed_at` in the one matching row of that
copy. Promote with the reviewed copy as an explicit immutable input:

```bash
uv run python -m lala_workflow video promote \
  --run-id LALA-VIDEO-ASSEMBLY-RUN \
  --candidate lady-lala-product-page-candidate-v001.mp4 \
  --review-file outputs/reviews/LALA-VIDEO-ASSEMBLY-RUN-review.csv
```

Promotion copies to `outputs/approved_videos/lady-lala-<preset>-approved-vN.mp4`, refuses collisions,
keeps the source, run evidence, and reviewed copy unchanged, and writes adjacent provenance
covering sources, scripts, selected shots, providers/models, hashes, the review-copy digest,
reviewer, and dates.

Provider capability and pricing evidence is dated in
`specs/002-lala-video-pipeline/research.md`. For cloned-voice pilots, exact HeyGen cost is unknown
before TTS because both Starfish speech and Avatar IV are billed by output duration. The explicit
`--max-talking-duration-seconds` value is a post-TTS workflow gate, not a provider-enforced speech
limit: dry-run records known unit rates, `TOTAL_EXACT_UNKNOWN_UNTIL_TTS`, and the cost projection at
that duration limit. After the WAV is downloaded, the runner measures its real duration, recomputes
voice, talking, Runway, and total estimates, and blocks before every Talking/Runway submission if
the duration gate or owner USD cap would be exceeded. Unknown values remain JSON `null`; neither
`--accept-unknown-provider-cost` nor a fabricated actual is needed when the staged projection is
complete. General Goal 2 generation resolves either a valid legacy one-result motion smoke or the
existing reviewed canonical V7 parent; V7 still requires one unique passing candidate with intact
review, keyframe, task, and media provenance. All Goal 2 automated provider clients, downloads,
clocks, and network behavior are fakes, while one test performs a real local FFmpeg export.

## Approved anchors

The existing source package is mapped by `configs/anchor-manifest.yaml`:

| Logical role | Authoritative source |
|--------------|----------------------|
| Face identity, age, proportions, hair | `assets/approved_anchors/face/lala-face-front.png` |
| Body, red gown, jewelry, silhouette | `assets/approved_anchors/full_body/lala-red-gown-full-body.png` |
| Decorolala environment, lighting, palette | `assets/approved_anchors/scene/lala-home-decor-scene.png` |

The character-sheet exploration and wardrobe-B images are configured as QA-only references. They
are not sent to generation unless a future preset explicitly selects them.

Approved source files are immutable: do not rename, crop, resize, recompress, redraw, move, or
overwrite them. Derived files belong in `assets/derived/`, `runs/`, or `outputs/`.

## Configuration

- `configs/anchor-manifest.yaml`: approved paths, logical roles, tags, ordering, QA references, and
  anchor-set version.
- `configs/generation.yaml`: default provider/model, verified API/SDK versions, model capabilities,
  supported output dimensions, and cost/time/concurrency guardrails.
- `configs/look-presets.yaml`: baseline identity and product-page presets.
- `configs/scene-presets.yaml`: home-decor preset.
- `prompts/*-v1.txt`: versioned prompt sources. Their exact bytes and resolved text are hashed and
  recorded in every run.

Runway's current `ratio` field is an exact output dimension token such as `1080:1440`, not a free
aspect-ratio label. `--ratio` and `--resolution` are CLI aliases; if both are supplied, they must be
identical. Model and dimension overrides are rejected unless listed in verified capabilities.

## Environment variables and secrets

`.env.example` contains names and safe false/blank defaults only. The CLI loads only the parsed
project-root `.env` with `override=False`; it never searches parent directories.

| Variable | Purpose |
|----------|---------|
| `RUNWAYML_API_SECRET` | Runway API key; required only for live calls |
| `RUNWAY_ALLOW_LIVE_CALLS=true` | Exact explicit paid-call permission |
| `RUNWAY_LIVE_SMOKE_TEST=true` | Restricts live execution to exactly one output |
| `VIDEO_ALLOW_LIVE_CALLS=true` | Separate exact Goal 2 paid-call permission |
| `VIDEO_LIVE_SMOKE_TEST=true` | Restricts the first video test to one short talking result |
| `VIDEO_MOTION_LIVE_SMOKE_TEST=true` | Separately authorizes the first one-result Runway motion smoke |
| `VIDEO_FULL_PILOT_LIVE=true` | Separately authorizes reviewed full pilot shot generation |
| `HEYGEN_API_KEY` | HeyGen key; required only for selected live talking work |
| `HEYGEN_VOICE_ID` | Canonical owner-selected voice ID; lowercase `voice_id` is rejected |

Never commit or print real credentials. The CLI and run storage redact secret values, Bearer
tokens, authorization fields, and data-URI payloads from metadata and errors.

## Validate without a run

```bash
python -m lala_workflow validate
```

This verifies YAML, required roles/presets, approved path containment, image readability/content
and dimensions, unique roles/tags, hashes, prompt versions/tags/length, and provider versions and
capabilities. It creates no run and makes no network call.

## Dry run

Dry run is the default generation mode and can be made explicit:

```bash
python -m lala_workflow generate \
  --preset baseline_identity \
  --count 10 \
  --dry-run
```

Dry run validates all inputs, hashes anchors/prompts, resolves references, expands the batch into
single-output provider-neutral requests, validates Runway capabilities, and writes previews. It
does not construct a Runway client, submit a task, download an output, or consume credits.

When `--seed N` is supplied, candidate 001 uses `N`, candidate 002 uses `N+1`, and so on after the
complete range is validated. When no seed is supplied, seed metadata remains null because seed
behavior is provider-specific.

## Required presets

### Baseline identity

Default: 10 candidates, `1080:1440`, face + full-body anchors.

```bash
python -m lala_workflow generate --preset baseline_identity --count 10 --dry-run
```

The prompt requires the approved red gown, jewelry, hair, age, body proportions, complete figure,
neutral warm studio, empty hands, and no people/text/logo/props/redesign.

### Home decor

Default: 5 candidates, `1920:1080`, face + full-body + approved scene anchors.

```bash
python -m lala_workflow generate --preset home_decor --count 5 --dry-run
```

The prompt preserves identity and the approved look inside the warm-neutral premium Decorolala
environment with realistic commercial lighting and a slightly off-center complete figure.

### Product page clean

Default: 5 candidates, `1080:1440`, face + full-body anchors.

```bash
python -m lala_workflow generate --preset product_page_clean --count 5 --dry-run
```

The prompt produces clear subject separation on a clean warm-neutral background with no extra
people, text, logo, props, or objects in hands.

## Live generation and cost controls

Live execution is refused unless `--live`, explicit environment permission, and a non-empty key
are all present. Defaults cap a run at 10 outputs, concurrency at 2, retries at 3 additional
pre-task submission/download attempts, per-task polling at 900 seconds, and total run time at 1800
seconds. Once a provider task ID exists, failures are recorded and never automatically resubmitted.

The runner sends one Runway task per candidate because the verified Gen-4 Image schema has no batch
count field. It never invents an `output_count` API parameter.

An optional estimated-credit ceiling can be supplied with `--max-estimated-credits`. Because
pricing changes, no price is hardcoded. If a ceiling is set while
`estimated_credits_per_output` is null in configuration, live execution fails closed.

### One-image smoke test

Run only with valid credentials and explicit project-owner paid-call permission:

```bash
export RUNWAYML_API_SECRET='set-locally-do-not-commit'
export RUNWAY_ALLOW_LIVE_CALLS=true
export RUNWAY_LIVE_SMOKE_TEST=true
python -m lala_workflow generate --preset baseline_identity --count 1 --live
```

This is the only automated live test and is capped at exactly one output. Remove the temporary
environment values from the shell when finished. If credentials or permission are unavailable,
complete all offline checks and report:

```text
BLOCKED_EXTERNAL: Runway live smoke test requires valid credentials and explicit paid-call permission.
```

After an authorized smoke test succeeds, a full baseline/home/product live run uses the same
commands with `--live`; each is paid, so review count/concurrency and costs before execution.

## Run records and outputs

Every attempted dry or authorized live run has a unique directory:

```text
runs/<run_id>/
├── request.json
├── resolved-config.yaml
├── resolved-prompt.txt
├── anchor-hashes.json
├── task-events.jsonl
├── result.json
├── review.csv
└── summary.md
```

Live images are downloaded immediately from expiring provider URLs to `outputs/<run_id>/` and
hashed. Run records store only sanitized provider-neutral data and redacted URLs. Inspect a run
without changing it:

```bash
python -m lala_workflow report --run-id LALA-RUNWAY-YYYYMMDD-HHMMSS-PRESET-001
```

## Human QA

`review.csv` has one row per downloaded output. The workflow fills provenance and leaves all
identity, age, hair, body, wardrobe, jewelry, hands, scene, extra-people, text/logo, keyframe/MTL
readiness, reviewer, review time, and notes fields blank. It never fabricates approval.

Review the image, then edit the row using a CSV-safe tool. For keyframe promotion:

- set `video_keyframe_ready` to `true` (also accepted: `yes`, `1`, `approved`, or `pass`);
- fill `reviewer`;
- fill timezone-aware ISO 8601 `reviewed_at`, such as `2026-08-18T22:00:00+08:00`.

MTL readiness remains an independent human field and is not set by promotion.

## Promote an approved keyframe

```bash
python -m lala_workflow promote \
  --run-id LALA-RUNWAY-YYYYMMDD-HHMMSS-PRESET-001 \
  --output-id output-001
```

Promotion verifies the review row, source path, result record, and SHA-256. It copies—not moves—the
source to `outputs/approved_keyframes/`, refuses to overwrite an existing target, and writes an
adjacent JSON record containing source run/image, hash, anchor version, prompt version,
provider/model, reviewer, and approval date.

## Provider abstraction

The runner depends on `ImageProvider` only:

```python
class ImageProvider(Protocol):
    def validate_request(self, request): ...
    def submit(self, request): ...
    def wait(self, task_id, timeout_seconds): ...
    def download_results(self, result, destination, output_id, timeout_seconds, max_retries): ...
```

To add Coze or ComfyUI in a future goal, implement this protocol, add documented capabilities and
a provider factory entry, and reuse the runner/storage/reporting tests. Do not leak provider SDK
objects into domain results or rewrite the batch engine.

## Verified Runway behavior

Implementation evidence is recorded in `specs/001-lala-static-images/research.md`. As verified on
2026-08-18:

- Static endpoint: `POST /v1/text_to_image`.
- API version: `2024-11-06`.
- Implemented models: `gen4_image` and `gen4_image_turbo`.
- References: up to 3 (`gen4_image`), 1–3 (`gen4_image_turbo`).
- Tag syntax: lowercase 3–16 characters matching `^[a-z][a-z0-9_]+$`; prompt use is `@tag`.
- Seed: optional integer 0–4,294,967,295; same seed gives similar rather than guaranteed identical
  output.
- Polling: `GET /v1/tasks/{id}`, no faster than once every 5 seconds.
- Success output: expiring URL list downloaded to owned storage.

Official sources:

- [Runway Text/Image to Image API](https://docs.dev.runwayml.com/api/#tag/Start-generating/paths/~1v1~1text_to_image/post)
- [Runway API Getting Started](https://docs.dev.runwayml.com/guides/using-the-api/)
- [Runway Task Detail API](https://docs.dev.runwayml.com/api/#tag/Task-management/paths/~1v1~1tasks~1%7Bid%7D/get)

## Testing

```bash
uv run pytest
```

All provider clients, task states, clocks, downloads, and images in automated tests are local
fakes. An automatic socket guard makes any attempted network connection fail the test immediately,
so the suite makes zero generation and paid calls.

## Troubleshooting

- **Missing/invalid anchor**: run `validate`; restore the approved source at the configured path or
  correct the manifest mapping. Never alter the image to satisfy validation.
- **Duplicate role/tag**: every manifest role/tag must be unique, including QA references.
- **Prompt tag not selected**: ensure every `@tag` belongs to a reference selected by that preset.
- **Unsupported model/dimension**: choose a value listed under the provider's verified capabilities;
  research the current official model schema before expanding the list.
- **Live call blocked**: supply all three guards. Exact lowercase `true` is required for permission.
- **Smoke test count rejected**: `RUNWAY_LIVE_SMOKE_TEST=true` requires `--count 1`.
- **Timeout/failure**: inspect `task-events.jsonl`, `result.json`, and `summary.md`. Provider terminal
  failures are not automatically resubmitted.
- **Successful task but missing image**: output URLs expire; the live runner downloads immediately.
  A failed download is bounded and recorded.
- **Promotion rejected**: verify `video_keyframe_ready`, reviewer, timezone-aware `reviewed_at`,
  source file existence, and unchanged source hash.

## Candidate 16 published keyframe authority

The role-complete Candidate 16 workflow now validates the seven-row V2 review, exact-byte promotes
one Owner selection per K1/K2/K3 role, builds and publishes an immutable keyframe set, and records a
revisioned Goal 2 binding. Use `video keyframe validate-review-package`, `video keyframe
promote-reviewed`, and the `video keyframe-set build|publish|bind-goal2|preflight` commands. Existing
Lady LaLa keyframes remain historical rather than current Candidate 16 authority.

Legacy V7 media remains character-bound to old K1 SHA `ab53d9d…` and is never transferred. The
separately executed Candidate 16 V7 evidence is bound to current K1 SHA `3ad624df…`; its explicit
Owner review selects `v7-b-natural-micro-motion`. Register that external review offline with:

```bash
uv run python -m lala_workflow video motion-v7-register-review \
  --package outputs/reviews/candidate16-v7
uv run python -m lala_workflow video keyframe-set preflight
```

Registration revalidates the A-success parent plus B/C-success recovery, all three task/media/prompt
hashes, the Candidate 16 keyframe, blank append-only run reviews, and the unique human winner. Goal 2
then returns `GOAL2_READY`. The dedicated `video campaign coffee-table --dry-run` planner is
motion-only, plans a 16:9 safe master plus guarded 1:1 and 9:16 delivery, and embeds the V7-B binding.
Its exact recommended non-executed plan is four sequential five-second Runway `gen4_turbo` tasks,
20 generated seconds, at most 100 credits / USD 1.00, concurrency one, and zero automatic
replacement tasks. The command has no live mode and stops at
`READY_FOR_COFFEE_TABLE_LIVE_AUTHORIZATION`; talking, dialogue, TTS, lip sync, and Coffee Table paid
Live remain unexecuted.

The approved dry-run plan is business authority, not a replayable request contract. Prepare the
separate zero-call execution manifest with the exact parent identity:

```bash
uv run python -m lala_workflow video campaign coffee-table \
  --prepare-execution-manifest \
  --parent-plan outputs/campaign-previews/COFFEE-TABLE-DRY-20260821-071433-640204/plan.json \
  --parent-plan-sha256 ed30e4984dd488cde79188e7e327bc4472ab0c331125a0c600d739a0d388ac5f \
  --confirm-owner-authorized-manifest-preparation
```

Preparation validates the current Candidate 16 Goal 2/V7/K1/K2/K3 authority and the V1 Owner
rejection. V2 freezes Task 01 from K1, Task 02 from K3, product-only Task 03 from PDP `02.jpg`,
and Task 04 from Task 02's deterministically extracted `LAST_VALID_FRAME`, including runtime hash
gates, versioned prompt hashes, the unchanged six-beat assembly map, Task 03 trimming, and a
two-second local hold of Task 04's last valid frame. It constructs no provider and stops at
`READY_FOR_OWNER_COFFEE_TABLE_EXECUTION_MANIFEST_REVIEW`. The returned execution-manifest SHA must
receive a later explicit Owner approval before any Live entry may consume it.

After the Owner approves that exact SHA, the bounded Live entry requires every authorization and
budget flag and consumes no alternate plan:

```bash
VIDEO_ALLOW_LIVE_CALLS=true uv run python -m lala_workflow video campaign coffee-table \
  --live \
  --execution-manifest outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json \
  --execution-manifest-sha256 ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea \
  --confirm-owner-authorized-live \
  --max-runway-credits 100 \
  --max-provider-cost-usd 1.00
```

The executor persists each task ID before continuation, stops on any failure or ambiguous
submission, derives Task 04 only from Task 02's deterministic last decoded frame, performs only
local 16:9/1:1/9:16 delivery, and can finish only at `READY_FOR_OWNER_REVIEW` with blank Human QA.

If the exact run above stops after the real Task 03 provider failure, prepare the Owner-specified
offline recovery contract with:

```bash
uv run python -m lala_workflow video campaign coffee-table \
  --prepare-recovery \
  --execution-manifest outputs/campaign-execution-manifests/COFFEE-TABLE-EXEC-20260821-075922-716655/execution-manifest-v2.json \
  --execution-manifest-sha256 ce3f280164907aba6468a72c9e3b19a15a77cc8b9db374f4729928b0e1defdea \
  --failed-live-run LALA-VIDEO-20260821-082100-COFFEE-TABLE-LIVE-001
```

Recovery reuses immutable Task 01/02 results, preserves Task 03 as the real failed provider task,
creates a three-second deterministic local product cutaway, extracts only Task 02 zero-based frame
96 for the proposed Task 04, freezes the v3 sit/hero prompt, and records the exact twenty-second
timeline and 50/75-credit actual/projected budget. It exposes no Live path, constructs no provider,
and stops at `READY_FOR_OWNER_COFFEE_TABLE_RECOVERY_REVIEW`. Task 04 remains unsubmitted until the
Owner separately authorizes the returned recovery-manifest SHA.

The later Owner-selected Frame 92 contract is append-only Recovery Manifest V2. Its dedicated Live
continuation is deliberately separate from the historical four-task executor and requires both
`--live` and `--recovery-live`:

```bash
VIDEO_ALLOW_LIVE_CALLS=true uv run python -m lala_workflow video campaign coffee-table \
  --live \
  --recovery-live \
  --execution-manifest outputs/campaign-recovery-manifests/COFFEE-TABLE-RECOVERY-20260821-204901-001/coffee-table-recovery-manifest-v2.json \
  --execution-manifest-sha256 e97ea0d34f4ea541ab07e6898083e7a35c3b82502030f8f40a06d58fb43e6cc3 \
  --confirm-owner-authorized-live \
  --max-runway-credits 25 \
  --max-provider-cost-usd 0.25
```

The V2 executor rehashes the manifest and every transitive protected input before provider
construction, submits only Task 04 from zero-based Frame 92 and prompt v3, fsyncs the provider task
ID as the idempotency boundary, and uses zero submission/download retries or replacement tasks. A
successful result is assembled locally into the exact eight-segment, 480-frame, twenty-second
16:9 master; the final two seconds use an explicitly extracted last decoded Task 04 frame. Because
V2 contains no Owner-approved objective safe-area geometry, 1:1 and 9:16 fail closed as
`BLOCKED_SAFE_AREA` instead of receiving guessed center crops or native provider regeneration. The
review package copies all four source videos and the master, records evidence/costs, leaves every
Owner checklist field blank, and stops at `READY_FOR_OWNER_REVIEW` without approval or promotion.

If Owner review rejects that delivered master for a semantic error, prepare the separate V3 recovery
review package without a Provider call:

```bash
uv run python -m lala_workflow video campaign coffee-table --prepare-v3-recovery
```

V3 preserves the historical master and blank review package byte-for-byte, records the explicit
Owner decision in a new reviewed-copy package, and keeps `wine glass` as a correct Henry requirement.
It extracts seven post-placement TASK-02 source candidates with blank Owner selection, drafts the
v4 sofa-seating prompt, and permits no Live generation, retry, replacement, promotion, crop, or
native-ratio regeneration. The V3 manifest can recommend `TASK-04 ONLY` only after protected-input
validation; its current-run provider/paid counts and authorized credits are all zero. It stops at
`READY_FOR_OWNER_COFFEE_TABLE_V3_RECOVERY_REVIEW` pending a frame choice, recovery-scope acceptance,
and a separate paid Live authorization.

### Coffee Table four-task redesign (dry-run review only)

The latest Henry-aligned plan is an append-only 20-second, 16:9 package with four exact five-second
tasks: fireplace approach, wine-glass placement and sofa turn, a same-room lifestyle product beauty
shot, and a final sofa-supported hero shot. Each task records its prompt, reference hierarchy,
terminal/start continuity contract, hard negatives, acceptance gates, composition, risks, and blank
Owner checklist. TASK-03 explicitly rejects a white-background/isolated PDP, and TASK-04 requires
Lady LaLa's hips and body weight to be visibly supported by the sofa while the Coffee Table remains
separate in the foreground.

Review `outputs/reviews/coffee-table-4task-dryrun/COFFEE-TABLE-4TASK-DRYRUN-20260821-001/REVIEW.md`
and `manifest.json`. This package makes and authorizes zero Provider calls, retries, replacements,
credits, or cost; it preserves historical 75-credit/USD 0.75 accounting and stops exactly at
`READY_FOR_OWNER_4TASK_DRYRUN_REVIEW`. Any future Live work must proceed one task at a time with an
Owner review and separately hash-bound authorization before each next task.

The optimized prompt review is append-only under
`outputs/reviews/coffee-table-4task-prompt-review/COFFEE-TABLE-4TASK-PROMPT-20260821-001/`.
It separates the detailed Owner storyboard, concise Runway `promptText`, and QA acceptance gates.
The final prompt versions are TASK-01 v3, TASK-02 v3, TASK-03 v4, and TASK-04 v6; their real UTF-16
lengths are 597/507/615/582 units, all below the project target of 850 and provider hard limit of
1000. The local preflight reuses the repository UTF-16 counter, while the provider adapter and
pre-provider runner retain independent hard-limit enforcement. This package stops at
`READY_FOR_OWNER_OPTIMIZED_4TASK_PROMPT_REVIEW` and grants no Live authority.

The final TASK-03 continuity revision is preserved as v5 and reviewed separately under
`outputs/reviews/coffee-table-4task-final-prompt-review/COFFEE-TABLE-4TASK-FINAL-PROMPT-20260821-001/`.
TASK-01 v3, TASK-02 v3, and TASK-04 v6 carry the Owner's explicit prompt approval; TASK-03 v5
remains the sole pending prompt decision. Its primary source is the accepted exact TASK-02 terminal
frame, and it carries the character continuously to a clearly visible sofa-side pre-sit position.
Prompt files are sent unchanged: the trailing newline is preserved, and both local preflight and
Runway payload validation count that exact string. Final UTF-16 units are 598/508/623/583. The
package stops at `READY_FOR_OWNER_FINAL_4TASK_PROMPT_REVIEW` with no Live authority.

The first bounded TASK-01 Live result is now explicitly `REJECTED_HUMAN_QA`; none of its terminal
frames is an approved TASK-02 source. Its immutable failure closure and zero-call replacement plan
are under `outputs/reviews/coffee-table-task01-replacement-plan/COFFEE-TABLE-TASK01-REPLACEMENT-20260822-001/`.
TASK-01 v4 fixes scale authority to a 32 x 16.8 x 20 inch Coffee Table, preserves exactly one glass
in hand and zero on the tabletop, and ends standing beside the table without placement language.
It is 641 UTF-16 payload units and grants no replacement Live authority. TASK-02 remains blocked.
