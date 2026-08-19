from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..video.domain import MediaArtifact, VoiceRequest
from .protocol_compat import ProviderProtocolMeta


@runtime_checkable
class VoiceProvider(Protocol, metaclass=ProviderProtocolMeta):
    def synthesize(self, request: VoiceRequest) -> MediaArtifact: ...
