"""
Core enumerations for django-pbac.

This module is pure Python — no Django imports allowed.
"""
from __future__ import annotations

from enum import Enum


class Effect(str, Enum):
    """The effect of a policy decision."""

    PERMIT = "PERMIT"
    DENY = "DENY"


class ConflictResolution(str, Enum):
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

    DENY_OVERRIDE = "deny_override"  # ✅ DEFAULT
    PERMIT_OVERRIDE = "permit_override"
    FIRST_APPLICABLE = "first_applicable"


class PolicySourceType(str, Enum):
    """Where a policy was loaded from."""

    DATABASE = "database"
    CODE = "code"
    YAML = "yaml"


class SubjectType(str, Enum):
    """The type of principal making the request."""

    USER = "user"
    SERVICE = "service"
    API_KEY = "api_key"
    ANONYMOUS = "anonymous"
