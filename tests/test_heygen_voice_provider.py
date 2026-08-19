from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from lala_workflow.audio.validation import inspect_wav
from lala_workflow.providers.base import ProviderSubmissionError, ProviderValidationError
from lala_workflow.providers.heygen_voice import HeyGenVoiceProvider
from lala_workflow.video.config import load_video_config
from lala_workflow.video.domain import VoiceRequest


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class Client:
    def __init__(self):
        self.posts = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return Response(
            {
                "data": {
                    "audio_url": "https://files.heygen.test/generated.wav?signature=private",
                    "duration": 10,
                    "request_id": "voice-request-123",
                }
            }
        )


class FailingClient:
    def post(self, _url, **_kwargs):
        raise RuntimeError("request rejected for local-test-secret")


def make_request(root: Path) -> VoiceRequest:
    script_path = root / "assets/scripts/tooltip.txt"
    content = script_path.read_bytes()
    return VoiceRequest(
        request_id="RUN-VOICE-tooltip-voice",
        run_id="RUN-VOICE",
        preset="tooltip",
        script_path=script_path,
        script_content=content,
        script_sha256=hashlib.sha256(content).hexdigest(),
        provider="heygen_voice",
        model="starfish",
        voice_id="approved-private-voice-id",
        language="en",
        speed=1.1,
        output_path=root / "outputs/audio/RUN-VOICE/tooltip.wav",
        output_format="wav",
        sample_rate=8000,
        timeout_seconds=30,
        max_retries=2,
    )


def test_translates_exact_script_and_downloads_pcm_wav(
    video_project_root: Path,
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    client = Client()
    source_wav = video_project_root / "assets/voice/approved/tooltip.wav"
    downloads = []

    def downloader(url: str, destination: Path, _timeout: float) -> None:
        downloads.append(url)
        shutil.copyfile(source_wav, destination)

    provider = HeyGenVoiceProvider(
        config.providers["heygen_voice"],
        api_key="local-test-secret",
        client=client,
        downloader=downloader,
    )
    request = make_request(video_project_root)
    artifact = provider.synthesize(request)

    url, kwargs = client.posts[0]
    assert url.endswith("/v3/voices/speech")
    assert kwargs["json"] == {
        "text": request.script_content.decode("utf-8"),
        "voice_id": "approved-private-voice-id",
        "input_type": "text",
        "speed": 1.1,
        "language": "en",
    }
    assert kwargs["headers"] == {"x-api-key": "local-test-secret"}
    assert downloads == ["https://files.heygen.test/generated.wav?signature=private"]
    assert artifact.path == request.output_path
    assert artifact.mime_type == "audio/wav"
    assert artifact.provenance["submission_policy"] == "single_submit_no_automatic_replay"
    assert "idempotency_key" not in artifact.provenance
    assert artifact.provider_task_id == "voice-request-123"
    assert artifact.source_url_redacted == "https://files.heygen.test/generated.wav"
    assert artifact.provenance["reported_duration_seconds"] == 10
    assert inspect_wav(artifact.path).sample_rate == 8000


def test_rejects_script_bytes_that_do_not_match_path_or_digest(
    video_project_root: Path,
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = HeyGenVoiceProvider(
        config.providers["heygen_voice"],
        api_key="local-test-secret",
        client=Client(),
        downloader=lambda *_args: None,
    )
    request = make_request(video_project_root)
    changed = VoiceRequest(
        **{
            field: getattr(request, field)
            for field in request.__dataclass_fields__
            if field != "script_content"
        },
        script_content=request.script_content + b"changed",
    )
    with pytest.raises(ProviderValidationError, match="script bytes"):
        provider.validate_request(changed)


def test_redacts_credential_from_submission_failure(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = HeyGenVoiceProvider(
        config.providers["heygen_voice"],
        api_key="local-test-secret",
        client=FailingClient(),
        downloader=lambda *_args: None,
    )

    with pytest.raises(ProviderSubmissionError) as captured:
        provider.synthesize(make_request(video_project_root))

    assert "local-test-secret" not in str(captured.value)
    assert "[REDACTED]" in str(captured.value)
