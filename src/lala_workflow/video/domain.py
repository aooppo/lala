from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ApprovedKeyframe:
    keyframe_id: str
    path: Path
    sha256: str
    mime_type: str
    width: int
    height: int
    provenance_type: str
    provenance_record: Path
    source_run_id: str | None = None
    source_output_id: str | None = None
    reviewer: str | None = None
    approved_at: str | None = None
    source_package: str | None = None
    source_package_sha256: str | None = None
    source_path: str | None = None
    owner_approval_reference: str | None = None
    roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScriptRecord:
    script_id: str
    path: Path
    version: str
    sha256: str
    source: str
    source_reference: str
    modification_policy: str
    content: bytes = field(repr=False)

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")


@dataclass(frozen=True, slots=True)
class ApprovedAudio:
    audio_id: str
    path: Path
    sha256: str
    script_sha256: str
    duration_seconds: float
    sample_rate: int
    channels: int
    voice_version: str
    provider_task_id: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    voice_version: str | None
    mode: str
    provider: str | None
    model: str | None
    voice_id: str | None
    source_audio: Path | None
    approved_audio: Path | None
    canonical_source_manifest: Path | None
    canonical_source_manifest_sha256: str | None
    canonical_sources: tuple[Mapping[str, Any], ...]
    script_audio: Mapping[str, Mapping[str, Any]]
    language: str | None
    accent: str | None
    speed: float | None
    style: str | None
    stability: float | None
    similarity: float | None
    output_format: str
    sample_rate: int | None
    approval_status: str
    gender: str | None = None
    locale: str | None = None
    engine: str | None = None
    voice_type: str | None = None
    created_at: str | None = None
    voice_name: str | None = None
    owner_supplied_voice_id: bool = False
    verification_run_id: str | None = None
    verification_time: str | None = None
    profile_version: str | None = None
    approval_scope: str | None = None
    owner_reference: str | None = None


@dataclass(frozen=True, slots=True)
class SafetyLimits:
    max_talking_variations_per_shot: int
    max_motion_variations_per_shot: int
    max_final_edits_per_video: int
    max_concurrency: int
    max_retries: int
    provider_timeout_seconds: float
    max_talking_duration_seconds: float
    allow_live_calls: bool


@dataclass(frozen=True, slots=True)
class ProviderDefinition:
    name: str
    responsibility: str
    settings: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ShotTemplate:
    shot_id: str
    kind: str
    source_role: str
    prompt_file: Path | None
    duration_seconds: float | None
    optional: bool = False


@dataclass(frozen=True, slots=True)
class VideoPreset:
    name: str
    script_id: str
    aspect_ratio: str
    resolution: str
    frame_rate: int
    talking_provider: str
    talking_model: str
    motion_provider: str
    motion_model: str
    alternate_takes: int
    talking_shot_variations: int
    broll_variations: int
    final_edit_variations: int
    single_shot_fallback: bool
    shots: tuple[ShotTemplate, ...]


@dataclass(frozen=True, slots=True)
class VideoProjectConfig:
    root: Path
    anchor_manifest: Mapping[str, Any]
    keyframe_status: str
    keyframes: Mapping[str, ApprovedKeyframe]
    scripts: Mapping[str, ScriptRecord]
    voice_profile: VoiceProfile
    presets: Mapping[str, VideoPreset]
    providers: Mapping[str, ProviderDefinition]
    limits: SafetyLimits
    verified_on: str
    currency: str
    input_blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResolvedPrompt:
    path: Path
    version: str
    text: str
    sha256: str


@dataclass(frozen=True, slots=True)
class PlannedRequest:
    request_id: str
    shot_id: str
    variation: int
    responsibility: str
    provider: str
    model: str
    duration_seconds: float | None


@dataclass(frozen=True, slots=True)
class PlannedShot:
    shot_id: str
    kind: str
    source_role: str
    prompt: ResolvedPrompt | None
    duration_seconds: float | None
    variation_count: int
    selection_required: bool
    requests: tuple[PlannedRequest, ...]
    optional: bool = False


@dataclass(frozen=True, slots=True)
class ShotPlan:
    preset: str
    mode: str
    script_id: str
    aspect_ratio: str
    resolution: str
    frame_rate: int
    shots: tuple[PlannedShot, ...]
    final_edit_variations: int
    voice_request_count: int = 0

    @property
    def provider_call_count(self) -> int:
        return self.voice_request_count + sum(len(shot.requests) for shot in self.shots)


@dataclass(frozen=True, slots=True)
class TalkingVideoRequest:
    request_id: str
    run_id: str
    preset: str
    shot_id: str
    variation: int
    provider: str
    model: str
    keyframe_path: Path
    keyframe_sha256: str
    audio_path: Path
    audio_sha256: str
    audio_duration_seconds: float
    script_path: Path
    script_version: str
    script_sha256: str
    aspect_ratio: str
    resolution: str
    prompt_text: str | None
    timeout_seconds: float
    max_retries: int


@dataclass(frozen=True, slots=True)
class MotionVideoRequest:
    request_id: str
    run_id: str
    preset: str
    shot_id: str
    variation: int
    provider: str
    model: str
    image_path: Path
    image_sha256: str
    prompt_path: Path
    prompt_text: str
    prompt_sha256: str
    ratio: str
    duration_seconds: int
    seed: int | None
    output_format: str
    timeout_seconds: float
    max_retries: int


@dataclass(frozen=True, slots=True)
class VoiceRequest:
    request_id: str
    run_id: str
    preset: str
    script_path: Path
    script_content: bytes
    script_sha256: str
    provider: str
    model: str
    voice_id: str
    language: str | None
    speed: float | None
    output_path: Path
    output_format: str
    sample_rate: int | None
    timeout_seconds: float
    max_retries: int


class VideoTaskStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


@dataclass(frozen=True, slots=True)
class VideoTaskResult:
    provider_task_id: str
    status: VideoTaskStatus
    output_urls: tuple[str, ...] = ()
    estimated_credits: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    actual_credits: float | None = None


@dataclass(frozen=True, slots=True)
class MediaArtifact:
    artifact_id: str
    kind: str
    path: Path
    sha256: str
    size_bytes: int
    mime_type: str
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    provider_task_id: str | None = None
    source_url_redacted: str | None = None
    container: str | None = None
    video_codec: str | None = None
    pixel_format: str | None = None
    average_frame_rate: str | None = None
    audio_stream_present: bool | None = None
    audio_codec: str | None = None
    sample_rate: int | None = None
    channel_count: int | None = None
    bit_rate: int | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ShotSelection:
    source_run_id: str
    reviewer: str
    selected_at: str
    selection_file: Path
    selections: Mapping[str, MediaArtifact]


@dataclass(frozen=True, slots=True)
class CostComponent:
    category: str
    provider: str
    model: str
    generated_seconds: float
    attempts: int
    successful_outputs: int
    failed_outputs: int
    amount: float
    basis: str
    currency: str
    pricing_source: str
    pricing_date: str
