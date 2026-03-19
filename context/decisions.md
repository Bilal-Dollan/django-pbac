# Architecture Decision Records (ADRs)

## ADR-001: Pure Python core with no Django imports

**Date**: 2024-01  
**Status**: Accepted

**Context**: The policy evaluation engine (types, models, operators, matchers, evaluator)
needs to be independently testable and reusable outside Django contexts.

**Decision**: `src/django_pbac/core/` MUST have zero imports from `django.*`.

**Consequences**:
- Core tests do not require `pytest-django` or Django app setup
- The evaluator can be embedded in non-Django Python code
- `ResourceFilter.q_filter` holds `django.db.models.Q` — this is the only Django type
  that bleeds into core. Accepted as an explicit trade-off for queryset integration.

---

## ADR-002: Frozen dataclasses for all domain objects

**Date**: 2024-01  
**Status**: Accepted

**Context**: Domain objects (Subject, Resource, Policy, etc.) must be safe to cache,
hash, and pass across threads without mutation bugs.

**Decision**: All domain objects use `@dataclass(frozen=True)`.  
Collections use `frozenset` (unordered sets) or `tuple` (ordered sequences).

**Consequences**:
- `frozenset` prevents dict-based policies from being accidentally mutated after loading
- `tuple` for matchers/conditions preserves ordering for deterministic evaluation
- `dict` for `attributes` — content immutability not enforced; documented as "do not mutate"

---

## ADR-003: Protocol-based plugin interfaces

**Date**: 2024-01  
**Status**: Accepted

**Context**: PolicyLoader, AuditLogger, PolicyCache, ContextInjector, ModelAdapter must
be extensible by third parties without tight coupling to a common base class.

**Decision**: Use `typing.Protocol` (structural subtyping) for all plugin interfaces.

**Consequences**:
- Third-party implementations don't need to inherit from any abc
- duck-typing works at runtime; mypy checks at static analysis time
- `runtime_checkable` decorator not always required (Protocol is for type hints)

---

## ADR-004: Lazy engine singleton

**Date**: 2024-01  
**Status**: Accepted

**Context**: `engine.py` is imported by `middleware.py`, `decorators.py`, etc. at module
load time. But Django settings may not be configured yet when the package is imported
during test collection.

**Decision**: `pbac_engine` is a `_LazyEngine` proxy that defers `_build_engine()` until
first attribute access.

**Consequences**:
- All integration code can `from django_pbac.engine import pbac_engine` at module level
- Tests can import without `DJANGO_SETTINGS_MODULE` being set
- `pbac_engine.reset()` allows engine re-initialization in tests

---

## ADR-005: DENY by default (closed system)

**Date**: 2024-01  
**Status**: Accepted

**Context**: Authorization systems should be secure by default. No policies → no access.

**Decision**: `DEFAULT_DENY = True` in settings. `PolicyEvaluator` returns DENY when no
policies match, regardless of conflict resolution strategy.

**Consequences**:
- More verbose policy writing (every access must have an explicit PERMIT)
- Significantly more secure — forgotten resources are protected automatically
- Override with `DEFAULT_DENY = False` for permit-by-default systems (not recommended)

---

## ADR-006: DENY_OVERRIDE as default conflict resolution

**Date**: 2024-01  
**Status**: Accepted

**Context**: When both PERMIT and DENY policies match a request, one must win.

**Decision**: Default is `DENY_OVERRIDE` — any matching DENY beats any matching PERMIT.

**Consequences**:
- Security-first: one deny rule is enough to block access
- Predictable: no need to understand policy priority ordering to reason about security
- Higher-priority PERMIT cannot override a DENY (use PERMIT_OVERRIDE if needed)

---

## ADR-007: v1 ResourceFilter only supports eq and in operators

**Date**: 2024-01  
**Status**: Accepted (with v2 roadmap)

**Context**: Generating Django ORM `Q()` objects from arbitrary operators (regex,
ip_in_cidr, date_before) is very complex and operator-specific.

**Decision**: In v1, `get_permitted_resource_filter()` only generates Q() objects for
`eq` and `in` operators. Complex operators fall back to `permit_all=True` with a warning.

**Consequences**:
- Simple attribute-based filters work out of the box
- Complex operator policies require manual queryset filtering
- v2 will add extensible operator-to-ORM-lookup translation
