"""
Core dataclasses for django-pbac.

All dataclasses are frozen=True (immutable). Use dataclasses.replace() to
produce modified copies. This module is pure Python — no Django imports allowed.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Self
from uuid import uuid4

from django_pbac.core.types import (
    ConflictResolution,
    Effect,
    PolicySourceType,
    SubjectType,
)


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Subject:
    """
    Represents the principal making the request.

    Attributes:
        id:         Unique identifier (Django user PK as string, API key ID, etc.)
        type:       SubjectType enum value.
        attributes: Arbitrary key-value pairs injected by ContextInjectors.
                    Common keys: roles (list[str]), groups (list[str]),
                    department (str), tenant_id (str), clearance_level (int).
    """

    id: str
    type: SubjectType = SubjectType.USER
    roles: frozenset[str] = field(default_factory=frozenset)
    attributes: dict[str, Any] = field(default_factory=dict)

    def with_attribute(self, key: str, value: Any) -> Self:
        """Return new Subject with an additional attribute. Used by injectors."""
        new_attrs = {**self.attributes, key: value}
        return replace(self, attributes=new_attrs)

    def has_role(self, role: str) -> bool:
        """Return True if the subject has the given role."""
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Return True if the subject has any of the given roles."""
        return bool(set(roles) & self.roles)

    @classmethod
    def anonymous(cls) -> Self:
        """Factory: create an anonymous subject."""
        return cls(id="anonymous", type=SubjectType.ANONYMOUS)


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Resource:
    """
    Represents the object being accessed.

    Attributes:
        type:       Resource type string, e.g. "document", "invoice", "workspace".
        id:         Resource instance ID. None = collection-level operation.
        attributes: Arbitrary key-value pairs loaded by ResourceAttributeInjector.
                    Common keys: owner_id, tenant_id, status, visibility.
        ancestors:  Ordered list of (resource_type, resource_id) tuples from
                    root → direct parent. Used for hierarchical policy matching.
                    Example: [("workspace", "ws-1"), ("folder", "folder-5")]
    """

    type: str
    id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    ancestors: list[tuple[str, str]] = field(default_factory=list)

    def with_attribute(self, key: str, value: Any) -> Self:
        """Return new Resource with an additional attribute."""
        return replace(self, attributes={**self.attributes, key: value})

    def with_ancestors(self, ancestors: list[tuple[str, str]]) -> Self:
        """Return new Resource with the given ancestors."""
        return replace(self, ancestors=ancestors)

    @classmethod
    def collection(cls, resource_type: str) -> Self:
        """Factory: create a collection-level resource (no specific ID)."""
        return cls(type=resource_type, id=None)


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Context:
    """
    Environmental context of the request (time, IP, etc.).

    Attributes:
        timestamp:   UTC datetime of the request. Defaults to now(UTC).
        ip_address:  Client IP address string.
        user_agent:  HTTP User-Agent header value.
        request_id:  Unique ID for this request (UUID4).
        extra:       Arbitrary additional context (e.g. from JWT claims).
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str = field(default_factory=lambda: str(uuid4()))
    environment: dict[str, Any] = field(default_factory=dict)

    def with_environment(self, key: str, value: Any) -> Self:
        """Return new Context with an additional environment field."""
        return replace(self, environment={**self.environment, key: value})


# ---------------------------------------------------------------------------
# PolicyRequest
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PolicyRequest:
    """
    The complete input to the policy evaluator.

    Attributes:
        subject:  Who is making the request.
        action:   Namespaced action string, e.g. "documents:read", "invoices:approve".
                  MUST contain exactly one ":" separator.
        resource: What is being accessed.
        context:  Environmental context.
    """

    subject: Subject
    action: str
    resource: Resource
    context: Context = field(default_factory=Context)

    def __post_init__(self) -> None:
        if not self.action or ":" not in self.action:
            raise ValueError(
                f"action must be namespaced with ':' separator. Got: {self.action!r}. "
                f"Example: 'documents:read'"
            )

    @property
    def action_namespace(self) -> str:
        """The namespace portion of the action string. e.g. 'documents'."""
        return self.action.split(":")[0]

    @property
    def action_verb(self) -> str:
        """The verb portion of the action string. e.g. 'read'."""
        return self.action.split(":", 1)[1]


# ---------------------------------------------------------------------------
# Condition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Condition:
    """
    A single condition that must hold for a policy to match.

    Attributes:
        operator:  Registered operator name: "eq", "in", "gte", "ip_in_cidr", etc.
        attribute: Dotted attribute path. Allowed roots: subject, resource, context.
                   Examples:
                     "subject.attributes.department"
                     "resource.attributes.status"
                     "context.ip_address"
                     "context.extra.tenant_id"
        value:     Comparison operand. May be a scalar, list, or cross-reference dict
                   {"ref": "subject.attributes.tenant_id"} — resolved at evaluation time.
        negate:    If True, the condition result is inverted (logical NOT).
    """

    operator: str
    attribute: str
    value: Any
    negate: bool = False

    ALLOWED_ROOTS: frozenset[str] = frozenset({"subject", "resource", "context"})

    def __post_init__(self) -> None:
        root = self.attribute.split(".")[0]
        if root not in self.ALLOWED_ROOTS:
            raise ValueError(
                f"Condition attribute must start with one of "
                f"{self.ALLOWED_ROOTS}. Got: {self.attribute!r}"
            )


# ---------------------------------------------------------------------------
# SubjectMatcher
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubjectMatcher:
    """
    Determines which subjects a policy applies to.

    All specified fields are ANDed — the subject must satisfy ALL criteria.
    Unspecified (None) criteria are skipped (treated as wildcard).

    Examples::

        # Any authenticated user
        SubjectMatcher.any_authenticated()

        # Finance managers or directors with clearance >= 3
        SubjectMatcher(
            roles=frozenset(["finance_manager", "finance_director"]),
            attribute_conditions={"clearance_level": {"gte": 3}},
        )
    """

    id: str | None = None
    type: SubjectType | None = None
    subject_types: frozenset[SubjectType] | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    groups: frozenset[str] | None = None
    attributes: dict[str, Any] | None = None

    @classmethod
    def anyone(cls) -> Self:
        """Matches any subject, including anonymous."""
        return cls()

    @classmethod
    def any_authenticated(cls) -> Self:
        """Matches any authenticated subject (USER, SERVICE, API_KEY)."""
        return cls(
            subject_types=frozenset(
                {SubjectType.USER, SubjectType.SERVICE, SubjectType.API_KEY}
            )
        )


# ---------------------------------------------------------------------------
# ResourceMatcher
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResourceMatcher:
    """
    Determines which resources a policy applies to.

    Attributes:
        types:               Required. Resource type strings this policy covers.
        ids:                 Optional. Restrict to exact resource IDs (rare).
        attribute_conditions: Conditions on resource attributes. Supports:
            {"status": "published"}                   → exact match (eq)
            {"status": {"in": ["draft", "review"]}}   → value in set
            {"tenant_id": {"ref": "subject.id"}}       → cross-reference
            {"score": {"gte": 5}}                      → comparison
        ancestor_conditions: Match on ancestor resources (hierarchical).
            [{"type": "workspace", "attribute_conditions": {"owner_id": {"ref": "subject.id"}}}]

    .. note::
        v1 Limitation: ``ancestor_conditions`` only matches by ancestor resource *type*.
        Full ancestor attribute evaluation requires the ancestor ``Resource`` object to
        be loaded in memory (via ``ResourceAttributeInjector``). If ``attribute_conditions``
        are specified in ``ancestor_conditions``, they are evaluated only when the
        corresponding ancestor ``Resource`` has been loaded and its attributes are present
        in ``resource.ancestors``. Pass fully-loaded ancestor resources via
        ``Resource.with_ancestors()`` to enable attribute-level ancestor matching.
    """

    types: str | None = None
    id: str | None = None
    attributes: dict[str, Any] | None = None
    ancestor_conditions: list[dict[str, Any]] | None = None

    @property
    def type(self) -> str | None:
        """Alias for types (singular access)."""
        return self.types


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Policy:
    """
    A single access control policy.

    Actions support glob patterns:
      "documents:read"  → exact match
      "documents:*"     → all actions in the documents namespace
      "*"               → all actions (use with extreme care)

    Conflict resolution is per-policy in v1 but the engine uses the global
    setting by default. Per-policy overrides are respected by the evaluator.
    """

    id: str
    effect: Effect
    subject_matchers: tuple[SubjectMatcher, ...]
    actions: frozenset[str]
    resource_matchers: tuple[ResourceMatcher, ...]
    conditions: tuple[Condition, ...] = field(default_factory=tuple)
    name: str = ""
    description: str = ""
    priority: int = 0
    conflict_resolution: ConflictResolution = ConflictResolution.DENY_OVERRIDE
    is_active: bool = True
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    source: PolicySourceType = PolicySourceType.DATABASE
    version: int = 1
    created_by: str = "system"
    tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.actions:
            raise ValueError("Policy must specify at least one action.")

    def is_valid_at(self, dt: datetime) -> bool:
        """Return True if this policy is valid (not expired) at the given datetime."""
        if self.valid_from and dt < self.valid_from:
            return False
        if self.valid_until and dt > self.valid_until:
            return False
        return True


# ---------------------------------------------------------------------------
# PolicyDecision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvaluationStep:
    """A single step in the evaluation trace — one policy considered."""

    policy_id: str
    policy_name: str
    matched: bool
    effect: Effect | None
    reason: str


@dataclass(frozen=True)
class PolicyDecision:
    """
    The result of evaluating a PolicyRequest against a set of policies.

    Attributes:
        effect:                 PERMIT or DENY.
        reason:                 Human-readable summary of the decision.
        request:                The original PolicyRequest.
        matched_policies:       IDs of policies that fully matched.
        denied_by:              Name of the policy that caused a DENY (if any).
        permitted_by:           Name of the policy that caused a PERMIT (if any).
        evaluation_trace:       Full per-policy evaluation trace (if enabled).
        evaluation_time_ms:     Time taken for evaluation in milliseconds.
        evaluated_policy_count: Total number of policies considered.
    """

    effect: Effect
    request: PolicyRequest
    reason: str = ""
    matched_policies: tuple[str, ...] = field(default_factory=tuple)
    denied_by: str | None = None
    permitted_by: str | None = None
    trace: tuple[EvaluationStep, ...] = field(default_factory=tuple)
    evaluation_time_ms: float = 0.0
    evaluated_policy_count: int = 0

    @property
    def is_permit(self) -> bool:
        return self.effect == Effect.PERMIT

    @property
    def is_deny(self) -> bool:
        return self.effect == Effect.DENY

    @classmethod
    def default_deny(
        cls,
        request: PolicyRequest,
        reason: str = "No matching policy found.",
    ) -> Self:
        """Factory: create a default-deny decision."""
        return cls(effect=Effect.DENY, reason=reason, request=request)


# ---------------------------------------------------------------------------
# ResourceFilter  (used by queryset integration — defined here to avoid Django deps)
# ---------------------------------------------------------------------------

@dataclass
class ResourceFilter:
    """
    Result of ``PolicyEvaluator.get_permitted_resource_filter()``.

    Used by ``PBACQuerySetMixin`` to filter a Django QuerySet to only
    the resources the subject is permitted to access.

    Attributes:
        permit_all:          Subject has unrestricted access — return all objects.
        deny_all:            Subject has no access — return empty QuerySet.
        q_filter:            A Django ``Q()`` object encoding attribute constraints
                             derived from PERMIT policy conditions.
                             Only set when neither ``permit_all`` nor ``deny_all``.
        filter_explanation:  Human-readable description of applied filters.
    """

    permit_all: bool = False
    deny_all: bool = False
    q_filter: Any = None
    filter_explanation: str = ""

    @property
    def is_unrestricted(self) -> bool:
        return self.permit_all

    @property
    def is_blocked(self) -> bool:
        return self.deny_all
