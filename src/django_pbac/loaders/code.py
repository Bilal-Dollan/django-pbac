"""
CodeDefinedPolicyLoader — define policies in Python code.

Usage::

    from django_pbac.loaders.code import BaseCodePolicy, code_policy_set
    from django_pbac.core.types import Effect
    from django_pbac.core.models import SubjectMatcher, ResourceMatcher

    class DocumentReadPolicy(BaseCodePolicy):
        id = "code-doc-read-01"
        name = "Document Read — Authenticated"
        effect = Effect.PERMIT
        actions = ["documents:read", "documents:list"]
        subject = SubjectMatcher.any_authenticated()
        resources = ResourceMatcher(types=frozenset(["document"]))

    code_policy_set.register(DocumentReadPolicy)
"""
from __future__ import annotations

import logging
from typing import Any

from django_pbac.core.models import (
    Condition,
    Policy,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.types import ConflictResolution, Effect, PolicySourceType


logger = logging.getLogger(__name__)


class BaseCodePolicy:
    """
    Base class for code-defined policies.

    Subclass this and set class attributes. Register with ``code_policy_set.register()``.

    Required attributes:
        id (str):           Unique policy ID.
        name (str):         Human-readable name.
        effect (Effect):    PERMIT or DENY.
        actions (list[str]): Action strings (may include glob patterns).
        subject (SubjectMatcher): Subject selector.
        resources (ResourceMatcher): Resource selector.

    Optional attributes:
        conditions (list[Condition]):   Extra conditions.
        description (str):              Human-readable description.
        priority (int):                 Policy priority (higher = evaluated first).
        conflict_resolution:            Override conflict resolution strategy.
        is_active (bool):               Whether this policy is active.
        created_by (str):               Creator identifier.
        tags (set[str] | frozenset[str]): Searchable tags.
    """

    id: str
    name: str
    effect: Effect
    actions: list[str]
    subject: SubjectMatcher = SubjectMatcher.anyone()
    resources: ResourceMatcher
    conditions: list[Condition] = []
    description: str = ""
    priority: int = 0
    conflict_resolution: ConflictResolution = ConflictResolution.DENY_OVERRIDE
    is_active: bool = True
    created_by: str = "code"
    tags: set[str] | frozenset[str] = frozenset()

    @classmethod
    def to_policy(cls) -> Policy:
        """Convert this class definition to a Policy dataclass."""
        return Policy(
            id=cls.id,
            name=cls.name,
            effect=cls.effect,
            subjects=cls.subject,
            actions=frozenset(cls.actions),
            resources=cls.resources,
            conditions=tuple(cls.conditions),
            description=cls.description,
            priority=cls.priority,
            conflict_resolution=cls.conflict_resolution,
            is_active=cls.is_active,
            created_by=cls.created_by,
            tags=frozenset(cls.tags),
            source=PolicySourceType.CODE,
        )


class CodePolicySet:
    """
    Registry of code-defined policies.

    Module-level singleton: ``code_policy_set``.
    """

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}

    def register(self, policy_class: type[BaseCodePolicy]) -> type[BaseCodePolicy]:
        """Register a BaseCodePolicy subclass. Can be used as a decorator."""
        policy = policy_class.to_policy()
        if policy.id in self._policies:
            logger.warning(
                "Code policy with ID %r is already registered. Overwriting.", policy.id
            )
        self._policies[policy.id] = policy
        return policy_class

    def register_policy(self, policy: Policy) -> None:
        """Register a Policy dataclass directly."""
        self._policies[policy.id] = policy

    def all(self) -> list[Policy]:
        return list(self._policies.values())

    def get(self, policy_id: str) -> Policy | None:
        return self._policies.get(policy_id)

    def clear(self) -> None:
        """Remove all registered code policies. Useful for testing."""
        self._policies.clear()


# Module-level singleton
code_policy_set = CodePolicySet()


class CodeDefinedPolicyLoader:
    """
    Loads policies from the in-memory ``code_policy_set`` registry.

    Uses the global singleton by default. Pass a custom ``CodePolicySet``
    instance for testing or multi-tenant isolation.
    """

    def __init__(self, policy_set: CodePolicySet | None = None) -> None:
        self._set = policy_set or code_policy_set

    def load_for_request(
        self,
        subject: Subject,
        action: str,
        resource_type: str,
    ) -> list[Policy]:
        """Return all code policies that could match this request."""
        result = []
        for policy in self._set.all():
            if not policy.is_active:
                continue
            # Filter by resource type
            if resource_type not in policy.resources.types:
                continue
            result.append(policy)
        return result

    def load_all(self) -> list[Policy]:
        return self._set.all()

    def get_by_id(self, policy_id: str) -> Policy | None:
        return self._set.get(policy_id)

    def save(self, policy: Policy) -> Policy:
        """Register a policy programmatically."""
        self._set.register_policy(policy)
        return policy

    def delete(self, policy_id: str) -> None:
        self._set._policies.pop(policy_id, None)
