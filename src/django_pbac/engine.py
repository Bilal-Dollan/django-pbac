"""
PBACEngine — the main entry point for django-pbac.

``pbac_engine`` is a module-level singleton configured from Django settings.
It wires together: PolicyLoaders, PolicyEvaluator, PolicyCache,
AuditLoggers, and ContextInjectors.

Usage::

    from django_pbac.engine import pbac_engine

    decision = pbac_engine.evaluate(policy_request)
    resource_filter = pbac_engine.get_resource_filter(subject, action, resource_type)
"""
from __future__ import annotations

import logging
from typing import Any

from django_pbac.core.evaluator import PolicyEvaluator
from django_pbac.core.models import (
    Context,
    PolicyDecision,
    PolicyRequest,
    Resource,
    ResourceFilter,
    Subject,
)
from django_pbac.core.operators import operator_registry
from django_pbac.core.types import ConflictResolution, SubjectType

logger = logging.getLogger(__name__)


class PBACEngine:
    """
    Central orchestrator for policy evaluation.

    Responsibilities:
    - Build Subject/Context from Django requests via ContextInjectors
    - Load relevant policies via CompositePolicyLoader (with caching)
    - Evaluate policies via PolicyEvaluator
    - Log decisions via AuditLoggers
    - Expose queryset filter generation

    Instantiated once at Django startup via ``_build_engine()``.
    """

    def __init__(
        self,
        loader: Any,
        evaluator: PolicyEvaluator,
        cache: Any,
        audit_logger: Any,
        context_injectors: list[Any],
    ) -> None:
        self._loader = loader
        self._evaluator = evaluator
        self._cache = cache
        self._audit_logger = audit_logger
        self._context_injectors = context_injectors

    @property
    def context_injectors(self) -> list[Any]:
        return self._context_injectors

    # ------------------------------------------------------------------
    # Core evaluate
    # ------------------------------------------------------------------

    def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        """
        Evaluate a PolicyRequest and return a PolicyDecision.

        Performs the full evaluation cycle:
        1. Check cache for policies.
        2. Load policies from loader.
        3. Evaluate via PolicyEvaluator.
        4. Log via AuditLogger.
        5. Return decision.
        """
        cache_key = self._cache.make_key(
            request.subject.id,
            request.action,
            request.resource.type,
        )

        policies = self._cache.get(cache_key)
        if policies is None:
            policies = self._loader.load_for_request(
                subject=request.subject,
                action=request.action,
                resource_type=request.resource.type,
            )
            self._cache.set(cache_key, policies)

        decision = self._evaluator.evaluate(request, policies)

        try:
            self._audit_logger.log(decision)
        except Exception as exc:
            logger.error("Audit logger failed: %s", exc)

        return decision

    # ------------------------------------------------------------------
    # QuerySet filter
    # ------------------------------------------------------------------

    def get_resource_filter(
        self,
        subject: Subject,
        action: str,
        resource_type: str,
    ) -> ResourceFilter:
        """
        Return a ResourceFilter for use with PBACQuerySetMixin.

        Loads all PERMIT-relevant policies and generates a Q() filter.
        """
        cache_key = self._cache.make_key(subject.id, action, resource_type)
        policies = self._cache.get(cache_key)
        if policies is None:
            policies = self._loader.load_for_request(
                subject=subject,
                action=action,
                resource_type=resource_type,
            )
            self._cache.set(cache_key, policies)

        return self._evaluator.get_permitted_resource_filter(
            subject=subject,
            action=action,
            resource_type=resource_type,
            policies=policies,
        )

    # ------------------------------------------------------------------
    # Subject building
    # ------------------------------------------------------------------

    def build_subject(self, request: Any) -> Subject:
        """
        Build a Subject from a Django HttpRequest using ContextInjectors.

        Falls back to anonymous subject if no injectors are configured.
        """
        subject = Subject(id="anonymous", type=SubjectType.ANONYMOUS)
        context = Context()

        for injector in self._context_injectors:
            try:
                subject = injector.inject_subject(subject, request)
                context = injector.inject_context(context, request)
            except Exception as exc:
                logger.warning(
                    "ContextInjector %s error: %s", type(injector).__name__, exc
                )

        return subject

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def is_permitted(
        self,
        subject: Subject,
        action: str,
        resource: Resource,
        context: Context | None = None,
    ) -> bool:
        """Quick boolean check. Use ``evaluate()`` for full decision info."""
        policy_request = PolicyRequest(
            subject=subject,
            action=action,
            resource=resource,
            context=context or Context(),
        )
        return self.evaluate(policy_request).is_permit

    def invalidate_cache(self, subject_id: str | None = None) -> None:
        """Invalidate policy cache. Pass subject_id to target a specific subject."""
        if subject_id is None:
            self._cache.clear()
        else:
            # We can only clear the whole cache; key-level invalidation requires
            # tracking all keys per subject (not implemented in v1).
            self._cache.clear()


# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------

def _build_engine() -> PBACEngine:
    """Build the PBACEngine singleton from Django settings."""
    from django.utils.module_loading import import_string

    from django_pbac.audit.composite import CompositeAuditLogger
    from django_pbac.conf import pbac_settings
    from django_pbac.loaders.composite import CompositePolicyLoader

    # Conflict resolution
    conflict_resolution = ConflictResolution(pbac_settings.CONFLICT_RESOLUTION)

    # Evaluator
    evaluator = PolicyEvaluator(
        conflict_resolution=conflict_resolution,
        operator_registry=operator_registry,
        enable_trace=pbac_settings.ENABLE_EVALUATION_TRACE,
    )

    # Loaders
    loader = CompositePolicyLoader.from_settings()

    # Cache
    try:
        cache_class = import_string(pbac_settings.CACHE_BACKEND)
        cache = cache_class()
    except Exception as exc:
        logger.warning("Failed to initialize cache backend: %s. Using NullCache.", exc)
        from django_pbac.cache.null import NullCache

        cache = NullCache()

    # Audit loggers
    audit_logger = CompositeAuditLogger.from_settings()

    # Context injectors
    injectors = []
    injectors_config = pbac_settings.CONTEXT_INJECTORS
    if isinstance(injectors_config, str):
        injectors_config = [injectors_config]

    for dotted_path in injectors_config:
        try:
            klass = import_string(dotted_path)
            injectors.append(klass())
        except Exception as exc:
            logger.error("Failed to load context injector %r: %s", dotted_path, exc)

    return PBACEngine(
        loader=loader,
        evaluator=evaluator,
        cache=cache,
        audit_logger=audit_logger,
        context_injectors=injectors,
    )


class _LazyEngine:
    """
    Lazy proxy for PBACEngine.

    The engine is not instantiated until first use, since Django settings
    may not be configured at import time.
    """

    def __init__(self) -> None:
        self._engine: PBACEngine | None = None

    def _get_engine(self) -> PBACEngine:
        if self._engine is None:
            self._engine = _build_engine()
        return self._engine

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_engine(), name)

    def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        return self._get_engine().evaluate(request)

    def get_resource_filter(
        self,
        subject: Subject,
        action: str,
        resource_type: str,
    ) -> ResourceFilter:
        return self._get_engine().get_resource_filter(subject, action, resource_type)

    def build_subject(self, request: Any) -> Subject:
        return self._get_engine().build_subject(request)

    def is_permitted(
        self,
        subject: Subject,
        action: str,
        resource: Resource,
        context: Context | None = None,
    ) -> bool:
        return self._get_engine().is_permitted(subject, action, resource, context)

    def invalidate_cache(self, subject_id: str | None = None) -> None:
        return self._get_engine().invalidate_cache(subject_id)

    @property
    def context_injectors(self) -> list[Any]:
        return self._get_engine().context_injectors

    def reset(self) -> None:
        """Reset the engine (useful for testing with overridden settings)."""
        self._engine = None


# Module-level singleton — lazy by default
pbac_engine: _LazyEngine = _LazyEngine()
