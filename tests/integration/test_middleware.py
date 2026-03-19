"""Tests for PBACMiddleware."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpRequest, HttpResponse


class TestPBACMiddleware:
    """Tests for PBACMiddleware — attaches subject/context to request."""

    def _make_get_response(self):
        return lambda req: HttpResponse("OK")

    def _make_request(self):
        req = HttpRequest()
        req.META["REMOTE_ADDR"] = "127.0.0.1"
        user = MagicMock()
        user.is_authenticated = False
        req.user = user
        return req

    def test_middleware_attaches_pbac_subject(self) -> None:
        from django_pbac.core.models import Subject
        from django_pbac.core.types import SubjectType
        from django_pbac.integration.middleware import PBACMiddleware

        subject = Subject(id="anonymous", type=SubjectType.ANONYMOUS)

        mock_engine = MagicMock()
        mock_engine.build_subject.return_value = subject
        mock_engine.context_injectors = []

        with patch("django_pbac.integration.middleware.pbac_engine", mock_engine):
            middleware = PBACMiddleware(self._make_get_response())
            req = self._make_request()
            middleware(req)

        assert hasattr(req, "pbac_subject")

    def test_middleware_attaches_pbac_context(self) -> None:
        from django_pbac.core.models import Context, Subject
        from django_pbac.core.types import SubjectType
        from django_pbac.integration.middleware import PBACMiddleware

        subject = Subject(id="anonymous", type=SubjectType.ANONYMOUS)
        ctx = Context(environment={"ip": "127.0.0.1"})

        mock_engine = MagicMock()
        mock_engine.build_subject.return_value = subject
        mock_engine.context_injectors = [MagicMock(inject_context=lambda c, r: ctx)]

        with patch("django_pbac.integration.middleware.pbac_engine", mock_engine):
            middleware = PBACMiddleware(self._make_get_response())
            req = self._make_request()
            middleware(req)

        assert hasattr(req, "pbac_context")
