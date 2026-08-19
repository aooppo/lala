from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Callable, Sequence

from ..hashing import sha256_file
from ..video.domain import MediaArtifact
from ..video.downloads import inspect_video


class FFmpegError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


class FFmpegEditor:
    def __init__(
        self,
        *,
        ffmpeg: str = "ffmpeg",
        runner: Runner = subprocess.run,
    ) -> None:
        self.ffmpeg = ffmpeg
        self.runner = runner

    def build_assembly_command(
        self,
        *,
        talking_path: Path,
        broll_paths: Sequence[Path],
        audio_path: Path,
        output_path: Path,
        audio_duration_seconds: float,
        resolution: str,
        frame_rate: int,
        transition_seconds: float,
    ) -> list[str]:
        if output_path.exists():
            raise FFmpegError(f"output already exists and will not be overwritten: {output_path}")
        if not 0 <= transition_seconds <= 0.5:
            raise FFmpegError("transition_seconds must be within 0..0.5")
        if audio_duration_seconds <= 0:
            raise FFmpegError("audio duration must be positive")
        try:
            width, height = (int(value) for value in resolution.split(":", 1))
        except (ValueError, TypeError) as exc:
            raise FFmpegError(f"invalid output resolution: {resolution}") from exc
        command = [self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(talking_path)]
        for path in broll_paths:
            command.extend(["-stream_loop", "-1", "-i", str(path)])
        audio_input = len(broll_paths) + 1
        command.extend(["-i", str(audio_path)])
        normalize = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"fps={frame_rate},format=yuv420p,settb=AVTB"
        )
        filters: list[str] = []
        if not broll_paths:
            filters.append(
                f"[0:v]{normalize},trim=duration={audio_duration_seconds:.6f},"
                "setpts=PTS-STARTPTS[vout]"
            )
        else:
            bookend = min(1.5, max(0.5, audio_duration_seconds * 0.2))
            segments = len(broll_paths) + 2
            overlap_total = transition_seconds * (segments - 1)
            broll_duration = (
                audio_duration_seconds - (2 * bookend) + overlap_total
            ) / len(broll_paths)
            if broll_duration <= transition_seconds:
                raise FFmpegError("audio is too short for selected B-roll and transition policy")
            filters.append(
                f"[0:v]{normalize},trim=start=0:duration={bookend:.6f},"
                "setpts=PTS-STARTPTS[seg0]"
            )
            durations = [bookend]
            for index, _path in enumerate(broll_paths, start=1):
                filters.append(
                    f"[{index}:v]{normalize},trim=duration={broll_duration:.6f},"
                    f"setpts=PTS-STARTPTS[seg{index}]"
                )
                durations.append(broll_duration)
            closing_index = len(broll_paths) + 1
            closing_start = max(0, audio_duration_seconds - bookend)
            filters.append(
                f"[0:v]{normalize},trim=start={closing_start:.6f}:duration={bookend:.6f},"
                f"setpts=PTS-STARTPTS[seg{closing_index}]"
            )
            durations.append(bookend)
            if transition_seconds == 0:
                inputs = "".join(f"[seg{index}]" for index in range(segments))
                filters.append(f"{inputs}concat=n={segments}:v=1:a=0[vout]")
            else:
                cumulative = durations[0]
                previous = "seg0"
                for index in range(1, segments):
                    output = "vout" if index == segments - 1 else f"xf{index}"
                    offset = cumulative - transition_seconds
                    filters.append(
                        f"[{previous}][seg{index}]xfade=transition=fade:"
                        f"duration={transition_seconds:.6f}:offset={offset:.6f}[{output}]"
                    )
                    cumulative += durations[index] - transition_seconds
                    previous = output
        command.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[vout]",
                "-map",
                f"{audio_input}:a:0",
                "-af",
                "loudnorm=I=-16:LRA=11:TP=-1.5",
                "-t",
                f"{audio_duration_seconds:.6f}",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-movflags",
                "+faststart",
                "-n",
                str(output_path),
            ]
        )
        return command

    def run(self, command: Sequence[str], *, timeout_seconds: float) -> None:
        try:
            self.runner(
                list(command),
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise FFmpegError(f"FFmpeg timed out after {timeout_seconds:g} seconds") from exc
        except subprocess.CalledProcessError as exc:
            message = (exc.stderr or exc.stdout or "FFmpeg failed").strip()
            raise FFmpegError(message) from exc
        except OSError as exc:
            raise FFmpegError(f"FFmpeg could not start: {exc}") from exc

    def assemble(
        self,
        *,
        talking_path: Path,
        broll_paths: Sequence[Path],
        audio_path: Path,
        output_path: Path,
        audio_duration_seconds: float,
        resolution: str,
        frame_rate: int,
        transition_seconds: float,
        timeout_seconds: float,
        artifact_id: str,
    ) -> tuple[MediaArtifact, str]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = self.build_assembly_command(
            talking_path=talking_path,
            broll_paths=broll_paths,
            audio_path=audio_path,
            output_path=output_path,
            audio_duration_seconds=audio_duration_seconds,
            resolution=resolution,
            frame_rate=frame_rate,
            transition_seconds=transition_seconds,
        )
        self.run(command, timeout_seconds=timeout_seconds)
        info = inspect_video(output_path, timeout_seconds=min(timeout_seconds, 30))
        artifact = MediaArtifact(
            artifact_id=artifact_id,
            kind="final",
            path=output_path,
            sha256=sha256_file(output_path),
            size_bytes=output_path.stat().st_size,
            mime_type="video/mp4",
            duration_seconds=info.duration_seconds,
            width=info.width,
            height=info.height,
        )
        return artifact, self.format_command(command)

    @staticmethod
    def format_command(command: Sequence[str]) -> str:
        return shlex.join(str(value) for value in command)
