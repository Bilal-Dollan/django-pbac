"""
Core enumerations for django-pbac.

This module is pure Python — no Django imports allowed.
"""
from __future__ import annotations

from enum import StrEnum


class Effect(StrEnum):
    """The effect of a policy decision."""

    PERMIT = "PERMIT"
    DENY = "DENY"


class ConflictResolution(StrEnum):
    """
    Strategy for resolving conflicts when multiple policies match a request.

    DENY_OVERRIDE (default — most secure):
        Any matching DENY policy wins over all PERMIT policies.

    PERMIT_OVERRIDE:
        Any matching PERMIT policy wins over all DENY policies.
        Use only when the security model requires optimistic defaults.

    FIRST_APPLICABLE:
        Policies are evaluated in priority order (DESC). The first matching
        policy determines the outcome. Similar to firewall rule semantics.
    """

    DENY_OVERRIDE = "DENY_OVERRIDE"  # ✅ DEFAULT
    PERMIT_OVERRIDE = "PERMIT_OVERRIDE"
    FIRST_APPLICABLE = "FIRST_APPLICABLE"


class PolicySourceType(StrEnum):
    """Where a policy was loaded from."""

    DATABASE = "database"
    CODE = "code"
    YAML = "yaml"


class SubjectType(StrEnum):
    """The type of principal making the request."""

    USER = "USER"
    SERVICE = "SERVICE"
    API_KEY = "API_KEY"
    ANONYMOUS = "ANONYMOUS"
