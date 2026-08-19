from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import yaml

from lala_workflow.providers.base import ProviderValidationError
from lala_workflow.providers.heygen_voice import (
    HeyGenVoiceVerification,
    HeyGenVoiceVerifier,
)
from lala_workflow.video.config import VideoConfigError, load_video_config
from lala_workflow.video.domain import ProviderDefinition
from lala_workflow.video.voice_verification import (
    EXPECTED_VOICE_ID,
    download_owner_voice_preview,
    verify_owner_voice,
)


def _definition() -> ProviderDefinition:
    return ProviderDefinition(
        name="heygen_voice",
        responsibility="voice",
        settings={
            "api_base_url": "https://api.heygen.test",
            "detail_endpoint": "/v3/voices/{voice_id}",
            "list_endpoint": "/v3/voices",
        },
    )


def test_voice_verifier_uses_only_read_requests_and_strips_preview_query() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith(EXPECTED_VOICE_ID):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "voice_id": EXPECTED_VOICE_ID,
                        "name": "Lady LaLa v1",
                        "gender": "female",
                        "language": "English",
                        "created_at": 1_700_000_000,
                        "preview_audio_url": "https://files.heygen.test/lala.mp3?token=secret",
                    }
                },
            )
        assert request.url.params.get("type") == "private"
        assert request.url.params.get("engine") == "starfish"
        assert request.url.params.get("limit") == "100"
        return httpx.Response(
            200,
            json={
                "data": [{"voice_id": EXPECTED_VOICE_ID, "name": "Lady LaLa v1"}],
                "has_more": False,
                "next_token": None,
            },
        )

    verifier = HeyGenVoiceVerifier(
        _definition(),
        api_key="test-secret",
        client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    result = verifier.verify(EXPECTED_VOICE_ID, expected_name="Lady LaLa v1")

    assert result.engine == "starfish"
    assert result.voice_type == "private"
    assert result.preview_url_safe == "https://files.heygen.test/lala.mp3"
    assert requests and all(request.method == "GET" for request in requests)
    assert all(request.headers.get("x-api-key") == "test-secret" for request in requests)


def test_voice_verifier_rejects_name_mismatch_before_list_lookup() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"data": {"voice_id": EXPECTED_VOICE_ID, "name": "Different Voice"}},
        )

    verifier = HeyGenVoiceVerifier(
        _definition(),
        api_key="test-secret",
        client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    with pytest.raises(ProviderValidationError, match="name mismatch"):
        verifier.verify(EXPECTED_VOICE_ID, expected_name="Lady LaLa v1")
    assert len(requests) == 1


class _Verifier:
    def verify(self, voice_id: str, *, expected_name: str) -> HeyGenVoiceVerification:
        assert voice_id == EXPECTED_VOICE_ID
        assert expected_name == "Lady LaLa v1"
        return HeyGenVoiceVerification(
            voice_id=voice_id,
            name=expected_name,
            gender="female",
            language="English",
            engine="starfish",
            voice_type="private",
            created_at="2023-11-14T22:13:20+00:00",
            preview_url_safe="https://files.heygen.test/lala.wav",
        )

    def preview_url(self, voice_id: str, *, expected_name: str) -> str:
        assert voice_id == EXPECTED_VOICE_ID
        assert expected_name == "Lady LaLa v1"
        return "https://files.heygen.test/lala.wav?signature=must-not-persist"


def _write_owner_profile(root: Path, *, approval_status: str = "pending") -> None:
    payload = {
        "voice_version": "lady-lala-v1",
        "mode": "cloned_voice",
        "provider": "heygen_voice",
        "model": "starfish",
        "voice_id": EXPECTED_VOICE_ID,
        "source_audio": None,
        "approved_audio": None,
        "canonical_source_manifest": None,
        "canonical_source_manifest_sha256": None,
        "script_audio": {},
        "language": None,
        "locale": None,
        "gender": None,
        "engine": None,
        "type": None,
        "created_at": None,
        "voice_name": "Lady LaLa v1",
        "accent": None,
        "speed": None,
        "style": None,
        "stability": None,
        "similarity": None,
        "output_format": "wav",
        "sample_rate": 48000,
        "approval_status": approval_status,
        "owner_supplied_voice_id": True,
        "verification_run_id": None,
        "verification_time": None,
        "profile_version": "lady-lala-v1",
        "approval_scope": "verification_only",
        "owner_reference": "synthetic test owner reference",
    }
    (root / "configs/voice-profile.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
    )


def test_verification_writes_only_safe_metadata_and_no_quality_approval(
    video_project_root: Path,
) -> None:
    _write_owner_profile(video_project_root)
    result = verify_owner_voice(
        video_project_root,
        voice_id=EXPECTED_VOICE_ID,
        environ={"HEYGEN_API_KEY": "must-not-persist", "HEYGEN_VOICE_ID": EXPECTED_VOICE_ID},
        verifier=_Verifier(),
        now=datetime(2026, 8, 19, 8, 0, tzinfo=UTC),
    )
    assert result["status"] == "VERIFIED_FOR_SMOKE"
    assert result["production_approved"] is False
    evidence = json.loads(
        (video_project_root / "outputs/audio/voice_verification" / result["run_id"] / "verification.json").read_text()
    )
    serialized = json.dumps(evidence)
    assert "must-not-persist" not in serialized
    assert "signature=" not in serialized


def test_preview_download_is_derived_validated_and_separate_from_review(
    video_project_root: Path,
) -> None:
    _write_owner_profile(video_project_root)
    source = video_project_root / "assets/voice/approved/tooltip.wav"

    def copy_preview(_url: str, destination: Path, _timeout: float) -> None:
        destination.write_bytes(source.read_bytes())

    result = download_owner_voice_preview(
        video_project_root,
        voice_id=EXPECTED_VOICE_ID,
        verifier=_Verifier(),
        downloader=copy_preview,
        now=datetime(2026, 8, 19, 8, 1, tzinfo=UTC),
    )
    target_dir = video_project_root / "outputs/audio/voice_preview" / result["run_id"]
    assert (target_dir / "voice-preview.wav").is_file()
    assert (target_dir / "preview.json").is_file()
    assert not (target_dir / "review.csv").exists()
    assert result["duration_seconds"] == pytest.approx(10.0)
    assert result["sample_rate"] == 8000
    assert result["channels"] == 1
    assert "signature=" not in json.dumps(result)


def test_approved_for_smoke_requires_real_verification_evidence(
    video_project_root: Path,
) -> None:
    _write_owner_profile(video_project_root, approval_status="approved_for_smoke")
    with pytest.raises(VideoConfigError, match="verification evidence"):
        load_video_config(video_project_root, require_inputs=False)


def test_voice_cli_exposes_verify_preview_and_explicit_migration_commands() -> None:
    from lala_workflow.cli import build_parser

    parser = build_parser()
    verify = parser.parse_args(
        ["video", "voice", "verify", "--voice-id-env", "HEYGEN_VOICE_ID"]
    )
    preview = parser.parse_args(
        ["video", "voice", "download-preview", "--voice-id", EXPECTED_VOICE_ID]
    )
    init_env = parser.parse_args(["video", "voice", "init-env"])
    assert verify.voice_command == "verify"
    assert preview.voice_command == "download-preview"
    assert init_env.voice_command == "init-env"
