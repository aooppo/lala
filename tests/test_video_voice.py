from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import yaml
import json

from lala_workflow.hashing import sha256_file
from lala_workflow.video.config import load_video_config
from lala_workflow.video.domain import MediaArtifact
from lala_workflow.video.voice import resolve_or_synthesize_audio
from lala_workflow.providers.heygen_voice import HeyGenVoiceProvider
from lala_workflow.video.runner import VideoRunOptions, _create_voice_provider, preview_video
from tests.fakes_video import FakeVoiceProvider


def test_approved_wav_bypasses_voice_provider(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    script = config.scripts["tooltip"]
    resolved = resolve_or_synthesize_audio(config, script, run_id="RUN-1", provider=None)
    assert resolved.path == Path("assets/voice/approved/tooltip.wav")
    assert resolved.script_sha256 == script.sha256


def test_script_matched_approved_wav_is_preferred_in_cloned_voice_mode(
    video_project_root: Path,
) -> None:
    profile_path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "mode": "cloned_voice",
            "provider": "heygen_voice",
            "model": "starfish",
            "voice_id": "approved-voice-id",
        }
    )
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    config = load_video_config(video_project_root, require_inputs=True)
    script = config.scripts["tooltip"]
    provider = FakeVoiceProvider(
        MediaArtifact(
            artifact_id="must-not-run",
            kind="audio",
            path=video_project_root / "not-used.wav",
            sha256="0" * 64,
            size_bytes=0,
            mime_type="audio/wav",
        )
    )
    resolved = resolve_or_synthesize_audio(
        config, script, run_id="RUN-PREFER-WAV", provider=provider
    )
    preview = preview_video(
        video_project_root, VideoRunOptions(preset="tooltip", action="generate")
    )
    assert resolved.path == Path("assets/voice/approved/tooltip.wav")
    assert provider.requests == []
    assert preview.provider_call_count == 3


def test_approved_cloned_voice_synthesizes_to_derived_audio(
    video_project_root: Path,
) -> None:
    profile_path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "mode": "cloned_voice",
            "provider": "heygen_voice",
            "model": "starfish",
            "voice_id": "approved-fake-voice",
            "script_audio": {},
        }
    )
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    config = load_video_config(video_project_root, require_inputs=True)
    script = config.scripts["tooltip"]
    output = video_project_root / "outputs/audio/RUN-VOICE/tooltip.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(video_project_root / "assets/voice/approved/tooltip.wav", output)
    artifact = MediaArtifact(
        artifact_id="voice-tooltip",
        kind="audio",
        path=output,
        sha256=sha256_file(output),
        size_bytes=output.stat().st_size,
        mime_type="audio/wav",
    )
    provider = FakeVoiceProvider(artifact)
    resolved = resolve_or_synthesize_audio(
        config, script, run_id="RUN-VOICE", provider=provider
    )
    assert len(provider.requests) == 1
    assert resolved.path == Path("outputs/audio/RUN-VOICE/tooltip.wav")
    assert resolved.sha256 == sha256_file(output)
    assert resolved.script_sha256 == script.sha256


def test_cloned_voice_dry_run_plans_one_zero_call_synthesis_with_unknown_cost(
    video_project_root: Path,
) -> None:
    profile_path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "mode": "cloned_voice",
            "provider": "heygen_voice",
            "model": "starfish",
            "voice_id": "approved-voice-id",
            "script_audio": {},
        }
    )
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    outcome = preview_video(
        video_project_root, VideoRunOptions(preset="tooltip", action="generate")
    )
    assert outcome.provider_call_count == 4
    assert outcome.submission_count == 0
    audio = json.loads((outcome.run_dir / "audio-hash.json").read_text(encoding="utf-8"))
    cost = json.loads((outcome.run_dir / "cost.json").read_text(encoding="utf-8"))
    assert audio["status"] == "PLANNED_DRY_RUN"
    assert audio["sha256"] is None
    assert cost["voice_cost"] is None
    assert cost["talking_video_cost"] is None
    assert cost["total_provider_cost"] is None


def test_talking_smoke_dry_run_uses_bounded_calibration_cost(
    video_project_root: Path,
) -> None:
    profile_path = video_project_root / "configs/voice-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "mode": "cloned_voice",
            "provider": "heygen_voice",
            "model": "starfish",
            "voice_id": "approved-voice-id",
            "script_audio": {},
        }
    )
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    outcome = preview_video(
        video_project_root,
        VideoRunOptions(
            preset="tooltip",
            action="talking_smoke",
            talking_variations=1,
            max_provider_cost_usd=1.0,
        ),
    )
    request = json.loads(
        (outcome.run_dir / "request.json").read_text(encoding="utf-8")
    )
    cost = json.loads((outcome.run_dir / "cost.json").read_text(encoding="utf-8"))

    assert outcome.submission_count == 0
    assert request["budget"]["accept_unknown_provider_cost"] is False
    assert request["budget"]["estimated_provider_cost_usd"] == 0.624012
    assert cost["total_provider_cost"] == 0.624012


def test_live_factory_constructs_configured_heygen_voice_adapter(
    video_project_root: Path,
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = _create_voice_provider(
        config, "heygen_voice", {"HEYGEN_API_KEY": "local-test-key"}
    )
    assert isinstance(provider, HeyGenVoiceProvider)
    assert provider.definition.responsibility == "voice"
