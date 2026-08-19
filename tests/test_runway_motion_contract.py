from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from lala_workflow.providers.base import ProviderValidationError
from lala_workflow.providers.runway_video import RunwayMotionProvider
from lala_workflow.video.config import load_video_config
from lala_workflow.video.domain import VideoTaskStatus
from tests.test_runway_motion_provider import ImageToVideo, make_motion_request


def test_runway_tracks_submit_estimate_and_terminal_actual_credits(
    video_project_root: Path,
) -> None:
    class Tasks:
        def retrieve(self, task_id: str, **_kwargs):
            assert task_id == "motion-task-1"
            return SimpleNamespace(
                status="SUCCEEDED",
                output=["https://example.test/video.mp4?signature=secret"],
                cost=SimpleNamespace(credits=19.5),
            )

    config = load_video_config(video_project_root, require_inputs=True)
    client = SimpleNamespace(image_to_video=ImageToVideo(), tasks=Tasks())
    provider = RunwayMotionProvider(
        config.providers["runway"], api_key="contract-secret", client=client
    )
    task_id = provider.submit(make_motion_request(video_project_root))
    result = provider.wait(task_id, 10)
    assert result.status is VideoTaskStatus.SUCCEEDED
    assert result.estimated_credits == 20
    assert result.actual_credits == 19.5


def test_runway_optional_prompt_is_omitted_and_prompt_image_bound_is_enforced(
    video_project_root: Path,
) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = RunwayMotionProvider(
        config.providers["runway"],
        api_key="contract-secret",
        client=SimpleNamespace(image_to_video=ImageToVideo(), tasks=SimpleNamespace()),
    )
    request = replace(make_motion_request(video_project_root), prompt_text="")
    payload = provider.translate_request(request)
    assert "prompt_text" not in payload
    assert payload["prompt_image"].startswith("data:image/png;base64,")

    settings = dict(config.providers["runway"].settings)
    models = {name: dict(value) for name, value in settings["supported_models"].items()}
    models["gen4_turbo"]["max_prompt_image_data_uri_bytes"] = 1
    settings["supported_models"] = models
    constrained = replace(config.providers["runway"], settings=settings)
    provider = RunwayMotionProvider(
        constrained,
        api_key="contract-secret",
        client=SimpleNamespace(image_to_video=ImageToVideo(), tasks=SimpleNamespace()),
    )
    with pytest.raises((ProviderValidationError, ValueError), match="image|size|bytes|limit"):
        provider.translate_request(make_motion_request(video_project_root))
