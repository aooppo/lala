from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lala_workflow.editing.ffmpeg import FFmpegEditor, FFmpegError


def test_builds_argument_safe_logged_cut_and_crossfade_commands(
    tmp_path: Path, synthetic_video: Path
) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fixture-placeholder")
    editor = FFmpegEditor()
    cut = editor.build_assembly_command(
        talking_path=synthetic_video,
        broll_paths=(synthetic_video, synthetic_video),
        audio_path=audio,
        output_path=tmp_path / "candidate-v001.mp4",
        audio_duration_seconds=10,
        resolution="1280:720",
        frame_rate=30,
        transition_seconds=0,
    )
    fade = editor.build_assembly_command(
        talking_path=synthetic_video,
        broll_paths=(synthetic_video,),
        audio_path=audio,
        output_path=tmp_path / "candidate-v002.mp4",
        audio_duration_seconds=10,
        resolution="1280:720",
        frame_rate=30,
        transition_seconds=0.25,
    )
    assert cut[0] == "ffmpeg"
    assert "-filter_complex" in cut
    assert "concat=n=4" in cut[cut.index("-filter_complex") + 1]
    assert any(value.startswith("loudnorm=") for value in cut)
    assert "xfade=transition=fade" in fade[fade.index("-filter_complex") + 1]
    assert "-n" in fade
    assert editor.format_command(fade).endswith("candidate-v002.mp4")


def test_ffmpeg_refuses_existing_output(tmp_path: Path, synthetic_video: Path) -> None:
    output = tmp_path / "exists.mp4"
    output.write_bytes(b"do not overwrite")
    editor = FFmpegEditor()
    with pytest.raises(FFmpegError, match="exists"):
        editor.build_assembly_command(
            talking_path=synthetic_video,
            broll_paths=(),
            audio_path=tmp_path / "audio.wav",
            output_path=output,
            audio_duration_seconds=10,
            resolution="1280:720",
            frame_rate=30,
            transition_seconds=0,
        )


def test_ffmpeg_timeout_is_normalized(tmp_path: Path, synthetic_video: Path) -> None:
    def timeout_runner(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)

    editor = FFmpegEditor(runner=timeout_runner)
    command = ["ffmpeg", "-version"]
    with pytest.raises(FFmpegError, match="timed out"):
        editor.run(command, timeout_seconds=1)
