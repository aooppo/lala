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


SYNTHETIC_SIGNED_AUDIO_URL = "https://files.heygen.test/generated.wav?" + "signature=private"
SYNTHETIC_SIGNED_MALFORMED_URL = "https://files.heygen.test/audio.wav?" + "signature=private"


class Response:
    def __init__(self, payload, *, status_code=200, content_type="application/json"):
        self.payload = payload
        self.status_code = status_code
        self.headers = {"content-type": content_type}

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
                    "audio_url": SYNTHETIC_SIGNED_AUDIO_URL,
                    "duration": 10,
                    "request_id": "voice-request-123",
                }
            }
        )


class FailingClient:
    def post(self, _url, **_kwargs):
        raise RuntimeError("request rejected for local-test-secret")


class PayloadClient:
    def __init__(self, payload):
        self.payload = payload

    def post(self, _url, **_kwargs):
        return Response(self.payload)


class MalformedResponse(Response):
    def json(self):
        raise ValueError(
            f"malformed {SYNTHETIC_SIGNED_MALFORMED_URL} "
            "local-test-secret"
        )


class MalformedClient:
    def post(self, _url, **_kwargs):
        return MalformedResponse(None)


class HttpErrorResponse(Response):
    def raise_for_status(self):
        raise RuntimeError(
            "local-test-secret " + SYNTHETIC_SIGNED_AUDIO_URL
        )


class HttpErrorClient:
    def post(self, _url, **_kwargs):
        return HttpErrorResponse(
            {"error": "not exposed"},
            status_code=503,
            content_type="application/problem+json",
        )


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
    assert downloads == [SYNTHETIC_SIGNED_AUDIO_URL]
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


@pytest.mark.parametrize(
    ("data", "request_id_present"),
    (
        (
            {
                "audio_url": SYNTHETIC_SIGNED_AUDIO_URL,
                "duration": 10,
                "request_id": None,
            },
            True,
        ),
        (
            {
                "audio_url": SYNTHETIC_SIGNED_AUDIO_URL,
                "duration": 10,
            },
            False,
        ),
    ),
)
def test_accepts_optional_request_id_without_fabricating_one(
    video_project_root: Path,
    data: dict[str, object],
    request_id_present: bool,
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    source_wav = video_project_root / "assets/voice/approved/tooltip.wav"

    def downloader(_url: str, destination: Path, _timeout: float) -> None:
        shutil.copyfile(source_wav, destination)

    provider = HeyGenVoiceProvider(
        config.providers["heygen_voice"],
        api_key="local-test-secret",
        client=PayloadClient({"data": data}),
        downloader=downloader,
    )

    artifact = provider.synthesize(make_request(video_project_root))

    assert artifact.provider_task_id is None
    assert artifact.provenance["provider_request_id"] is None
    assert artifact.provenance["provider_request_id_present"] is request_id_present
    assert artifact.source_url_redacted == "https://files.heygen.test/generated.wav"
    assert "signature=" not in str(artifact.provenance)


def test_rejects_missing_audio_url_with_safe_response_shape(
    video_project_root: Path,
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = HeyGenVoiceProvider(
        config.providers["heygen_voice"],
        api_key="local-test-secret",
        client=PayloadClient(
            {
                "data": {
                    "request_id": "voice-request-123",
                    "duration": 10,
                    "message": (
                        "local-test-secret " + SYNTHETIC_SIGNED_AUDIO_URL
                    ),
                }
            }
        ),
        downloader=lambda *_args: None,
    )

    with pytest.raises(ProviderSubmissionError) as captured:
        provider.synthesize(make_request(video_project_root))

    message = str(captured.value)
    assert "missing audio_url" in message
    assert "http_status=200" in message
    assert "content_type=application/json" in message
    assert "request_id=string" in message
    assert "local-test-secret" not in message
    assert "signature=private" not in message


def test_rejects_missing_data_with_safe_response_shape(
    video_project_root: Path,
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = HeyGenVoiceProvider(
        config.providers["heygen_voice"],
        api_key="local-test-secret",
        client=PayloadClient({"status": "ok"}),
        downloader=lambda *_args: None,
    )

    with pytest.raises(ProviderSubmissionError) as captured:
        provider.synthesize(make_request(video_project_root))

    message = str(captured.value)
    assert "missing data object" in message
    assert "data=missing" in message
    assert "http_status=200" in message


def test_rejects_malformed_json_without_leaking_response_details(
    video_project_root: Path,
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = HeyGenVoiceProvider(
        config.providers["heygen_voice"],
        api_key="local-test-secret",
        client=MalformedClient(),
        downloader=lambda *_args: None,
    )

    with pytest.raises(ProviderSubmissionError) as captured:
        provider.synthesize(make_request(video_project_root))

    message = str(captured.value)
    assert "malformed JSON" in message
    assert "http_status=200" in message
    assert "content_type=application/json" in message
    assert "local-test-secret" not in message
    assert "signature=private" not in message


def test_reports_http_provider_error_without_leaking_response_details(
    video_project_root: Path,
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = HeyGenVoiceProvider(
        config.providers["heygen_voice"],
        api_key="local-test-secret",
        client=HttpErrorClient(),
        downloader=lambda *_args: None,
    )

    with pytest.raises(ProviderSubmissionError) as captured:
        provider.synthesize(make_request(video_project_root))

    message = str(captured.value)
    assert "HTTP/provider error" in message
    assert "http_status=503" in message
    assert "content_type=application/problem+json" in message
    assert "local-test-secret" not in message
    assert "signature=private" not in message
