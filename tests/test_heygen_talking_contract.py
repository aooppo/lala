from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import httpx

from lala_workflow.providers.heygen_talking import HeyGenTalkingProvider
from lala_workflow.video.config import load_video_config
from lala_workflow.video.domain import VideoTaskStatus
from tests.test_heygen_talking_provider import make_request


def test_httpx_transport_captures_real_multipart_idempotency_and_asset_reuse(
    video_project_root: Path,
) -> None:
    uploads: list[httpx.Request] = []
    videos: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v3/assets":
            uploads.append(request)
            return httpx.Response(
                200,
                json={"data": {"asset_id": f"asset-{len(uploads)}"}},
                request=request,
            )
        if request.url.path == "/v3/videos":
            videos.append(request)
            return httpx.Response(
                200,
                json={"data": {"video_id": f"video-{len(videos)}"}},
                request=request,
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = load_video_config(video_project_root, require_inputs=True)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = HeyGenTalkingProvider(
            config.providers["heygen"], api_key="contract-secret", client=client
        )
        first = make_request(video_project_root)
        second = replace(first, request_id="tooltip-message-v002", variation=2)
        assert provider.submit(first) == "video-1"
        assert provider.submit(second) == "video-2"

    assert len(uploads) == 2
    assert len(videos) == 2
    for request in uploads:
        content_type = request.headers["content-type"]
        assert content_type.startswith("multipart/form-data; boundary=")
        body = request.content
        assert b'name="file"' in body
        assert b"filename=" in body
        assert b"Content-Type: image/png" in body or b"Content-Type: audio/wav" in body
        assert request.headers["idempotency-key"]
        assert len(request.headers["idempotency-key"]) <= 255
        assert len([name for name, _ in request.headers.raw if name.lower() == b"x-api-key"]) == 1
    assert videos[0].headers["idempotency-key"] != videos[1].headers["idempotency-key"]


def test_httpx_transport_reuses_key_for_bounded_409_and_reads_failure_fields(
    video_project_root: Path,
) -> None:
    keys: list[str] = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v3/assets":
            return httpx.Response(200, json={"data": {"asset_id": "asset"}}, request=request)
        if request.method == "POST" and request.url.path == "/v3/videos":
            keys.append(request.headers["idempotency-key"])
            if len(keys) == 1:
                return httpx.Response(
                    409,
                    headers={"Retry-After": "2"},
                    json={"code": "request_in_progress"},
                    request=request,
                )
            return httpx.Response(200, json={"data": {"video_id": "video-1"}}, request=request)
        if request.method == "GET" and request.url.path == "/v3/videos/video-1":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "status": "failed",
                        "failure_code": "avatar_rejected",
                        "failure_message": "safe failure detail",
                    }
                },
                request=request,
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = load_video_config(video_project_root, require_inputs=True)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = HeyGenTalkingProvider(
            config.providers["heygen"],
            api_key="contract-secret",
            client=client,
            sleep=sleeps.append,
        )
        assert provider.submit(make_request(video_project_root)) == "video-1"
        result = provider.wait("video-1", 10)
    assert keys[0] == keys[1]
    assert sleeps == [2.0]
    assert result.status is VideoTaskStatus.FAILED
    assert result.error_code == "avatar_rejected"
    assert result.error_message == "safe failure detail"
