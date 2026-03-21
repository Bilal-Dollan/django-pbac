"""
Subject and resource matcher logic.

This module is pure Python — no Django imports allowed.

Matchers determine whether a policy's subject/resource selectors apply to a
given request. The evaluator calls these after filtering for action and
resource type.
"""
from __future__ import annotations

import logging
from typing import Any

from django_pbac.core.exceptions import ConfigurationError
from django_pbac.core.models import (
    PolicyRequest,
    Resource,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.operators import operator_registry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Action glob matching
# ---------------------------------------------------------------------------

def action_matches(pattern: str, action: str) -> bool:
    """
    Return True if ``pattern`` matches ``action``.

    Supported patterns:
        ``"documents:read"``  — exact match
        ``"documents:*"``     — all actions in the documents namespace
        ``"*"``               — matches any action

    v1 Constraint: ``*`` is only supported as a full wildcard (``"*"``) or as
    a namespace-trailing wildcard (``"ns:*"``). Mid-string wildcards like
    ``"doc:re*"`` are NOT supported and will raise ``ConfigurationError``.
    """
    if pattern == "*":
        return True

    if pattern == action:
        return True

    if "*" in pattern:
        # Validate pattern structure
        namespace, _, verb_pattern = pattern.partition(":")
        if "*" in namespace:
            raise ConfigurationError(
                f"Wildcard in action namespace is not supported. Got: {pattern!r}. "
                "Use 'namespace:*' for all actions in a namespace, or '*' for all."
            )
        if verb_pattern != "*" and "*" in verb_pattern:
            raise ConfigurationError(
                f"Mid-string wildcards in action verb are not supported in v1. "
                f"Got: {pattern!r}. Only trailing '*' is allowed, e.g. 'documents:*'."
            )
        # namespace:* pattern
        if verb_pattern == "*":
            action_namespace = action.split(":")[0]
            return namespace == action_namespace

    return False


# ---------------------------------------------------------------------------
# SubjectMatcher
# ---------------------------------------------------------------------------

def subject_matcher_matches(
    matcher: SubjectMatcher,
    request_or_subject: PolicyRequest | Subject,
) -> bool:
    """
    Return True if the subject satisfies ALL criteria in the matcher.

    An empty SubjectMatcher (all None/empty) matches ANY subject including anonymous.
    Accepts either a PolicyRequest or a Subject directly.
    """
    subject = (
        request_or_subject.subject
        if isinstance(request_or_subject, PolicyRequest)
        else request_or_subject
    )
    # id: subject.id must match
    if matcher.id is not None and subject.id != matcher.id:
        return False

    # single-type shorthand (SubjectMatcher.type)
    if matcher.type is not None and subject.type != matcher.type:
        return False

    # subject_types: subject.type must be in the set
    if matcher.subject_types is not None and subject.type not in matcher.subject_types:
        return False

    # roles: subject must have ANY of the specified roles (skip if empty)
    if matcher.roles:
        if not (matcher.roles & subject.roles):
            return False

    # groups: subject must be in ANY of the specified groups
    if matcher.groups is not None:
        subject_groups = set(subject.attributes.get("groups", []))
        if not (set(matcher.groups) & subject_groups):
            return False

    # attributes: each k→v must hold
    if matcher.attributes is not None:
        for attr_key, expected in matcher.attributes.items():
            actual = subject.attributes.get(attr_key)
            if not _evaluate_attribute_condition(actual, expected):
                return False

    return True


# ---------------------------------------------------------------------------
# ResourceMatcher
# ---------------------------------------------------------------------------

def resource_matcher_matches(
    matcher: ResourceMatcher,
    request_or_resource: PolicyRequest | Resource,
    subject: Subject | None = None,
) -> bool:
    """
    Return True if the resource satisfies ALL criteria in the matcher.

    Accepts either a PolicyRequest (preferred) or a (Resource, Subject) pair.
    """
    if isinstance(request_or_resource, PolicyRequest):
        resource = request_or_resource.resource
        subject = request_or_resource.subject
    else:
        resource = request_or_resource
        if subject is None:
            raise ValueError("subject is required when passing a Resource directly")
    # types: if specified, resource.type must match exactly
    if matcher.types is not None and resource.type != matcher.types:
        return False

    # id: if specified, resource.id must match exactly
    if matcher.id is not None and resource.id != matcher.id:
        return False

    # attributes
    if matcher.attributes is not None:
        for attr_key, expected in matcher.attributes.items():
            actual = resource.attributes.get(attr_key)
            # Resolve cross-references against the subject
            resolved_expected = _resolve_ref_against_subject(expected, subject)
            if not _evaluate_attribute_condition(actual, resolved_expected):
                return False

    # ancestor_conditions
    if matcher.ancestor_conditions is not None:
        for anc_condition in matcher.ancestor_conditions:
            if not _check_ancestor_condition(anc_condition, resource, subject):
                return False

    return True


def _resolve_ref_against_subject(value: Any, subject: Subject) -> Any:
    """
    Resolve {"ref": "subject.xxx"} cross-references against the subject.

    Note: Only subject.* refs are supported at matcher level.
    Full request-level refs require a PolicyRequest and are handled in
    the evaluator's condition-evaluation phase.
    """
    if isinstance(value, dict) and "ref" in value:
        ref_path = value["ref"]
        parts = ref_path.split(".")
        if parts[0] == "subject":
            if len(parts) >= 3 and parts[1] == "attributes":
                return subject.attributes.get(parts[2])
            elif len(parts) == 2 and parts[1] == "id":
                return subject.id
            elif len(parts) == 2 and parts[1] == "type":
                return subject.type.value
    return value


def _check_ancestor_condition(
    condition: dict[str, Any],
    resource: Resource,
    subject: Subject,
) -> bool:
    """
    Check a single ancestor condition.

    v1: Matches ancestors by type. If attribute_conditions are specified,
    they are evaluated only if the ancestor has attribute data available.

    The ancestor list is a list of (resource_type, resource_id) tuples.
    In v1, ancestor attributes are NOT available unless explicitly loaded
    via ResourceAttributeInjector. This is a known limitation.
    """
    required_type = condition.get("type")
    attr_conditions: dict[str, Any] = condition.get("attribute_conditions", {})

    matching_ancestors = [
        (atype, aid)
        for atype, aid in resource.ancestors
        if atype == required_type
    ]

    if not matching_ancestors:
        return False

    # If no attribute conditions, type match is sufficient
    if not attr_conditions:
        return True

    # v1: attribute conditions on ancestors require extended ancestor data.
    # Since ancestors only store (type, id), attribute evaluation falls back
    # to True (permissive) to avoid false negatives. Log a warning.
    logger.warning(
        "django-pbac v1 limitation: ancestor attribute_conditions cannot be evaluated "
        "without loaded ancestor resource objects. Condition on ancestor type %r is "
        "type-matched only. Use ResourceAttributeInjector to load ancestor attributes.",
        required_type,
    )
    return True


def _evaluate_attribute_condition(actual: Any, expected: Any) -> bool:
    """
    Evaluate a simple attribute condition.

    Supports:
        scalar value    → ``eq`` comparison
        {"gte": N}      → numeric comparison
        {"lte": N}      → numeric comparison
        {"gt": N}       → numeric comparison
        {"lt": N}       → numeric comparison
        {"in": [...]}   → membership check
        {"not_in": ...} → non-membership check
        {"regex": ...}  → regex match
    """
    if isinstance(expected, dict):
        # Operator dict: e.g. {"gte": 3} or {"in": ["a", "b"]}
        for op_name, op_value in expected.items():
            if op_name == "ref":
                # Cross-reference that wasn't resolved — treat as eq
                return operator_registry.evaluate("eq", actual, op_value)
            if operator_registry.is_registered(op_name):
                return operator_registry.evaluate(op_name, actual, op_value)
        return False

    # Plain equality
    return operator_registry.evaluate("eq", actual, expected)
