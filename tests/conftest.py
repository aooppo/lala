from __future__ import annotations

import shutil
import socket
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from lala_workflow.config import load_project_config
from lala_workflow.domain import (
    GenerationRequest,
    OutputArtifact,
    ProviderTaskResult,
    ReferenceImage,
    TaskStatus,
)
from lala_workflow.hashing import sha256_file
from lala_workflow.prompts import load_prompt
from lala_workflow.providers.base import ProviderSubmissionError
from lala_workflow.runner import RunOptions, run_generation


SOURCE_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def block_network(monkeypatch) -> None:
    def reject_network(*_args, **_kwargs):
        raise AssertionError("automated tests must not access the network")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)


@pytest.fixture
def image_factory():
    def create(path: Path, *, size: tuple[int, int] = (32, 48), color=(120, 20, 20)) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, color).save(path)
        return path

    return create


@pytest.fixture
def project_root(tmp_path: Path, image_factory) -> Path:
    for directory in ("configs", "prompts"):
        shutil.copytree(SOURCE_ROOT / directory, tmp_path / directory)
    anchor_paths = (
        "assets/approved_anchors/face/lala-face-front.png",
        "assets/approved_anchors/full_body/lala-red-gown-full-body.png",
        "assets/approved_anchors/scene/lala-home-decor-scene.png",
        "assets/approved_anchors/scene/lady-lala-character-sheet-exploration-v0.8.png",
        "assets/approved_anchors/scene/lady-lala-wardrobe-b-v0.6.png",
    )
    for index, relative in enumerate(anchor_paths):
        image_factory(
            tmp_path / relative,
            size=(32 + index, 48 + index),
            color=(120 + index, 20, 20),
        )
    for relative in ("runs", "outputs", "outputs/approved_keyframes", "assets/derived"):
        (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def runway_capabilities(project_root: Path):
    return load_project_config(project_root).providers["runway"]


@pytest.fixture
def generation_request(project_root: Path) -> GenerationRequest:
    config = load_project_config(project_root)
    preset = config.presets["baseline_identity"]
    capabilities = config.providers["runway"]
    anchors = tuple(config.manifest.anchors[name] for name in preset.references)
    prompt = load_prompt(
        config.root,
        preset.prompt_file,
        selected_tags={anchor.tag for anchor in anchors},
        max_utf16_units=capabilities.prompt_utf16_max,
    )
    references = tuple(
        ReferenceImage(
            name=anchor.name,
            path=config.root / anchor.path,
            role=anchor.role,
            tag=anchor.tag,
            sha256=anchor.sha256,
            mime_type=anchor.mime_type,
        )
        for anchor in anchors
    )
    return GenerationRequest(
        run_id="RUN-TEST",
        output_id="output-001",
        preset=preset.name,
        provider="runway",
        model="gen4_image",
        ratio="1080:1440",
        resolution="1080:1440",
        prompt=prompt,
        references=references,
        seed=42,
        output_count=1,
    )


class FakeImageProvider:
    def __init__(self, *, submission_failures: int = 0, failed_outputs: set[str] | None = None):
        self.submission_failures = submission_failures
        self.failed_outputs = failed_outputs or set()
        self.submit_calls = 0
        self.validated = 0
        self._requests = {}
        self._lock = threading.Lock()

    def validate_request(self, request) -> None:
        self.validated += 1

    def submit(self, request) -> str:
        with self._lock:
            self.submit_calls += 1
            if self.submit_calls <= self.submission_failures:
                raise ProviderSubmissionError("temporary submit error")
            task_id = f"task-{request.output_id}"
            self._requests[task_id] = request
            return task_id

    def wait(self, task_id: str, timeout_seconds: float) -> ProviderTaskResult:
        output_id = self._requests[task_id].output_id
        if output_id in self.failed_outputs:
            return ProviderTaskResult(task_id, TaskStatus.FAILED, error_code="fake_failure")
        return ProviderTaskResult(task_id, TaskStatus.SUCCEEDED, (f"fake://{output_id}",))

    def download_results(
        self, result, destination: Path, output_id: str, timeout_seconds: float, max_retries: int
    ) -> tuple[OutputArtifact, ...]:
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / f"{output_id}.png"
        Image.new("RGB", (8, 8), "red").save(path)
        return (
            OutputArtifact(
                output_id=output_id,
                provider_task_id=result.provider_task_id,
                file=path,
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
                source_url_redacted="fake://output",
            ),
        )


@pytest.fixture
def fake_image_provider_factory():
    return FakeImageProvider


@pytest.fixture
def fake_runway_client():
    class TextToImage:
        def __init__(self) -> None:
            self.requests = []

        def create(self, **kwargs):
            self.requests.append(kwargs)
            return SimpleNamespace(id=f"task-{len(self.requests)}")

    class Tasks:
        def retrieve(self, task_id: str, **kwargs):
            return SimpleNamespace(
                status="SUCCEEDED", output=[f"https://example.test/{task_id}.png"]
            )

    return SimpleNamespace(text_to_image=TextToImage(), tasks=Tasks())


@pytest.fixture
def fake_png_downloader():
    def download(url: str, destination: Path, timeout: float) -> None:
        Image.new("RGB", (12, 12), "red").save(destination)

    return download


@pytest.fixture
def dry_run_outcome(project_root: Path):
    return run_generation(
        project_root,
        RunOptions(preset="product_page_clean", count=1),
    )
