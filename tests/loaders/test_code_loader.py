"""Tests for CodeDefinedPolicyLoader and CodePolicySet."""
from __future__ import annotations

from typing import ClassVar

import pytest

from django_pbac.core.models import (
    Context,
    PolicyRequest,
    Resource,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.types import Effect, SubjectType
from django_pbac.loaders.code import (
    BaseCodePolicy,
    CodeDefinedPolicyLoader,
    CodePolicySet,
)


class ReadDocumentPolicy(BaseCodePolicy):
    policy_id = "code:read-doc"
    effect = Effect.PERMIT
    actions: ClassVar[set[str]] = {"documents:read"}
    subject_matchers: ClassVar[list[SubjectMatcher]] = [SubjectMatcher(roles=frozenset({"viewer"}))]
    resource_matchers: ClassVar[list[ResourceMatcher]] = [ResourceMatcher(types="document")]


class DenyGuestPolicy(BaseCodePolicy):
    policy_id = "code:deny-guest"
    effect = Effect.DENY
    actions: ClassVar[set[str]] = {"*"}
    subject_matchers: ClassVar[list[SubjectMatcher]] = [SubjectMatcher(roles=frozenset({"guest"}))]
    resource_matchers: ClassVar[list[ResourceMatcher]] = [ResourceMatcher()]


@pytest.fixture
def code_loader() -> CodeDefinedPolicyLoader:
    policy_set = CodePolicySet()
    policy_set.register(ReadDocumentPolicy)
    policy_set.register(DenyGuestPolicy)
    return CodeDefinedPolicyLoader(policy_set=policy_set)


@pytest.fixture
def alice_req() -> PolicyRequest:
    return PolicyRequest(
        subject=Subject(
            id="user:alice",
            type=SubjectType.USER,
            roles=frozenset({"viewer"}),
        ),
        action="documents:read",
        resource=Resource(id="doc:1", type="document"),
        context=Context(),
    )


class TestCodeDefinedPolicyLoader:
    def test_load_all(self, code_loader) -> None:
        policies = code_loader.load_all()
        assert len(policies) == 2

    def test_load_for_request_returns_matching(self, code_loader, alice_req) -> None:
        policies = code_loader.load_for_request(
            subject=alice_req.subject,
            action=alice_req.action,
            resource_type=alice_req.resource.type,
        )
        ids = [p.id for p in policies]
        assert "code:read-doc" in ids

    def test_get_by_id(self, code_loader) -> None:
        policy = code_loader.get_by_id("code:read-doc")
        assert policy is not None
        assert policy.effect is Effect.PERMIT

    def test_get_by_id_missing_returns_none(self, code_loader) -> None:
        policy = code_loader.get_by_id("nonexistent:policy")
        assert policy is None

    def test_policy_ids(self, code_loader) -> None:
        all_policies = code_loader.load_all()
        ids = {p.id for p in all_policies}
        assert "code:read-doc" in ids
        assert "code:deny-guest" in ids


class TestCodePolicySet:
    def test_register_and_retrieve(self) -> None:
        ps = CodePolicySet()
        ps.register(ReadDocumentPolicy)
        assert len(ps.all()) == 1

    def test_duplicate_registration(self) -> None:
        ps = CodePolicySet()
        ps.register(ReadDocumentPolicy)
        ps.register(ReadDocumentPolicy)
        # Should not duplicate
        assert len(ps.all()) == 1

    def test_unregister(self) -> None:
        ps = CodePolicySet()
        ps.register(ReadDocumentPolicy)
        ps.unregister("code:read-doc")
        assert len(ps.all()) == 0
