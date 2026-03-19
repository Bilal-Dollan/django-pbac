"""Tests for ContextInjectors."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import AnonymousUser

from django_pbac.core.models import Context, Subject
from django_pbac.core.types import SubjectType
from django_pbac.injectors.request_meta import RequestMetadataInjector
from django_pbac.injectors.user import UserAttributeInjector


# ---------------------------------------------------------------------------
# UserAttributeInjector
# ---------------------------------------------------------------------------


class TestUserAttributeInjector:
    def _make_user(self, *, username="alice", is_auth=True, groups=None):
        user = MagicMock()
        user.pk = 1
        user.username = username
        user.is_authenticated = is_auth
        if groups is None:
            g1 = MagicMock()
            g1.name = "editors"
            user.groups.all.return_value = [g1]
        else:
            group_mocks = []
            for name in groups:
                g = MagicMock()
                g.name = name
                group_mocks.append(g)
            user.groups.all.return_value = group_mocks
        return user

    def _make_request(self, user=None):
        req = MagicMock()
        req.user = user or self._make_user()
        return req

    def test_inject_subject_authenticated(self) -> None:
        injector = UserAttributeInjector()
        user = self._make_user(username="alice", groups=["editors", "viewers"])
        req = self._make_request(user=user)
        base = Subject(id="anonymous", type=SubjectType.ANONYMOUS)

        subject = injector.inject_subject(base, req)

        assert subject.type is SubjectType.USER
        assert "editors" in subject.roles
        assert "viewers" in subject.roles

    def test_inject_subject_anonymous(self) -> None:
        injector = UserAttributeInjector()
        anon = AnonymousUser()
        req = self._make_request(user=anon)
        base = Subject(id="anonymous", type=SubjectType.ANONYMOUS)

        subject = injector.inject_subject(base, req)
        assert subject.type is SubjectType.ANONYMOUS

    def test_inject_context_unchanged(self) -> None:
        injector = UserAttributeInjector()
        req = self._make_request()
        ctx = Context(environment={"key": "val"})
        result = injector.inject_context(ctx, req)
        assert result.environment.get("key") == "val"


# ---------------------------------------------------------------------------
# RequestMetadataInjector
# ---------------------------------------------------------------------------


class TestRequestMetadataInjector:
    def _make_request(self, meta=None):
        req = MagicMock()
        req.META = meta or {"REMOTE_ADDR": "192.168.1.1", "HTTP_USER_AGENT": "TestAgent/1.0"}
        return req

    def test_inject_context_ip(self) -> None:
        injector = RequestMetadataInjector()
        req = self._make_request()
        base = Subject(id="user:1", type=SubjectType.USER)
        ctx = Context()

        result_ctx = injector.inject_context(ctx, req)
        assert result_ctx.environment.get("ip") == "192.168.1.1"

    def test_inject_context_x_forwarded_for(self) -> None:
        injector = RequestMetadataInjector()
        req = self._make_request(meta={
            "REMOTE_ADDR": "10.0.0.1",
            "HTTP_X_FORWARDED_FOR": "203.0.113.5, 10.0.0.1",
        })
        ctx = Context()
        result_ctx = injector.inject_context(ctx, req)
        # Should use the first (real client) IP from X-Forwarded-For
        assert result_ctx.environment.get("ip") == "203.0.113.5"

    def test_inject_subject_unchanged(self) -> None:
        injector = RequestMetadataInjector()
        req = self._make_request()
        base = Subject(id="user:test", type=SubjectType.USER)
        result = injector.inject_subject(base, req)
        assert result is base  # Should not change subject
