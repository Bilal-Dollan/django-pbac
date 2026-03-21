"""Tests for django_pbac.core.models (frozen dataclasses)."""
from __future__ import annotations

import pytest

from django_pbac.core.exceptions import EvaluationError
from django_pbac.core.models import (
    Condition,
    Context,
    Policy,
    PolicyRequest,
    Resource,
    ResourceFilter,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.types import ConflictResolution, Effect, SubjectType


class TestSubject:
    def test_minimal(self) -> None:
        s = Subject(id="user:1", type=SubjectType.USER)
        assert s.id == "user:1"
        assert s.type is SubjectType.USER
        assert s.roles == frozenset()
        assert s.attributes == {}

    def test_with_roles(self) -> None:
        s = Subject(id="u", type=SubjectType.USER, roles=frozenset({"admin"}))
        assert "admin" in s.roles

    def test_frozen(self) -> None:
        s = Subject(id="u", type=SubjectType.USER)
        with pytest.raises((AttributeError, TypeError)):
            s.id = "changed"  # type: ignore[misc]


class TestResource:
    def test_minimal(self) -> None:
        r = Resource(id="doc:1", type="document")
        assert r.id == "doc:1"
        assert r.type == "document"

    def test_with_attributes(self) -> None:
        r = Resource(id="d", type="doc", attributes={"owner": "alice"})
        assert r.attributes["owner"] == "alice"


class TestPolicyRequest:
    def test_valid_action(self, subject_alice, resource_doc) -> None:
        req = PolicyRequest(
            subject=subject_alice,
            action="documents:read",
            resource=resource_doc,
            context=Context(),
        )
        assert req.action == "documents:read"

    def test_invalid_action_no_colon(self, subject_alice, resource_doc) -> None:
        with pytest.raises(ValueError, match="action"):
            PolicyRequest(
                subject=subject_alice,
                action="documentsread",  # Missing ":"
                resource=resource_doc,
                context=Context(),
            )


class TestCondition:
    def test_valid_subject_attribute(self) -> None:
        c = Condition(attribute="subject.attributes.role", operator="eq", value="admin")
        assert c.attribute.startswith("subject")

    def test_valid_resource_attribute(self) -> None:
        c = Condition(attribute="resource.attributes.owner", operator="eq", value="x")
        assert c.attribute.startswith("resource")

    def test_invalid_attribute_root(self) -> None:
        with pytest.raises(ValueError, match="attribute"):
            Condition(attribute="user.name", operator="eq", value="alice")


class TestSubjectMatcher:
    def test_empty_matches_anyone(self) -> None:
        m = SubjectMatcher()
        assert m.id is None
        assert m.roles == frozenset()

    def test_with_id(self) -> None:
        m = SubjectMatcher(id="user:alice")
        assert m.id == "user:alice"


class TestResourceMatcher:
    def test_type_only(self) -> None:
        m = ResourceMatcher(types="document")
        assert m.type == "document"
        assert m.id is None


class TestPolicy:
    def test_basic(self) -> None:
        p = Policy(
            id="p1",
            effect=Effect.PERMIT,
            actions=frozenset({"documents:read"}),
            subject_matchers=(SubjectMatcher(),),
            resource_matchers=(ResourceMatcher(types="document"),),
            conditions=(),
        )
        assert p.id == "p1"
        assert p.effect is Effect.PERMIT


class TestResourceFilter:
    def test_permit_all(self) -> None:
        rf = ResourceFilter(permit_all=True, deny_all=False)
        assert rf.permit_all is True

    def test_deny_all(self) -> None:
        rf = ResourceFilter(permit_all=False, deny_all=True)
        assert rf.deny_all is True

    def test_with_q_filter(self) -> None:
        from django.db.models import Q

        rf = ResourceFilter(permit_all=False, deny_all=False, q_filter=Q(pk__in=[1, 2]))
        assert rf.q_filter is not None
