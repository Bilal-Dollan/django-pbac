"""
ModelAdapter registry — maps resource type strings to ModelAdapter instances.
"""
from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Registry mapping resource type strings to ModelAdapter implementations.

    Module-level singleton: ``adapter_registry``.

    Usage::

        from django_pbac.adapters.registry import adapter_registry

        adapter_registry.register("document", DocumentAdapter())

        # Retrieve:
        adapter = adapter_registry.get("document")
        attrs = adapter.get_attributes("doc-42")
    """

    def __init__(self) -> None:
        self._adapters: dict[str, Any] = {}

    def register(self, resource_type: str, adapter: Any) -> None:
        """Register a ModelAdapter for the given resource type."""
        if resource_type in self._adapters:
            logger.warning(
                "Overwriting existing adapter for resource type %r.", resource_type
            )
        self._adapters[resource_type] = adapter

    def get(self, resource_type: str) -> Any | None:
        """Return the adapter for the given resource type, or None."""
        return self._adapters.get(resource_type)

    def unregister(self, resource_type: str) -> None:
        """Remove the adapter for the given resource type."""
        self._adapters.pop(resource_type, None)

    def list_types(self) -> list[str]:
        """Return all registered resource type strings."""
        return list(self._adapters.keys())


# Module-level singleton
adapter_registry = AdapterRegistry()
