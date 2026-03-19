# Architecture

## Pattern: PEP / PDP / PIP

django-pbac follows the standard XACML-inspired architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│  Django Request                                                  │
│                                                                  │
│  ┌─────────────┐     ┌──────────────────┐                       │
│  │  Middleware  │────▶│  PBACMiddleware  │  (PEP: request entry)│
│  └─────────────┘     └────────┬─────────┘                       │
│                               │ builds Subject + Context         │
│                               ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PBACEngine  (engine.py)                                 │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐  │   │
│  │  │ PolicyLoader  │  │PolicyEvaluator│  │AuditLogger  │  │   │
│  │  │  (composite)  │  │   (PDP)       │  │             │  │   │
│  │  └───────┬───────┘  └───────┬───────┘  └─────────────┘  │   │
│  │          │                  │                             │   │
│  │  ┌───────▼───────┐  ┌───────▼───────┐                    │   │
│  │  │  PolicyCache  │  │ operator_reg  │                    │   │
│  │  └───────────────┘  └───────────────┘                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                               │ PolicyDecision                   │
│                               ▼                                  │
│  ┌──────────────────────────────┐                               │
│  │  require_policy decorator    │  (PEP: view enforcement)      │
│  │  PBACViewMixin               │                               │
│  │  PBACPermission (DRF)        │                               │
│  └──────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## Core Layer (pure Python, no Django)

Located in `src/django_pbac/core/` — this module MUST NOT import Django.
It can be tested in isolation without a Django app setup.

| Module | Responsibility |
|---|---|
| `types.py` | Enumerations: Effect, ConflictResolution, PolicySourceType, SubjectType |
| `exceptions.py` | Exception hierarchy rooted at PBACError |
| `models.py` | Frozen dataclasses: Subject, Resource, Context, PolicyRequest, Policy, PolicyDecision, etc. |
| `operators.py` | OperatorRegistry + 22 built-in operators + attribute path resolver |
| `matchers.py` | action_matches, subject_matcher_matches, resource_matcher_matches |
| `evaluator.py` | PolicyEvaluator — 7-step evaluation algorithm |

## Evaluation Algorithm (PolicyEvaluator.evaluate)

1. Find all policies where `action` matches (exact, wildcard `ns:*`, global `*`)
2. For each candidate policy, check all `subject_matchers` — ANY must match
3. For each remaining policy, check all `resource_matchers` — ANY must match
4. For each remaining policy, evaluate all `conditions` — ALL must pass
5. Collect PERMIT set and DENY set
6. Apply conflict resolution:
   - **DENY_OVERRIDE**: if DENY set non-empty → DENY. Else if PERMIT set non-empty → PERMIT. Else → DENY (default deny)
   - **PERMIT_OVERRIDE**: if PERMIT set non-empty → PERMIT. Else if DENY set non-empty → DENY. Else → DENY
   - **FIRST_APPLICABLE**: sort all matching by priority (desc), return first matching effect
7. Return `PolicyDecision` (immutable, with optional `trace`)

## Data Flow for Queryset Filtering

```
PBACQuerySetMixin.get_queryset()
    → pbac_engine.get_resource_filter(subject, action, resource_type)
        → loader.load_for_request(...)
        → evaluator.get_permitted_resource_filter(...)
            → _build_q_filters(permit_policies)
                → Q(field=value) for "eq" conditions
                → Q(field__in=values) for "in" conditions
                → permit_all=True if no conditions found (open policy)
    → queryset.filter(resource_filter.q_filter)
```

## Key Design Decisions

1. **Frozen dataclasses** for all domain objects — immutability prevents subtle bugs
2. **Protocol-based plugins** — PolicyLoader, AuditLogger, PolicyCache are Protocols, not ABCs
3. **Lazy engine singleton** — `pbac_engine` is a `_LazyEngine` proxy; real engine built on first access
4. **No circular imports** — `engine.py` imports from loaders/audit/cache only; integration imports engine
5. **DENY by default** — `DEFAULT_DENY = True` means no matching policies → DENY
