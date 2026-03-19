# Convention Rules

Rules governing code conventions for the django-pbac codebase.

---

## RULE-CONV-001: core/ must have zero Django imports

`src/django_pbac/core/` is the pure-Python evaluation engine.
No file in `core/` may import from `django.*`.

The only exception is `ResourceFilter.q_filter` which holds a `django.db.models.Q`
object — but the import of `Q` lives in `integration/` and `db/`, not `core/`.

---

## RULE-CONV-002: All domain objects use frozen dataclasses

```python
@dataclass(frozen=True)
class MyDomainObject:
    ...
```

Never use regular dicts or mutable objects to represent policies, subjects, or decisions.

---

## RULE-CONV-003: Use frozenset for unordered collections in dataclasses

```python
roles: frozenset[str] = field(default_factory=frozenset)
actions: frozenset[str] = field(default_factory=frozenset)
```

Use `tuple` for ordered sequences (matchers, conditions, trace steps).

---

## RULE-CONV-004: Plugin interfaces use typing.Protocol

```python
class PolicyLoader(Protocol):
    def load_for_request(self, ...) -> list[Policy]: ...
```

Never use ABCs for plugin interfaces. This allows duck-typing without inheritance.

---

## RULE-CONV-005: pbac_engine is always a lazy proxy

Never build `PBACEngine` at module import time. Always use `_LazyEngine`.

```python
# Correct
pbac_engine: _LazyEngine = _LazyEngine()

# Wrong — breaks import before django.setup()
pbac_engine = _build_engine()
```

---

## RULE-CONV-006: Settings accessed via pbac_settings, not django.conf.settings

```python
from django_pbac.conf import pbac_settings
value = pbac_settings.CACHE_TTL
```

Never use `from django.conf import settings; settings.PBAC`.

---

## RULE-CONV-007: Avoid shadowing stdlib names

- Use `yaml_loader.py` not `yaml.py`
- Use `json_serializer.py` not `json.py`
- Do not create files that shadow standard library module names

---

## RULE-CONV-008: Plugin loading failures are logged, not raised

When a plugin (injector, loader, audit logger) fails to initialize or execute,
log the error and continue gracefully. Never crash the request.

```python
try:
    injector.inject_subject(subject, request)
except Exception as exc:
    logger.warning("ContextInjector %s error: %s", type(injector).__name__, exc)
```

---

## RULE-CONV-009: Import order

1. Standard library
2. Third-party (`django`, `yaml`, `jwt`)
3. Local (`from django_pbac.xxx import ...`)

Enforced by ruff.

---

## RULE-CONV-010: No circular imports

Import dependency order (lower cannot import from higher):
```
core/  ←  db/ loaders/ injectors/ cache/ audit/  ←  engine.py  ←  integration/
```

`apps.py` imports from `engine.py` in `ready()`, not at module level.
