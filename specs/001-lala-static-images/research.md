# Research: Reproducible Lady LaLa Static Images

**Verified**: 2026-08-18

**Revalidated**: 2026-08-18 against the live official `openapi.json`, generated `api.md`, current
official usage guide, PyPI package metadata, and the installed SDK signatures. The endpoint/API
version, Gen-4 request fields and limits, six task states, five-second polling guidance, output URL
behavior, and latest SDK version still match the implementation.

## Decision 1: Current Runway static-image endpoint and API version

**Decision**: Use `POST /v1/text_to_image` through the official Python SDK and record
`X-Runway-Version: 2024-11-06` as the current API version required by the official reference.

**Rationale**: The official Runway API reference labels this endpoint “Text/Image to Image” and
states that it starts an asynchronous task for images from text and/or images. The version header
has one exact accepted value in the current reference.

**Alternatives considered**: Image-to-video and web-UI generation were rejected because this goal
is static-only and web-UI behavior is not an API contract. Raw HTTP was rejected for the first
implementation because the official SDK exposes the verified schema and typed task resources.

**Official evidence**:

- https://docs.dev.runwayml.com/api/#tag/Start-generating/paths/~1v1~1text_to_image/post
- https://docs.dev.runwayml.com/openapi.json
- https://docs.dev.runwayml.com/api.md
- https://docs.dev.runwayml.com/guides/using-the-api/

## Decision 2: Supported model scope

**Decision**: Record all image models currently listed by the endpoint, but implement and validate
the MVP's tagged-reference workflow for `gen4_image` (default) and `gen4_image_turbo` only.

Current endpoint model list:

- `gen4_image_turbo`
- `gen4_image`
- `gpt_image_2`
- `gemini_image3_pro`
- `gemini_image3.1_flash`
- `seedream5_pro`
- `seedream5_lite`
- `grok_imagine_image_2`
- `gemini_2.5_flash`

**Rationale**: The API reference is model-discriminated; accepted fields and ratios change with
the model. `gen4_image` and `gen4_image_turbo` explicitly support reference tags, seeds, all three
project reference counts, and required output dimensions. Claiming equivalent behavior for every
listed model would invent unsupported cross-model assumptions.

**Alternatives considered**: Supporting every listed model in one generic capability table was
rejected until each model's dynamic schema is researched and tested. `gen4_image_turbo` as the
default was rejected because its references are mandatory; `gen4_image` supports the same project
workflow while also allowing an empty reference list for future neutral tests.

## Decision 3: References, tags, prompts, dimensions, and seeds

**Decision**:

- `gen4_image`: zero to three `referenceImages`.
- `gen4_image_turbo`: one to three `referenceImages`.
- Each reference has required `uri` and optional `tag`.
- Tags are 3–16 characters and use `^[a-z][a-z0-9_]+$`.
- Prompt references use at-mention syntax such as `@lala_face`.
- Prompt text is 1–1000 UTF-16 code units.
- Seed is optional and ranges from 0 to 4,294,967,295; identical seeds promise similar, not
  byte-identical, results.
- Verified dimensions for the supported models are `1024:1024`, `1080:1080`, `1168:880`,
  `1360:768`, `1440:1080`, `1080:1440`, `1808:768`, `1920:1080`, `1080:1920`, `2112:912`,
  `1280:720`, `720:1280`, `720:720`, `960:720`, `720:960`, and `1680:720`.

**Rationale**: These values come directly from the model-selected official API schema. The project
uses lowercase tags even though an older guide example displays uppercase tags, because the
current request schema is the stronger validation source.

**Input transport**: Reference `uri` accepts HTTPS, Runway upload, or image data URI. Data URIs are
limited to 5,242,880 characters in the current schema. The three generation anchors encode below
this limit, so local data URI translation is sufficient for the MVP without modifying the source
files or introducing upload lifecycle state.

## Decision 4: Asynchronous polling and outputs

**Decision**: Submission returns a task ID. Poll `GET /v1/tasks/{id}` no faster than every five
seconds until `SUCCEEDED`, `FAILED`, `CANCELLED`, or timeout. Normalize `PENDING`, `THROTTLED`, and
`RUNNING` as nonterminal events. On success, immediately download every URL in `output`.

**Rationale**: The official task reference says clients should not expect updates more frequently
than once every five seconds. The official Python SDK types define all six states. Successful task
output is a list of URLs that expire within 24–48 hours, and the SDK recommends copying assets to
owned storage.

**Alternatives considered**: Indefinite SDK waiting was rejected because project timeouts must be
bounded. Re-submitting a failed provider task was rejected because it can create a second paid
generation; only pre-task submission failures and downloads receive bounded retries.

**Official evidence**:

- https://docs.dev.runwayml.com/api/#tag/Task-management/paths/~1v1~1tasks~1%7Bid%7D/get
- https://docs.dev.runwayml.com/openapi.json
- https://docs.dev.runwayml.com/api.md

## Decision 5: SDK version and method mapping

**Decision**: Pin `runwayml==5.14.0` for the MVP. Use:

- `RunwayML(api_key=...)`
- `client.text_to_image.create(model=..., prompt_text=..., ratio=...,
  reference_images=..., seed=...)`
- `client.tasks.retrieve(task_id)`

**Rationale**: Version 5.14.0 was the current package release on 2026-08-18. Its generated OpenAPI
resources expose the verified model overloads, support per-call network timeouts, and represent
successful task output as `list[str]`. Pinning preserves reproducibility against future generated
schema changes.

**Alternatives considered**: The SDK's convenience `wait_for_task_output` was not selected for the
adapter because custom polling is needed to record every task event and treat cancellation,
timeouts, and tests consistently.

**Current package evidence**: PyPI reports `runwayml==5.14.0` as the latest release. The installed
SDK's `text_to_image.create` signature exposes the documented Gen-4 `model`, `prompt_text`,
`ratio`, `reference_images`, `seed`, and per-call `timeout` fields, while `tasks.retrieve` exposes
the task ID and timeout. The broader endpoint currently lists one model (`grok_imagine_image_2`)
that is not present in this SDK method's generated type signature; it is outside the implemented
Gen-4 scope and is not claimed as supported.

## Decision 6: Provider-neutral batching

**Decision**: The runner expands `count` into provider-neutral requests whose `output_count` is
always 1. The Runway adapter rejects any request with another value.

**Rationale**: The verified `gen4_image`/`gen4_image_turbo` request schema has no output-count field.
Sending one would invent an API parameter. Batch count therefore belongs to the workflow engine,
which may run up to the configured concurrency and preserves one provider task ID per candidate.

**Alternatives considered**: Putting `count` into `extra_body` was rejected as undocumented.

## Decision 7: Local configuration and test stack

**Decision**: Use YAML for operator configuration, versioned text files for prompts, dataclasses for
provider-neutral models, Pillow for image verification, argparse for the CLI, and pytest with fake
providers/SDK clients for automated tests.

**Rationale**: This keeps the small CLI inspectable, avoids a framework dependency, and supports
strict offline tests. Files are the required run-record format and no database is needed.

**Alternatives considered**: Pydantic models were rejected for the provider-neutral core to avoid
coupling application serialization to the SDK's Pydantic version. A database was rejected because
the objective requires portable per-run artifacts.
