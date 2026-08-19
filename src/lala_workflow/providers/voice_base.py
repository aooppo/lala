from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..video.domain import MediaArtifact, VoiceRequest


@runtime_checkable
class VoiceProvider(Protocol):
    def synthesize(self, request: VoiceRequest) -> MediaArtifact: ...
