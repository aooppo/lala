from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class AnchorImage:
    name: str
    path: Path
    role: str
    tag: str
    priority: int
    generation_input: bool
    sha256: str
    mime_type: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class AnchorManifest:
    project: str
    anchor_set_version: str
    status: str
    anchors: Mapping[str, AnchorImage]
    qa_references: Mapping[str, AnchorImage]


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    path: Path
    filename: str
    version: str
    text: str
    sha256: str
    referenced_tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GenerationPreset:
    name: str
    purpose: str
    references: tuple[str, ...]
    prompt_file: Path
    default_count: int
    default_ratio: str


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    min_references: int
    max_references: int
    supports_seed: bool


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    provider: str
    api_version: str
    sdk_version: str
    endpoint: str
    poll_endpoint: str
    poll_interval_seconds: float
    supported_models: tuple[str, ...]
    supported_ratios: tuple[str, ...]
    model_capabilities: Mapping[str, ModelCapabilities]
    seed_min: int
    seed_max: int
    tag_pattern: str
    tag_min_length: int
    tag_max_length: int
    prompt_utf16_max: int
    data_uri_max_chars: int


@dataclass(frozen=True, slots=True)
class GenerationLimits:
    max_outputs_per_run: int
    max_concurrency: int
    max_retries: int
    poll_timeout_seconds: float
    overall_timeout_seconds: float
    network_timeout_seconds: float
    download_timeout_seconds: float
    allow_live_calls: bool
    estimated_credits_per_output: float | None
    max_estimated_credits: float | None


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    root: Path
    manifest: AnchorManifest
    presets: Mapping[str, GenerationPreset]
    provider: str
    model: str
    ratio: str
    limits: GenerationLimits
    providers: Mapping[str, ProviderCapabilities]


@dataclass(frozen=True, slots=True)
class ReferenceImage:
    name: str
    path: Path
    role: str
    tag: str
    sha256: str
    mime_type: str


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    run_id: str
    output_id: str
    preset: str
    provider: str
    model: str
    ratio: str
    resolution: str
    prompt: PromptTemplate
    references: tuple[ReferenceImage, ...]
    seed: int | None
    output_count: int = 1


@dataclass(frozen=True, slots=True)
class ResolvedRunConfig:
    run_id: str
    preset: str
    provider: str
    model: str
    ratio: str
    resolution: str
    count: int
    concurrency: int
    max_retries: int
    poll_timeout_seconds: float
    overall_timeout_seconds: float
    network_timeout_seconds: float
    download_timeout_seconds: float
    live: bool
    allow_live_calls: bool
    estimated_credits_per_output: float | None
    max_estimated_credits: float | None
    api_version: str
    sdk_version: str
    anchor_set_version: str


class TaskStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


@dataclass(frozen=True, slots=True)
class ProviderTaskResult:
    provider_task_id: str
    status: TaskStatus
    output_urls: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OutputArtifact:
    output_id: str
    provider_task_id: str
    file: Path
    sha256: str
    size_bytes: int
    source_url_redacted: str | None = None


class RunStatus(str, Enum):
    DRY_RUN = "DRY_RUN"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class GenerationResult:
    run_id: str
    provider: str
    model: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    requests: tuple[Mapping[str, Any], ...] = ()
    tasks: tuple[Mapping[str, Any], ...] = ()
    outputs: tuple[OutputArtifact, ...] = ()
    errors: tuple[Mapping[str, Any], ...] = ()


def utc_now() -> datetime:
    return datetime.now(UTC)


def make_run_id(
    provider: str,
    preset: str,
    now: datetime | None = None,
    sequence: int = 1,
) -> str:
    timestamp = (now or utc_now()).astimezone(UTC).strftime("%Y%m%d-%H%M%S")
    provider_part = _run_id_part(provider)
    preset_part = _run_id_part(preset)
    if sequence < 1 or sequence > 999:
        raise ValueError("run sequence must be between 1 and 999")
    return f"LALA-{provider_part}-{timestamp}-{preset_part}-{sequence:03d}"


def _run_id_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").upper()
    if not cleaned:
        raise ValueError("run ID component cannot be empty")
    return cleaned


def to_primitive(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_primitive(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [to_primitive(item) for item in value]
    return value
