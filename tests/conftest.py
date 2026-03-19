"""
Shared pytest fixtures for the django-pbac test suite.

Provides reusable fixtures for:
- Django users
- Subject / Resource / Context domain objects
- Policy and Condition builders
- PolicyRequest builders
"""
from __future__ import annotations

import os

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()


from django_pbac.core.models import (  # noqa: E402
    Condition,
    Context,
    Policy,
    PolicyRequest,
    Resource,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.types import ConflictResolution, Effect, SubjectType  # noqa: E402


# ---------------------------------------------------------------------------
# Core domain fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def subject_alice() -> Subject:
    return Subject(
        id="user:alice",
        type=SubjectType.USER,
        roles=frozenset({"editor", "viewer"}),
        attributes={"department": "engineering", "clearance": "high"},
    )


@pytest.fixture
def subject_bob() -> Subject:
    return Subject(
        id="user:bob",
        type=SubjectType.USER,
        roles=frozenset({"viewer"}),
        attributes={"department": "marketing", "clearance": "low"},
    )


@pytest.fixture
def subject_service() -> Subject:
    return Subject(
        id="service:data-api",
        type=SubjectType.SERVICE,
        roles=frozenset({"service-account"}),
        attributes={"env": "production"},
    )


@pytest.fixture
def resource_doc() -> Resource:
    return Resource(
        id="doc:123",
        type="document",
        attributes={"owner": "user:alice", "classification": "internal"},
    )


@pytest.fixture
def resource_report() -> Resource:
    return Resource(
        id="report:456",
        type="report",
        attributes={"owner": "user:bob", "classification": "public"},
    )


@pytest.fixture
def context_default() -> Context:
    return Context(
        environment={"ip": "10.0.0.1", "time": "14:30"},
    )


# ---------------------------------------------------------------------------
# Policy fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def permit_policy_any_doc_read() -> Policy:
    """Allow any user with 'viewer' role to read documents."""
    return Policy(
        id="policy:any-viewer-doc-read",
        effect=Effect.PERMIT,
        actions=frozenset({"documents:read"}),
        subject_matchers=(
            SubjectMatcher(
                roles=frozenset({"viewer"}),
            ),
        ),
        resource_matchers=(
            ResourceMatcher(type="document"),
        ),
        conditions=(),
        priority=10,
    )


@pytest.fixture
def deny_policy_low_clearance() -> Policy:
    """Deny low-clearance users from reading classified docs."""
    return Policy(
        id="policy:deny-low-clearance",
        effect=Effect.DENY,
        actions=frozenset({"documents:read"}),
        subject_matchers=(
            SubjectMatcher(
                attributes={"clearance": "low"},
            ),
        ),
        resource_matchers=(
            ResourceMatcher(
                type="document",
                attributes={"classification": "internal"},
            ),
        ),
        conditions=(),
        priority=100,
    )


@pytest.fixture
def permit_policy_owner_edit() -> Policy:
    """Allow the owner of a document to edit it."""
    return Policy(
        id="policy:owner-edit",
        effect=Effect.PERMIT,
        actions=frozenset({"documents:edit", "documents:delete"}),
        subject_matchers=(
            SubjectMatcher(),
        ),
        resource_matchers=(
            ResourceMatcher(
                type="document",
                attributes={"owner": {"ref": "subject.id"}},
            ),
        ),
        conditions=(),
        priority=50,
    )


@pytest.fixture
def condition_dept_engineering() -> Condition:
    return Condition(
        attribute="subject.attributes.department",
        operator="eq",
        value="engineering",
    )


# ---------------------------------------------------------------------------
# Request builders
# ---------------------------------------------------------------------------


@pytest.fixture
def build_request():
    """Factory fixture to build PolicyRequest objects."""
    def _build(
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

    return _build


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


@pytest.fixture
def evaluator():
    from django_pbac.core.evaluator import PolicyEvaluator
    from django_pbac.core.operators import operator_registry

    return PolicyEvaluator(
        conflict_resolution=ConflictResolution.DENY_OVERRIDE,
        operator_registry=operator_registry,
        enable_trace=True,
    )
