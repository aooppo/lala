from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Iterable

from .domain import to_primitive


REDACTED = "[REDACTED]"
SENSITIVE_KEY_RE = re.compile(
    r"(?:authorization|x[_-]?api[_-]?key|api[_-]?key|api[_-]?secret|secret|"
    r"credential|access[_-]?token|refresh[_-]?token|password|cookie|signature)",
    re.IGNORECASE,
)
BEARER_RE = re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+")
DATA_URI_RE = re.compile(r"(data:[^;,]+;base64,)[^\s\"']+", re.IGNORECASE)


def redact_text(text: str, secrets: Iterable[str] = ()) -> str:
    redacted = BEARER_RE.sub(lambda match: match.group(1) + REDACTED, text)
    redacted = DATA_URI_RE.sub(lambda match: match.group(1) + REDACTED, redacted)
    for secret in sorted({item for item in secrets if item}, key=len, reverse=True):
        redacted = redacted.replace(secret, REDACTED)
    return redacted


def sanitize(value: Any, secrets: Iterable[str] = ()) -> Any:
    primitive = to_primitive(value)
    secret_tuple = tuple(item for item in secrets if item)
    return _sanitize_primitive(primitive, secret_tuple)


def _sanitize_primitive(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            string_key = str(key)
            if SENSITIVE_KEY_RE.search(string_key):
                sanitized[string_key] = REDACTED
            else:
                sanitized[string_key] = _sanitize_primitive(item, secrets)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_primitive(item, secrets) for item in value]
    if isinstance(value, str):
        if value in secrets:
            return REDACTED
        return redact_text(value, secrets)
    return value
