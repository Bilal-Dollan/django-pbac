"""
ModelAdapter Protocol — bridges Django models with PBAC resource loading.

Implement this protocol to teach django-pbac how to load attributes
and ancestor hierarchies for your domain models.

Usage::

    from django_pbac.adapters.base import ModelAdapter
    from django_pbac.adapters.registry import adapter_registry
    from myapp.models import Document

    class DocumentAdapter:
        def get_attributes(self, resource_id: str) -> dict:
            doc = Document.objects.values(
                "owner_id", "tenant_id", "status", "visibility"
            ).get(pk=resource_id)
            return doc

        def get_ancestors(self, resource_id: str) -> list[tuple[str, str]]:
            doc = Document.objects.select_related("folder__workspace").get(pk=resource_id)
            ancestors = []
            if doc.folder:
                if doc.folder.workspace:
                    ancestors.append(("workspace", str(doc.folder.workspace.pk)))
                ancestors.append(("folder", str(doc.folder.pk)))
            return ancestors

    adapter_registry.register("document", DocumentAdapter())
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ModelAdapter(Protocol):
    """
    Protocol for loading resource attributes and ancestors.

    Implementations must be registered with ``adapter_registry.register()``.
    """

    def get_attributes(self, resource_id: str) -> dict[str, Any]:
        """
        Return a dict of attribute key-value pairs for the given resource ID.

        These attributes are available in policy conditions as
        ``resource.attributes.<key>``.

        Should return {} (not raise) if resource is not found.
        """
        ...

    def get_ancestors(self, resource_id: str) -> list[tuple[str, str]]:
        """
        Return the ordered ancestor chain for the given resource ID.

        Each tuple is (resource_type, resource_id), ordered from root → parent.
        Example: [("workspace", "ws-1"), ("folder", "folder-5")]

        Should return [] (not raise) if resource is not found.
        """
        ...
