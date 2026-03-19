"""
CompositePolicyLoader — merges policies from multiple sources.

Deduplication: if the same policy ID appears in multiple loaders,
the last loader wins (respecting the configured loader order).
"""
from __future__ import annotations

import logging
from typing import Any

from django_pbac.core.models import Policy, Subject
from django_pbac.loaders.base import PolicyLoader


logger = logging.getLogger(__name__)


class CompositePolicyLoader:
    """
    Aggregates policies from multiple PolicyLoader implementations.

    Loader order matters:
    - Policies are loaded from all loaders and deduplicated by ID.
    - Later loaders override earlier ones on ID collision.
    - The order of loaders in PBAC settings defines override priority.

    Thread safety: instances are assumed to be created once at startup and
    shared across threads. Individual loaders are responsible for their own
    thread safety.
    """

    def __init__(self, loaders: list[Any]) -> None:
        self._loaders: list[Any] = loaders

    def load_for_request(
        self,
        subject: Subject,
        action: str,
        resource_type: str,
    ) -> list[Policy]:
        """Load and merge policies from all loaders."""
        merged: dict[str, Policy] = {}
        for loader in self._loaders:
            try:
                for policy in loader.load_for_request(subject, action, resource_type):
                    merged[policy.id] = policy
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "CompositePolicyLoader: error loading from %s: %s",
                    type(loader).__name__,
                    exc,
                )
        return list(merged.values())

    def load_all(self) -> list[Policy]:
        merged: dict[str, Policy] = {}
        for loader in self._loaders:
            try:
                for policy in loader.load_all():
                    merged[policy.id] = policy
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "CompositePolicyLoader: error in load_all from %s: %s",
                    type(loader).__name__,
                    exc,
                )
        return list(merged.values())

    def get_by_id(self, policy_id: str) -> Policy | None:
        for loader in reversed(self._loaders):
            try:
                policy = loader.get_by_id(policy_id)
                if policy is not None:
                    return policy
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "CompositePolicyLoader: get_by_id error from %s: %s",
                    type(loader).__name__,
                    exc,
                )
        return None

    def save(self, policy: Policy) -> Policy:
        """Save to the first loader that supports save (DatabasePolicyLoader)."""
        for loader in self._loaders:
            if hasattr(loader, "save"):
                from django_pbac.loaders.db import DatabasePolicyLoader

                if isinstance(loader, DatabasePolicyLoader):
                    return loader.save(policy)
        # Fallback: save to first loader
        if self._loaders:
            return self._loaders[0].save(policy)
        return policy

    def delete(self, policy_id: str) -> None:
        for loader in self._loaders:
            try:
                loader.delete(policy_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "CompositePolicyLoader: delete error from %s: %s",
                    type(loader).__name__,
                    exc,
                )

    @classmethod
    def from_settings(cls) -> "CompositePolicyLoader":
        """
        Instantiate from Django settings.

        Reads ``PBAC["POLICY_LOADERS"]`` and instantiates each loader.
        """
        from django.utils.module_loading import import_string

        from django_pbac.conf import pbac_settings

        loaders = []
        for dotted_path in pbac_settings.POLICY_LOADERS:
            try:
                loader_class = import_string(dotted_path)
                loaders.append(loader_class())
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to instantiate policy loader %r: %s", dotted_path, exc
                )
        return cls(loaders)
