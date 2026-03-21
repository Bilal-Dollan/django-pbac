"""Tests for django_pbac.core.matchers."""
from __future__ import annotations

import pytest

from django_pbac.core.matchers import (
    action_matches,
    resource_matcher_matches,
    subject_matcher_matches,
)
from django_pbac.core.models import (
    Context,
    PolicyRequest,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.types import SubjectType


@pytest.fixture
def policy_request(subject_alice, resource_doc) -> PolicyRequest:
    return PolicyRequest(
        subject=subject_alice,
        action="documents:read",
        resource=resource_doc,
        context=Context(),
    )


class TestActionMatches:
    def test_exact_match(self) -> None:
        assert action_matches("documents:read", "documents:read") is True

    def test_wildcard_namespace(self) -> None:
        assert action_matches("documents:*", "documents:read") is True
        assert action_matches("documents:*", "reports:read") is False

    def test_global_wildcard(self) -> None:
        assert action_matches("*", "documents:read") is True
        assert action_matches("*", "anything:else") is True

    def test_no_match(self) -> None:
        assert action_matches("documents:write", "documents:read") is False

    def test_partial_namespace_no_match(self) -> None:
        assert action_matches("doc:*", "documents:read") is False


class TestSubjectMatcherMatches:
    def test_empty_matcher_matches_any(self, policy_request) -> None:
        m = SubjectMatcher()
        assert subject_matcher_matches(m, policy_request) is True

    def test_id_match(self, policy_request) -> None:
        m = SubjectMatcher(id="user:alice")
        assert subject_matcher_matches(m, policy_request) is True

    def test_id_no_match(self, policy_request) -> None:
        m = SubjectMatcher(id="user:charlie")
        assert subject_matcher_matches(m, policy_request) is False

    def test_type_match(self, policy_request) -> None:
        m = SubjectMatcher(type=SubjectType.USER)
        assert subject_matcher_matches(m, policy_request) is True

    def test_type_no_match(self, policy_request) -> None:
        m = SubjectMatcher(type=SubjectType.SERVICE)
        assert subject_matcher_matches(m, policy_request) is False

    def test_role_match(self, policy_request) -> None:
        m = SubjectMatcher(roles=frozenset({"editor"}))
        assert subject_matcher_matches(m, policy_request) is True

    def test_roles_subset_match(self, policy_request) -> None:
        # alice has both editor and viewer — matching any one role is enough
        m = SubjectMatcher(roles=frozenset({"viewer"}))
        assert subject_matcher_matches(m, policy_request) is True

    def test_role_no_match(self, policy_request) -> None:
        m = SubjectMatcher(roles=frozenset({"admin"}))
        assert subject_matcher_matches(m, policy_request) is False

    def test_attribute_match(self, policy_request) -> None:
        m = SubjectMatcher(attributes={"department": "engineering"})
        assert subject_matcher_matches(m, policy_request) is True

    def test_attribute_no_match(self, policy_request) -> None:
        m = SubjectMatcher(attributes={"department": "finance"})
        assert subject_matcher_matches(m, policy_request) is False


class TestResourceMatcherMatches:
    def test_empty_matcher_matches_any(self, policy_request) -> None:
        m = ResourceMatcher()
        assert resource_matcher_matches(m, policy_request) is True

    def test_type_match(self, policy_request) -> None:
        m = ResourceMatcher(types="document")
        assert resource_matcher_matches(m, policy_request) is True

    def test_type_no_match(self, policy_request) -> None:
        m = ResourceMatcher(types="report")
        assert resource_matcher_matches(m, policy_request) is False

    def test_id_match(self, policy_request) -> None:
        m = ResourceMatcher(id="doc:123")
        assert resource_matcher_matches(m, policy_request) is True

    def test_id_no_match(self, policy_request) -> None:
        m = ResourceMatcher(id="doc:999")
        assert resource_matcher_matches(m, policy_request) is False

    def test_attribute_match(self, policy_request) -> None:
        m = ResourceMatcher(attributes={"classification": "internal"})
        assert resource_matcher_matches(m, policy_request) is True

    def test_attribute_no_match(self, policy_request) -> None:
        m = ResourceMatcher(attributes={"classification": "secret"})
        assert resource_matcher_matches(m, policy_request) is False

    def test_cross_ref_attribute_match(self, policy_request) -> None:
        """resource.owner == subject.id cross-reference match."""
        m = ResourceMatcher(attributes={"owner": {"ref": "subject.id"}})
        assert resource_matcher_matches(m, policy_request) is True

    def test_cross_ref_attribute_no_match(self, policy_request) -> None:
        m = ResourceMatcher(attributes={"owner": {"ref": "subject.id"}})
        # bob is not alice, so he shouldn't match alice's doc
        req_bob = PolicyRequest(
            subject=Subject(
                id="user:bob",
                type=SubjectType.USER,
                attributes={"department": "marketing"},
            ),
            action="documents:read",
            resource=policy_request.resource,
            context=Context(),
        )
        assert resource_matcher_matches(m, req_bob) is False
