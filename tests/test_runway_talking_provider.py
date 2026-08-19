from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from lala_workflow.providers.runway_talking import RunwayTalkingProvider
from lala_workflow.providers.base import ProviderValidationError
from lala_workflow.video.config import load_video_config
from lala_workflow.video.domain import ProviderDefinition
from lala_workflow.video.voice import resolve_approved_audio
from tests.test_heygen_talking_provider import make_request


class AvatarVideos:
    def __init__(self):
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(id="runway-avatar-task")


def test_runway_talking_requires_approved_custom_avatar_mapping(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    request = replace(make_request(video_project_root), provider="runway_talking", model="gwm1_avatars")
    settings = dict(config.providers["runway_talking"].settings)
    settings["approved_custom_avatars"] = {
        request.keyframe_sha256: "123e4567-e89b-12d3-a456-426614174000"
    }
    definition = ProviderDefinition("runway_talking", "talking", settings)
    client = SimpleNamespace(avatar_videos=AvatarVideos())
    provider = RunwayTalkingProvider(definition, api_key="local-test-secret", client=client)

    payload = provider.translate_request(request)
    assert payload["model"] == "gwm1_avatars"
    assert payload["avatar"] == {
        "type": "custom",
        "avatarId": "123e4567-e89b-12d3-a456-426614174000",
    }
    assert payload["speech"]["type"] == "audio"
    assert payload["speech"]["audio"].startswith("data:audio/wav;base64,")
    assert provider.submit(request) == "runway-avatar-task"


def test_runway_talking_rejects_unmapped_keyframe(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    request = replace(make_request(video_project_root), provider="runway_talking", model="gwm1_avatars")
    provider = RunwayTalkingProvider(
        config.providers["runway_talking"],
        api_key="local-test-secret",
        client=SimpleNamespace(avatar_videos=AvatarVideos()),
    )
    with pytest.raises(ProviderValidationError, match="approved custom avatar"):
        provider.translate_request(request)
