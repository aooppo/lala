from __future__ import annotations

import hashlib
import json
import shutil
import socket
import struct
import subprocess
import threading
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
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
def video_project_root(project_root: Path, image_factory) -> Path:
    root = project_root
    keyframe = image_factory(
        root / "assets/approved_keyframes/hero.png",
        size=(128, 72),
        color=(140, 30, 30),
    )
    keyframe_hash = hashlib.sha256(keyframe.read_bytes()).hexdigest()
    promotion = keyframe.with_suffix(".json")
    promotion.write_text(
        json.dumps(
            {
                "source_run_id": "synthetic-goal1-run",
                "source_output_id": "synthetic-output-001",
                "sha256": keyframe_hash,
                "reviewer": "Synthetic test reviewer",
                "approved_at": "2026-08-19T12:00:00+08:00",
            }
        ),
        encoding="utf-8",
    )
    keyframe_manifest = {
        "project": "lady-lala",
        "status": "approved",
        "keyframe_set_version": "synthetic-test-only",
        "keyframes": {
            "hero": {
                "path": "assets/approved_keyframes/hero.png",
                "sha256": keyframe_hash,
                "source_run_id": "synthetic-goal1-run",
                "source_output_id": "synthetic-output-001",
                "promotion_record": "assets/approved_keyframes/hero.json",
                "reviewer": "Synthetic test reviewer",
                "approved_at": "2026-08-19T12:00:00+08:00",
            }
        },
    }
    (root / "configs/keyframe-manifest.yaml").write_text(
        yaml.safe_dump(keyframe_manifest, sort_keys=False), encoding="utf-8"
    )

    scripts: dict[str, dict[str, str]] = {}
    audio_mappings: dict[str, dict[str, str]] = {}
    script_files = {
        "product_page": "product-page.txt",
        "tooltip": "tooltip.txt",
        "homepage": "homepage.txt",
    }
    for script_id, filename in script_files.items():
        content = f"Synthetic MTL fixture for {script_id}.\n".encode()
        script_path = root / "assets/scripts" / filename
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_bytes(content)
        script_hash = hashlib.sha256(content).hexdigest()
        scripts[script_id] = {
            "path": f"assets/scripts/{filename}",
            "version": "synthetic-test-only",
            "sha256": script_hash,
            "source_reference": "Synthetic MTL test fixture; not production authority",
        }
        audio_path = root / f"assets/voice/approved/{script_id}.wav"
        _write_test_wav(audio_path, seconds=10)
        audio_mappings[script_id] = {
            "path": f"assets/voice/approved/{script_id}.wav",
            "sha256": hashlib.sha256(audio_path.read_bytes()).hexdigest(),
            "script_sha256": script_hash,
        }
    (root / "configs/script-manifest.yaml").write_text(
        yaml.safe_dump(
            {"source": "MTL", "modification_policy": "immutable", "scripts": scripts},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (root / "configs/voice-profile.yaml").write_text(
        yaml.safe_dump(
            {
                "voice_version": "synthetic-test-only",
                "mode": "approved_audio",
                "provider": None,
                "model": None,
                "voice_id": None,
                "source_audio": None,
                "approved_audio": None,
                "script_audio": audio_mappings,
                "language": "en",
                "accent": None,
                "speed": None,
                "style": None,
                "stability": None,
                "similarity": None,
                "output_format": "wav",
                "sample_rate": 8000,
                "approval_status": "approved",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    for relative in (
        "outputs/audio",
        "outputs/talking_shots",
        "outputs/broll",
        "outputs/edits",
        "outputs/final",
        "outputs/approved_videos",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    return root


def _write_test_wav(path: Path, *, seconds: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 8000
    samples = b"".join(
        struct.pack("<h", 600 if index % 2 else -600)
        for index in range(sample_rate * seconds)
    )
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(samples)


@pytest.fixture
def synthetic_video(tmp_path: Path) -> Path:
    path = tmp_path / "synthetic-fixture.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=128x72:r=10:d=10",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=8000:cl=mono",
            "-t",
            "10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            "-y",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


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
