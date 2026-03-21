"""
Operator registry and built-in operators for condition evaluation.

This module is pure Python — no Django imports allowed.

Operators are pure functions: (actual_value, expected_value) -> bool.
They must NEVER raise — return False on type mismatch or missing value.

Usage::

    from django_pbac.core.operators import operator_registry

    result = operator_registry.evaluate("eq", "hello", "hello")  # True

    @operator_registry.register("my_custom_op")
    def my_op(actual, expected):
        return str(actual).startswith(str(expected))
"""
from __future__ import annotations

import ipaddress
import logging
import re
from collections.abc import Callable
from datetime import datetime, time
from typing import Any

from django_pbac.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class OperatorRegistry:
    """
    Registry mapping operator name strings to callable implementations.

    Thread-safe for reads. Operators should be registered at module import time.
    """

    def __init__(self) -> None:
        self._operators: dict[str, Callable[[Any, Any], bool]] = {}

    def register(
        self, name: str
    ) -> Callable[[Callable[[Any, Any], bool]], Callable[[Any, Any], bool]]:
        """Decorator to register a new operator by name."""

        def decorator(fn: Callable[[Any, Any], bool]) -> Callable[[Any, Any], bool]:
            self._operators[name] = fn
            return fn

        return decorator

    def get(self, name: str) -> Any:
        """
        Return the callable for the named operator.

        Raises KeyError if the operator is not registered.
        """
        if name not in self._operators:
            raise KeyError(f"Unknown operator: {name!r}")
        return self._operators[name]

    def evaluate(self, operator: str, actual: Any, expected: Any) -> bool:
        """
        Evaluate an operator.

        Returns False (not raises) on type mismatch or None values.
        Raises ConfigurationError if the operator is unknown.
        """
        if operator not in self._operators:
            raise ConfigurationError(f"Unknown operator: {operator!r}")
        try:
            return bool(self._operators[operator](actual, expected))
        except Exception:
            return False

    def is_registered(self, name: str) -> bool:
        return name in self._operators

    def list_operators(self) -> list[str]:
        return sorted(self._operators.keys())


# Module-level singleton
operator_registry = OperatorRegistry()


# ---------------------------------------------------------------------------
# String operators
# ---------------------------------------------------------------------------

@operator_registry.register("eq")
def op_eq(actual: Any, expected: Any) -> bool:
    """Equality — case-sensitive."""
    return bool(actual == expected)


@operator_registry.register("neq")
def op_neq(actual: Any, expected: Any) -> bool:
    """Inequality."""
    return bool(actual != expected)


@operator_registry.register("eq_i")
def op_eq_i(actual: Any, expected: Any) -> bool:
    """Case-insensitive equality."""
    return str(actual).lower() == str(expected).lower()


@operator_registry.register("startswith")
def op_startswith(actual: Any, expected: Any) -> bool:
    return str(actual).startswith(str(expected))


@operator_registry.register("endswith")
def op_endswith(actual: Any, expected: Any) -> bool:
    return str(actual).endswith(str(expected))


@operator_registry.register("contains")
def op_contains(actual: Any, expected: Any) -> bool:
    """True if expected substring is found in actual string."""
    return str(expected) in str(actual)


@operator_registry.register("regex")
def op_regex(actual: Any, expected: Any) -> bool:
    """Full regex match against the actual value."""
    return bool(re.fullmatch(str(expected), str(actual)))


# ---------------------------------------------------------------------------
# Numeric operators
# ---------------------------------------------------------------------------

@operator_registry.register("gt")
def op_gt(actual: Any, expected: Any) -> bool:
    return float(actual) > float(expected)


@operator_registry.register("gte")
def op_gte(actual: Any, expected: Any) -> bool:
    return float(actual) >= float(expected)


@operator_registry.register("lt")
def op_lt(actual: Any, expected: Any) -> bool:
    return float(actual) < float(expected)


@operator_registry.register("lte")
def op_lte(actual: Any, expected: Any) -> bool:
    return float(actual) <= float(expected)


# ---------------------------------------------------------------------------
# Collection operators
# ---------------------------------------------------------------------------

@operator_registry.register("in")
def op_in(actual: Any, expected: Any) -> bool:
    """True if actual is a member of the expected collection."""
    return actual in expected


@operator_registry.register("not_in")
def op_not_in(actual: Any, expected: Any) -> bool:
    return actual not in expected


@operator_registry.register("contains_any")
def op_contains_any(actual: Any, expected: Any) -> bool:
    """True if actual list/set shares any element with expected."""
    return bool(set(actual) & set(expected))


@operator_registry.register("contains_all")
def op_contains_all(actual: Any, expected: Any) -> bool:
    """True if actual list/set contains all elements of expected."""
    return set(expected).issubset(set(actual))


# ---------------------------------------------------------------------------
# Boolean / null operators
# ---------------------------------------------------------------------------

@operator_registry.register("is_true")
def op_is_true(actual: Any, _expected: Any) -> bool:
    return bool(actual) is True


@operator_registry.register("is_false")
def op_is_false(actual: Any, _expected: Any) -> bool:
    return bool(actual) is False


@operator_registry.register("is_null")
def op_is_null(actual: Any, _expected: Any) -> bool:
    return actual is None


@operator_registry.register("is_not_null")
def op_is_not_null(actual: Any, _expected: Any) -> bool:
    return actual is not None


# ---------------------------------------------------------------------------
# Network operators
# ---------------------------------------------------------------------------

@operator_registry.register("ip_in_cidr")
def op_ip_in_cidr(actual: Any, expected: Any) -> bool:
    """True if actual IP address is within the expected CIDR network."""
    return ipaddress.ip_address(str(actual)) in ipaddress.ip_network(str(expected), strict=False)


@operator_registry.register("ip_not_in_cidr")
def op_ip_not_in_cidr(actual: Any, expected: Any) -> bool:
    return ipaddress.ip_address(str(actual)) not in ipaddress.ip_network(
        str(expected), strict=False
    )


# ---------------------------------------------------------------------------
# DateTime operators
# ---------------------------------------------------------------------------

@operator_registry.register("date_before")
def op_date_before(actual: Any, expected: Any) -> bool:
    """True if actual datetime is before expected (both as ISO strings or datetime)."""
    actual_dt = datetime.fromisoformat(str(actual)) if isinstance(actual, str) else actual
    expected_dt = datetime.fromisoformat(str(expected)) if isinstance(expected, str) else expected
    return actual_dt < expected_dt


@operator_registry.register("date_after")
def op_date_after(actual: Any, expected: Any) -> bool:
    """True if actual datetime is after expected."""
    actual_dt = datetime.fromisoformat(str(actual)) if isinstance(actual, str) else actual
    expected_dt = datetime.fromisoformat(str(expected)) if isinstance(expected, str) else expected
    return actual_dt > expected_dt


@operator_registry.register("time_between")
def op_time_between(actual: Any, expected: Any) -> bool:
    """
    True if actual time (or datetime) falls between start and end times.

    ``expected`` must be a dict: {"start": "HH:MM", "end": "HH:MM"}

    Handles midnight crossover: if start > end (e.g., 22:00-06:00), the
    check wraps around midnight correctly.
    """
    if isinstance(actual, datetime):
        actual_time = actual.time()
    elif isinstance(actual, time):
        actual_time = actual
    else:
        # Parse HH:MM or HH:MM:SS
        parts = str(actual).split("T")[-1].split("+")[0].split("Z")[0]
        h, m, *s = parts.split(":")
        actual_time = time(int(h), int(m), int(s[0]) if s else 0)

    start_h, start_m = expected["start"].split(":")
    end_h, end_m = expected["end"].split(":")
    start_time = time(int(start_h), int(start_m))
    end_time = time(int(end_h), int(end_m))

    if start_time <= end_time:
        return start_time <= actual_time <= end_time
    else:
        # Midnight crossover: e.g., 22:00 → 06:00
        return actual_time >= start_time or actual_time <= end_time


# ---------------------------------------------------------------------------
# Attribute path resolver
# ---------------------------------------------------------------------------

def resolve_attribute(path: str, request: Any) -> Any:
    """
    Resolve a dotted attribute path against a PolicyRequest.

    Supported paths:
        subject.id
        subject.type
        subject.attributes.<key>
        resource.type
        resource.id
        resource.attributes.<key>
        resource.ancestors
        context.ip_address
        context.timestamp
        context.user_agent
        context.request_id
        context.extra.<key>

    Returns None (not raises) if any part of the path is missing.
    """
    parts = path.split(".")
    if not parts:
        return None

    root = parts[0]
    if root == "subject":
        return _resolve_subject(parts[1:], request.subject)
    elif root == "resource":
        return _resolve_resource(parts[1:], request.resource)
    elif root == "context":
        return _resolve_context(parts[1:], request.context)
    return None


def _resolve_subject(parts: list[str], subject: Any) -> Any:
    if not parts:
        return subject
    segment = parts[0]
    if segment == "id":
        return subject.id
    if segment == "type":
        return subject.type.value if hasattr(subject.type, "value") else subject.type
    if segment == "attributes":
        if len(parts) < 2:
            return subject.attributes
        return subject.attributes.get(parts[1])
    return None


def _resolve_resource(parts: list[str], resource: Any) -> Any:
    if not parts:
        return resource
    segment = parts[0]
    if segment == "id":
        return resource.id
    if segment == "type":
        return resource.type
    if segment == "ancestors":
        return resource.ancestors
    if segment == "attributes":
        if len(parts) < 2:
            return resource.attributes
        return resource.attributes.get(parts[1])
    return None


def _resolve_context(parts: list[str], context: Any) -> Any:
    if not parts:
        return context
    segment = parts[0]
    if segment == "timestamp":
        return context.timestamp
    if segment == "ip_address":
        return context.ip_address
    if segment == "user_agent":
        return context.user_agent
    if segment == "request_id":
        return context.request_id
    if segment == "environment":
        if len(parts) < 2:
            return context.environment
        return context.environment.get(parts[1])
    if segment == "extra":
        if len(parts) < 2:
            return getattr(context, "extra", context.environment)
        return getattr(context, "extra", context.environment).get(parts[1])
    return None


def resolve_condition_value(value: Any, request: Any) -> Any:
    """
    Resolve a condition value, handling cross-references.

    If ``value`` is a dict with key ``"ref"``, the value of that key is
    treated as an attribute path and resolved against the request.

    Example::

        resolve_condition_value({"ref": "subject.attributes.tenant_id"}, request)
        # Returns: request.subject.attributes["tenant_id"]
    """
    if isinstance(value, dict) and "ref" in value:
        return resolve_attribute(value["ref"], request)
    return value
