from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..video.domain import MediaArtifact, MotionVideoRequest, VideoTaskResult


@runtime_checkable
class MotionVideoProvider(Protocol):
    def validate_request(self, request: MotionVideoRequest) -> None: ...

    def submit(self, request: MotionVideoRequest) -> str: ...

    def wait(self, task_id: str, timeout_seconds: float) -> VideoTaskResult: ...

    def download_results(
        self,
        result: VideoTaskResult,
        output_dir: Path,
        output_stem: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> tuple[MediaArtifact, ...]: ...
