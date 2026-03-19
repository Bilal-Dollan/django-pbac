"""Core package — pure Python, no Django imports."""
from django_pbac.core.types import (
    ConflictResolution,
    Effect,
    PolicySourceType,
    SubjectType,
)
from django_pbac.core.models import (
    Condition,
    Context,
    EvaluationStep,
    Policy,
    PolicyDecision,
    PolicyRequest,
    Resource,
    ResourceFilter,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.exceptions import (
    ConfigurationError,
    EvaluationError,
    PBACError,
    PolicyNotFound,
)
from django_pbac.core.operators import operator_registry
from django_pbac.core.evaluator import PolicyEvaluator

__all__ = [
    # types
    "Effect",
    "ConflictResolution",
    "PolicySourceType",
    "SubjectType",
    # models
    "Subject",
    "Resource",
    "Context",
    "PolicyRequest",
    "Condition",
    "SubjectMatcher",
    "ResourceMatcher",
    "Policy",
    "PolicyDecision",
    "EvaluationStep",
    "ResourceFilter",
    # exceptions
    "PBACError",
    "PolicyNotFound",
    "EvaluationError",
    "ConfigurationError",
    # engine
    "operator_registry",
    "PolicyEvaluator",
]
