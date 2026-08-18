# Lady LaLa Runway Static Image Workflow MVP

## 1. Objective

Build a reproducible, testable, and documented static-image generation workflow for Lady LaLa using the official Runway API.

The workflow must use the approved anchor images as the only authoritative identity references and support repeatable generation of multiple image variations.

This phase covers static images only. Do not implement talking-avatar or final video generation in this phase.

---

## 2. Source of Truth

The approved anchor images are stored under:

- `assets/approved_anchors/face/`
- `assets/approved_anchors/full_body/`
- `assets/approved_anchors/scene/`

The required logical roles are:

1. `face_anchor`
   - Defines Lady LaLa's facial identity
   - Defines apparent age
   - Defines facial proportions
   - Defines hair color, parting, length, and hairstyle

2. `full_body_anchor`
   - Defines body proportions
   - Defines the approved red-gown look
   - Defines jewelry
   - Defines the complete character silhouette

3. `scene_anchor`
   - Defines the Decorolala home-decor environment
   - Defines lighting, composition, palette, and brand atmosphere

Do not silently replace, redraw, modify, crop, or overwrite the original approved anchor files.

Generated derivative files must be stored separately.

---

## 3. Primary Workflow

Implement the following workflow:

```text
Load approved anchor manifest
        ↓
Validate required files and checksums
        ↓
Load generation preset
        ↓
Build Runway request
        ↓
Attach tagged reference images
        ↓
Submit generation task
        ↓
Poll task with bounded timeout
        ↓
Download generated output
        ↓
Write sanitized run metadata
        ↓
Create manual QA review row
        ↓
Generate run summary
````

---

## 4. MVP Scope

The MVP must support:

* Runway text/image-to-image generation
* One to three tagged reference images
* Baseline identity preset
* Home-decor scene preset
* Clean product-page preset
* Configurable output count
* Configurable model
* Configurable aspect ratio
* Explicit seeds
* Bounded concurrency
* Bounded retries
* Polling timeout
* Dry-run mode
* Live mode
* Output downloading
* SHA-256 hashes for input and output files
* JSON metadata for every generated output
* CSV review sheet
* Provider abstraction for future Coze and ComfyUI support

Do not implement automatic face-recognition scoring in the MVP.

Identity approval remains a human review step.

---

## 5. Required Project Structure

Create or normalize the project to this structure:

```text
.
├── AGENTS.md
├── PLAN.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── assets/
│   └── approved_anchors/
├── configs/
│   ├── anchor-manifest.yaml
│   ├── generation.yaml
│   ├── look-presets.yaml
│   └── scene-presets.yaml
├── prompts/
│   ├── baseline-identity-v1.txt
│   ├── home-decor-v1.txt
│   └── product-page-clean-v1.txt
├── src/
│   └── lala_workflow/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── domain.py
│       ├── hashing.py
│       ├── prompts.py
│       ├── runner.py
│       ├── storage.py
│       ├── reporting.py
│       └── providers/
│           ├── __init__.py
│           ├── base.py
│           └── runway.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── runs/
└── outputs/
```

Generated outputs and secrets must not be committed to Git.

---

## 6. Anchor Manifest

Create `configs/anchor-manifest.yaml`.

It must support this logical structure:

```yaml
project: lady-lala
anchor_set_version: "1.0"
status: approved

anchors:
  face:
    path: assets/approved_anchors/face/lala-face-front.png
    tag: lala_face
    role: facial_identity
    priority: 1

  full_body:
    path: assets/approved_anchors/full_body/lala-red-gown-full-body.png
    tag: lala_look
    role: body_proportions_wardrobe_and_jewelry
    priority: 2

  scene:
    path: assets/approved_anchors/scene/lala-home-decor-scene.png
    tag: home_scene
    role: environment_style
    priority: 3
```

Validate:

* File exists
* File is readable
* File is a supported image type
* Image dimensions are valid
* SHA-256 can be computed
* No duplicate tags exist
* Required anchor roles are present

If actual filenames differ, inspect the existing anchor directory and update only the manifest. Do not rename or overwrite original files unless required for safe filesystem compatibility.

If anchor roles cannot be identified safely, pause and report the exact files requiring human mapping.

---

## 7. Runway Integration

Use the official Runway SDK where practical.

Before implementation:

1. Read the current official Runway API documentation.
2. Verify the current image-generation endpoint.
3. Verify supported models.
4. Verify reference-image limits.
5. Verify reference-image tag syntax.
6. Verify supported output ratios.
7. Verify task polling and output retrieval.
8. Pin or record the API version used.

Do not invent API fields.

Do not assume that Runway web-UI behavior is identical to Runway API behavior.

The Runway provider must accept a provider-neutral request object and translate it to the current official Runway API request.

Expected provider-neutral input:

```python
GenerationRequest(
    run_id: str,
    prompt: str,
    references: list[ReferenceImage],
    model: str,
    ratio: str,
    seed: int | None,
    output_count: int,
)
```

Expected normalized result:

```python
GenerationResult(
    provider: str,
    provider_task_id: str,
    model: str,
    seed: int | None,
    reference_hashes: dict[str, str],
    prompt_hash: str,
    output_files: list[str],
    started_at: str,
    completed_at: str,
    duration_seconds: float,
    status: str,
    error_code: str | None,
    error_message: str | None,
)
```

Provider interface:

```python
class ImageProvider(Protocol):
    def validate_request(self, request: GenerationRequest) -> None:
        ...

    def submit(self, request: GenerationRequest) -> str:
        ...

    def wait(self, task_id: str) -> GenerationResult:
        ...
```

The implementation must make it possible to add:

* `CozeImageProvider`
* `ComfyUIImageProvider`

without changing the batch runner or reporting layer.

---

## 8. Prompt Templates

### Baseline identity

Create `prompts/baseline-identity-v1.txt`.

Its purpose is to verify identity and approved Look A without a complex environment.

Requirements:

* Photorealistic commercial spokesperson portrait
* Full figure visible from head to floor
* Neutral warm studio background
* Face controlled by the face anchor
* Body, wardrobe, hairstyle, and jewelry controlled by the full-body anchor
* Red gown must remain unchanged
* Arms relaxed at sides
* No object in hands
* No extra people
* No text
* No logo
* No wardrobe redesign
* No significant facial or age change

Use the official Runway reference-tag syntax verified from current documentation.

### Home-decor scene

Create `prompts/home-decor-v1.txt`.

Requirements:

* Preserve approved Lady LaLa identity
* Preserve red gown, jewelry, hair, and body proportions
* Place her naturally in the approved home-decor environment
* Premium contemporary interior
* Warm neutral palette
* Restrained gold accents
* Realistic depth
* Complete figure visible
* Slightly off-center composition
* No extra people
* No props in her hands
* No text or logo

### Product-page clean background

Create `prompts/product-page-clean-v1.txt`.

Requirements:

* Preserve approved Lady LaLa identity and Look A
* Clean warm neutral background
* Strong subject separation
* Suitable for product-page compositing
* Natural commercial lighting
* No extra people
* No text
* No logo
* No props
* No wardrobe changes

---

## 9. Generation Presets

Create configurable presets.

### Baseline preset

```yaml
name: baseline_identity
references:
  - face
  - full_body
prompt_file: prompts/baseline-identity-v1.txt
default_count: 10
default_ratio: "1080:1440"
```

### Home-decor preset

```yaml
name: home_decor
references:
  - face
  - full_body
  - scene
prompt_file: prompts/home-decor-v1.txt
default_count: 5
default_ratio: "1920:1080"
```

### Product-page preset

```yaml
name: product_page_clean
references:
  - face
  - full_body
prompt_file: prompts/product-page-clean-v1.txt
default_count: 5
default_ratio: "1080:1440"
```

Model names and supported ratios must remain configurable and must be validated against current provider capabilities.

---

## 10. CLI Commands

Implement these commands or equivalent commands with the same behavior:

```bash
python -m lala_workflow validate

python -m lala_workflow generate \
  --preset baseline_identity \
  --count 10 \
  --dry-run

python -m lala_workflow generate \
  --preset baseline_identity \
  --count 1 \
  --live

python -m lala_workflow generate \
  --preset home_decor \
  --count 5 \
  --live

python -m lala_workflow report \
  --run-id RUN_ID
```

The dry-run command must:

* Validate configuration
* Validate anchor files
* Compute hashes
* Render final prompts
* Construct provider requests
* Write request previews
* Make no network request
* Consume no Runway credits

---

## 11. Cost and Safety Guardrails

Paid Runway calls must be disabled by default.

Require both:

```text
RUNWAYML_API_SECRET
RUNWAY_ALLOW_LIVE_CALLS=true
```

before making a live request.

Add:

* Explicit `--live` flag
* Maximum output count
* Maximum concurrency
* Maximum retries
* Poll timeout
* Overall run timeout
* Optional estimated-credit ceiling
* Clear confirmation in logs before live execution

Never:

* Commit the API key
* Print the API key
* Store the API key in metadata
* Include authorization headers in logs
* Run unlimited retry loops
* Continue paid generation after repeated provider failure
* Automatically generate 10 paid images during tests

Default limits:

```yaml
max_outputs_per_run: 10
max_concurrency: 2
max_retries: 3
poll_timeout_seconds: 900
allow_live_calls: false
```

When credentials or live-call permission are missing, complete all dry-run work and report the live smoke test as blocked. Do not loop or repeatedly ask for credentials.

---

## 12. Run Records

For every run, create:

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

Use a run ID similar to:

```text
LALA-RUNWAY-20260818-153045-BASELINE-001
```

Do not store API secrets or authorization headers.

---

## 13. Manual QA Review Sheet

Create one row per generated image with these columns:

```csv
run_id,output_id,output_file,provider_task_id,seed,face_identity_pass,age_pass,hair_pass,body_proportions_pass,wardrobe_pass,jewelry_pass,hands_pass,scene_pass,no_extra_people_pass,no_text_logo_pass,mtl_review_ready,reviewer,reviewed_at,notes
```

Leave subjective QA fields blank by default.

Do not fabricate an identity score or automatically mark an output as MTL-approved.

---

## 14. Tests

Implement:

### Unit tests

* Config loading
* Manifest validation
* Missing anchor behavior
* Duplicate tag rejection
* Prompt rendering
* SHA-256 generation
* Run ID generation
* Result serialization
* Secret redaction
* Retry limits
* Timeout behavior

### Mock integration tests

* Runway request contains the correct references
* Runway request uses the expected tags
* No more than the supported number of references is sent
* Task polling terminates
* Output files are downloaded correctly
* Provider error becomes a normalized error
* Dry-run makes no network request

### Optional live smoke test

Run only when:

```text
RUNWAY_ALLOW_LIVE_CALLS=true
```

The live smoke test must generate only one image.

---

## 15. Documentation

Create a complete `README.md` explaining:

* Installation
* Python version
* Environment setup
* Runway API key setup
* Anchor placement
* Manifest configuration
* Dry-run
* One-image live smoke test
* Ten-image baseline run
* Home-decor run
* Output review
* Troubleshooting
* Cost controls
* How to add another provider

Create `.env.example` without real secrets.

Create `AGENTS.md` describing:

* Project purpose
* Architectural boundaries
* Commands Codex should run
* Files Codex must not overwrite
* Paid-call restrictions
* Definition of done

---

## 16. Progress Log

Maintain `PROGRESS.md`.

After every checkpoint, record:

* Current checkpoint
* Files changed
* Tests run
* What passed
* What remains
* Current blocker
* Whether any paid API call was made

Keep entries concise.

---

## 17. Checkpoints

Work in this order:

1. Inspect repository and approved anchors
2. Create plan-compatible structure
3. Create domain models and configuration
4. Implement manifest validation
5. Implement provider abstraction
6. Implement Runway provider
7. Implement dry-run workflow
8. Implement metadata and reporting
9. Add tests
10. Run all offline tests
11. Write documentation
12. Run one live smoke test only when explicitly permitted
13. Review final diff and summarize results

Do not begin the next checkpoint while the current checkpoint has failing tests, unless the failure is explicitly documented as an external blocker.

---

## 18. Definition of Done

The goal is complete when all of the following are true:

1. The repository contains the required workflow implementation.
2. Approved anchors remain unchanged.
3. Configuration and anchor validation work.
4. Provider abstraction is implemented.
5. Runway integration uses verified official API behavior.
6. Baseline, home-decor, and product-page presets exist.
7. The baseline workflow supports 10 variations.
8. Dry-run mode completes without network access.
9. Unit and mock integration tests pass.
10. Every run can produce reproducibility metadata.
11. A manual QA CSV is generated.
12. README, AGENTS.md, and `.env.example` are complete.
13. No secret appears in Git, logs, fixtures, or run metadata.
14. No uncontrolled paid-call loop exists.
15. One capped live smoke test succeeds when credentials and explicit permission are available.

If live credentials or paid-call permission are unavailable, stop after all offline acceptance criteria pass and clearly report:

```text
BLOCKED_EXTERNAL: live Runway smoke test requires credentials and explicit paid-call permission.
```

That external block must not be treated as a code failure.

---

## 19. Out of Scope

Do not implement in this goal:

* HeyGen
* Talking avatars
* Voice cloning
* Final video editing
* ComfyUI workflow
* Coze workflow
* Automatic MTL approval
* Automatic face-recognition approval
* Shopify integration
* Deployment to production
