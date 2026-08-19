from __future__ import annotations

import argparse
from typing import Any


def configure_parser(subparsers: Any) -> None:
    video = subparsers.add_parser("video", help="validate and run Lady LaLa video workflows")
    commands = video.add_subparsers(dest="video_command", required=True)

    validate = commands.add_parser("validate", help="validate video inputs and configuration")
    _project_root(validate)

    smoke = commands.add_parser("talking-smoke-test", help="preview or run one short talking test")
    _project_root(smoke)
    smoke.add_argument("--preset", required=True, choices=("product_page", "tooltip", "homepage"))
    smoke.add_argument("--provider")
    smoke.add_argument("--audio")
    smoke.add_argument("--keyframe")
    smoke.add_argument("--variations", type=int)
    smoke.add_argument("--smoke-run-id")
    smoke.add_argument("--smoke-review-file")
    _mode(smoke)

    generate = commands.add_parser("generate", help="preview or generate shot alternatives")
    _project_root(generate)
    generate.add_argument("--preset", required=True, choices=("product_page", "tooltip", "homepage"))
    generate.add_argument("--single-shot", action="store_true")
    generate.add_argument("--smoke-run-id")
    generate.add_argument("--smoke-review-file")
    generate.add_argument("--talking-variations", type=int)
    generate.add_argument("--motion-variations", type=int)
    _mode(generate)

    assemble = commands.add_parser("assemble", help="assemble explicitly selected shots")
    _project_root(assemble)
    assemble.add_argument("--run-id", required=True)
    assemble.add_argument("--selection-file", required=True)
    assemble.add_argument("--final-edits", type=int)

    report = commands.add_parser("report", help="show a video run summary")
    _project_root(report)
    report.add_argument("--run-id", required=True)

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
