from __future__ import annotations

from pathlib import Path
import re
from typing import Protocol, runtime_checkable

from ..domain import GenerationRequest, OutputArtifact, ProviderCapabilities, ProviderTaskResult
from ..hashing import encoded_data_uri_length
from ..prompts import utf16_code_units


class WorkflowError(RuntimeError):
    """Base error with a stable, sanitized code."""

    code = "workflow_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class ProviderValidationError(WorkflowError):
    code = "provider_validation_error"


class ProviderSubmissionError(WorkflowError):
    code = "provider_submission_error"


class ProviderTaskError(WorkflowError):
    code = "provider_task_error"


class ProviderTimeoutError(ProviderTaskError):
    code = "provider_timeout"


class ProviderDownloadError(WorkflowError):
    code = "provider_download_error"


def validate_request_capabilities(
    request: GenerationRequest,
    capabilities: ProviderCapabilities,
) -> None:
    if request.provider != capabilities.provider:
        raise ProviderValidationError(
            f"request provider {request.provider} does not match {capabilities.provider}"
        )
    if request.model not in capabilities.supported_models:
        raise ProviderValidationError(f"unsupported model: {request.model}")
    if request.ratio != request.resolution:
        raise ProviderValidationError("ratio and resolution must match for Runway")
    if request.resolution not in capabilities.supported_ratios:
        raise ProviderValidationError(f"unsupported ratio/resolution: {request.resolution}")
    if request.output_count != 1:
        raise ProviderValidationError("Runway requests must have output_count=1")
    model = capabilities.model_capabilities[request.model]
    if not model.min_references <= len(request.references) <= model.max_references:
        raise ProviderValidationError(
            f"model {request.model} requires {model.min_references}..{model.max_references} references"
        )
    tag_re = re.compile(capabilities.tag_pattern)
    seen: set[str] = set()
    for reference in request.references:
        if reference.tag in seen:
            raise ProviderValidationError(f"duplicate reference tag: {reference.tag}")
        if not capabilities.tag_min_length <= len(reference.tag) <= capabilities.tag_max_length:
            raise ProviderValidationError(f"invalid reference tag length: {reference.tag}")
        if not tag_re.fullmatch(reference.tag):
            raise ProviderValidationError(f"invalid reference tag: {reference.tag}")
        if encoded_data_uri_length(reference.path, reference.mime_type) > capabilities.data_uri_max_chars:
            raise ProviderValidationError(f"reference exceeds data URI limit: {reference.name}")
        seen.add(reference.tag)
    units = utf16_code_units(request.prompt.text)
    if not 1 <= units <= capabilities.prompt_utf16_max:
        raise ProviderValidationError(
            f"prompt UTF-16 length must be 1..{capabilities.prompt_utf16_max}"
        )
    if request.seed is not None:
        if not model.supports_seed:
            raise ProviderValidationError(f"model does not support seed: {request.model}")
        if not capabilities.seed_min <= request.seed <= capabilities.seed_max:
            raise ProviderValidationError(
                f"seed must be between {capabilities.seed_min} and {capabilities.seed_max}"
            )


@runtime_checkable
class ImageProvider(Protocol):
    def validate_request(self, request: GenerationRequest) -> None:
        ...

    def submit(self, request: GenerationRequest) -> str:
        ...

    def wait(self, task_id: str, timeout_seconds: float) -> ProviderTaskResult:
        ...

    def download_results(
        self,
        result: ProviderTaskResult,
        destination: Path,
        output_id: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> tuple[OutputArtifact, ...]:
        ...
