from __future__ import annotations

import json
import os
import subprocess
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from ..domain import utc_now
from ..env import require_canonical_voice_env
from ..hashing import sha256_file
from ..providers.heygen_voice import HeyGenVoiceVerifier
from .downloads import Downloader, redacted_url
from .config import VideoConfigError, load_video_config
from .validation import ExternalInputBlocked


EXPECTED_VOICE_ID = "7a738e1ced454de6b92d2c76a6ccb8c0"
EXPECTED_VOICE_NAME = "Lady LaLa v1"


def verify_owner_voice(
    project_root: Path,
    *,
    voice_id: str | None = None,
    voice_id_env: str | None = None,
    environ: Mapping[str, str] | None = None,
    verifier: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    environment = os.environ if environ is None else environ
    config = load_video_config(project_root, require_inputs=False)
    profile = config.voice_profile
    selected = voice_id
    if voice_id_env:
        if voice_id_env != "HEYGEN_VOICE_ID":
            raise VideoConfigError("voice ID environment variable must be HEYGEN_VOICE_ID")
        selected = require_canonical_voice_env(environment)
    selected = str(selected or profile.voice_id or "").strip()
    if selected != EXPECTED_VOICE_ID or selected != profile.voice_id:
        raise ExternalInputBlocked("requested HeyGen voice ID does not match the approved profile")
    canonical_env = str(environment.get("HEYGEN_VOICE_ID") or "").strip()
    if canonical_env and canonical_env != selected:
        raise ExternalInputBlocked("HEYGEN_VOICE_ID does not match the approved profile")
    api_key = str(environment.get("HEYGEN_API_KEY") or "").strip()
    if verifier is None:
        if not api_key:
            raise ExternalInputBlocked("voice verification requires HEYGEN_API_KEY")
        verifier = HeyGenVoiceVerifier(
            config.providers["heygen_voice"], api_key=api_key
        )
    verified = verifier.verify(selected, expected_name=EXPECTED_VOICE_NAME)
    current = now or utc_now()
    run_id = _allocate_verification_run(config.root, current)
    result = {
        "status": "VERIFIED_FOR_SMOKE",
        "run_id": run_id,
        "verified_at": current.isoformat(),
        "approval_scope": "smoke_only",
        "production_approved": False,
        "voice_id": verified.voice_id,
        "name": verified.name,
        "gender": verified.gender,
        "language": verified.language,
        "engine": verified.engine,
        "type": verified.voice_type,
        "created_at": verified.created_at,
        "preview_url_safe": verified.preview_url_safe,
    }
    target = config.root / "outputs/audio/voice_verification" / run_id
    target.mkdir(parents=True, exist_ok=False)
    with (target / "verification.json").open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
    return result


def _allocate_verification_run(root: Path, now: datetime) -> str:
    stem = now.strftime("LALA-VOICE-VERIFY-%Y%m%d-%H%M%S")
    base = root / "outputs/audio/voice_verification"
    for sequence in range(1, 1000):
        run_id = f"{stem}-{sequence:03d}"
        if not (base / run_id).exists():
            return run_id
    raise RuntimeError("could not allocate voice verification run ID")


def download_owner_voice_preview(
    project_root: Path,
    *,
    voice_id: str,
    environ: Mapping[str, str] | None = None,
    verifier: Any | None = None,
    downloader: Downloader | None = None,
    runner: Any = subprocess.run,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Download one unapproved preview without changing voice/profile approval state."""

    environment = os.environ if environ is None else environ
    config = load_video_config(project_root, require_inputs=False)
    profile = config.voice_profile
    selected = str(voice_id or "").strip()
    if selected != EXPECTED_VOICE_ID or selected != profile.voice_id:
        raise ExternalInputBlocked("requested HeyGen voice ID does not match the configured profile")
    canonical_env = str(environment.get("HEYGEN_VOICE_ID") or "").strip()
    if canonical_env and canonical_env != selected:
        raise ExternalInputBlocked("HEYGEN_VOICE_ID does not match the configured profile")
    api_key = str(environment.get("HEYGEN_API_KEY") or "").strip()
    if verifier is None:
        if not api_key:
            raise ExternalInputBlocked("voice preview download requires HEYGEN_API_KEY")
        verifier = HeyGenVoiceVerifier(config.providers["heygen_voice"], api_key=api_key)
    verified = verifier.verify(selected, expected_name=EXPECTED_VOICE_NAME)
    preview_url = verifier.preview_url(selected, expected_name=EXPECTED_VOICE_NAME)
    current = now or utc_now()
    run_id = _allocate_preview_run(config.root, current)
    target_dir = config.root / "outputs/audio/voice_preview" / run_id
    target_dir.mkdir(parents=True, exist_ok=False)
    suffix = Path(urlsplit(preview_url).path).suffix.lower()
    if suffix not in {".mp3", ".wav", ".m4a", ".aac", ".ogg"}:
        suffix = ".audio"
    target = target_dir / f"voice-preview{suffix}"
    temporary = target_dir / f".{target.stem}.{uuid.uuid4().hex}.part{suffix}"
    retrieve = downloader or _download_preview
    try:
        retrieve(preview_url, temporary, 60)
        technical = _inspect_audio_preview(temporary, runner=runner)
        os.replace(temporary, target)
        result = {
            "status": "DOWNLOADED_FOR_HUMAN_REVIEW",
            "run_id": run_id,
            "downloaded_at": current.isoformat(),
            "voice_id": verified.voice_id,
            "voice_name": verified.name,
            "approval_status": "unreviewed",
            "source_url_safe": redacted_url(preview_url),
            "path": str(target.relative_to(config.root)),
            "sha256": sha256_file(target),
            **technical,
        }
        with (target_dir / "preview.json").open("x", encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
        return result
    except Exception:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        for child in target_dir.iterdir():
            child.unlink(missing_ok=True)
        target_dir.rmdir()
        raise


def _allocate_preview_run(root: Path, now: datetime) -> str:
    stem = now.strftime("LALA-VOICE-PREVIEW-%Y%m%d-%H%M%S")
    base = root / "outputs/audio/voice_preview"
    for sequence in range(1, 1000):
        run_id = f"{stem}-{sequence:03d}"
        if not (base / run_id).exists():
            return run_id
    raise RuntimeError("could not allocate voice preview run ID")


def _inspect_audio_preview(path: Path, *, runner: Any = subprocess.run) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        raise VideoConfigError("downloaded voice preview is missing or empty")
    try:
        completed = runner(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name,sample_rate,channels",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        payload = json.loads(completed.stdout)
        streams = [
            item for item in payload.get("streams", []) if item.get("codec_type") == "audio"
        ]
        stream = streams[0]
        duration = float(payload.get("format", {}).get("duration") or 0)
        sample_rate = int(stream.get("sample_rate") or 0)
        channels = int(stream.get("channels") or 0)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, IndexError, TypeError, ValueError) as exc:
        raise VideoConfigError("FFprobe could not validate the voice preview") from exc
    if duration <= 0 or sample_rate <= 0 or channels <= 0:
        raise VideoConfigError("voice preview technical metadata is invalid")
    return {
        "duration_seconds": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "audio_codec": str(stream.get("codec_name") or "") or None,
    }


def _download_preview(url: str, destination: Path, timeout_seconds: float) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "lady-lala-workflow/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        with destination.open("xb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
