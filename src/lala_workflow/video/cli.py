from __future__ import annotations

import argparse
from typing import Any


def configure_parser(subparsers: Any) -> None:
    video = subparsers.add_parser("video", help="validate and run Lady LaLa video workflows")
    commands = video.add_subparsers(dest="video_command", required=True)

    validate = commands.add_parser("validate", help="validate video inputs and configuration")
    _project_root(validate)

    voice = commands.add_parser("voice", help="verify or inspect the approved Lady LaLa voice")
    voice_commands = voice.add_subparsers(dest="voice_command", required=True)
    voice_verify = voice_commands.add_parser("verify", help="read-only verify the approved voice")
    _project_root(voice_verify)
    voice_source = voice_verify.add_mutually_exclusive_group(required=True)
    voice_source.add_argument("--voice-id")
    voice_source.add_argument("--voice-id-env", choices=("HEYGEN_VOICE_ID",))
    voice_preview = voice_commands.add_parser(
        "download-preview", help="download one unapproved voice preview for human review"
    )
    _project_root(voice_preview)
    voice_preview.add_argument("--voice-id", required=True)
    voice_init = voice_commands.add_parser(
        "init-env", help="explicitly migrate legacy voice_id to HEYGEN_VOICE_ID"
    )
    _project_root(voice_init)

    smoke = commands.add_parser("talking-smoke-test", help="preview or run one short talking test")
    _project_root(smoke)
    smoke.add_argument("--preset", required=True, choices=("product_page", "tooltip", "homepage"))
    smoke.add_argument("--provider")
    smoke.add_argument("--audio")
    smoke.add_argument("--keyframe")
    smoke.add_argument("--variations", type=int)
    smoke.add_argument("--smoke-run-id")
    smoke.add_argument("--smoke-review-file")
    _budgets(smoke)
    _mode(smoke)

    motion_smoke = commands.add_parser(
        "motion-smoke-test", help="preview or run one independent Runway motion test"
    )
    _project_root(motion_smoke)
    motion_smoke.add_argument("--keyframe", required=True)
    motion_smoke.add_argument("--model", default="gen4_turbo")
    motion_smoke.add_argument("--duration", type=int, default=5)
    motion_smoke.add_argument("--ratio", default="1280:720")
    motion_smoke.add_argument("--variations", type=int, default=1)
    motion_smoke.add_argument("--prompt", default="prompts/home-broll-v3.txt")
    _budgets(motion_smoke)
    _mode(motion_smoke)

    motion_v7 = commands.add_parser(
        "motion-v7-dry-run",
        help="prepare the three-candidate P1-1 Motion V7 experiment without provider submission",
    )
    _project_root(motion_v7)
    motion_v7.add_argument("--keyframe", required=True)

    motion_generate = commands.add_parser(
        "motion-generate", help="generate bounded Runway motion variations after a reviewed smoke"
    )
    _project_root(motion_generate)
    motion_generate.add_argument("--keyframe", required=True)
    motion_generate.add_argument("--model", default="gen4_turbo")
    motion_generate.add_argument("--duration", type=int, default=5)
    motion_generate.add_argument("--ratio", default="1280:720")
    motion_generate.add_argument("--variations", type=int, default=1)
    motion_generate.add_argument("--motion-smoke-run-id", required=True)
    motion_generate.add_argument("--motion-smoke-review-file", required=True)
    motion_generate.add_argument(
        "--motion-smoke-qa-attested",
        action="store_true",
        help="dry-run only: record owner-attested smoke QA without editing the review copy",
    )
    motion_generate.add_argument("--max-runway-credits", type=float)
    _mode(motion_generate)
    generate = commands.add_parser("generate", help="preview or generate shot alternatives")
    _project_root(generate)
    generate.add_argument("--preset", required=True, choices=("product_page", "tooltip", "homepage"))
    generate.add_argument("--single-shot", action="store_true")
    generate.add_argument("--smoke-run-id")
    generate.add_argument("--smoke-review-file")
    generate.add_argument("--motion-smoke-run-id")
    generate.add_argument("--motion-smoke-review-file")
    generate.add_argument("--talking-variations", type=int)
    generate.add_argument("--motion-variations", type=int)
    _budgets(generate)
    _mode(generate)

    keyframe = commands.add_parser("keyframe", help="derive review-only keyframe candidates")
    keyframe_commands = keyframe.add_subparsers(dest="keyframe_command", required=True)
    talking_crop = keyframe_commands.add_parser(
        "derive-talking-crop", help="create an unapproved deterministic talking crop"
    )
    _project_root(talking_crop)
    talking_crop.add_argument("--source", required=True)

    assemble = commands.add_parser("assemble", help="assemble explicitly selected shots")
    _project_root(assemble)
    assemble.add_argument("--run-id", required=True)
    assemble.add_argument("--selection-file", required=True)
    assemble.add_argument("--final-edits", type=int)

    report = commands.add_parser("report", help="show a video run summary")
    _project_root(report)
    report.add_argument("--run-id", required=True)

    subject_lock = commands.add_parser(
        "subject-lock", help="build offline subject-lock diagnostics for a motion review package"
    )
    _project_root(subject_lock)
    subject_lock.add_argument("--run-id", required=True)
    subject_lock.add_argument("--package-dir", required=True)

    promote = commands.add_parser("promote", help="promote a reviewed final candidate")
    _project_root(promote)
    promote.add_argument("--run-id", required=True)
    promote.add_argument("--candidate", required=True)
    promote.add_argument("--review-file", required=True)
    promote.add_argument("--approved-version", type=int)


def handle(args: argparse.Namespace) -> tuple[int, Any]:
    from .runner import handle_video_command

    return handle_video_command(args)


def _project_root(parser: argparse.ArgumentParser) -> None:
    from pathlib import Path

    parser.add_argument("--project-root", type=Path, default=Path.cwd())


def _mode(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")


def _budgets(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-provider-cost-usd", type=float)
    parser.add_argument("--max-runway-credits", type=float)
    parser.add_argument("--accept-unknown-provider-cost", action="store_true")
