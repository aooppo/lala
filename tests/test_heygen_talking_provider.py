from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from lala_workflow.video.config import load_video_config
from lala_workflow.video.domain import TalkingVideoRequest, VideoTaskStatus
from lala_workflow.video.voice import resolve_approved_audio
from lala_workflow.providers.heygen_talking import HeyGenTalkingProvider


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
        self.gets = []
        self.uploads = 0

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        if url.endswith("/v3/assets"):
            self.uploads += 1
            return Response({"data": {"asset_id": f"asset-{self.uploads}"}})
        return Response({"data": {"video_id": "video-123"}})

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        return Response(
            {"data": {"status": "completed", "video_url": "https://example.test/result.mp4"}}
        )


def make_request(root: Path) -> TalkingVideoRequest:
    config = load_video_config(root, require_inputs=True)
    script = config.scripts["tooltip"]
    audio = resolve_approved_audio(config, script)
    keyframe = config.keyframes["hero"]
    return TalkingVideoRequest(
        request_id="tooltip-message-v001",
        run_id="RUN-1",
        preset="tooltip",
        shot_id="message",
        variation=1,
        provider="heygen",
        model="avatar_iv",
        keyframe_path=root / keyframe.path,
        keyframe_sha256=keyframe.sha256,
        audio_path=root / audio.path,
        audio_sha256=audio.sha256,
        audio_duration_seconds=audio.duration_seconds,
        script_path=root / script.path,
        script_version=script.version,
        script_sha256=script.sha256,
        aspect_ratio="16:9",
        resolution="1280:720",
        prompt_text="subtle motion",
        timeout_seconds=1800,
        max_retries=2,
    )


def test_translates_uploads_and_submits_image_plus_audio(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    client = Client()
    provider = HeyGenTalkingProvider(
        config.providers["heygen"], api_key="local-test-secret", client=client
    )
    request = make_request(video_project_root)

    payload = provider.translate_request(request, "image-asset", "audio-asset")
    assert payload["type"] == "image"
    assert payload["image"] == {"type": "asset_id", "asset_id": "image-asset"}
    assert payload["audio_asset_id"] == "audio-asset"
    assert "audio_url" not in payload

    assert provider.submit(request) == "video-123"
    assert client.uploads == 2
    submit_payload = client.posts[-1][1]["json"]
    assert submit_payload["image"]["asset_id"] == "asset-1"
    assert submit_payload["audio_asset_id"] == "asset-2"
    assert client.posts[0][1]["headers"]["Idempotency-Key"].endswith("-image")


def test_polls_completed_video_without_exposing_sdk_objects(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = HeyGenTalkingProvider(
        config.providers["heygen"], api_key="local-test-secret", client=Client()
    )
    result = provider.wait("video-123", 10)
    assert result.status is VideoTaskStatus.SUCCEEDED
    assert result.provider_task_id == "video-123"
    assert result.output_urls == ("https://example.test/result.mp4",)
