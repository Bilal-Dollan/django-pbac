"""
DRF permission classes for django-pbac.

Usage::

    from django_pbac.integration.drf.permissions import PBACPermission, PBACObjectPermission

    class DocumentViewSet(viewsets.ModelViewSet):
        queryset = Document.objects.all()
        serializer_class = DocumentSerializer
        permission_classes = [PBACPermission]

        # Map DRF actions to PBAC actions:
        pbac_action_map = {
            "list":    "documents:list",
            "create":  "documents:create",
            "retrieve": "documents:read",
            "update":  "documents:update",
            "partial_update": "documents:update",
            "destroy": "documents:delete",
        }
        pbac_resource_type = "document"
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from rest_framework.permissions import BasePermission
    from rest_framework.request import Request as DRFRequest

    HAS_DRF = True
except ImportError:
    HAS_DRF = False
    BasePermission = object
    DRFRequest = object


def _require_drf() -> None:
    if not HAS_DRF:
        raise ImportError(
            "djangorestframework is required for PBACPermission. "
            "Install with: pip install django-pbac[drf]"
        )


class PBACPermission(BasePermission):  # type: ignore[misc]
    """
    DRF permission class that enforces PBAC policies.

    Configure on your ViewSet:
        permission_classes = [PBACPermission]
        pbac_resource_type = "document"
        pbac_action_map = {
            "list":    "documents:list",
            "create":  "documents:create",
            "retrieve": "documents:read",
            ...
        }

    Default action map uses ``{resource_type}:{drf_action}`` if not overridden.
    """

    def has_permission(self, request: Any, view: Any) -> bool:
        _require_drf()

        action = self._get_pbac_action(request, view)
        resource_type = self._get_resource_type(view)

        if not action or not resource_type:
            logger.warning(
                "PBACPermission: could not determine action or resource_type for %s. "
                "Denying by default.",
                view.__class__.__name__,
            )
            return False

        from django_pbac.core.models import Context, PolicyRequest, Resource
        from django_pbac.engine import pbac_engine

        subject = self._get_subject(request, pbac_engine)
        context = getattr(request, "pbac_context", None) or Context()

        resource = Resource(type=resource_type)
        policy_request = PolicyRequest(
            subject=subject,
            action=action,
            resource=resource,
            context=context,
        )

        decision = pbac_engine.evaluate(policy_request)
        return decision.is_permit

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        """
        Object-level permission check.

        Falls through to ``PBACObjectPermission`` logic. Override if you need
        different behavior for object vs. collection permissions.
        """
        return self.has_permission(request, view)

    def _get_pbac_action(self, request: Any, view: Any) -> str | None:
        action_map: dict[str, str] = getattr(view, "pbac_action_map", {})
        drf_action: str = getattr(view, "action", "") or ""

        if drf_action in action_map:
            return action_map[drf_action]

        resource_type = self._get_resource_type(view) or "resource"
        if drf_action:
            return f"{resource_type}:{drf_action}"

        # HTTP method fallback
        method_map = {
            "GET": "read",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
            "HEAD": "read",
            "OPTIONS": "read",
        }
        verb = method_map.get(request.method.upper(), "access")
        return f"{resource_type}:{verb}"

    def _get_resource_type(self, view: Any) -> str | None:
        return getattr(view, "pbac_resource_type", None)

    def _get_subject(self, request: Any, engine: Any) -> Any:
        subject = getattr(request, "pbac_subject", None)
        if subject is None:
            subject = engine.build_subject(request)
        return subject


class PBACObjectPermission(PBACPermission):
    """
    DRF permission class that performs per-object PBAC evaluation.

    Loads resource attributes from the database for the specific object
    being accessed, enabling attribute-level policy conditions.

    Usage::

        permission_classes = [PBACObjectPermission]
        pbac_resource_type = "document"
        pbac_load_resource_attributes = True   # (default)
    """

    pbac_load_resource_attributes: bool = True

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        _require_drf()

        action = self._get_pbac_action(request, view)
        resource_type = self._get_resource_type(view)

        if not action or not resource_type:
            return False

        from django_pbac.core.models import Context, PolicyRequest, Resource
        from django_pbac.engine import pbac_engine

        subject = self._get_subject(request, pbac_engine)
        context = getattr(request, "pbac_context", None) or Context()

        # Build resource with object's PK
        resource_id = str(getattr(obj, "pk", "") or "")
        resource = Resource(type=resource_type, id=resource_id or None)

        # Load resource attributes if configured
        if self.pbac_load_resource_attributes and resource_id:
            try:
                from django_pbac.adapters.registry import adapter_registry
                from django_pbac.injectors.resource import ResourceAttributeInjector

                adapter = adapter_registry.get(resource_type)
                if adapter:
                    resource = ResourceAttributeInjector().load(resource)
            except Exception as exc:
                logger.debug("PBACObjectPermission: failed to load resource attrs: %s", exc)

        policy_request = PolicyRequest(
            subject=subject,
            action=action,
            resource=resource,
            context=context,
        )

        decision = pbac_engine.evaluate(policy_request)
        return decision.is_permit
