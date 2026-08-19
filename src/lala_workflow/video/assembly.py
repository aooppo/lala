from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ..editing.ffmpeg import FFmpegEditor
from ..hashing import sha256_file
from .config import VideoConfigError, load_video_config
from .domain import MediaArtifact
from .naming import next_candidate_path
from .graphics import resolve_preset_graphics
from .reporting import blank_review_rows, summary_markdown
from .selection import load_shot_selection
from .storage import VideoRunStorage


@dataclass(frozen=True, slots=True)
class AssemblyOutcome:
    run_id: str
    run_dir: Path
    source_run_id: str
    candidates: tuple[MediaArtifact, ...]
    submission_count: int
    status: str


def assemble_video(
    project_root: Path,
    source_run_id: str,
    selection_file: Path,
    *,
    final_edits: int | None = None,
    editor: FFmpegEditor | None = None,
) -> AssemblyOutcome:
    config = load_video_config(project_root, require_inputs=True)
    selection = load_shot_selection(config.root, source_run_id, selection_file)
    source_dir = config.root / "runs" / source_run_id
    request = _read_json(source_dir / "request.json")
    preset_name = str(request.get("preset") or "")
    if preset_name not in config.presets:
        raise VideoConfigError(f"source run has unknown preset: {preset_name}")
    preset = config.presets[preset_name]
    count = preset.final_edit_variations if final_edits is None else final_edits
    if not 1 <= count <= config.limits.max_final_edits_per_video:
        raise VideoConfigError(
            f"final edits must be within 1..{config.limits.max_final_edits_per_video}"
        )
    source_plan = _read_json(source_dir / "shot-plan.json")
    script_hash = _read_json(source_dir / "script-hash.json")
    audio_hash = _read_json(source_dir / "audio-hash.json")
    keyframe_hash = _read_json(source_dir / "keyframe-hash.json")
    script_bytes = (source_dir / "script.txt").read_bytes()
    if sha256_file(source_dir / "script.txt") != script_hash.get("sha256"):
        raise VideoConfigError("source run script evidence no longer matches exact bytes")
    audio_path = (config.root / str(audio_hash.get("path") or "")).resolve()
    if not audio_path.is_file() or sha256_file(audio_path) != audio_hash.get("sha256"):
        raise VideoConfigError("source run approved audio no longer matches evidence")
    audio_duration = float(audio_hash.get("duration_seconds") or 0)

    selected_talking: MediaArtifact | None = None
    broll: list[MediaArtifact] = []
    for shot in source_plan.get("shots", []):
        shot_id = str(shot.get("shot_id") or "")
        selected = selection.selections.get(shot_id)
        if selected is None:
            continue
        if shot.get("kind") == "talking":
            if selected_talking is not None:
                raise VideoConfigError("assembly supports one selected full-script talking performance")
            selected_talking = selected
        elif shot.get("kind") == "motion":
            broll.append(selected)
    if selected_talking is None:
        raise VideoConfigError("selection has no talking performance")

    storage = VideoRunStorage(config.root)
    run = storage.create_run(preset_name)
    storage.append_event(
        run,
        "assembly_started",
        {"source_run_id": source_run_id, "final_edits": count, "provider_calls": 0},
    )
    output_dir = config.root / "outputs/final" / run.run_id
    graphics = resolve_preset_graphics(
        config.root,
        preset=preset_name,
        run_id=run.run_id,
        exact_script=script_bytes,
        script_sha256=str(script_hash.get("sha256") or ""),
    )
    graphic_evidence = [
        {
            "asset_id": item.asset_id,
            "path": item.path.relative_to(config.root),
            "sha256": item.sha256,
            "version": item.version,
            "approval_status": item.approval_status,
            "draft": item.draft,
            "reviewer": item.reviewer,
            "reviewed_at": item.reviewed_at,
            "source_reference": item.source_reference,
            "provenance": item.provenance,
        }
        for item in graphics
    ]
    has_draft_graphics = any(item.draft for item in graphics)
    review_status = "REVIEW_READY_DRAFT_ASSETS" if has_draft_graphics else "REVIEW_READY"
    edit = editor or FFmpegEditor()
    candidates: list[MediaArtifact] = []
    commands: list[str] = []
    for index in range(1, count + 1):
        output_path = next_candidate_path(output_dir, preset_name)
        transition = 0.0 if index == 1 else 0.25
        artifact, command = edit.assemble(
            talking_path=selected_talking.path,
            broll_paths=tuple(item.path for item in broll),
            audio_path=audio_path,
            output_path=output_path,
            audio_duration_seconds=audio_duration,
            resolution=preset.resolution,
            frame_rate=preset.frame_rate,
            transition_seconds=transition,
            timeout_seconds=config.limits.provider_timeout_seconds,
            artifact_id=output_path.stem,
            graphic_paths=tuple(item.path for item in graphics),
        )
        artifact = replace(
            artifact,
            provenance={
                **dict(artifact.provenance),
                "graphics": graphic_evidence,
                "contains_draft_brand_assets": has_draft_graphics,
            },
        )
        candidates.append(artifact)
        commands.append(command)
        storage.append_event(
            run,
            "candidate_assembled",
            {"candidate": output_path.name, "sha256": artifact.sha256, "transition": transition},
        )
    candidate_evidence = [_artifact_evidence(item, config.root) for item in candidates]
    selection_evidence = {
        "source_run_id": selection.source_run_id,
        "reviewer": selection.reviewer,
        "selected_at": selection.selected_at,
        "selection_file": str(selection.selection_file),
        "selections": {
            shot_id: {
                "artifact_id": artifact.artifact_id,
                "path": artifact.path.relative_to(config.root),
                "sha256": artifact.sha256,
            }
            for shot_id, artifact in selection.selections.items()
        },
    }
    storage.write_json_new(
        run,
        "request.json",
        {
            "run_id": run.run_id,
            "mode": "ASSEMBLY",
            "action": "assemble",
            "preset": preset_name,
            "source_run_id": source_run_id,
            "selection": selection_evidence,
            "final_edits": count,
            "provider_call_count": 0,
            "graphics": graphic_evidence,
            "contains_draft_brand_assets": has_draft_graphics,
        },
    )
    storage.write_yaml_new(
        run,
        "resolved-config.yaml",
        {
            "preset": preset_name,
            "source_run_id": source_run_id,
            "resolution": preset.resolution,
            "frame_rate": preset.frame_rate,
            "final_edits": count,
            "transitions": [0.0 if index == 1 else 0.25 for index in range(1, count + 1)],
            "provider_calls": 0,
            "graphics": graphic_evidence,
            "contains_draft_brand_assets": has_draft_graphics,
        },
    )
    storage.write_bytes_new(run, "script.txt", script_bytes)
    storage.write_json_new(run, "script-hash.json", script_hash)
    storage.write_json_new(run, "audio-hash.json", audio_hash)
    storage.write_json_new(run, "keyframe-hash.json", keyframe_hash)
    storage.write_json_new(
        run,
        "shot-plan.json",
        {
            "source_plan": source_plan,
            "selection": selection_evidence,
            "candidate_count": count,
            "graphics": graphic_evidence,
            "contains_draft_brand_assets": has_draft_graphics,
        },
    )
    storage.write_json_new(
        run,
        "provider-results.json",
        {
            "status": review_status,
            "submission_count": 0,
            "successful_outputs": len(candidates),
            "failed_outputs": 0,
            "source_run_id": source_run_id,
            "results": candidate_evidence,
            "graphics": graphic_evidence,
            "contains_draft_brand_assets": has_draft_graphics,
        },
    )
    storage.write_text_new(run, "edit-commands.txt", "\n".join(commands) + "\n")
    storage.write_review_new(run, blank_review_rows(run.run_id, preset_name, candidate_evidence))
    cost = {
        "voice_cost": None,
        "talking_video_cost": None,
        "motion_video_cost": None,
        "editing_cost": 0,
        "storage_cost": None,
        "total_provider_cost": None,
        "currency": config.currency,
        "components": [],
        "source_run_id": source_run_id,
    }
    storage.write_json_new(run, "cost.json", cost)
    storage.write_text_new(
        run,
        "summary.md",
        summary_markdown(
            run_id=run.run_id,
            preset=preset_name,
            status=review_status,
            provider_call_count=0,
            output_count=len(candidates),
            total_provider_cost=None,
        ),
    )
    storage.append_event(run, "assembly_completed", {"status": review_status})
    storage.assert_complete(run)
    return AssemblyOutcome(
        run.run_id,
        run.path,
        source_run_id,
        tuple(candidates),
        0,
        review_status,
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoConfigError(f"assembly source artifact is unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise VideoConfigError(f"assembly source artifact must be an object: {path.name}")
    return value


def _artifact_evidence(artifact: MediaArtifact, project_root: Path) -> dict[str, Any]:
    return {
        "video_id": artifact.artifact_id,
        "candidate": artifact.path.name,
        "artifact_id": artifact.artifact_id,
        "kind": artifact.kind,
        "path": artifact.path.relative_to(project_root),
        "sha256": artifact.sha256,
        "size_bytes": artifact.size_bytes,
        "mime_type": artifact.mime_type,
        "duration_seconds": artifact.duration_seconds,
        "width": artifact.width,
        "height": artifact.height,
        "container": artifact.container,
        "video_codec": artifact.video_codec,
        "pixel_format": artifact.pixel_format,
        "average_frame_rate": artifact.average_frame_rate,
        "audio_stream_present": artifact.audio_stream_present,
        "audio_codec": artifact.audio_codec,
        "sample_rate": artifact.sample_rate,
        "channel_count": artifact.channel_count,
        "bit_rate": artifact.bit_rate,
        "provenance": artifact.provenance,
    }
