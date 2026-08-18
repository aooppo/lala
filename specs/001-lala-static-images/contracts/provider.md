# Provider Contract

## Protocol

Every image provider implements these provider-neutral operations:

```python
class ImageProvider(Protocol):
    def validate_request(self, request: GenerationRequest) -> None: ...
    def submit(self, request: GenerationRequest) -> str: ...
    def wait(self, task_id: str, timeout_seconds: float) -> ProviderTaskResult: ...
    def download_results(
        self,
        result: ProviderTaskResult,
        destination: Path,
        output_id: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> tuple[OutputArtifact, ...]: ...
```

## Behavioral Contract

### `validate_request`

- Performs no generation call and no paid call.
- Validates only against declared provider/model capabilities.
- Rejects unsupported model, dimensions, references, tags, prompt length, seed, local input size,
  or `output_count` before submission.
- Does not construct or persist credentials.

### `submit`

- May be called only after workflow live guards have passed.
- Translates provider-neutral fields to documented provider parameters only.
- Returns a non-empty task ID after provider acceptance.
- Must not include secrets, authorization headers, or full data URIs in events/errors.
- A failure before a task ID exists may be retried by the runner within `max_retries`; once a task
  ID exists, the request is never automatically resubmitted.

### `wait`

- Polls no faster than provider guidance permits.
- Emits/returns normalized observations for nonterminal states.
- Returns a terminal normalized result for success, failure, cancellation, or timeout.
- Never waits indefinitely; caller timeout is mandatory and positive.

### `download_results`

- Accepts only a successful result.
- Downloads all returned URLs promptly with a per-request timeout.
- Retries each transient download at most `max_retries` additional times.
- Writes outside approved anchors, computes SHA-256, and returns normalized artifacts.
- Removes incomplete temporary files after a failed attempt and never overwrites approved anchors.

## Runway Translation Contract

For `runway` + `gen4_image`/`gen4_image_turbo`:

| Neutral field | Official SDK field |
|---------------|--------------------|
| `model` | `model` |
| `prompt` | `prompt_text` |
| `resolution` (equal to `ratio`) | `ratio` |
| reference local path/MIME/tag | `reference_images[].uri` data URI and `reference_images[].tag` |
| `seed` when non-null | `seed` |

No `output_count`, concurrency, retry, timeout, run ID, output ID, or metadata field is sent in the
request body. Those are workflow concerns. The SDK network timeout is passed using its documented
`timeout` argument.

## Normalized Failure Contract

Provider exceptions are converted to a project error code and redacted message. Known terminal
states preserve the provider failure code when available. Unknown exception types use
`provider_error`; no exception representation may contain the configured secret or an
authorization header.
