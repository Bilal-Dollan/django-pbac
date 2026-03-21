"""
Exceptions for django-pbac.

This module is pure Python — no Django imports allowed.
"""
from __future__ import annotations


class PBACError(Exception):
    """Base class for all django-pbac exceptions."""


class PolicyNotFound(PBACError):  # noqa: N818
    """Raised when a policy with the given ID is not found."""

    def __init__(self, policy_id: str) -> None:
        self.policy_id = policy_id
        super().__init__(f"Policy not found: {policy_id!r}")


class EvaluationError(PBACError):
    """
    Raised when the policy evaluator encounters an unrecoverable error.

    Note: Individual condition evaluation failures are NOT raised — they
    return False silently. EvaluationError is reserved for structural
    issues (e.g., invalid policy graph, circular references).
    """


class ConfigurationError(PBACError):
    """
    Raised when the PBAC configuration is invalid.

    Examples:
    - Unknown operator referenced in a condition
    - Invalid policy loader dotted path
    - Missing required setting
    """
