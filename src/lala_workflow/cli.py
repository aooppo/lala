from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .config import ConfigError
from .domain import RunStatus
from .prompts import PromptError
from .providers.base import ProviderTaskError, WorkflowError
from .redaction import redact_text
from .reporting import promote_keyframe, read_run_summary
from .runner import LiveCallBlocked, RunOptions, run_generation, validate_project
from .video import cli as video_cli
from .video.validation import ExternalInputBlocked


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

    report = subparsers.add_parser("report", help="show an existing run summary")
    report.add_argument("--project-root", type=Path, default=Path.cwd())
    report.add_argument("--run-id", required=True)

    promote = subparsers.add_parser("promote", help="promote a reviewed output")
    promote.add_argument("--project-root", type=Path, default=Path.cwd())
    promote.add_argument("--run-id", required=True)
    promote.add_argument("--output-id", required=True)
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
        if args.command == "video":
            exit_code, payload = video_cli.handle(args)
            if isinstance(payload, str):
                print(payload, end="" if payload.endswith("\n") else "\n")
            else:
                print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
            return exit_code
        raise ValueError(f"unknown command: {args.command}")
    except (LiveCallBlocked, ExternalInputBlocked) as exc:
        print(f"BLOCKED_EXTERNAL: {redact_text(str(exc))}", file=sys.stderr)
        return 4
    except ProviderTaskError as exc:
        print(f"{exc.code}: {redact_text(str(exc))}", file=sys.stderr)
        return 3
    except (ConfigError, PromptError, WorkflowError, ValueError, OSError) as exc:
        print(redact_text(str(exc)), file=sys.stderr)
        return 2
