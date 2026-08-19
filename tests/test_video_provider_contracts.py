from __future__ import annotations

from pathlib import Path

from lala_workflow.providers.motion_base import MotionVideoProvider
from lala_workflow.providers.talking_base import TalkingVideoProvider
from lala_workflow.providers.voice_base import VoiceProvider


class TalkingFake:
    def validate_request(self, request):
        return None

    def submit(self, request):
        return "talk-1"

    def wait(self, task_id, timeout_seconds):
        return object()

    def download_results(self, result, output_dir, output_stem, timeout_seconds, max_retries):
        return ()


class MotionFake(TalkingFake):
    pass


class VoiceFake:
    def synthesize(self, request):
        return object()


def test_provider_protocols_are_runtime_replaceable() -> None:
    assert isinstance(TalkingFake(), TalkingVideoProvider)
    assert isinstance(MotionFake(), MotionVideoProvider)
    assert isinstance(VoiceFake(), VoiceProvider)


def test_provider_protocols_expose_provider_neutral_methods_only() -> None:
    assert set(TalkingVideoProvider.__protocol_attrs__) >= {
        "validate_request",
        "submit",
        "wait",
        "download_results",
    }
    assert "client" not in TalkingVideoProvider.__protocol_attrs__
    assert set(VoiceProvider.__protocol_attrs__) == {"synthesize"}
