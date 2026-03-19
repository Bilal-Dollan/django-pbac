"""PolicyCache Protocol."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from django_pbac.core.models import Policy


@runtime_checkable
class PolicyCache(Protocol):
    """Protocol for caching loaded policies."""

    def get(self, key: str) -> list[Policy] | None:
        """Return cached policies or None if cache miss."""
        ...

    def set(self, key: str, policies: list[Policy], ttl: int | None = None) -> None:
        """Cache policies with optional TTL in seconds."""
        ...

    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache key."""
        ...

    def clear(self) -> None:
        """Clear all cached policies."""
        ...

    def make_key(self, subject_id: str, action: str, resource_type: str) -> str:
        """Generate a cache key from request parameters."""
        ...
