"""
PBACMiddleware — attaches PBAC engine and subject to every request.

The middleware:
1. Runs all ContextInjectors to build Subject and initial Context.
2. Attaches ``request.pbac_subject`` and the engine to the request.
3. Does NOT enforce any policy — enforcement is done by decorators/DRF.

Usage::

    MIDDLEWARE = [
        ...
        "django_pbac.integration.middleware.PBACMiddleware",
    ]
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse

from django_pbac.core.models import Context, Subject
from django_pbac.core.types import SubjectType


logger = logging.getLogger(__name__)


class PBACMiddleware:
    """
    Django middleware that enriches requests with PBAC subject and context.

    Attaches:
    - ``request.pbac_subject``: enriched Subject built by ContextInjectors
    - ``request.pbac_context``: initial Context built by ContextInjectors
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self._engine: Any = None

    @property
    def engine(self) -> Any:
        if self._engine is None:
            from django_pbac.engine import pbac_engine

            self._engine = pbac_engine
        return self._engine

    def __call__(self, request: HttpRequest) -> HttpResponse:
        subject, context = self._build_subject_context(request)
        request.pbac_subject = subject  # type: ignore[attr-defined]
        request.pbac_context = context  # type: ignore[attr-defined]
        return self.get_response(request)

    def _build_subject_context(
        self, request: HttpRequest
    ) -> tuple[Subject, Context]:
        """Run all ContextInjectors to build the enriched Subject and Context."""
        subject = Subject(id="anonymous", type=SubjectType.ANONYMOUS)
        context = Context()

        for injector in self.engine.context_injectors:
            try:
                subject = injector.inject_subject(subject, request)
                context = injector.inject_context(context, request)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "ContextInjector %s raised: %s", type(injector).__name__, exc
                )

        return subject, context
