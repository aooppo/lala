from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from lala_workflow.providers.base import ProviderValidationError
from lala_workflow.providers.runway_video import RunwayMotionProvider
from lala_workflow.video.config import load_video_config
from lala_workflow.video.domain import MotionVideoRequest, VideoTaskStatus
from lala_workflow.video.prompts import load_video_prompt


def make_motion_request(root: Path, *, model: str = "gen4_turbo") -> MotionVideoRequest:
    config = load_video_config(root, require_inputs=True)
    keyframe = config.keyframes["hero"]
    prompt = load_video_prompt(root, Path("prompts/product-broll-v1.txt"))
    return MotionVideoRequest(
        request_id="product-page-product-v001",
        run_id="RUN-1",
        preset="product_page",
        shot_id="product_interaction",
        variation=1,
        provider="runway",
        model=model,
        image_path=root / keyframe.path,
        image_sha256=keyframe.sha256,
        prompt_path=root / prompt.path,
        prompt_text=prompt.text,
        prompt_sha256=prompt.sha256,
        ratio="1280:720",
        duration_seconds=4,
        seed=42,
        output_format="mp4",
        timeout_seconds=1800,
        max_retries=2,
    )


class ImageToVideo:
    def __init__(self):
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(id="motion-task-1", estimated_cost=SimpleNamespace(credits=20))


class Tasks:
    def retrieve(self, task_id, **kwargs):
        return SimpleNamespace(status="SUCCEEDED", output=["https://example.test/motion.mp4"])


def test_runway_motion_translates_current_image_to_video_fields(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    client = SimpleNamespace(image_to_video=ImageToVideo(), tasks=Tasks())
    provider = RunwayMotionProvider(
        config.providers["runway"], api_key="local-test-secret", client=client
    )
    request = make_motion_request(video_project_root)
    payload = provider.translate_request(request)
    assert payload["model"] == "gen4_turbo"
    assert payload["prompt_image"].startswith("data:image/png;base64,")
    assert payload["prompt_text"].startswith("Preserve")
    assert payload["ratio"] == "1280:720"
    assert payload["duration"] == 4
    assert payload["seed"] == 42
    assert provider.submit(request) == "motion-task-1"
    result = provider.wait("motion-task-1", 10)
    assert result.status is VideoTaskStatus.SUCCEEDED


def test_runway_motion_enforces_model_prompt_duration_and_hash(video_project_root: Path) -> None:
    config = load_video_config(video_project_root, require_inputs=True)
    provider = RunwayMotionProvider(
        config.providers["runway"],
        api_key="local-test-secret",
        client=SimpleNamespace(image_to_video=ImageToVideo(), tasks=Tasks()),
    )
    with pytest.raises(ProviderValidationError, match="duration"):
        provider.validate_request(replace(make_motion_request(video_project_root), duration_seconds=11))
    request = make_motion_request(video_project_root, model="gen4.5")
    request = replace(request, prompt_text="")
    with pytest.raises(ProviderValidationError, match="prompt"):
        provider.validate_request(request)
