"""Tests for django_pbac.core.evaluator — PolicyEvaluator."""
from __future__ import annotations

import pytest

from django_pbac.core.evaluator import PolicyEvaluator
from django_pbac.core.models import (
    Condition,
    Context,
    Policy,
    PolicyDecision,
    PolicyRequest,
    Resource,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.operators import operator_registry
from django_pbac.core.types import ConflictResolution, Effect, SubjectType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_evaluator(resolution: ConflictResolution = ConflictResolution.DENY_OVERRIDE) -> PolicyEvaluator:
    return PolicyEvaluator(
        conflict_resolution=resolution,
        operator_registry=operator_registry,
        enable_trace=True,
    )


def make_request(
    subject: Subject,
    action: str,
    resource: Resource,
    context: Context | None = None,
) -> PolicyRequest:
    return PolicyRequest(
        subject=subject,
        action=action,
        resource=resource,
        context=context or Context(),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def alice() -> Subject:
    return Subject(
        id="user:alice",
        type=SubjectType.USER,
        roles=frozenset({"editor", "viewer"}),
        attributes={"department": "engineering", "clearance": "high"},
    )


@pytest.fixture
def bob() -> Subject:
    return Subject(
        id="user:bob",
        type=SubjectType.USER,
        roles=frozenset({"viewer"}),
        attributes={"department": "marketing", "clearance": "low"},
    )


@pytest.fixture
def doc() -> Resource:
    return Resource(
        id="doc:1",
        type="document",
        attributes={"owner": "user:alice", "classification": "internal"},
    )


@pytest.fixture
def permit_read_policy() -> Policy:
    return Policy(
        id="allow-viewer-read",
        effect=Effect.PERMIT,
        actions=frozenset({"documents:read"}),
        subject_matchers=(SubjectMatcher(roles=frozenset({"viewer"})),),
        resource_matchers=(ResourceMatcher(types="document"),),
        conditions=(),
        priority=10,
    )


@pytest.fixture
def deny_low_clearance_policy() -> Policy:
    return Policy(
        id="deny-low-clearance",
        effect=Effect.DENY,
        actions=frozenset({"documents:read"}),
        subject_matchers=(SubjectMatcher(attributes={"clearance": "low"}),),
        resource_matchers=(ResourceMatcher(types="document", attributes={"classification": "internal"}),),
        conditions=(),
        priority=100,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDefaultDeny:
    def test_no_policies_returns_deny(self, alice, doc) -> None:
        ev = make_evaluator()
        req = make_request(alice, "documents:read", doc)
        decision = ev.evaluate(req, [])
        assert decision.effect is Effect.DENY
        assert not decision.is_permit


class TestPermitWithMatchingPolicy:
    def test_alice_viewer_can_read(self, alice, doc, permit_read_policy) -> None:
        ev = make_evaluator()
        req = make_request(alice, "documents:read", doc)
        decision = ev.evaluate(req, [permit_read_policy])
        assert decision.is_permit

    def test_wrong_action_denied(self, alice, doc, permit_read_policy) -> None:
        ev = make_evaluator()
        req = make_request(alice, "documents:delete", doc)
        decision = ev.evaluate(req, [permit_read_policy])
        assert not decision.is_permit

    def test_wrong_resource_type_denied(self, alice, permit_read_policy) -> None:
        ev = make_evaluator()
        report = Resource(id="r:1", type="report")
        req = make_request(alice, "documents:read", report)
        decision = ev.evaluate(req, [permit_read_policy])
        assert not decision.is_permit

    def test_wildcard_action_matches(self, alice, doc) -> None:
        policy = Policy(
            id="wildcard",
            effect=Effect.PERMIT,
            actions=frozenset({"documents:*"}),
            subject_matchers=(SubjectMatcher(),),
            resource_matchers=(ResourceMatcher(types="document"),),
            conditions=(),
        )
        ev = make_evaluator()
        req = make_request(alice, "documents:delete", doc)
        decision = ev.evaluate(req, [policy])
        assert decision.is_permit


class TestDenyOverride:
    def test_deny_wins_over_permit(self, alice, doc, permit_read_policy, deny_low_clearance_policy) -> None:
        """DENY_OVERRIDE: if both PERMIT and DENY match, DENY wins (but alice has high clearance)."""
        ev = make_evaluator(ConflictResolution.DENY_OVERRIDE)
        req = make_request(alice, "documents:read", doc)
        # Alice has high clearance, so deny_low_clearance_policy doesn't match her
        decision = ev.evaluate(req, [permit_read_policy, deny_low_clearance_policy])
        assert decision.is_permit  # Alice is not denied

    def test_bob_denied_by_clearance(self, bob, doc, permit_read_policy, deny_low_clearance_policy) -> None:
        ev = make_evaluator(ConflictResolution.DENY_OVERRIDE)
        req = make_request(bob, "documents:read", doc)
        decision = ev.evaluate(req, [permit_read_policy, deny_low_clearance_policy])
        assert not decision.is_permit  # DENY wins

    def test_explicit_deny_no_permit(self, alice, doc, deny_low_clearance_policy) -> None:
        policy_deny_all = Policy(
            id="deny-all",
            effect=Effect.DENY,
            actions=frozenset({"documents:read"}),
            subject_matchers=(SubjectMatcher(),),
            resource_matchers=(ResourceMatcher(types="document"),),
            conditions=(),
        )
        ev = make_evaluator(ConflictResolution.DENY_OVERRIDE)
        req = make_request(alice, "documents:read", doc)
        decision = ev.evaluate(req, [policy_deny_all])
        assert not decision.is_permit


class TestPermitOverride:
    def test_permit_wins_over_deny(self, bob, doc, permit_read_policy, deny_low_clearance_policy) -> None:
        ev = make_evaluator(ConflictResolution.PERMIT_OVERRIDE)
        req = make_request(bob, "documents:read", doc)
        decision = ev.evaluate(req, [permit_read_policy, deny_low_clearance_policy])
        assert decision.is_permit  # PERMIT wins


class TestFirstApplicable:
    def test_first_applicable_permit(self, alice, doc, permit_read_policy) -> None:
        ev = make_evaluator(ConflictResolution.FIRST_APPLICABLE)
        req = make_request(alice, "documents:read", doc)
        decision = ev.evaluate(req, [permit_read_policy])
        assert decision.is_permit

    def test_first_applicable_deny_first(self, alice, doc, permit_read_policy) -> None:
        deny_policy = Policy(
            id="deny-first",
            effect=Effect.DENY,
            actions=frozenset({"documents:read"}),
            subject_matchers=(SubjectMatcher(),),
            resource_matchers=(ResourceMatcher(types="document"),),
            conditions=(),
            priority=99,  # Higher priority = evaluated first
        )
        ev = make_evaluator(ConflictResolution.FIRST_APPLICABLE)
        req = make_request(alice, "documents:read", doc)
        # With FIRST_APPLICABLE, policies are checked highest priority first
        decision = ev.evaluate(req, [permit_read_policy, deny_policy])
        # deny_policy has higher priority so it's first applicable
        assert not decision.is_permit


class TestConditions:
    def test_condition_passes(self, alice, doc) -> None:
        policy = Policy(
            id="cond-pass",
            effect=Effect.PERMIT,
            actions=frozenset({"documents:read"}),
            subject_matchers=(SubjectMatcher(),),
            resource_matchers=(ResourceMatcher(types="document"),),
            conditions=(
                Condition(
                    attribute="subject.attributes.department",
                    operator="eq",
                    value="engineering",
                ),
            ),
        )
        ev = make_evaluator()
        req = make_request(alice, "documents:read", doc)
        decision = ev.evaluate(req, [policy])
        assert decision.is_permit

    def test_condition_fails(self, alice, doc) -> None:
        policy = Policy(
            id="cond-fail",
            effect=Effect.PERMIT,
            actions=frozenset({"documents:read"}),
            subject_matchers=(SubjectMatcher(),),
            resource_matchers=(ResourceMatcher(types="document"),),
            conditions=(
                Condition(
                    attribute="subject.attributes.department",
                    operator="eq",
                    value="finance",  # alice is engineering
                ),
            ),
        )
        ev = make_evaluator()
        req = make_request(alice, "documents:read", doc)
        decision = ev.evaluate(req, [policy])
        assert not decision.is_permit

    def test_multiple_conditions_all_must_pass(self, alice, doc) -> None:
        policy = Policy(
            id="multi-cond",
            effect=Effect.PERMIT,
            actions=frozenset({"documents:read"}),
            subject_matchers=(SubjectMatcher(),),
            resource_matchers=(ResourceMatcher(types="document"),),
            conditions=(
                Condition(
                    attribute="subject.attributes.department",
                    operator="eq",
                    value="engineering",
                ),
                Condition(
                    attribute="subject.attributes.clearance",
                    operator="eq",
                    value="low",  # alice has "high"
                ),
            ),
        )
        ev = make_evaluator()
        req = make_request(alice, "documents:read", doc)
        decision = ev.evaluate(req, [policy])
        assert not decision.is_permit


class TestTrace:
    def test_trace_populated(self, alice, doc, permit_read_policy) -> None:
        ev = make_evaluator()
        req = make_request(alice, "documents:read", doc)
        decision = ev.evaluate(req, [permit_read_policy])
        assert decision.trace is not None
        assert len(decision.trace) > 0

    def test_matching_policy_in_trace(self, alice, doc, permit_read_policy) -> None:
        ev = make_evaluator()
        req = make_request(alice, "documents:read", doc)
        decision = ev.evaluate(req, [permit_read_policy])
        matched_ids = [step.policy_id for step in decision.trace]
        assert "allow-viewer-read" in matched_ids
