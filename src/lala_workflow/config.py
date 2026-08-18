from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from .domain import (
    AnchorImage,
    AnchorManifest,
    GenerationLimits,
    GenerationPreset,
    ModelCapabilities,
    ProjectConfig,
    ProviderCapabilities,
)
from .hashing import assert_within_directory, inspect_image, sha256_file


REQUIRED_ANCHORS = {"face", "full_body", "scene"}
TAG_RE = re.compile(r"^[a-z][a-z0-9_]+$")


class ConfigError(ValueError):
    pass


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file does not exist: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"configuration root must be a mapping: {path}")
    return data


def parse_manifest(data: Mapping[str, Any], project_root: Path) -> AnchorManifest:
    if data.get("project") != "lady-lala":
        raise ConfigError("anchor manifest project must be lady-lala")
    if data.get("status") != "approved":
        raise ConfigError("anchor manifest status must be approved")
    version = str(data.get("anchor_set_version", "")).strip()
    if not version:
        raise ConfigError("anchor_set_version is required")
    anchor_data = data.get("anchors")
    if not isinstance(anchor_data, Mapping):
        raise ConfigError("anchors must be a mapping")
    missing = sorted(REQUIRED_ANCHORS - set(anchor_data))
    if missing:
        raise ConfigError(f"missing required anchors: {', '.join(missing)}")
    qa_data = data.get("qa_references", {})
    if not isinstance(qa_data, Mapping):
        raise ConfigError("qa_references must be a mapping")

    seen_roles: set[str] = set()
    seen_tags: set[str] = set()
    approved_root = project_root / "assets/approved_anchors"

    def parse_group(group: Mapping[str, Any], *, generation_default: bool) -> dict[str, AnchorImage]:
        parsed: dict[str, AnchorImage] = {}
        for name, raw in group.items():
            if not isinstance(raw, Mapping):
                raise ConfigError(f"anchor {name} must be a mapping")
            role = str(raw.get("role", "")).strip()
            tag = str(raw.get("tag", "")).strip()
            if not role:
                raise ConfigError(f"anchor {name} has no role")
            if role in seen_roles:
                raise ConfigError(f"duplicate anchor role: {role}")
            if tag in seen_tags:
                raise ConfigError(f"duplicate anchor tag: {tag}")
            if not 3 <= len(tag) <= 16 or not TAG_RE.fullmatch(tag):
                raise ConfigError(f"invalid anchor tag: {tag}")
            relative = Path(str(raw.get("path", "")))
            if relative.is_absolute() or not relative.as_posix():
                raise ConfigError(f"anchor {name} path must be project-relative")
            source = project_root / relative
            try:
                resolved = assert_within_directory(source, approved_root)
                info = inspect_image(resolved)
            except (ValueError, OSError) as exc:
                raise ConfigError(f"invalid anchor {name}: {exc}") from exc
            if not os.access(resolved, os.R_OK):
                raise ConfigError(f"anchor is not readable: {relative}")
            priority = _positive_int(raw.get("priority"), f"anchor {name} priority")
            generation_input = bool(raw.get("generation_input", generation_default))
            seen_roles.add(role)
            seen_tags.add(tag)
            parsed[str(name)] = AnchorImage(
                name=str(name),
                path=resolved.relative_to(project_root.resolve()),
                role=role,
                tag=tag,
                priority=priority,
                generation_input=generation_input,
                sha256=sha256_file(resolved),
                mime_type=info.mime_type,
                width=info.width,
                height=info.height,
            )
        return parsed

    anchors = parse_group(anchor_data, generation_default=True)
    qa_references = parse_group(qa_data, generation_default=False)
    for name in REQUIRED_ANCHORS:
        if not anchors[name].generation_input:
            raise ConfigError(f"required anchor is not a generation input: {name}")
    return AnchorManifest(
        project="lady-lala",
        anchor_set_version=version,
        status="approved",
        anchors=anchors,
        qa_references=qa_references,
    )


def _parse_limits(raw: Mapping[str, Any]) -> GenerationLimits:
    limits = GenerationLimits(
        max_outputs_per_run=_positive_int(raw.get("max_outputs_per_run"), "max_outputs_per_run"),
        max_concurrency=_positive_int(raw.get("max_concurrency"), "max_concurrency"),
        max_retries=_nonnegative_int(raw.get("max_retries"), "max_retries"),
        poll_timeout_seconds=_positive_float(raw.get("poll_timeout_seconds"), "poll_timeout_seconds"),
        overall_timeout_seconds=_positive_float(
            raw.get("overall_timeout_seconds"), "overall_timeout_seconds"
        ),
        network_timeout_seconds=_positive_float(
            raw.get("network_timeout_seconds"), "network_timeout_seconds"
        ),
        download_timeout_seconds=_positive_float(
            raw.get("download_timeout_seconds"), "download_timeout_seconds"
        ),
        allow_live_calls=bool(raw.get("allow_live_calls", False)),
        estimated_credits_per_output=_optional_nonnegative_float(
            raw.get("estimated_credits_per_output"), "estimated_credits_per_output"
        ),
        max_estimated_credits=_optional_nonnegative_float(
            raw.get("max_estimated_credits"), "max_estimated_credits"
        ),
    )
    if limits.overall_timeout_seconds < limits.poll_timeout_seconds:
        raise ConfigError("overall_timeout_seconds must be >= poll_timeout_seconds")
    return limits


def _parse_provider(name: str, raw: Mapping[str, Any]) -> ProviderCapabilities:
    models = tuple(str(item) for item in _required_list(raw, "supported_models"))
    ratios = tuple(str(item) for item in _required_list(raw, "supported_ratios"))
    model_data = raw.get("model_capabilities")
    if not isinstance(model_data, Mapping):
        raise ConfigError(f"provider {name} model_capabilities must be a mapping")
    capabilities: dict[str, ModelCapabilities] = {}
    for model in models:
        item = model_data.get(model)
        if not isinstance(item, Mapping):
            raise ConfigError(f"missing capabilities for model {model}")
        min_refs = _nonnegative_int(item.get("min_references"), f"{model} min_references")
        max_refs = _nonnegative_int(item.get("max_references"), f"{model} max_references")
        if min_refs > max_refs:
            raise ConfigError(f"invalid reference range for model {model}")
        capabilities[model] = ModelCapabilities(min_refs, max_refs, bool(item.get("supports_seed")))
    poll_interval = _positive_float(raw.get("poll_interval_seconds"), "poll_interval_seconds")
    if name == "runway" and poll_interval < 5:
        raise ConfigError("Runway poll_interval_seconds must be at least 5")
    return ProviderCapabilities(
        provider=name,
        api_version=str(raw.get("api_version", "")),
        sdk_version=str(raw.get("sdk_version", "")),
        endpoint=str(raw.get("endpoint", "")),
        poll_endpoint=str(raw.get("poll_endpoint", "")),
        poll_interval_seconds=poll_interval,
        supported_models=models,
        supported_ratios=ratios,
        model_capabilities=capabilities,
        seed_min=_nonnegative_int(raw.get("seed_min"), "seed_min"),
        seed_max=_nonnegative_int(raw.get("seed_max"), "seed_max"),
        tag_pattern=str(raw.get("tag_pattern", "")),
        tag_min_length=_positive_int(raw.get("tag_min_length"), "tag_min_length"),
        tag_max_length=_positive_int(raw.get("tag_max_length"), "tag_max_length"),
        prompt_utf16_max=_positive_int(raw.get("prompt_utf16_max"), "prompt_utf16_max"),
        data_uri_max_chars=_positive_int(raw.get("data_uri_max_chars"), "data_uri_max_chars"),
    )


def _parse_presets(
    project_root: Path,
    files: tuple[Path, ...],
    manifest: AnchorManifest,
    max_outputs: int,
) -> dict[str, GenerationPreset]:
    presets: dict[str, GenerationPreset] = {}
    available = set(manifest.anchors) | set(manifest.qa_references)
    for path in files:
        raw = load_yaml(path).get("presets")
        if not isinstance(raw, Mapping):
            raise ConfigError(f"presets must be a mapping: {path}")
        for name, item in raw.items():
            if name in presets:
                raise ConfigError(f"duplicate preset: {name}")
            if not isinstance(item, Mapping):
                raise ConfigError(f"preset {name} must be a mapping")
            references = tuple(str(value) for value in _required_list(item, "references"))
            if len(set(references)) != len(references):
                raise ConfigError(f"preset {name} has duplicate references")
            missing = sorted(set(references) - available)
            if missing:
                raise ConfigError(f"preset {name} references unknown anchors: {', '.join(missing)}")
            count = _positive_int(item.get("default_count"), f"preset {name} default_count")
            if count > max_outputs:
                raise ConfigError(f"preset {name} count exceeds max_outputs_per_run")
            prompt_file = Path(str(item.get("prompt_file", "")))
            if prompt_file.is_absolute():
                raise ConfigError(f"preset {name} prompt_file must be project-relative")
            presets[str(name)] = GenerationPreset(
                name=str(name),
                purpose=str(item.get("purpose", "")).strip(),
                references=references,
                prompt_file=prompt_file,
                default_count=count,
                default_ratio=str(item.get("default_ratio", "")),
            )
    required = {"baseline_identity", "home_decor", "product_page_clean"}
    missing_presets = sorted(required - set(presets))
    if missing_presets:
        raise ConfigError(f"missing required presets: {', '.join(missing_presets)}")
    return presets


def load_project_config(project_root: Path) -> ProjectConfig:
    root = project_root.resolve()
    generation = load_yaml(root / "configs/generation.yaml")
    limits_data = generation.get("limits")
    if not isinstance(limits_data, Mapping):
        raise ConfigError("generation limits must be a mapping")
    limits = _parse_limits(limits_data)
    manifest = parse_manifest(load_yaml(root / "configs/anchor-manifest.yaml"), root)
    provider_data = generation.get("providers")
    if not isinstance(provider_data, Mapping):
        raise ConfigError("providers must be a mapping")
    providers = {
        str(name): _parse_provider(str(name), raw)
        for name, raw in provider_data.items()
        if isinstance(raw, Mapping)
    }
    provider = str(generation.get("provider", ""))
    model = str(generation.get("model", ""))
    ratio = str(generation.get("ratio", ""))
    if provider not in providers:
        raise ConfigError(f"unknown default provider: {provider}")
    capabilities = providers[provider]
    if model not in capabilities.supported_models:
        raise ConfigError(f"unsupported default model for {provider}: {model}")
    if ratio not in capabilities.supported_ratios:
        raise ConfigError(f"unsupported default ratio for {provider}: {ratio}")
    presets = _parse_presets(
        root,
        (root / "configs/look-presets.yaml", root / "configs/scene-presets.yaml"),
        manifest,
        limits.max_outputs_per_run,
    )
    for preset in presets.values():
        if preset.default_ratio not in capabilities.supported_ratios:
            raise ConfigError(f"preset {preset.name} has unsupported ratio: {preset.default_ratio}")
    return ProjectConfig(root, manifest, presets, provider, model, ratio, limits, providers)


def env_flag(value: str | None) -> bool:
    return value == "true"


def _required_list(raw: Mapping[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{key} must be a non-empty list")
    return value


def _positive_int(value: Any, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if isinstance(value, bool) or parsed <= 0:
        raise ConfigError(f"{name} must be positive")
    return parsed


def _nonnegative_int(value: Any, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if isinstance(value, bool) or parsed < 0:
        raise ConfigError(f"{name} must be non-negative")
    return parsed


def _positive_float(value: Any, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a number") from exc
    if parsed <= 0:
        raise ConfigError(f"{name} must be positive")
    return parsed


def _optional_nonnegative_float(value: Any, name: str) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a number or null") from exc
    if parsed < 0:
        raise ConfigError(f"{name} must be non-negative")
    return parsed
