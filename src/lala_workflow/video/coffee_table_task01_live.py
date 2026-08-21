from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image
import yaml

from ..hashing import sha256_file
from ..characters.domain import CharacterProfile
from ..providers.motion_base import MotionVideoProvider
from ..providers.runway_video import RunwayMotionProvider
from ..redaction import redact_text
from .coffee_table_prompt_preflight import preflight_coffee_table_prompts
from .config import load_video_config
from .domain import MotionVideoRequest, VideoTaskStatus
from .downloads import inspect_video, validate_media_artifact
from .prompts import load_video_prompt, utf16_code_units
from .storage import VideoRunStorage
from .validation import ExternalInputBlocked


FINAL_PACKAGE = Path("outputs/reviews/coffee-table-4task-final-prompt-review/COFFEE-TABLE-4TASK-FINAL-PROMPT-20260821-001")
FINAL_MANIFEST_SHA256 = "606b9eafb27289213aaa5f60418e614c90383211acddf4fc4f60cac693dd27e3"
FINAL_REVIEW_SHA256 = "e4cc866200b5bcebb3a3435e122342c134cdae343353328b8f5fcff31e73bc57"
PROMPT = Path("prompts/coffee-table-task-01-establish-approach-v3.txt")
PROMPT_SHA256 = "a47631429cebca845b5275bdb279a47d49f27eccf4e3e1786224626cf796d21b"
PROMPT_UTF16 = 598
K1 = Path("assets/approved_keyframes/K1-V2-002.png")
K1_SHA256 = "3ad624df44cc31f56309a45ae4ba9577d526693a7332ee97fb7fd9f914a7043c"
K3 = Path("assets/approved_keyframes/K3-V2-002.png")
K3_SHA256 = "7281237344ddfc81b7f4635a83410d87b109688b03be4188f648f20dff6fd631"
CHARACTER_PROFILE = Path("configs/characters/profiles/character-20260821-001-v006.yaml")
CHARACTER_PROFILE_SHA256 = "659378036a36b44f69b2e5bb4312d1a62446da36b30f52eaf67e1337cfaa434b"
READY = "READY_FOR_OWNER_TASK01_LIVE_REVIEW"


@dataclass(frozen=True, slots=True)
class Task01Outcome:
    run_id: str
    status: str
    provider_task_id: str
    artifact: Mapping[str, Any]
    review_package: Path
    review_manifest_sha256: str
    actual_credits: float | None
    actual_cost_usd: float | None
    terminal_candidates: tuple[Mapping[str, Any], ...]


ProviderFactory = Callable[[Callable[[str, str | None, float | None], None]], MotionVideoProvider]


def execute_task01_live(
    root: Path, *, confirm_owner_authorized: bool, max_runway_credits: float,
    environ: Mapping[str, str] | None = None, provider_factory: ProviderFactory | None = None,
    now: datetime | None = None,
) -> Task01Outcome:
    project = root.resolve()
    env = os.environ if environ is None else environ
    if not confirm_owner_authorized:
        raise ExternalInputBlocked("TASK-01 requires explicit Owner Live authorization")
    if max_runway_credits != 25:
        raise ExternalInputBlocked("TASK-01 authorized budget must be exactly 25 credits")
    if env.get("VIDEO_ALLOW_LIVE_CALLS") != "true":
        raise ExternalInputBlocked("TASK-01 requires exact VIDEO_ALLOW_LIVE_CALLS=true")
    credential = str(env.get("RUNWAYML_API_SECRET") or "").strip()
    if not credential:
        raise ExternalInputBlocked("TASK-01 Runway credential is missing")
    manifest = project / FINAL_PACKAGE / "manifest.json"
    review = project / FINAL_PACKAGE / "REVIEW.md"
    if sha256_file(manifest) != FINAL_MANIFEST_SHA256 or sha256_file(review) != FINAL_REVIEW_SHA256:
        raise ExternalInputBlocked("TASK-01 final Owner package hash drift")
    subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS.txt"], cwd=project / FINAL_PACKAGE, check=True, capture_output=True, text=True)
    for path, expected, label in ((project / PROMPT, PROMPT_SHA256, "prompt"), (project / K1, K1_SHA256, "K1"), (project / K3, K3_SHA256, "K3")):
        if not path.is_file() or sha256_file(path) != expected:
            raise ExternalInputBlocked(f"TASK-01 {label} hash drift")
    profile_path = project / CHARACTER_PROFILE
    profile = CharacterProfile.from_dict(yaml.safe_load(profile_path.read_text(encoding="utf-8")))
    if profile.profile_sha256 != CHARACTER_PROFILE_SHA256:
        raise ExternalInputBlocked("TASK-01 character profile semantic hash drift")
    checks = {item.task_id: item for item in preflight_coffee_table_prompts(project)}
    if checks["TASK-01"].utf16_units != PROMPT_UTF16:
        raise ExternalInputBlocked("BLOCKED_TASK01_PROMPT_PAYLOAD_MISMATCH")
    prompt = load_video_prompt(project, PROMPT)
    if prompt.text != (project / PROMPT).read_text(encoding="utf-8") or utf16_code_units(prompt.text) != PROMPT_UTF16:
        raise ExternalInputBlocked("BLOCKED_TASK01_PROMPT_PAYLOAD_MISMATCH")
    _block_prior_task01(project)

    storage = VideoRunStorage(project, secrets=(credential,))
    run = storage.create_run("coffee-table-task01-live", now=now)
    raw_dir = project / "outputs/broll" / run.run_id
    package = project / "outputs/reviews/coffee-table-task01-live" / run.run_id
    raw_dir.mkdir(parents=True, exist_ok=False)
    package.mkdir(parents=True, exist_ok=False)
    durable: dict[str, str | None] = {"id": None}

    def sink(task_id: str, _request_id: str | None, credits: float | None) -> None:
        durable["id"] = task_id
        storage.append_event(run, "provider_task_id_durable", {"task_id": "TASK-01", "provider_task_id": task_id, "estimated_credits": credits})

    authorization = {"task": "TASK-01", "owner_authorized": True, "maximum_runway_credits": 25, "maximum_provider_submissions": 1, "automatic_retry": False, "replacement_submission": False, "TASK-02": "NOT_AUTHORIZED", "TASK-03": "NOT_AUTHORIZED", "TASK-04": "NOT_AUTHORIZED", "final_owner_manifest_sha256": FINAL_MANIFEST_SHA256}
    storage.write_json_new(run, "coffee-table-task01-live-authorization.json", authorization)
    request = MotionVideoRequest(
        request_id="TASK-01", run_id=run.run_id, preset="coffee-table-task01-live", shot_id="TASK-01", variation=1,
        provider="runway", model="gen4_turbo", image_path=project / K1, image_sha256=K1_SHA256,
        prompt_path=project / PROMPT, prompt_text=prompt.text, prompt_sha256=PROMPT_SHA256,
        ratio="1280:720", duration_seconds=5, seed=None, output_format="mp4", timeout_seconds=1800, max_retries=0,
    )
    audit = {"character_reference": {"path": CHARACTER_PROFILE.as_posix(), "sha256": CHARACTER_PROFILE_SHA256}, "scene_reference": {"path": K1.as_posix(), "sha256": K1_SHA256}, "product_reference": {"path": K3.as_posix(), "sha256": K3_SHA256, "provider_input": False}, "provider_input_image": {"path": K1.as_posix(), "sha256": K1_SHA256}, "provider": "runway", "model": "gen4_turbo", "duration_seconds": 5, "ratio": "1280:720", "aspect_ratio": "16:9", "prompt": {"path": PROMPT.as_posix(), "sha256": PROMPT_SHA256, "utf16_units": PROMPT_UTF16}}
    storage.write_json_new(run, "request.json", {"mode": "LIVE", "task": "TASK-01", "submission_count_cap": 1, "audit": audit})
    storage.append_event(run, "live_preflight_passed", audit)
    config = load_video_config(project, require_inputs=False)
    if provider_factory is None:
        definition = config.providers["runway"]
        provider_factory = lambda callback: RunwayMotionProvider(definition, api_key=credential, max_poll_retries=2, task_created_sink=callback)
    provider = provider_factory(sink)
    provider.validate_request(request)
    storage.append_event(run, "task_submitting", {"task_id": "TASK-01", "submission_attempt": 1, "planned_credits": 25})
    try:
        task_id = provider.submit(request)
        if durable["id"] is None:
            durable["id"] = task_id
            sink(task_id, "TASK-01", None)
        if durable["id"] != task_id:
            raise RuntimeError("provider task ID changed after durable persistence")
        result = provider.wait(task_id, request.timeout_seconds)
        storage.append_event(run, "provider_task_terminal", {"task_id": "TASK-01", "provider_task_id": task_id, "status": result.status.value, "actual_credits": result.actual_credits, "error_code": result.error_code, "error_message": result.error_message})
        if result.status is not VideoTaskStatus.SUCCEEDED:
            raise RuntimeError(f"FAILED_TASK01_PROVIDER_{result.status.value}")
        if result.actual_credits is not None and float(result.actual_credits) > 25:
            raise RuntimeError("reported TASK-01 credits exceed authorization")
        artifacts = provider.download_results(result, raw_dir, "TASK-01", request.timeout_seconds, 0)
        if len(artifacts) != 1:
            raise RuntimeError("TASK-01 requires exactly one output")
        artifact = validate_media_artifact(artifacts[0])
        info = inspect_video(artifact.path)
        if (info.width, info.height) != (1280, 720) or info.duration_seconds < 5:
            raise RuntimeError("TASK-01 output fails media contract")
        frame_count, frame_rate = _video_frame_facts(artifact.path)
        candidates = _extract_terminal_candidates(artifact.path, package, frame_count, frame_rate)
        video_copy = package / "TASK-01.mp4"
        shutil.copyfile(artifact.path, video_copy)
        if sha256_file(video_copy) != sha256_file(artifact.path):
            raise RuntimeError("TASK-01 review video copy hash mismatch")
        review_csv = package / "review.csv"
        _write_blank_review(review_csv)
        actual = None if result.actual_credits is None else float(result.actual_credits)
        evidence = {"run_id": run.run_id, "status": READY, "execution": {"task_id": "TASK-01", "provider": "runway", "model": "gen4_turbo", "provider_task_id": task_id, "submission_count": 1, "prompt": audit["prompt"], "source_references": audit, "authorized_credits": 25, "actual_credits": actual, "actual_cost_usd": None if actual is None else actual * 0.01}, "output": {"path": str(artifact.path.relative_to(project)), "sha256": sha256_file(artifact.path), "width": info.width, "height": info.height, "duration_seconds": info.duration_seconds, "frame_rate": frame_rate, "frame_count": frame_count, "audio_stream_present": info.audio_stream_present}, "terminal_candidates": candidates, "review_csv": {"path": str(review_csv.relative_to(project)), "sha256": sha256_file(review_csv), "human_fields": "BLANK"}, "authorization_consumed": True, "TASK-02": "NOT_AUTHORIZED", "TASK-03": "NOT_AUTHORIZED", "TASK-04": "NOT_AUTHORIZED"}
        manifest_path = package / "manifest.json"
        _write_json_new(manifest_path, evidence)
        storage.write_json_new(run, "provider-results.json", {"status": READY, "submission_count": 1, "results": [{"task_id": "TASK-01", "provider_task_id": task_id, "status": "SUCCEEDED", "actual_credits": actual, "artifact": asdict(artifact)}]})
        storage.write_json_new(run, "cost.json", {"authorized_runway_credits": 25, "actual_runway_credits": actual, "actual_cost_usd": None if actual is None else actual * 0.01, "authorization_remaining": 0})
        storage.write_text_new(run, "summary.md", f"# TASK-01 Live {run.run_id}\n\n- Status: `{READY}`\n- Provider submissions: 1\n- Owner review: blank\n")
        storage.append_event(run, "ready_for_owner_task01_live_review", {"status": READY})
        return Task01Outcome(run.run_id, READY, task_id, evidence["output"], package, sha256_file(manifest_path), actual, None if actual is None else actual * 0.01, tuple(candidates))
    except Exception as exc:
        storage.write_json_new(run, "provider-results.json", {"status": "STOPPED", "submission_count": 1 if durable["id"] else 0, "provider_task_id": durable["id"], "reason": redact_text(str(exc), secrets=(credential,)), "automatic_retry": 0, "replacement_submission": 0})
        storage.write_text_new(run, "summary.md", f"# TASK-01 Live {run.run_id}\n\n- Status: `STOPPED`\n- Reason: `{redact_text(str(exc), secrets=(credential,))}`\n- No retry or replacement authorized.\n")
        raise


def _block_prior_task01(root: Path) -> None:
    for path in (root / "runs").glob("*/coffee-table-task01-live-authorization.json"):
        if path.is_file():
            raise ExternalInputBlocked(f"TASK-01 Live authorization already consumed: {path.parent.name}")


def _extract_terminal_candidates(source: Path, package: Path, count: int, frame_rate: float) -> list[dict[str, Any]]:
    if count < 9:
        raise RuntimeError("TASK-01 has insufficient frames")
    indices = [count - 9, count - 7, count - 5, count - 3, count - 1]
    rows = []
    for index in indices:
        target = package / f"TASK-01-terminal-frame-{index:06d}.png"
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(source), "-vf", f"select=eq(n\\,{index})", "-frames:v", "1", "-c:v", "png", "-n", str(target)], check=True, capture_output=True, text=True, timeout=120)
        with Image.open(target) as image:
            image.verify()
        rows.append({"frame_index": index, "timestamp_seconds": index / frame_rate, "path": str(target), "sha256": sha256_file(target), "owner_decision": None, "recommendation": "REVIEW_REQUIRED"})
    return rows


def _video_frame_facts(source: Path) -> tuple[int, float]:
    completed = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames,avg_frame_rate", "-of", "json", str(source)], check=True, capture_output=True, text=True, timeout=60)
    stream = json.loads(completed.stdout)["streams"][0]
    count = int(stream["nb_read_frames"])
    numerator, denominator = str(stream["avg_frame_rate"]).split("/", 1)
    frame_rate = float(numerator) / float(denominator)
    if count <= 0 or frame_rate <= 0:
        raise RuntimeError("TASK-01 invalid frame facts")
    return count, frame_rate


def _write_blank_review(path: Path) -> None:
    fields = ["check_item", "decision", "notes", "reviewer", "reviewed_at"]
    checks = ["Character Identity", "Character Scale", "Coffee Table Geometry", "Coffee Table Leg Consistency", "Coffee Table Scale", "Wine Glass Count", "Wine Glass Custody", "Motion Naturalness", "Frame Containment", "Spatial Continuity", "Terminal Pose", "TASK-02 Readiness"]
    with path.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader()
        for item in checks: writer.writerow({"check_item": item, "decision": "", "notes": "", "reviewer": "", "reviewed_at": ""})


def _write_json_new(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True, default=str); output.write("\n")
