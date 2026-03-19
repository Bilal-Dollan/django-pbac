"""
PolicyLoader Protocol.

All policy loaders must implement this interface.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from django_pbac.core.models import Policy, Subject


@runtime_checkable
class PolicyLoader(Protocol):
    """
    Protocol for loading policies from a data source.

    Implementations must filter aggressively in ``load_for_request``:
    return only policies that COULD match the given subject/action/resource_type.
    Over-inclusion is safe (extra policies are filtered by the evaluator).
    Under-inclusion is a security bug — a matching policy would not be evaluated.
    """

    def load_for_request(
        self,
        subject: Subject,
        action: str,
        resource_type: str,
    ) -> list[Policy]:
        """Load policies relevant to this (subject, action, resource_type) triple."""
        ...

    def load_all(self) -> list[Policy]:
        """Load all policies from this source."""
        ...

    def get_by_id(self, policy_id: str) -> Policy | None:
        """Return the policy with the given ID, or None if not found."""
        ...

    def save(self, policy: Policy) -> Policy:
        """Persist a policy. Returns the saved policy (with any DB-generated fields)."""
        ...

    def delete(self, policy_id: str) -> None:
        """Delete the policy with the given ID."""
        ...
