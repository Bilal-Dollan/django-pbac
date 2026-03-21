"""
ResourceAttributeInjector — lazily loads resource attributes from the DB.

This injector enriches the Resource object with attributes fetched from
the database using the registered ModelAdapter for the resource type.
It also resolves ancestor resources for hierarchical policy matching.

This injector is NOT a ContextInjector — it enriches a Resource, not
Subject/Context. It is called by the engine when a resource ID is known.
"""
from __future__ import annotations

import logging
from typing import Any

from django_pbac.core.models import Resource

logger = logging.getLogger(__name__)


class ResourceAttributeInjector:
    """
    Loads resource attributes and ancestors via the ModelAdapter registry.

    Usage::

        injector = ResourceAttributeInjector()
        resource = injector.load(Resource(type="document", id="doc-42"))
        # resource.attributes now populated from DB
        # resource.ancestors now populated for hierarchical matching

    Uses ``adapter_registry`` to find the right adapter for each resource type.
    Falls back to an empty resource if no adapter is found.
    """

    def load(self, resource: Resource) -> Resource:
        """
        Load attributes for the given resource.

        Returns a new Resource with populated ``attributes`` and ``ancestors``.
        Returns the original resource unchanged if:
        - resource.id is None (collection-level resource)
        - No ModelAdapter is registered for resource.type
        """
        if resource.id is None:
            return resource

        try:
            from django_pbac.adapters.registry import adapter_registry

            adapter = adapter_registry.get(resource.type)
            if adapter is None:
                logger.debug(
                    "No ModelAdapter registered for resource type %r. "
                    "Resource attributes will not be loaded.",
                    resource.type,
                )
                return resource

            attributes = adapter.get_attributes(resource.id)
            ancestors = adapter.get_ancestors(resource.id)

            return resource.__class__(
                type=resource.type,
                id=resource.id,
                attributes=attributes,
                ancestors=ancestors,
            )
        except Exception as exc:
            logger.warning(
                "ResourceAttributeInjector: failed to load attributes for "
                "%s/%s: %s",
                resource.type,
                resource.id,
                exc,
            )
            return resource

    def inject_subject(self, subject: Any, request: Any) -> Any:
        """No-op — this injector enriches Resources, not Subjects."""
        return subject

    def inject_context(self, context: Any, request: Any) -> Any:
        """No-op — this injector enriches Resources, not Context."""
        return context
