"""
View decorators for PBAC enforcement.

Decorators:
  @require_policy(action, resource_type, ...)  — require PERMIT to proceed
  @deny_policy(action, resource_type, ...)     — require DENY to be absent (block if denied)

Usage::

    from django_pbac.integration.decorators import require_policy, deny_policy

    @require_policy("documents:read", resource_type="document", resource_id_kwarg="pk")
    def document_detail(request, pk):
        ...

    @deny_policy("admin:access", resource_type="system")
    def non_admin_view(request):
        ...
"""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from django.http import HttpRequest


logger = logging.getLogger(__name__)


def require_policy(
    action: str,
    resource_type: str,
    resource_id_kwarg: str | None = None,
    resource_id_param: str | None = None,
    load_resource: bool = False,
    raise_exception: bool = True,
) -> Callable:
    """
    Decorator that enforces a PBAC PERMIT decision before calling the view.

    Args:
        action:              Action string, e.g. "documents:read".
        resource_type:       Resource type, e.g. "document".
        resource_id_kwarg:   URL keyword argument name containing the resource ID.
        resource_id_param:   Query parameter name containing the resource ID.
        load_resource:       If True, use ResourceAttributeInjector to load
                             resource attributes from the database before evaluation.
        raise_exception:     If True (default), raises PermissionDenied on DENY.
                             If False, redirects to login for unauthenticated users.
    """

    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            from django_pbac.engine import pbac_engine
            from django_pbac.core.models import Resource, PolicyRequest, Context
            from django_pbac.core.types import SubjectType

            # Build subject
            subject = getattr(request, "pbac_subject", None)
            context = getattr(request, "pbac_context", None) or Context()

            if subject is None:
                # Middleware not installed — build subject on the fly
                subject = pbac_engine.build_subject(request)

            # Build resource
            resource_id: str | None = None
            if resource_id_kwarg:
                resource_id = str(kwargs.get(resource_id_kwarg, "")) or None
            elif resource_id_param:
                resource_id = request.GET.get(resource_id_param) or None

            resource = Resource(type=resource_type, id=resource_id)

            # Optionally load resource attributes from DB
            if load_resource and resource_id:
                from django_pbac.injectors.resource import ResourceAttributeInjector

                resource = ResourceAttributeInjector().load(resource)

            policy_request = PolicyRequest(
                subject=subject,
                action=action,
                resource=resource,
                context=context,
            )

            decision = pbac_engine.evaluate(policy_request)

            if decision.is_deny:
                if raise_exception:
                    from django.core.exceptions import PermissionDenied

                    raise PermissionDenied(decision.reason)
                else:
                    from django.contrib.auth.views import redirect_to_login

                    return redirect_to_login(request.get_full_path())

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def deny_policy(
    action: str,
    resource_type: str,
    resource_id_kwarg: str | None = None,
) -> Callable:
    """
    Decorator that raises PermissionDenied if the action is explicitly DENIED.

    Unlike ``require_policy``, this allows through requests that have no
    matching policy (default allow semantics). Use for additive blocking.

    Rarely needed — only use when your security model requires explicit DENY
    policies to block access while defaulting to open.
    """

    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            from django_pbac.engine import pbac_engine
            from django_pbac.core.models import Resource, PolicyRequest, Context
            from django_pbac.core.types import Effect

            subject = getattr(request, "pbac_subject", None)
            context = getattr(request, "pbac_context", None) or Context()

            if subject is None:
                subject = pbac_engine.build_subject(request)

            resource_id: str | None = None
            if resource_id_kwarg:
                resource_id = str(kwargs.get(resource_id_kwarg, "")) or None

            resource = Resource(type=resource_type, id=resource_id)
            policy_request = PolicyRequest(
                subject=subject,
                action=action,
                resource=resource,
                context=context,
            )

            decision = pbac_engine.evaluate(policy_request)

            if decision.effect == Effect.DENY and decision.denied_by:
                from django.core.exceptions import PermissionDenied

                raise PermissionDenied(decision.reason)

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
