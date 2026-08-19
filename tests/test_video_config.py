from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from lala_workflow.audio.validation import inspect_wav
from lala_workflow.video.config import VideoConfigError, load_video_config
from lala_workflow.video.prompts import load_video_prompt
from lala_workflow.video.validation import ExternalInputBlocked


def test_loads_all_approved_sources_presets_and_bounds(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    assert set(config.scripts) == {"product_page", "tooltip", "homepage"}
    assert set(config.keyframes) == {"hero"}
    assert set(config.presets) == {"product_page", "tooltip", "homepage"}
    assert config.limits.max_concurrency == 1
    assert config.limits.max_retries == 2
    assert config.input_blockers == ()


def test_repository_imported_inputs_have_owner_voice_smoke_verification() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_video_config(root, require_inputs=True)
    assert config.voice_profile.approval_status == "approved_for_smoke"
    assert (config.voice_profile.verification_run_id or "").startswith("LALA-VOICE-VERIFY-")
    assert config.voice_profile.engine == "starfish"


def test_preset_limit_above_owner_bound_is_rejected(video_project_root: Path) -> None:
    path = video_project_root / "configs/video-presets.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["defaults"]["talking_shot_variations"] = 4
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(VideoConfigError, match="1..3"):
        load_video_config(video_project_root, require_inputs=True)


def test_changed_script_digest_is_rejected(video_project_root: Path) -> None:
    path = video_project_root / "assets/scripts/tooltip.txt"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(VideoConfigError, match="digest mismatch"):
        load_video_config(video_project_root, require_inputs=True)


def test_script_authoritative_source_reference_is_required(
    video_project_root: Path,
) -> None:
    path = video_project_root / "configs/script-manifest.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["scripts"]["tooltip"].pop("source_reference")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ExternalInputBlocked, match="source_reference"):
        load_video_config(video_project_root, require_inputs=True)


def test_preset_provider_model_and_resolution_must_match_verified_capability(
    video_project_root: Path,
) -> None:
    path = video_project_root / "configs/video-presets.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["presets"]["homepage"]["motion_model"] = "invented-model"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(VideoConfigError, match="unsupported motion model"):
        load_video_config(video_project_root, require_inputs=True)


def test_cloned_voice_requires_a_configured_voice_provider_model(
    video_project_root: Path,
) -> None:
    path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    profile.update(
        {
            "mode": "cloned_voice",
            "provider": "missing_voice_provider",
            "model": "invented-model",
            "voice_id": "approved-voice-id",
            "script_audio": {},
            "verification_run_id": "synthetic-verification-run",
            "verification_time": "2026-08-19T12:00:00+08:00",
            "voice_name": "Synthetic Voice",
            "engine": "starfish",
            "type": "private",
        }
    )
    path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    with pytest.raises(VideoConfigError, match="not configured for voice work"):
        load_video_config(video_project_root, require_inputs=True)


def test_prompt_version_and_hash_are_resolved(video_project_root: Path) -> None:
    prompt = load_video_prompt(video_project_root, Path("prompts/talking-motion-v1.txt"))
    assert prompt.version == "v1"
    assert len(prompt.sha256) == 64
    assert prompt.text.startswith("Preserve")


def test_canonical_voice_sources_validate_but_do_not_satisfy_voice_approval(
    video_project_root: Path,
) -> None:
    source_root = video_project_root / "assets/voice/source"
    metadata_root = video_project_root / "assets/voice/metadata"
    source_root.mkdir(parents=True, exist_ok=True)
    metadata_root.mkdir(parents=True, exist_ok=True)
    fixture_wav = video_project_root / "assets/voice/approved/tooltip.wav"
    info = inspect_wav(fixture_wav)
    clips = []
    for index in range(8):
        destination = source_root / f"canonical-{index:02d}.wav"
        shutil.copyfile(fixture_wav, destination)
        clips.append(
            {
                "path": f"assets/voice/source/{destination.name}",
                "source_path": f"03_voice/canonical_source/{destination.name}",
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "bytes": destination.stat().st_size,
                "codec": "pcm_s16le",
                "sample_rate_hz": info.sample_rate,
                "channels": info.channels,
                "duration_seconds": info.duration_seconds,
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "role": "canonical Lady LaLa voice-cloning source material",
        "status": "source_material_ready_profile_or_per_script_audio_still_required",
        "source_package": {
            "name": "synthetic-owner-inputs.zip",
            "sha256": "b" * 64,
            "manifest_path": "04_provenance/manifests/voice-manifest.json",
            "manifest_sha256": "c" * 64,
        },
        "clips": clips,
        "total_duration_seconds": info.duration_seconds * 8,
        "acceptance_rule": "source material only; not per-script narration",
    }
    manifest_path = metadata_root / "canonical-source-manifest-v1.0.0.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    profile_path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "voice_version": None,
            "mode": "pending",
            "provider": None,
            "model": None,
            "voice_id": None,
            "source_audio": None,
            "approved_audio": None,
            "script_audio": {},
            "approval_status": "pending",
            "canonical_source_manifest": (
                "assets/voice/metadata/canonical-source-manifest-v1.0.0.json"
            ),
            "canonical_source_manifest_sha256": hashlib.sha256(
                manifest_path.read_bytes()
            ).hexdigest(),
        }
    )
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")

    config = load_video_config(video_project_root)

    assert len(config.voice_profile.canonical_sources) == 8
    assert config.voice_profile.script_audio == {}
    assert config.input_blockers == (
        "Goal 2 still requires a real approved HeyGen Starfish/private Lady LaLa voice "
        "profile or approved per-script Lady LaLa narration WAVs.",
    )
    with pytest.raises(ExternalInputBlocked, match="real approved HeyGen Starfish"):
        load_video_config(video_project_root, require_inputs=True)


def test_canonical_voice_source_digest_mismatch_is_rejected(
    video_project_root: Path,
) -> None:
    source_root = video_project_root / "assets/voice/source"
    metadata_root = video_project_root / "assets/voice/metadata"
    source_root.mkdir(parents=True, exist_ok=True)
    metadata_root.mkdir(parents=True, exist_ok=True)
    source = source_root / "canonical.wav"
    shutil.copyfile(video_project_root / "assets/voice/approved/tooltip.wav", source)
    info = inspect_wav(source)
    manifest = {
        "schema_version": "1.0.0",
        "role": "canonical Lady LaLa voice-cloning source material",
        "status": "source_material_ready_profile_or_per_script_audio_still_required",
        "source_package": {
            "name": "synthetic-owner-inputs.zip",
            "sha256": "b" * 64,
            "manifest_path": "04_provenance/manifests/voice-manifest.json",
            "manifest_sha256": "c" * 64,
        },
        "clips": [
            {
                "path": "assets/voice/source/canonical.wav",
                "source_path": "03_voice/canonical_source/canonical.wav",
                "sha256": "0" * 64,
                "bytes": source.stat().st_size,
                "codec": "pcm_s16le",
                "sample_rate_hz": info.sample_rate,
                "channels": info.channels,
                "duration_seconds": info.duration_seconds,
            }
        ],
        "total_duration_seconds": info.duration_seconds,
        "acceptance_rule": "source material only; not per-script narration",
    }
    manifest_path = metadata_root / "canonical-source-manifest-v1.0.0.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    profile_path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "mode": "pending",
            "approval_status": "pending",
            "script_audio": {},
            "canonical_source_manifest": (
                "assets/voice/metadata/canonical-source-manifest-v1.0.0.json"
            ),
            "canonical_source_manifest_sha256": hashlib.sha256(
                manifest_path.read_bytes()
            ).hexdigest(),
        }
    )
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")

    with pytest.raises(VideoConfigError, match="canonical voice source digest mismatch"):
        load_video_config(video_project_root)
