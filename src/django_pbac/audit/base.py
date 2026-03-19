"""AuditLogger Protocol."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from django_pbac.core.models import PolicyDecision


@runtime_checkable
class AuditLogger(Protocol):
    """
    Protocol for audit loggers.

    Implementors receive every PolicyDecision and are responsible for
    persisting or emitting the audit record. They must not raise — log
    errors internally and continue.
    """

    def log(self, decision: PolicyDecision) -> None:
        """Log a policy decision."""
        ...
