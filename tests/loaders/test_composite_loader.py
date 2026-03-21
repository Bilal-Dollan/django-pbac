"""Tests for CompositePolicyLoader."""
from __future__ import annotations

from typing import ClassVar

import pytest

from django_pbac.core.models import (
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.types import Effect, SubjectType
from django_pbac.loaders.code import BaseCodePolicy, CodeDefinedPolicyLoader, CodePolicySet
from django_pbac.loaders.composite import CompositePolicyLoader


class PermitReadPolicy(BaseCodePolicy):
    policy_id = "composite:permit-read"
    effect = Effect.PERMIT
    actions: ClassVar[set[str]] = {"documents:read"}
    subject_matchers: ClassVar[list[SubjectMatcher]] = [SubjectMatcher()]
    resource_matchers: ClassVar[list[ResourceMatcher]] = [ResourceMatcher(types="document")]


class DenyWritePolicy(BaseCodePolicy):
    policy_id = "composite:deny-write"
    effect = Effect.DENY
    actions: ClassVar[set[str]] = {"documents:write"}
    subject_matchers: ClassVar[list[SubjectMatcher]] = [SubjectMatcher()]
    resource_matchers: ClassVar[list[ResourceMatcher]] = [ResourceMatcher()]


@pytest.fixture
def loader_a() -> CodeDefinedPolicyLoader:
    ps = CodePolicySet()
    ps.register(PermitReadPolicy)
    return CodeDefinedPolicyLoader(policy_set=ps)


@pytest.fixture
def loader_b() -> CodeDefinedPolicyLoader:
    ps = CodePolicySet()
    ps.register(DenyWritePolicy)
    return CodeDefinedPolicyLoader(policy_set=ps)


@pytest.fixture
def composite(loader_a, loader_b) -> CompositePolicyLoader:
    return CompositePolicyLoader(loaders=[loader_a, loader_b])


class TestCompositePolicyLoader:
    def test_load_all_merges(self, composite) -> None:
        all_policies = composite.load_all()
        ids = {p.id for p in all_policies}
        assert "composite:permit-read" in ids
        assert "composite:deny-write" in ids

    def test_no_duplicates(self, composite, loader_a) -> None:
        # Add loader_a again to composite — IDs should be deduplicated
        composite_dup = CompositePolicyLoader(loaders=[composite, loader_a])
        all_policies = composite_dup.load_all()
        ids = [p.id for p in all_policies]
        assert ids.count("composite:permit-read") == 1

    def test_load_for_request(self, composite) -> None:
        subject = Subject(id="user:x", type=SubjectType.USER)
        policies = composite.load_for_request(
            subject=subject,
            action="documents:read",
            resource_type="document",
        )
        ids = [p.id for p in policies]
        assert "composite:permit-read" in ids

    def test_get_by_id_across_loaders(self, composite) -> None:
        p = composite.get_by_id("composite:deny-write")
        assert p is not None
        assert p.effect is Effect.DENY

    def test_get_by_id_missing(self, composite) -> None:
        p = composite.get_by_id("nonexistent:policy")
        assert p is None

    def test_empty_composite(self) -> None:
        c = CompositePolicyLoader(loaders=[])
        assert c.load_all() == []
