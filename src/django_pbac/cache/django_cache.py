"""
DjangoCacheBackend — wraps Django's cache framework for policy caching.
"""
from __future__ import annotations

import hashlib
import logging
import pickle
from typing import Any

from django_pbac.core.models import Policy

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "pbac:policies:"


class DjangoCacheBackend:
    """
    Policy cache backed by Django's cache framework.

    Uses the configured ``PBAC["CACHE_ALIAS"]`` Django cache.
    Policies are serialized with pickle.

    Cache key format: ``pbac:policies:<sha256(subject_id:action:resource_type)>``
    """

    def __init__(self) -> None:
        from django_pbac.conf import pbac_settings

        self._alias: str = pbac_settings.CACHE_ALIAS
        self._ttl: int = pbac_settings.CACHE_TTL

    @property
    def _cache(self) -> Any:
        from django.core.cache import caches

        return caches[self._alias]

    def get(self, key: str) -> list[Policy] | None:
        try:
            raw = self._cache.get(key)
            if raw is None:
                return None
            return pickle.loads(raw)  # noqa: S301
        except Exception as exc:
            logger.debug("PolicyCache get error for key %r: %s", key, exc)
            return None

    def set(self, key: str, policies: list[Policy], ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._ttl
        if effective_ttl == 0:
            return
        try:
            raw = pickle.dumps(policies)
            self._cache.set(key, raw, effective_ttl)
        except Exception as exc:
            logger.debug("PolicyCache set error for key %r: %s", key, exc)

    def invalidate(self, key: str) -> None:
        try:
            self._cache.delete(key)
        except Exception as exc:
            logger.debug("PolicyCache invalidate error for key %r: %s", key, exc)

    def clear(self) -> None:
        try:
            # Django cache clear clears all keys — use pattern delete if supported
            self._cache.clear()
        except Exception as exc:
            logger.debug("PolicyCache clear error: %s", exc)

    def make_key(self, subject_id: str, action: str, resource_type: str) -> str:
        raw = f"{subject_id}:{action}:{resource_type}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"{CACHE_KEY_PREFIX}{digest}"
