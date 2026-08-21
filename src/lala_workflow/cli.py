from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .config import ConfigError
from .domain import RunStatus
from .domain import to_primitive
from .prompts import PromptError
from .providers.base import ProviderTaskError, WorkflowError
from .redaction import redact_text
from .reporting import promote_keyframe, read_run_summary
from .runner import LiveCallBlocked, RunOptions, run_generation, validate_project
from .video import cli as video_cli
from .video.validation import ExternalInputBlocked
from .characters.errors import (
    CharacterError,
    MotionSubmissionUnknownError,
    PreviewUnavailableError,
)
from .characters.validation import DEFAULT_MAX_UPLOAD_BYTES
from .redaction import sanitize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lala-workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate configuration and approved anchors")
    validate.add_argument("--project-root", type=Path, default=Path.cwd())

    generate = subparsers.add_parser("generate", help="preview or run a generation batch")
    generate.add_argument("--project-root", type=Path, default=Path.cwd())
    generate.add_argument("--preset", required=True)
    generate.add_argument("--count", type=int)
    generate.add_argument("--provider")
    generate.add_argument("--model")
    generate.add_argument("--ratio")
    generate.add_argument("--resolution")
    generate.add_argument("--seed", type=int)
    generate.add_argument("--concurrency", type=int)
    generate.add_argument("--retries", type=int)
    generate.add_argument("--timeout", type=float)
    generate.add_argument("--overall-timeout", type=float)
    generate.add_argument("--max-estimated-credits", type=float)
    generate.add_argument("--dry-run", action="store_true")
    generate.add_argument("--live", action="store_true")
    generate.add_argument("--character")

    report = subparsers.add_parser("report", help="show an existing run summary")
    report.add_argument("--project-root", type=Path, default=Path.cwd())
    report.add_argument("--run-id", required=True)

    promote = subparsers.add_parser("promote", help="promote a reviewed output")
    promote.add_argument("--project-root", type=Path, default=Path.cwd())
    promote.add_argument("--run-id", required=True)
    promote.add_argument("--output-id", required=True)

    character = subparsers.add_parser("character", help="create, review, and switch characters")
    character_commands = character.add_subparsers(dest="character_command", required=True)
    character_list = character_commands.add_parser("list", help="list characters")
    character_list.add_argument("--project-root", type=Path, default=Path.cwd())
    character_show = character_commands.add_parser("show", help="show one character")
    character_show.add_argument("character_id")
    character_show.add_argument("--project-root", type=Path, default=Path.cwd())
    character_import = character_commands.add_parser("import", help="import character photos")
    character_import.add_argument("--face", required=True, type=Path)
    character_import.add_argument("--full-body", required=True, type=Path)
    character_import.add_argument("--three-quarter", required=True, type=Path)
    character_import.add_argument("--name")
    character_import.add_argument("--project-root", type=Path, default=Path.cwd())
    character_build = character_commands.add_parser("build", help="validate and prepare a character")
    character_build.add_argument("character_id")
    character_build.add_argument("--project-root", type=Path, default=Path.cwd())
    character_preview = character_commands.add_parser("preview", help="plan or generate previews")
    character_preview.add_argument("character_id")
    character_preview.add_argument("--dry-run", action="store_true")
    character_preview.add_argument("--live", action="store_true")
    character_preview.add_argument("--max-runway-credits", type=float)
    character_preview.add_argument("--project-root", type=Path, default=Path.cwd())
    character_motion_recover = character_commands.add_parser(
        "motion-recover", help="resume or safely recover motion without regenerating static preview"
    )
    character_motion_recover.add_argument("character_id")
    character_motion_recover.add_argument("--live", action="store_true")
    character_motion_recover.add_argument("--max-runway-credits", type=float, required=True)
    character_motion_recover.add_argument("--project-root", type=Path, default=Path.cwd())
    character_activate = character_commands.add_parser("activate", help="approve and activate")
    character_activate.add_argument("character_id")
    character_activate.add_argument("--project-root", type=Path, default=Path.cwd())
    character_activate.add_argument("--expected-revision", type=int)
    character_reject = character_commands.add_parser("reject", help="reject a staging character")
    character_reject.add_argument("character_id")
    character_reject.add_argument("--project-root", type=Path, default=Path.cwd())
    character_reject.add_argument("--expected-revision", type=int)
    video_cli.configure_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return int(exc.code)
    try:
        from .env import load_project_env

        load_project_env(getattr(args, "project_root", Path.cwd()))
        if args.command == "validate":
            payload = validate_project(args.project_root)
            print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "generate":
            if args.dry_run and args.live:
                raise ValueError("--dry-run and --live are mutually exclusive")
            outcome = run_generation(
                args.project_root,
                RunOptions(
                    preset=args.preset,
                    count=args.count,
                    provider=args.provider,
                    model=args.model,
                    ratio=args.ratio,
                    resolution=args.resolution,
                    seed=args.seed,
                    concurrency=args.concurrency,
                    max_retries=args.retries,
                    poll_timeout_seconds=args.timeout,
                    overall_timeout_seconds=args.overall_timeout,
                    max_estimated_credits=args.max_estimated_credits,
                    live=bool(args.live),
                    character_id=args.character,
                ),
            )
            print(
                json.dumps(
                    {
                        "run_id": outcome.run_id,
                        "run_dir": str(outcome.run_dir),
                        "mode": "live" if args.live else "dry-run",
                        "requests": len(outcome.result.requests),
                        "status": outcome.result.status.value,
                        "outputs": len(outcome.result.outputs),
                    },
                    indent=2,
                )
            )
            if args.live and outcome.result.status in {RunStatus.FAILED, RunStatus.PARTIAL}:
                return 3
            return 0
        if args.command == "report":
            print(read_run_summary(args.project_root, args.run_id), end="")
            return 0
        if args.command == "promote":
            record = promote_keyframe(args.project_root, args.run_id, args.output_id)
            print(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "character":
            payload = _handle_character(args)
            print(json.dumps(sanitize(to_primitive(payload)), indent=2, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "video":
            exit_code, payload = video_cli.handle(args)
            if isinstance(payload, str):
                print(payload, end="" if payload.endswith("\n") else "\n")
            else:
                print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
            return exit_code
        raise ValueError(f"unknown command: {args.command}")
    except MotionSubmissionUnknownError as exc:
        print(f"BLOCKED_SUBMISSION_UNKNOWN: {redact_text(str(exc))}", file=sys.stderr)
        return 4
    except (LiveCallBlocked, ExternalInputBlocked, PreviewUnavailableError) as exc:
        print(f"BLOCKED_EXTERNAL: {redact_text(str(exc))}", file=sys.stderr)
        return 4
    except ProviderTaskError as exc:
        print(f"{exc.code}: {redact_text(str(exc))}", file=sys.stderr)
        return 3
    except (ConfigError, PromptError, WorkflowError, CharacterError, ValueError, OSError) as exc:
        print(redact_text(str(exc)), file=sys.stderr)
        return 2


def _handle_character(args):
    from .characters.domain import CharacterUpload
    from .characters.service import CharacterService

    command = args.character_command
    credit_cap = getattr(args, "max_runway_credits", None)
    if credit_cap is not None and (credit_cap <= 0 or credit_cap > 25):
        raise ValueError("--max-runway-credits must be positive and at most 25")
    service = CharacterService(
        args.project_root, max_runway_credits=credit_cap if credit_cap is not None else 25.0
    )
    if command == "list":
        return service.list_characters()
    if command == "show":
        return service.show(args.character_id)
    if command == "import":
        uploads = {}
        for role, path in (
            ("face", args.face),
            ("full_body", args.full_body),
            ("three_quarter", args.three_quarter),
        ):
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"unsafe or missing input for {role}")
            if path.stat().st_size > DEFAULT_MAX_UPLOAD_BYTES:
                raise ValueError(f"input for {role} exceeds the upload size limit")
            uploads[role] = CharacterUpload(role, path.read_bytes(), path.name)
        return service.import_character(uploads, display_name=args.name, created_by="cli")
    if command == "build":
        return service.build(args.character_id)
    if command == "preview":
        if args.dry_run and args.live:
            raise ValueError("--dry-run and --live are mutually exclusive")
        if args.max_runway_credits is not None and not args.live:
            raise ValueError("--max-runway-credits is valid only with --live")
        return service.preview(args.character_id, live=bool(args.live))
    if command == "motion-recover":
        if not args.live:
            raise ValueError("motion-recover requires explicit --live")
        return service.recover_motion(args.character_id, live=True)
    if command == "activate":
        return service.approve_and_activate(
            args.character_id, expected_revision=args.expected_revision
        )
    if command == "reject":
        return service.reject(args.character_id, expected_revision=args.expected_revision)
    raise ValueError(f"unknown character command: {command}")
