from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from ..audio.validation import AudioValidationError, inspect_wav, validate_approved_wav
from ..hashing import assert_within_directory, sha256_file
from .domain import ApprovedAudio, ScriptRecord, VideoProjectConfig, VoiceRequest


HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class VoiceResolutionError(ValueError):
    pass


def resolve_approved_audio(
    config: VideoProjectConfig,
    script: ScriptRecord,
    *,
    override: Path | None = None,
) -> ApprovedAudio:
    profile = config.voice_profile
    if profile.approval_status != "approved":
        raise VoiceResolutionError("Lady LaLa voice approval_status must be approved")
    raw = profile.script_audio.get(script.script_id)
    if not isinstance(raw, Mapping):
        raise VoiceResolutionError(f"approved WAV mapping is missing for {script.script_id}")
    relative = Path(str(raw.get("path") or ""))
    configured = (config.root / relative).resolve()
    if override is not None:
        requested = override if override.is_absolute() else config.root / override
        if requested.resolve() != configured:
            raise VoiceResolutionError("audio override must match the approved script-audio mapping")
    try:
        source = assert_within_directory(configured, config.root / "assets/voice/approved")
    except ValueError as exc:
        raise VoiceResolutionError("approved WAV must remain under assets/voice/approved") from exc
    expected = str(raw.get("sha256") or "").lower()
    script_hash = str(raw.get("script_sha256") or "").lower()
    if not HASH_RE.fullmatch(expected):
        raise VoiceResolutionError(f"approved WAV digest is missing for {script.script_id}")
    if script_hash != script.sha256:
        raise VoiceResolutionError(f"approved WAV script hash mismatch for {script.script_id}")
    actual = sha256_file(source) if source.is_file() else ""
    if actual != expected:
        raise VoiceResolutionError(
            f"approved WAV digest mismatch for {script.script_id}: expected {expected}, got {actual}"
        )
    try:
        info = validate_approved_wav(source, config.root / "assets/voice/approved")
    except AudioValidationError as exc:
        raise VoiceResolutionError(str(exc)) from exc
    return ApprovedAudio(
        audio_id=script.script_id,
        path=source.relative_to(config.root),
        sha256=actual,
        script_sha256=script.sha256,
        duration_seconds=info.duration_seconds,
        sample_rate=info.sample_rate,
        channels=info.channels,
        voice_version=profile.voice_version or "",
        provenance={"mode": "approved_audio", "source": "human_approved_wav"},
    )


def resolve_or_synthesize_audio(
    config: VideoProjectConfig,
    script: ScriptRecord,
    *,
    run_id: str,
    provider: Any | None,
) -> ApprovedAudio:
    if script.script_id in config.voice_profile.script_audio:
        return resolve_approved_audio(config, script)
    profile = config.voice_profile
    if profile.mode != "cloned_voice" or profile.approval_status != "approved":
        raise VoiceResolutionError("an approved audio or cloned-voice mode is required")
    if provider is None:
        raise VoiceResolutionError("configured cloned voice requires a VoiceProvider")
    if not all((profile.provider, profile.model, profile.voice_id, profile.voice_version)):
        raise VoiceResolutionError("approved cloned voice profile is incomplete")
    output = config.root / "outputs/audio" / run_id / f"{script.script_id}.wav"
    request = VoiceRequest(
        request_id=f"{run_id}-{script.script_id}-voice",
        run_id=run_id,
        preset=script.script_id,
        script_path=config.root / script.path,
        script_content=script.content,
        script_sha256=script.sha256,
        provider=profile.provider,
        model=profile.model,
        voice_id=profile.voice_id,
        language=profile.language,
        speed=profile.speed,
        output_path=output,
        output_format=profile.output_format,
        sample_rate=profile.sample_rate,
        timeout_seconds=config.limits.provider_timeout_seconds,
        max_retries=config.limits.max_retries,
    )
    artifact = provider.synthesize(request)
    expected_root = (config.root / "outputs/audio" / run_id).resolve()
    artifact_path = artifact.path.resolve()
    if expected_root not in artifact_path.parents or artifact_path != output.resolve():
        raise VoiceResolutionError("voice provider output escaped the derived run audio path")
    if artifact.mime_type != "audio/wav" or artifact.sha256 != sha256_file(artifact.path):
        raise VoiceResolutionError("voice provider returned invalid WAV provenance")
    try:
        info = inspect_wav(artifact.path)
    except AudioValidationError as exc:
        raise VoiceResolutionError(str(exc)) from exc
    return ApprovedAudio(
        audio_id=f"derived-{script.script_id}",
        path=artifact.path.relative_to(config.root),
        sha256=info.sha256,
        script_sha256=script.sha256,
        duration_seconds=info.duration_seconds,
        sample_rate=info.sample_rate,
        channels=info.channels,
        voice_version=profile.voice_version,
        provider_task_id=artifact.provider_task_id,
        provenance=artifact.provenance,
    )
