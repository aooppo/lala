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
        stored = cls.__dict__.get("_provider_protocol_attrs")
        if stored is not None:
            return frozenset(stored)
        return frozenset(
            name
            for name, value in cls.__dict__.items()
            if not name.startswith("_") and callable(value)
        )

    @__protocol_attrs__.setter
    def __protocol_attrs__(cls, value: object) -> None:
        # Python 3.13's typing.Protocol assigns this cache during class creation.
        # Store it under a private name so the public compatibility property remains
        # introspection-only and does not become a structural protocol member.
        type.__setattr__(cls, "_provider_protocol_attrs", frozenset(value))
