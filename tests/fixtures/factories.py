"""
Factory helpers for tests.

These are plain builder functions — no dependency on factory_boy.
Use factory_boy factories in your own tests if you need Django ORM integration.
"""
from __future__ import annotations

from django_pbac.core.models import (
    Condition,
    Context,
    Policy,
    PolicyRequest,
    Resource,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.types import Effect, SubjectType


def make_subject(
    *,
    id: str = "user:test",  # noqa: A002
    type: SubjectType = SubjectType.USER,  # noqa: A002
    roles: frozenset[str] | None = None,
    attributes: dict | None = None,
) -> Subject:
    return Subject(
        id=id,
        type=type,
        roles=roles or frozenset(),
        attributes=attributes or {},
    )


def make_resource(
    *,
    id: str = "resource:test",  # noqa: A002
    type: str = "document",  # noqa: A002
    attributes: dict | None = None,
) -> Resource:
    return Resource(id=id, type=type, attributes=attributes or {})


def make_context(*, environment: dict | None = None) -> Context:
    return Context(environment=environment or {})


def make_policy(
    *,
    id: str = "policy:test",  # noqa: A002
    effect: Effect = Effect.PERMIT,
    actions: frozenset[str] | None = None,
    subject_matchers: tuple[SubjectMatcher, ...] | None = None,
    resource_matchers: tuple[ResourceMatcher, ...] | None = None,
    conditions: tuple[Condition, ...] = (),
    priority: int = 10,
    enabled: bool = True,
) -> Policy:
    return Policy(
        id=id,
        effect=effect,
        actions=actions or frozenset({"*:*"}),
        subject_matchers=subject_matchers or (SubjectMatcher(),),
        resource_matchers=resource_matchers or (ResourceMatcher(),),
        conditions=conditions,
        priority=priority,
        enabled=enabled,
    )


def make_request(
    *,
    subject: Subject | None = None,
    action: str = "documents:read",
    resource: Resource | None = None,
    context: Context | None = None,
) -> PolicyRequest:
    return PolicyRequest(
        subject=subject or make_subject(),
        action=action,
        resource=resource or make_resource(),
        context=context or make_context(),
    )
