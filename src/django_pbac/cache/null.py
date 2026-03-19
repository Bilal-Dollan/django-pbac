"""NullCache — a no-op cache for testing or when caching is disabled."""
from __future__ import annotations

from django_pbac.core.models import Policy


class NullCache:
    """
    A no-op implementation of the PolicyCache protocol.

    Use this in tests or set ``PBAC["CACHE_TTL"] = 0`` to disable caching.
    """

    def get(self, key: str) -> list[Policy] | None:
        return None

    def set(self, key: str, policies: list[Policy], ttl: int | None = None) -> None:
        pass

    def invalidate(self, key: str) -> None:
        pass

    def clear(self) -> None:
        pass

    def make_key(self, subject_id: str, action: str, resource_type: str) -> str:
        return f"null:{subject_id}:{action}:{resource_type}"
