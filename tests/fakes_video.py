from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

from lala_workflow.hashing import sha256_file
from lala_workflow.video.domain import MediaArtifact, VideoTaskResult, VideoTaskStatus


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


def fake_video_downloader(_url: str, destination: Path, _timeout_seconds: float) -> None:
    destination.write_bytes(b"synthetic-video-fixture")


class FakeTalkingProvider:
    def __init__(self, fixture_video: Path | None = None) -> None:
        self.fixture_video = fixture_video
        self.validated: list[object] = []
        self.submitted: list[object] = []
        self.waited: list[str] = []

    def validate_request(self, request) -> None:
        self.validated.append(request)

    def submit(self, request) -> str:
        self.submitted.append(request)
        return f"fake-talking-{request.request_id}"

    def wait(self, task_id: str, timeout_seconds: float) -> VideoTaskResult:
        self.waited.append(task_id)
        return VideoTaskResult(task_id, VideoTaskStatus.SUCCEEDED, (f"fake://{task_id}.mp4",))

    def download_results(
        self, result, output_dir: Path, output_stem: str, timeout_seconds: float, max_retries: int
    ) -> tuple[MediaArtifact, ...]:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{output_stem}.mp4"
        if self.fixture_video:
            shutil.copyfile(self.fixture_video, path)
        else:
            path.write_bytes(b"synthetic-video-fixture")
        return (
            MediaArtifact(
                artifact_id=output_stem,
                kind="talking",
                path=path,
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
                mime_type="video/mp4",
                provider_task_id=result.provider_task_id,
            ),
        )


class FakeMotionProvider(FakeTalkingProvider):
    def download_results(
        self, result, output_dir: Path, output_stem: str, timeout_seconds: float, max_retries: int
    ) -> tuple[MediaArtifact, ...]:
        artifacts = super().download_results(
            result, output_dir, output_stem, timeout_seconds, max_retries
        )
        return tuple(replace(artifact, kind="motion") for artifact in artifacts)


class FakeVoiceProvider:
    def __init__(self, artifact: MediaArtifact) -> None:
        self.artifact = artifact
        self.requests: list[object] = []

    def synthesize(self, request) -> MediaArtifact:
        self.requests.append(request)
        return self.artifact
