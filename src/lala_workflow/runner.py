from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from .config import ConfigError, env_flag, load_project_config
from .domain import (
    GenerationRequest,
    GenerationResult,
    OutputArtifact,
    ProviderTaskResult,
    ReferenceImage,
    ResolvedRunConfig,
    RunStatus,
    TaskStatus,
    to_primitive,
    utc_now,
)
from .prompts import load_prompt
from .providers.base import (
    ImageProvider,
    ProviderSubmissionError,
    WorkflowError,
    validate_request_capabilities,
)
from .reporting import review_csv_text, summary_markdown
from .storage import RunContext, RunStorage


class LiveCallBlocked(WorkflowError):
    code = "live_call_blocked"


@dataclass(frozen=True, slots=True)
class RunOptions:
    preset: str
    count: int | None = None
    provider: str | None = None
    model: str | None = None
    ratio: str | None = None
    resolution: str | None = None
    seed: int | None = None
    concurrency: int | None = None
    max_retries: int | None = None
    poll_timeout_seconds: float | None = None
    overall_timeout_seconds: float | None = None
    max_estimated_credits: float | None = None
    live: bool = False
    character_id: str | None = None
    allow_staging_character: bool = False
    reference_names: tuple[str, ...] | None = None
    prompt_file: Path | None = None


@dataclass(frozen=True, slots=True)
class RunOutcome:
    run_id: str
    run_dir: Path
    result: GenerationResult


def run_generation(
    project_root: Path,
    options: RunOptions,
    *,
    provider: ImageProvider | None = None,
    environment: Mapping[str, str] | None = None,
) -> RunOutcome:
    config = load_project_config(project_root)
    character = None
    registry_path = config.root / "configs/characters/registry.yaml"
    if registry_path.is_file() or options.character_id is not None:
        from .characters.resolver import CharacterResolver

        character = CharacterResolver(config.root).resolve(
            options.character_id, allow_staging=options.allow_staging_character
        )
        config = replace(config, manifest=character.manifest)
    if options.preset not in config.presets:
        raise ConfigError(f"unknown preset: {options.preset}")
    preset = config.presets[options.preset]
    provider_name = options.provider or config.provider
    if provider_name not in config.providers:
        raise ConfigError(f"unknown provider: {provider_name}")
    capabilities = config.providers[provider_name]
    model = options.model or config.model
    if model not in capabilities.supported_models:
        raise ConfigError(f"unsupported model for {provider_name}: {model}")
    count = options.count if options.count is not None else preset.default_count
    if count < 1 or count > config.limits.max_outputs_per_run:
        raise ValueError(
            f"count must be 1..max_outputs_per_run ({config.limits.max_outputs_per_run})"
        )
    concurrency = (
        options.concurrency if options.concurrency is not None else config.limits.max_concurrency
    )
    if not 1 <= concurrency <= config.limits.max_concurrency:
        raise ValueError(f"concurrency must be 1..{config.limits.max_concurrency}")
    max_retries = (
        options.max_retries if options.max_retries is not None else config.limits.max_retries
    )
    if not 0 <= max_retries <= config.limits.max_retries:
        raise ValueError(f"max_retries must be 0..{config.limits.max_retries}")
    ratio = options.ratio or options.resolution or preset.default_ratio
    if options.ratio and options.resolution and options.ratio != options.resolution:
        raise ValueError("ratio and resolution must be identical when both are supplied")
    if ratio not in capabilities.supported_ratios:
        raise ValueError(f"unsupported ratio/resolution for {provider_name}: {ratio}")
    poll_timeout = (
        options.poll_timeout_seconds
        if options.poll_timeout_seconds is not None
        else config.limits.poll_timeout_seconds
    )
    overall_timeout = (
        options.overall_timeout_seconds
        if options.overall_timeout_seconds is not None
        else config.limits.overall_timeout_seconds
    )
    if poll_timeout <= 0 or overall_timeout <= 0 or overall_timeout < poll_timeout:
        raise ValueError("timeouts must be positive and overall timeout must be >= poll timeout")
    if options.seed is not None:
        if options.seed < capabilities.seed_min or options.seed + count - 1 > capabilities.seed_max:
            raise ValueError(
                f"seed range must stay within {capabilities.seed_min}..{capabilities.seed_max}"
            )

    env = dict(os.environ if environment is None else environment)
    allow_live = env_flag(env.get("RUNWAY_ALLOW_LIVE_CALLS"))
    max_estimated = (
        options.max_estimated_credits
        if options.max_estimated_credits is not None
        else config.limits.max_estimated_credits
    )
    api_secret = env.get("RUNWAYML_API_SECRET", "")
    if options.live:
        if not allow_live or not api_secret:
            raise LiveCallBlocked(
                "Runway live smoke test requires valid credentials and explicit paid-call permission."
            )
        if env_flag(env.get("RUNWAY_LIVE_SMOKE_TEST")) and count != 1:
            raise LiveCallBlocked("live smoke-test mode permits exactly one output")
        if max_estimated is not None:
            estimate = config.limits.estimated_credits_per_output
            if estimate is None:
                raise LiveCallBlocked(
                    "estimated-credit ceiling is set but estimated_credits_per_output is unavailable"
                )
            if count * estimate > max_estimated:
                raise LiveCallBlocked(
                    f"estimated credits {count * estimate:g} exceed ceiling {max_estimated:g}"
                )
    storage = RunStorage(config.root, secrets=(api_secret,))

    reference_catalog = {**config.manifest.anchors, **config.manifest.qa_references}
    reference_names = options.reference_names or preset.references
    references = tuple(
        ReferenceImage(
            name=anchor.name,
            path=config.root / anchor.path,
            role=anchor.role,
            tag=anchor.tag,
            sha256=anchor.sha256,
            mime_type=anchor.mime_type,
        )
        for anchor in (reference_catalog[name] for name in reference_names)
    )
    prompt = load_prompt(
        config.root,
        options.prompt_file or preset.prompt_file,
        selected_tags={reference.tag for reference in references},
        max_utf16_units=capabilities.prompt_utf16_max,
    )

    # Allocate only after every free validation succeeds.
    provisional_run_id = "PENDING"
    provisional = tuple(
        GenerationRequest(
            run_id=provisional_run_id,
            output_id=f"output-{index + 1:03d}",
            preset=preset.name,
            provider=provider_name,
            model=model,
            ratio=ratio,
            resolution=ratio,
            prompt=prompt,
            references=references,
            seed=None if options.seed is None else options.seed + index,
            output_count=1,
            character_id=character.profile.character_id if character else None,
            character_profile_version=character.profile.profile_version if character else None,
            character_profile_sha256=character.profile.profile_sha256 if character else None,
            character_source_hashes=(
                {name: item.sha256 for name, item in character.profile.references.items()}
                if character
                else {}
            ),
        )
        for index in range(count)
    )
    for request in provisional:
        validate_request_capabilities(request, capabilities)

    run = storage.create_run(provider_name, preset.name)
    requests = tuple(
        GenerationRequest(
            run_id=run.run_id,
            output_id=request.output_id,
            preset=request.preset,
            provider=request.provider,
            model=request.model,
            ratio=request.ratio,
            resolution=request.resolution,
            prompt=request.prompt,
            references=request.references,
            seed=request.seed,
            output_count=request.output_count,
            character_id=request.character_id,
            character_profile_version=request.character_profile_version,
            character_profile_sha256=request.character_profile_sha256,
            character_source_hashes=request.character_source_hashes,
        )
        for request in provisional
    )
    resolved = ResolvedRunConfig(
        run_id=run.run_id,
        preset=preset.name,
        provider=provider_name,
        model=model,
        ratio=ratio,
        resolution=ratio,
        count=count,
        concurrency=concurrency,
        max_retries=max_retries,
        poll_timeout_seconds=poll_timeout,
        overall_timeout_seconds=overall_timeout,
        network_timeout_seconds=config.limits.network_timeout_seconds,
        download_timeout_seconds=config.limits.download_timeout_seconds,
        live=options.live,
        allow_live_calls=allow_live,
        estimated_credits_per_output=config.limits.estimated_credits_per_output,
        max_estimated_credits=max_estimated,
        api_version=capabilities.api_version,
        sdk_version=capabilities.sdk_version,
        anchor_set_version=config.manifest.anchor_set_version,
        character_id=character.profile.character_id if character else None,
        character_profile_version=character.profile.profile_version if character else None,
        character_profile_sha256=character.profile.profile_sha256 if character else None,
        character_selection_source=character.selection_source if character else None,
    )
    _write_input_artifacts(storage, run, config, preset.name, resolved, prompt.text, requests)
    storage.append_event(run, "validated", {"mode": "live" if options.live else "dry-run"})

    if options.live:
        storage.append_event(
            run,
            "live_execution_authorized",
            {
                "count": resolved.count,
                "concurrency": resolved.concurrency,
                "max_retries": resolved.max_retries,
                "overall_timeout_seconds": resolved.overall_timeout_seconds,
                "max_estimated_credits": resolved.max_estimated_credits,
            },
        )
        live_provider = provider or _create_provider(
            provider_name,
            capabilities,
            api_secret,
            resolved.network_timeout_seconds,
            resolved.max_retries,
            lambda event, details: storage.append_event(run, event, details),
        )
        result, paid_calls = _execute_live(
            config.root,
            live_provider,
            storage,
            run,
            resolved,
            requests,
            secret=api_secret,
        )
        storage.append_event(
            run,
            "run_completed",
            {
                "status": result.status.value,
                "outputs": len(result.outputs),
                "errors": len(result.errors),
                "paid_calls": paid_calls,
            },
        )
        _write_final_artifacts(storage, run, resolved, result, paid_calls=paid_calls)
        return RunOutcome(run.run_id, run.path, result)

    started = utc_now()
    completed = utc_now()
    request_payloads = tuple(to_primitive(request) for request in requests)
    result = GenerationResult(
        run_id=run.run_id,
        provider=provider_name,
        model=model,
        status=RunStatus.DRY_RUN,
        started_at=started,
        completed_at=completed,
        duration_seconds=max(0.0, (completed - started).total_seconds()),
        requests=request_payloads,
    )
    storage.append_event(run, "dry_run_completed", {"request_count": len(requests)})
    _write_final_artifacts(storage, run, resolved, result, paid_calls=0)
    return RunOutcome(run.run_id, run.path, result)


def _create_provider(
    provider_name,
    capabilities,
    api_secret: str,
    network_timeout_seconds: float,
    max_poll_retries: int,
    event_sink,
) -> ImageProvider:
    if provider_name != "runway":
        raise ConfigError(f"no provider adapter is implemented for: {provider_name}")
    from .providers.runway import RunwayImageProvider

    return RunwayImageProvider(
        capabilities,
        api_key=api_secret,
        network_timeout_seconds=network_timeout_seconds,
        max_poll_retries=max_poll_retries,
        event_sink=event_sink,
    )


def _execute_live(
    project_root: Path,
    provider: ImageProvider,
    storage: RunStorage,
    run: RunContext,
    resolved: ResolvedRunConfig,
    requests: tuple[GenerationRequest, ...],
    *,
    secret: str,
) -> tuple[GenerationResult, int]:
    started = utc_now()
    deadline = time.monotonic() + resolved.overall_timeout_seconds
    output_dir = project_root / "outputs" / run.run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    paid_calls = [0]
    paid_lock = threading.Lock()

    def execute(request: GenerationRequest) -> dict[str, Any]:
        provider.validate_request(request)
        task_id: str | None = None
        last_error: Exception | None = None
        for attempt in range(resolved.max_retries + 1):
            if time.monotonic() >= deadline:
                storage.append_event(
                    run,
                    "overall_timeout",
                    {"output_id": request.output_id, "phase": "before_submission"},
                )
                return _execution_error(request.output_id, "overall_timeout", "overall timeout reached")
            storage.append_event(
                run,
                "submit_attempt",
                {"output_id": request.output_id, "attempt": attempt + 1},
            )
            with paid_lock:
                paid_calls[0] += 1
            try:
                task_id = provider.submit(request)
                storage.append_event(
                    run,
                    "task_submitted",
                    {"output_id": request.output_id, "provider_task_id": task_id},
                )
                break
            except Exception as exc:
                last_error = exc
                storage.append_event(
                    run,
                    "submission_retry" if attempt < resolved.max_retries else "submission_failed",
                    {
                        "output_id": request.output_id,
                        "attempt": attempt + 1,
                        "error": str(exc),
                    },
                )
        if task_id is None:
            code = getattr(last_error, "code", "provider_submission_error")
            return _execution_error(request.output_id, code, str(last_error or "submission failed"))
        remaining = max(0.001, deadline - time.monotonic())
        task_timeout = min(resolved.poll_timeout_seconds, remaining)
        try:
            task_result = provider.wait(task_id, task_timeout)
        except Exception as exc:
            return _execution_error(
                request.output_id,
                getattr(exc, "code", "provider_wait_error"),
                str(exc),
                task_id,
            )
        task_payload = {
            "output_id": request.output_id,
            "provider_task_id": task_result.provider_task_id,
            "status": task_result.status.value,
            "error_code": task_result.error_code,
            "error_message": task_result.error_message,
            "started_at": task_result.started_at,
            "completed_at": task_result.completed_at,
        }
        storage.append_event(run, "task_terminal", task_payload)
        if task_result.status is not TaskStatus.SUCCEEDED:
            return {
                "task": task_payload,
                "outputs": (),
                "error": {
                    "output_id": request.output_id,
                    "provider_task_id": task_id,
                    "code": task_result.error_code or task_result.status.value.lower(),
                    "message": task_result.error_message or f"task {task_result.status.value.lower()}",
                },
            }
        download_time_remaining = deadline - time.monotonic()
        if download_time_remaining <= 0:
            storage.append_event(
                run,
                "overall_timeout",
                {
                    "output_id": request.output_id,
                    "provider_task_id": task_id,
                    "phase": "before_download",
                },
            )
            return {
                "task": task_payload,
                "outputs": (),
                "error": {
                    "output_id": request.output_id,
                    "provider_task_id": task_id,
                    "code": "overall_timeout",
                    "message": "overall timeout reached before output download",
                },
            }
        try:
            artifacts = provider.download_results(
                task_result,
                output_dir,
                request.output_id,
                min(resolved.download_timeout_seconds, download_time_remaining),
                resolved.max_retries,
            )
        except Exception as exc:
            return {
                "task": task_payload,
                "outputs": (),
                "error": {
                    "output_id": request.output_id,
                    "provider_task_id": task_id,
                    "code": getattr(exc, "code", "provider_download_error"),
                    "message": str(exc),
                },
            }
        normalized = tuple(
            replace(
                artifact,
                file=(
                    artifact.file.resolve().relative_to(project_root.resolve())
                    if artifact.file.is_absolute()
                    else artifact.file
                ),
            )
            for artifact in artifacts
        )
        if not normalized:
            return {
                "task": task_payload,
                "outputs": (),
                "error": {
                    "output_id": request.output_id,
                    "provider_task_id": task_id,
                    "code": "empty_download",
                    "message": "provider produced no downloaded output",
                },
            }
        return {"task": task_payload, "outputs": normalized, "error": None}

    executions: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=resolved.concurrency, thread_name_prefix="lala-image") as pool:
        future_map = {pool.submit(execute, request): request.output_id for request in requests}
        for future in as_completed(future_map):
            output_id = future_map[future]
            try:
                executions.append(future.result())
            except Exception as exc:
                executions.append(
                    _execution_error(output_id, getattr(exc, "code", "workflow_error"), str(exc))
                )

    outputs = tuple(
        sorted(
            (artifact for item in executions for artifact in item.get("outputs", ())),
            key=lambda artifact: artifact.output_id,
        )
    )
    tasks = tuple(
        sorted(
            (item["task"] for item in executions if item.get("task")),
            key=lambda item: item["output_id"],
        )
    )
    errors = tuple(
        sorted(
            (item["error"] for item in executions if item.get("error")),
            key=lambda item: item["output_id"],
        )
    )
    if outputs and not errors:
        status = RunStatus.SUCCEEDED
    elif outputs:
        status = RunStatus.PARTIAL
    else:
        status = RunStatus.FAILED
    completed = utc_now()
    result = GenerationResult(
        run_id=run.run_id,
        provider=resolved.provider,
        model=resolved.model,
        status=status,
        started_at=started,
        completed_at=completed,
        duration_seconds=max(0.0, (completed - started).total_seconds()),
        requests=tuple(to_primitive(request) for request in requests),
        tasks=tasks,
        outputs=outputs,
        errors=errors,
    )
    return result, paid_calls[0]


def _execution_error(
    output_id: str,
    code: str,
    message: str,
    provider_task_id: str | None = None,
) -> dict[str, Any]:
    return {
        "task": None,
        "outputs": (),
        "error": {
            "output_id": output_id,
            "provider_task_id": provider_task_id,
            "code": code,
            "message": message,
        },
    }


def validate_project(project_root: Path) -> dict[str, object]:
    config = load_project_config(project_root)
    capabilities = config.providers[config.provider]
    reference_catalog = {**config.manifest.anchors, **config.manifest.qa_references}
    prompts: dict[str, str] = {}
    for preset in config.presets.values():
        refs = tuple(reference_catalog[name] for name in preset.references)
        prompt = load_prompt(
            config.root,
            preset.prompt_file,
            selected_tags={item.tag for item in refs},
            max_utf16_units=capabilities.prompt_utf16_max,
        )
        prompts[preset.name] = prompt.sha256
    return {
        "project": config.manifest.project,
        "anchor_set_version": config.manifest.anchor_set_version,
        "anchors": {
            name: {"path": item.path.as_posix(), "sha256": item.sha256}
            for name, item in config.manifest.anchors.items()
        },
        "qa_references": sorted(config.manifest.qa_references),
        "presets": sorted(config.presets),
        "prompt_hashes": prompts,
        "provider": config.provider,
        "models": list(capabilities.supported_models),
        "api_version": capabilities.api_version,
        "sdk_version": capabilities.sdk_version,
    }


def _write_input_artifacts(
    storage: RunStorage,
    run: RunContext,
    config,
    preset_name: str,
    resolved: ResolvedRunConfig,
    prompt_text: str,
    requests: tuple[GenerationRequest, ...],
) -> None:
    storage.write_json(
        run,
        "request.json",
        {"run_id": run.run_id, "preset": preset_name, "requests": requests},
    )
    storage.write_yaml(run, "resolved-config.yaml", resolved)
    storage.write_text(run, "resolved-prompt.txt", prompt_text + "\n")
    all_anchors = {**config.manifest.anchors, **config.manifest.qa_references}
    selected = {reference.name for request in requests[:1] for reference in request.references}
    storage.write_json(
        run,
        "anchor-hashes.json",
        {
            "anchor_set_version": config.manifest.anchor_set_version,
            "character": {
                "character_id": resolved.character_id,
                "profile_version": resolved.character_profile_version,
                "profile_sha256": resolved.character_profile_sha256,
                "selection_source": resolved.character_selection_source,
                "source_hashes": (
                    requests[0].character_source_hashes if requests else {}
                ),
            }
            if resolved.character_id
            else None,
            "anchors": {
                name: {
                    "path": item.path.as_posix(),
                    "role": item.role,
                    "tag": item.tag,
                    "sha256": item.sha256,
                    "selected": name in selected,
                    "generation_input": item.generation_input,
                }
                for name, item in all_anchors.items()
            },
        },
    )


def _write_final_artifacts(
    storage: RunStorage,
    run: RunContext,
    resolved: ResolvedRunConfig,
    result: GenerationResult,
    *,
    paid_calls: int,
) -> None:
    storage.write_json(run, "result.json", result)
    requests_by_output = {
        str(item.get("output_id")): item for item in result.requests if isinstance(item, Mapping)
    }
    storage.write_text(run, "review.csv", review_csv_text(result, requests_by_output))
    storage.write_text(
        run,
        "summary.md",
        summary_markdown(resolved, result, paid_calls=paid_calls),
    )
