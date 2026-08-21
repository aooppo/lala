from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..audio.validation import AudioValidationError, inspect_wav
from ..config import ConfigError, load_yaml, parse_manifest
from ..domain import to_primitive
from ..hashing import assert_within_directory, sha256_file
from .domain import (
    ProviderDefinition,
    SafetyLimits,
    ShotTemplate,
    VideoPreset,
    VideoProjectConfig,
    VoiceProfile,
)
from .scripts import ScriptIntegrityError, load_script_record
from .validation import (
    HASH_RE,
    ExternalInputBlocked,
    SourceValidationError,
    validate_approved_keyframe,
)


REQUIRED_PRESETS = ("product_page", "tooltip", "homepage")
SUPPORTED_SHOT_KINDS = {"talking", "motion", "graphic", "local"}
USABLE_VOICE_APPROVALS = {"approved_for_smoke", "production_approved"}


class VideoConfigError(ConfigError):
    pass


def load_video_config(project_root: Path, *, require_inputs: bool = False) -> VideoProjectConfig:
    root = project_root.resolve()
    try:
        anchor_manifest = parse_manifest(load_yaml(root / "configs/anchor-manifest.yaml"), root)
    except ConfigError as exc:
        raise VideoConfigError(str(exc)) from exc
    keyframe_data = load_yaml(root / "configs/keyframe-manifest.yaml")
    script_data = load_yaml(root / "configs/script-manifest.yaml")
    voice_data = load_yaml(root / "configs/voice-profile.yaml")
    preset_data = load_yaml(root / "configs/video-presets.yaml")
    provider_data = load_yaml(root / "configs/providers.yaml")

    blockers: list[str] = []
    keyframes = _parse_keyframes(keyframe_data, root, blockers)
    scripts = _parse_scripts(script_data, root, blockers)
    voice_profile = _parse_voice_profile(voice_data, root, blockers)
    limits, providers = _parse_providers(provider_data)
    _validate_voice_provider_configuration(voice_profile, providers)
    presets = _parse_presets(preset_data, providers, limits)
    _validate_script_audio_links(voice_profile, scripts, blockers)

    config = VideoProjectConfig(
        root=root,
        anchor_manifest=to_primitive(anchor_manifest),
        keyframe_status=str(keyframe_data.get("status") or "pending"),
        keyframes=keyframes,
        scripts=scripts,
        voice_profile=voice_profile,
        presets=presets,
        providers=providers,
        limits=limits,
        verified_on=str(provider_data.get("verified_on") or ""),
        currency=str(provider_data.get("currency") or "USD"),
        input_blockers=tuple(blockers),
    )
    if require_inputs and blockers:
        raise ExternalInputBlocked("; ".join(blockers))
    return config


def _parse_keyframes(
    data: Mapping[str, Any], root: Path, blockers: list[str]
) -> dict[str, Any]:
    if data.get("project") != "lady-lala":
        raise VideoConfigError("keyframe manifest project must be lady-lala")
    status = str(data.get("status") or "pending")
    if status not in {"pending", "approved"}:
        raise VideoConfigError("keyframe manifest status must be pending or approved")
    raw_keyframes = data.get("keyframes")
    if not isinstance(raw_keyframes, Mapping):
        raise VideoConfigError("keyframes must be a mapping")
    if status != "approved":
        blockers.append(
            "approved keyframe manifest is pending: configs/keyframe-manifest.yaml"
        )
        if raw_keyframes:
            raise VideoConfigError("pending keyframe manifest must not contain approved entries")
        return {}
    if not raw_keyframes:
        blockers.append("at least one approved keyframe with promotion provenance is required")
        return {}
    parsed = {}
    for keyframe_id, raw in raw_keyframes.items():
        if not isinstance(raw, Mapping):
            raise VideoConfigError(f"keyframe {keyframe_id} must be a mapping")
        try:
            parsed[str(keyframe_id)] = validate_approved_keyframe(str(keyframe_id), raw, root)
        except SourceValidationError as exc:
            raise VideoConfigError(str(exc)) from exc
    return parsed


def _parse_scripts(
    data: Mapping[str, Any], root: Path, blockers: list[str]
) -> dict[str, Any]:
    source = str(data.get("source") or "")
    policy = str(data.get("modification_policy") or "")
    if source != "MTL" or policy != "immutable":
        raise VideoConfigError("script manifest must declare source MTL and immutable policy")
    raw_scripts = data.get("scripts")
    if not isinstance(raw_scripts, Mapping):
        raise VideoConfigError("scripts must be a mapping")
    parsed = {}
    for script_id in REQUIRED_PRESETS:
        raw = raw_scripts.get(script_id)
        if not isinstance(raw, Mapping):
            blockers.append(f"authoritative MTL script metadata is missing for {script_id}")
            continue
        missing = [
            name for name in ("version", "sha256", "source_reference") if not raw.get(name)
        ]
        source_path = root / Path(str(raw.get("path") or ""))
        if missing or not source_path.is_file():
            details = ", ".join(missing + ([] if source_path.is_file() else ["file"]))
            blockers.append(
                f"authoritative MTL script {script_id} is pending ({details}): {raw.get('path')}"
            )
            continue
        try:
            parsed[script_id] = load_script_record(
                script_id, raw, root, source=source, modification_policy=policy
            )
        except ScriptIntegrityError as exc:
            raise VideoConfigError(str(exc)) from exc
    return parsed


def _parse_voice_profile(
    data: Mapping[str, Any], root: Path, blockers: list[str]
) -> VoiceProfile:
    mode = str(data.get("mode") or "pending")
    approval = str(data.get("approval_status") or "pending")
    if mode not in {"pending", "approved_audio", "cloned_voice"}:
        raise VideoConfigError("voice mode must be pending, approved_audio, or cloned_voice")
    if approval == "approved":
        approval = "production_approved"
    if approval not in {
        "pending",
        "verified",
        "approved_for_smoke",
        "production_approved",
        "rejected",
    }:
        raise VideoConfigError(
            "voice approval_status must be pending, verified, approved_for_smoke, "
            "production_approved, or rejected"
        )
    script_audio = data.get("script_audio") or {}
    if not isinstance(script_audio, Mapping):
        raise VideoConfigError("voice script_audio must be a mapping")
    canonical_manifest, canonical_manifest_sha256, canonical_sources = (
        _parse_canonical_voice_sources(data, root)
    )
    if mode == "pending" or approval not in USABLE_VOICE_APPROVALS:
        blockers.append(
            "Goal 2 still requires a real approved HeyGen Starfish/private Lady LaLa voice "
            "profile or approved per-script Lady LaLa narration WAVs."
        )
    if mode == "approved_audio" and approval in USABLE_VOICE_APPROVALS and not script_audio:
        blockers.append("approved WAV mappings are required for each selected MTL script")
    if mode == "cloned_voice" and approval in USABLE_VOICE_APPROVALS:
        missing = [name for name in ("voice_version", "provider", "model", "voice_id") if not data.get(name)]
        if missing:
            raise VideoConfigError(
                f"approved cloned voice profile is missing: {', '.join(missing)}"
            )
        # A smoke approval must always carry the read-only verification evidence.
        # Legacy/fixture profiles using the historical ``approved`` alias are
        # normalized to ``production_approved`` above and are intentionally
        # accepted here for backwards-compatible offline provider fixtures;
        # production promotion still has its independent human-review gate.
        if approval == "approved_for_smoke":
            verification_missing = [
                name
                for name in ("verification_run_id", "verification_time", "voice_name")
                if not data.get(name)
            ]
            if verification_missing:
                raise VideoConfigError(
                    "approved-for-smoke voice profile is missing verification evidence: "
                    + ", ".join(verification_missing)
                )
            if data.get("engine") != "starfish" or data.get("type") != "private":
                raise VideoConfigError(
                    "approved-for-smoke voice must be verified as private and Starfish-compatible"
                )
    approved_audio = _optional_voice_path(data.get("approved_audio"), root, "approved")
    source_audio = _optional_voice_path(data.get("source_audio"), root, "source")
    return VoiceProfile(
        voice_version=_optional_str(data.get("voice_version")),
        mode=mode,
        provider=_optional_str(data.get("provider")),
        model=_optional_str(data.get("model")),
        voice_id=_optional_str(data.get("voice_id")),
        source_audio=source_audio,
        approved_audio=approved_audio,
        canonical_source_manifest=canonical_manifest,
        canonical_source_manifest_sha256=canonical_manifest_sha256,
        canonical_sources=canonical_sources,
        script_audio={str(key): dict(value) for key, value in script_audio.items() if isinstance(value, Mapping)},
        language=_optional_str(data.get("language")),
        accent=_optional_str(data.get("accent")),
        speed=_optional_float(data.get("speed"), "voice speed"),
        style=_optional_str(data.get("style")),
        stability=_optional_float(data.get("stability"), "voice stability"),
        similarity=_optional_float(data.get("similarity"), "voice similarity"),
        output_format=str(data.get("output_format") or "wav").lower(),
        sample_rate=_optional_int(data.get("sample_rate"), "voice sample_rate"),
        approval_status=approval,
        gender=_optional_str(data.get("gender")),
        locale=_optional_str(data.get("locale")),
        engine=_optional_str(data.get("engine")),
        voice_type=_optional_str(data.get("type")),
        created_at=_optional_str(data.get("created_at")),
        voice_name=_optional_str(data.get("voice_name")),
        owner_supplied_voice_id=data.get("owner_supplied_voice_id") is True,
        verification_run_id=_optional_str(data.get("verification_run_id")),
        verification_time=_optional_str(data.get("verification_time")),
        profile_version=_optional_str(data.get("profile_version")),
        approval_scope=_optional_str(data.get("approval_scope")),
        owner_reference=_optional_str(data.get("owner_reference")),
    )


def _parse_canonical_voice_sources(
    data: Mapping[str, Any], root: Path
) -> tuple[Path | None, str | None, tuple[Mapping[str, Any], ...]]:
    manifest_value = data.get("canonical_source_manifest")
    digest_value = data.get("canonical_source_manifest_sha256")
    if manifest_value in {None, ""} and digest_value in {None, ""}:
        return None, None, ()
    if manifest_value in {None, ""} or digest_value in {None, ""}:
        raise VideoConfigError(
            "canonical_source_manifest and canonical_source_manifest_sha256 must be set together"
        )
    relative = Path(str(manifest_value))
    if relative.is_absolute() or ".." in relative.parts:
        raise VideoConfigError("canonical voice source manifest path must be project-relative")
    try:
        manifest_path = assert_within_directory(
            root / relative, root / "assets/voice/metadata"
        )
    except ValueError as exc:
        raise VideoConfigError(
            "canonical voice source manifest must remain under assets/voice/metadata"
        ) from exc
    expected_manifest_hash = str(digest_value).strip().lower()
    if not HASH_RE.fullmatch(expected_manifest_hash):
        raise VideoConfigError(
            "canonical_source_manifest_sha256 must be 64 lowercase hex characters"
        )
    if not manifest_path.is_file():
        raise VideoConfigError("canonical voice source manifest does not exist")
    actual_manifest_hash = sha256_file(manifest_path)
    if actual_manifest_hash != expected_manifest_hash:
        raise VideoConfigError(
            "canonical voice source manifest digest mismatch: "
            f"expected {expected_manifest_hash}, got {actual_manifest_hash}"
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise VideoConfigError("canonical voice source manifest is invalid JSON") from exc
    if not isinstance(payload, Mapping):
        raise VideoConfigError("canonical voice source manifest must be an object")
    if payload.get("role") != "canonical Lady LaLa voice-cloning source material":
        raise VideoConfigError("canonical voice source manifest role is invalid")
    if payload.get("status") != "source_material_ready_profile_or_per_script_audio_still_required":
        raise VideoConfigError("canonical voice source manifest status is invalid")
    if not str(payload.get("acceptance_rule") or "").strip():
        raise VideoConfigError("canonical voice source acceptance_rule is required")
    package = payload.get("source_package")
    if not isinstance(package, Mapping):
        raise VideoConfigError("canonical voice source package provenance is required")
    for name in ("name", "manifest_path"):
        if not str(package.get(name) or "").strip():
            raise VideoConfigError(f"canonical voice source package {name} is required")
    for name in ("sha256", "manifest_sha256"):
        if not HASH_RE.fullmatch(str(package.get(name) or "").strip().lower()):
            raise VideoConfigError(
                f"canonical voice source package {name} must be 64 lowercase hex characters"
            )
    package_manifest_path = Path(str(package["manifest_path"]))
    if package_manifest_path.is_absolute() or ".." in package_manifest_path.parts:
        raise VideoConfigError(
            "canonical voice source package manifest_path must be package-relative"
        )
    raw_clips = payload.get("clips")
    if not isinstance(raw_clips, list) or not raw_clips:
        raise VideoConfigError("canonical voice source manifest clips must be non-empty")
    sources: list[Mapping[str, Any]] = []
    seen_paths: set[Path] = set()
    duration_total = 0.0
    for index, raw_clip in enumerate(raw_clips):
        if not isinstance(raw_clip, Mapping):
            raise VideoConfigError(f"canonical voice source clip {index} must be an object")
        clip_relative = Path(str(raw_clip.get("path") or ""))
        if clip_relative.is_absolute() or ".." in clip_relative.parts:
            raise VideoConfigError(
                f"canonical voice source clip {index} path must be project-relative"
            )
        try:
            clip_path = assert_within_directory(
                root / clip_relative, root / "assets/voice/source"
            )
        except ValueError as exc:
            raise VideoConfigError(
                f"canonical voice source clip {index} must remain under assets/voice/source"
            ) from exc
        if clip_path in seen_paths:
            raise VideoConfigError("canonical voice source paths must be unique")
        seen_paths.add(clip_path)
        source_path = Path(str(raw_clip.get("source_path") or ""))
        if (
            not source_path.as_posix()
            or source_path.is_absolute()
            or ".." in source_path.parts
        ):
            raise VideoConfigError(
                f"canonical voice source clip {index} source_path must be package-relative"
            )
        expected = str(raw_clip.get("sha256") or "").strip().lower()
        if not HASH_RE.fullmatch(expected):
            raise VideoConfigError(
                f"canonical voice source clip {index} sha256 must be 64 lowercase hex characters"
            )
        actual = sha256_file(clip_path) if clip_path.is_file() else ""
        if actual != expected:
            raise VideoConfigError(
                f"canonical voice source digest mismatch for {clip_relative}: "
                f"expected {expected}, got {actual}"
            )
        if raw_clip.get("bytes") != clip_path.stat().st_size:
            raise VideoConfigError(f"canonical voice source byte count mismatch for {clip_relative}")
        try:
            info = inspect_wav(clip_path)
        except AudioValidationError as exc:
            raise VideoConfigError(str(exc)) from exc
        expected_codec = {
            1: "pcm_u8",
            2: "pcm_s16le",
            3: "pcm_s24le",
            4: "pcm_s32le",
        }.get(info.sample_width)
        if raw_clip.get("codec") != expected_codec:
            raise VideoConfigError(f"canonical voice source codec mismatch for {clip_relative}")
        if raw_clip.get("sample_rate_hz") != info.sample_rate:
            raise VideoConfigError(
                f"canonical voice source sample rate mismatch for {clip_relative}"
            )
        if raw_clip.get("channels") != info.channels:
            raise VideoConfigError(f"canonical voice source channel mismatch for {clip_relative}")
        try:
            reported_duration = float(raw_clip.get("duration_seconds"))
        except (TypeError, ValueError) as exc:
            raise VideoConfigError(
                f"canonical voice source duration is invalid for {clip_relative}"
            ) from exc
        tolerance = max(1 / info.sample_rate, 0.000001)
        if abs(reported_duration - info.duration_seconds) > tolerance:
            raise VideoConfigError(f"canonical voice source duration mismatch for {clip_relative}")
        duration_total += info.duration_seconds
        sources.append(dict(raw_clip))
    try:
        reported_total = float(payload.get("total_duration_seconds"))
    except (TypeError, ValueError) as exc:
        raise VideoConfigError("canonical voice source total duration is invalid") from exc
    if abs(reported_total - duration_total) > 0.000001:
        raise VideoConfigError("canonical voice source total duration mismatch")
    return (
        manifest_path.relative_to(root.resolve()),
        actual_manifest_hash,
        tuple(sources),
    )


def _optional_voice_path(value: Any, root: Path, subdir: str) -> Path | None:
    if value in {None, ""}:
        return None
    relative = Path(str(value))
    if relative.is_absolute() or ".." in relative.parts:
        raise VideoConfigError("voice paths must be project-relative")
    resolved = (root / relative).resolve()
    expected = (root / f"assets/voice/{subdir}").resolve()
    if resolved != expected and expected not in resolved.parents:
        raise VideoConfigError(f"voice path must remain under assets/voice/{subdir}")
    return relative


def _parse_providers(
    data: Mapping[str, Any],
) -> tuple[SafetyLimits, dict[str, ProviderDefinition]]:
    verified_on = str(data.get("verified_on") or "").strip()
    if not verified_on:
        raise VideoConfigError("providers verified_on is required")
    raw_safety = data.get("safety")
    if not isinstance(raw_safety, Mapping):
        raise VideoConfigError("provider safety settings must be a mapping")
    limits = SafetyLimits(
        max_talking_variations_per_shot=_bounded_int(
            raw_safety.get("max_talking_variations_per_shot"), "max talking variations", 1, 3
        ),
        max_motion_variations_per_shot=_bounded_int(
            raw_safety.get("max_motion_variations_per_shot"), "max motion variations", 1, 5
        ),
        max_final_edits_per_video=_bounded_int(
            raw_safety.get("max_final_edits_per_video"), "max final edits", 1, 2
        ),
        max_concurrency=_bounded_int(raw_safety.get("max_concurrency"), "max concurrency", 1, 1),
        max_retries=_bounded_int(raw_safety.get("max_retries"), "max retries", 0, 2),
        provider_timeout_seconds=float(raw_safety.get("provider_timeout_seconds") or 0),
        max_talking_duration_seconds=float(
            raw_safety.get("max_talking_duration_seconds") or 0
        ),
        allow_live_calls=raw_safety.get("allow_live_calls") is True,
    )
    if not 0 < limits.provider_timeout_seconds <= 1800:
        raise VideoConfigError("provider_timeout_seconds must be within 1..1800")
    if not 0 < limits.max_talking_duration_seconds <= 60:
        raise VideoConfigError("max_talking_duration_seconds must be within 1..60")
    raw_providers = data.get("providers")
    if not isinstance(raw_providers, Mapping):
        raise VideoConfigError("providers must be a mapping")
    parsed: dict[str, ProviderDefinition] = {}
    for name, raw in raw_providers.items():
        if not isinstance(raw, Mapping):
            raise VideoConfigError(f"provider {name} must be a mapping")
        responsibility = str(raw.get("responsibility") or "")
        if responsibility not in {"talking", "motion", "voice"}:
            raise VideoConfigError(f"provider {name} has invalid responsibility")
        parsed[str(name)] = ProviderDefinition(str(name), responsibility, dict(raw))
    for required in ("heygen", "heygen_voice", "runway", "runway_talking"):
        if required not in parsed:
            raise VideoConfigError(f"missing provider capability record: {required}")
    return limits, parsed


def _validate_voice_provider_configuration(
    profile: VoiceProfile, providers: Mapping[str, ProviderDefinition]
) -> None:
    if profile.mode != "cloned_voice" or profile.approval_status not in USABLE_VOICE_APPROVALS:
        return
    definition = providers.get(str(profile.provider or ""))
    if definition is None or definition.responsibility != "voice":
        raise VideoConfigError("approved cloned voice provider is not configured for voice work")
    configured_model = str(definition.settings.get("model") or "")
    if not configured_model or profile.model != configured_model:
        raise VideoConfigError("approved cloned voice model is not supported by its provider")
    if profile.output_format != "wav":
        raise VideoConfigError("approved cloned voice output_format must be wav")
    if profile.speed is not None and not 0.5 <= profile.speed <= 2.0:
        raise VideoConfigError("approved cloned voice speed must be within 0.5..2.0")


def _parse_presets(
    data: Mapping[str, Any],
    providers: Mapping[str, ProviderDefinition],
    limits: SafetyLimits,
) -> dict[str, VideoPreset]:
    defaults = data.get("defaults")
    raw_presets = data.get("presets")
    if not isinstance(defaults, Mapping) or not isinstance(raw_presets, Mapping):
        raise VideoConfigError("video preset defaults and presets must be mappings")
    result: dict[str, VideoPreset] = {}
    for name in REQUIRED_PRESETS:
        raw = raw_presets.get(name)
        if not isinstance(raw, Mapping):
            raise VideoConfigError(f"missing video preset: {name}")
        talking_provider = str(raw.get("talking_provider") or "")
        motion_provider = str(raw.get("motion_provider") or "")
        if talking_provider not in providers or providers[talking_provider].responsibility != "talking":
            raise VideoConfigError(f"preset {name} has unsupported talking provider")
        if motion_provider not in providers or providers[motion_provider].responsibility != "motion":
            raise VideoConfigError(f"preset {name} has unsupported motion provider")
        talking_model = str(raw.get("talking_model") or "")
        motion_model = str(raw.get("motion_model") or "")
        talking_settings = providers[talking_provider].settings
        motion_settings = providers[motion_provider].settings
        if talking_provider == "heygen" and talking_model != str(talking_settings.get("model") or ""):
            raise VideoConfigError(f"preset {name} has unsupported HeyGen talking model")
        if talking_provider == "runway_talking" and talking_model != str(
            talking_settings.get("model") or ""
        ):
            raise VideoConfigError(f"preset {name} has unsupported Runway talking model")
        supported_motion = motion_settings.get("supported_models")
        motion_capability = (
            supported_motion.get(motion_model)
            if isinstance(supported_motion, Mapping)
            else None
        )
        if not isinstance(motion_capability, Mapping):
            raise VideoConfigError(f"preset {name} has unsupported motion model")
        talking_variations = _bounded_int(
            defaults.get("talking_shot_variations"), "talking shot variations", 1,
            limits.max_talking_variations_per_shot,
        )
        motion_variations = _bounded_int(
            defaults.get("broll_variations"), "B-roll variations", 1,
            limits.max_motion_variations_per_shot,
        )
        edit_variations = _bounded_int(
            defaults.get("final_edit_variations"), "final edit variations", 1,
            limits.max_final_edits_per_video,
        )
        raw_shots = raw.get("shots")
        if not isinstance(raw_shots, list) or not raw_shots:
            raise VideoConfigError(f"preset {name} shots must be a non-empty list")
        shots: list[ShotTemplate] = []
        seen: set[str] = set()
        for raw_shot in raw_shots:
            if not isinstance(raw_shot, Mapping):
                raise VideoConfigError(f"preset {name} shot must be a mapping")
            shot_id = str(raw_shot.get("id") or "")
            kind = str(raw_shot.get("kind") or "")
            if not shot_id or shot_id in seen:
                raise VideoConfigError(f"preset {name} has missing or duplicate shot id: {shot_id}")
            if kind not in SUPPORTED_SHOT_KINDS:
                raise VideoConfigError(f"preset {name} shot {shot_id} has invalid kind")
            prompt_value = raw_shot.get("prompt")
            prompt_file = Path(str(prompt_value)) if prompt_value else None
            if kind in {"talking", "motion"} and prompt_file is None:
                raise VideoConfigError(f"preset {name} shot {shot_id} requires a prompt")
            duration = raw_shot.get("duration_seconds")
            shots.append(
                ShotTemplate(
                    shot_id=shot_id,
                    kind=kind,
                    source_role=str(raw_shot.get("source_role") or ""),
                    prompt_file=prompt_file,
                    duration_seconds=float(duration) if duration is not None else None,
                    optional=raw_shot.get("optional") is True,
                )
            )
            seen.add(shot_id)
        if not any(shot.kind == "talking" for shot in shots):
            raise VideoConfigError(f"preset {name} must include at least one talking shot")
        result[name] = VideoPreset(
            name=name,
            script_id=str(raw.get("script") or ""),
            aspect_ratio=str(raw.get("aspect_ratio") or defaults.get("aspect_ratio") or ""),
            resolution=str(raw.get("resolution") or defaults.get("resolution") or ""),
            frame_rate=_bounded_int(
                raw.get("frame_rate", defaults.get("frame_rate")), "frame rate", 1, 120
            ),
            talking_provider=talking_provider,
            talking_model=talking_model,
            motion_provider=motion_provider,
            motion_model=motion_model,
            alternate_takes=_bounded_int(raw.get("alternate_takes"), "alternate takes", 1, 3),
            talking_shot_variations=talking_variations,
            broll_variations=motion_variations,
            final_edit_variations=edit_variations,
            single_shot_fallback=bool(defaults.get("single_shot_fallback", True)),
            shots=tuple(shots),
        )
        if result[name].resolution not in {
            str(value) for value in motion_capability.get("ratios", [])
        }:
            raise VideoConfigError(f"preset {name} resolution is unsupported by its motion model")
        if (
            talking_provider == "heygen"
            and (result[name].aspect_ratio != "16:9" or result[name].resolution != "1280:720")
        ):
            raise VideoConfigError(f"preset {name} output is unsupported by HeyGen MVP")
    return result


def _validate_script_audio_links(
    profile: VoiceProfile, scripts: Mapping[str, Any], blockers: list[str]
) -> None:
    if profile.approval_status not in USABLE_VOICE_APPROVALS:
        return
    required = REQUIRED_PRESETS if profile.mode == "approved_audio" else tuple(profile.script_audio)
    for script_id in required:
        mapping = profile.script_audio.get(script_id)
        if not isinstance(mapping, Mapping):
            blockers.append(f"approved WAV mapping is missing for {script_id}")
            continue
        if script_id in scripts and mapping.get("script_sha256") != scripts[script_id].sha256:
            raise VideoConfigError(f"approved WAV script hash mismatch for {script_id}")


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise VideoConfigError(f"{name} must be an integer") from exc
    if isinstance(value, bool) or not minimum <= parsed <= maximum:
        raise VideoConfigError(f"{name} must be within {minimum}..{maximum}")
    return parsed


def _optional_str(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)


def _optional_float(value: Any, name: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise VideoConfigError(f"{name} must be numeric or null") from exc


def _optional_int(value: Any, name: str) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise VideoConfigError(f"{name} must be an integer or null") from exc
    if parsed <= 0:
        raise VideoConfigError(f"{name} must be positive")
    return parsed
