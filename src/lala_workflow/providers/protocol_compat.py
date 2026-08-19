"""Compatibility helpers for provider-neutral runtime protocols."""

from __future__ import annotations

from typing import Protocol


class ProviderProtocolMeta(type(Protocol)):
    """Expose protocol members on Python versions that omit the public alias.

    Python 3.13 publishes ``__protocol_attrs__`` on protocol classes, while
    Python 3.11 does not.  A metaclass property keeps the introspection API
    available without inserting a synthetic member into the protocol class
    dictionary (which would make structural ``isinstance`` checks require the
    synthetic attribute too).
    """

    @property
    def __protocol_attrs__(cls) -> frozenset[str]:
        return frozenset(
            name
            for name, value in cls.__dict__.items()
            if not name.startswith("_") and callable(value)
        )
