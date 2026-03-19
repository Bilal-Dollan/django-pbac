"""
Django view mixins for PBAC integration.

PBACViewMixin:      Enforce policy in class-based views.
PBACQuerySetMixin:  Automatically filter querysets to permitted resources.
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet


logger = logging.getLogger(__name__)


class PBACViewMixin:
    """
    Mixin for class-based views that enforces a PBAC policy.

    Set class attributes:
        pbac_action (str):        Required. Action to check, e.g. "documents:read".
        pbac_resource_type (str): Required. Resource type, e.g. "document".
        pbac_resource_id_kwarg (str): URL kwarg for resource ID.
        pbac_load_resource (bool): Whether to load resource attributes from DB.

    Usage::

        class DocumentDetailView(PBACViewMixin, DetailView):
            pbac_action = "documents:read"
            pbac_resource_type = "document"
            pbac_resource_id_kwarg = "pk"
            model = Document
    """

    pbac_action: str = ""
    pbac_resource_type: str = ""
    pbac_resource_id_kwarg: str = "pk"
    pbac_load_resource: bool = False

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        self.pbac_check(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]

    def pbac_check(self, request: Any, *args: Any, **kwargs: Any) -> None:
        from django_pbac.engine import pbac_engine
        from django_pbac.core.models import Resource, PolicyRequest, Context

        if not self.pbac_action or not self.pbac_resource_type:
            return

        subject = getattr(request, "pbac_subject", None)
        context = getattr(request, "pbac_context", None) or Context()

        if subject is None:
            subject = pbac_engine.build_subject(request)

        resource_id_str = kwargs.get(self.pbac_resource_id_kwarg)
        resource_id = str(resource_id_str) if resource_id_str else None
        resource = Resource(type=self.pbac_resource_type, id=resource_id)

        if self.pbac_load_resource and resource_id:
            from django_pbac.injectors.resource import ResourceAttributeInjector

            resource = ResourceAttributeInjector().load(resource)

        policy_request = PolicyRequest(
            subject=subject,
            action=self.pbac_action,
            resource=resource,
            context=context,
        )

        decision = pbac_engine.evaluate(policy_request)

        if decision.is_deny:
            raise PermissionDenied(decision.reason)


class PBACQuerySetMixin:
    """
    Mixin for class-based views (especially ListViews and ViewSets) that
    automatically filters the queryset to only permitted resources.

    The filter is derived from PERMIT policies for the (subject, action, resource_type)
    triple using ``PolicyEvaluator.get_permitted_resource_filter()``.

    Set class attributes:
        pbac_action (str):        Required. Action to scope, e.g. "documents:list".
        pbac_resource_type (str): Required. Resource type, e.g. "document".
        model (Model):            The Django model (provides the base queryset).

    Usage::

        class DocumentListView(PBACQuerySetMixin, ListView):
            pbac_action = "documents:list"
            pbac_resource_type = "document"
            model = Document

        # In your view, call self.get_pbac_queryset(queryset) to apply the filter.
    """

    pbac_action: str = ""
    pbac_resource_type: str = ""

    def get_pbac_queryset(self, queryset: QuerySet) -> QuerySet:
        """Apply PBAC filter to the given queryset."""
        from django_pbac.engine import pbac_engine

        request = getattr(self, "request", None)
        if request is None:
            return queryset

        subject = getattr(request, "pbac_subject", None)
        if subject is None:
            from django_pbac.core.models import Subject
            from django_pbac.core.types import SubjectType

            subject = Subject(id="anonymous", type=SubjectType.ANONYMOUS)

        resource_filter = pbac_engine.get_resource_filter(
            subject=subject,
            action=self.pbac_action,
            resource_type=self.pbac_resource_type,
        )

        if resource_filter.deny_all:
            return queryset.none()

        if resource_filter.permit_all:
            return queryset

        if resource_filter.q_filter is not None:
            return queryset.filter(resource_filter.q_filter)

        return queryset.none()

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()  # type: ignore[misc]
        return self.get_pbac_queryset(qs)
