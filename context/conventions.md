# Code Conventions

## Python Style

- **Python 3.11+** target — uses `match` statements, `Self` type, `from __future__ import annotations`
- **Ruff** for linting (replaces flake8 + isort + pyupgrade)
- **mypy** with `strict = true` for type checking
- Line length: 100 characters
- Docstrings: Google style

## Frozen Dataclasses

All domain objects (`Subject`, `Resource`, `Policy`, etc.) are `@dataclass(frozen=True)`.

```python
@dataclass(frozen=True)
class Subject:
    id: str
    type: SubjectType
    roles: frozenset[str] = field(default_factory=frozenset)
    attributes: dict[str, Any] = field(default_factory=dict)
```

**Key rules:**
- `frozenset` for collections that must be immutable (roles, actions)
- `tuple` for ordered collections that must be immutable (matchers `tuple[SubjectMatcher, ...]`, conditions)
- `dict` is allowed for attributes since content immutability is not enforced
- `__post_init__` for validation — raise `ValueError` on invalid data

## Domain Object Field Names (authoritative)

Use these exact field names; do not use the old names on the left:

| Dataclass | Old name (removed) | Current name |
|---|---|---|
| `Policy` | `subjects` | `subject_matchers: tuple[SubjectMatcher, ...]` |
| `Policy` | `resources` | `resource_matchers: tuple[ResourceMatcher, ...]` |
| `Context` | `extra` | `environment: dict[str, Any]` |
| `PolicyDecision` | `evaluation_trace` | `trace` |
| `SubjectMatcher` | `user_ids` | `id: str \| None` |
| `SubjectMatcher` | `attribute_conditions` | `attributes: dict \| None` |
| `ResourceMatcher` | `ids` | `id: str \| None` |
| `ResourceMatcher` | `attribute_conditions` | `attributes: dict \| None` |

## Enum Values

All enum string values are **UPPERCASE**.

```python
class ConflictResolution(str, Enum):
    DENY_OVERRIDE = "DENY_OVERRIDE"
    PERMIT_OVERRIDE = "PERMIT_OVERRIDE"
    FIRST_APPLICABLE = "FIRST_APPLICABLE"

class SubjectType(str, Enum):
    USER = "USER"
    SERVICE = "SERVICE"
    API_KEY = "API_KEY"
    ANONYMOUS = "ANONYMOUS"
```

YAML policy files must use uppercase values: `effect: PERMIT`, `conflict_resolution: DENY_OVERRIDE`.

## StrEnum (Python 3.11+)

All enums in `core/types.py` use `StrEnum` (via `from enum import StrEnum`), not `class Foo(str, Enum)`.
This was applied by `ruff --fix` (UP042). Behaviour is identical; `StrEnum` is the idiomatic
3.11+ form.

## ClassVar on Mutable Class Attributes (RUF012)

Class attributes with mutable defaults must be annotated with `typing.ClassVar` to satisfy
ruff RUF012, **except** in Django `Meta` inner classes and migration files where the
convention is to use `# noqa: RUF012` inline (adding `ClassVar` to Django Meta attributes
would be non-idiomatic):

```python
# Good — in regular classes
class BaseCodePolicy:
    subject_matchers: ClassVar[list[SubjectMatcher]] = []
    resource_matchers: ClassVar[list[ResourceMatcher]] = []

# Good — Django Meta / migration boilerplate
class Meta:
    ordering = ["-priority", "name"]  # noqa: RUF012
    indexes = [...]                   # noqa: RUF012
```

## `except Exception: pass` (S110)

The `# noqa: S110` directive must appear on the `except` line, not the `pass` line:

```python
# Correct
except Exception:  # noqa: S110
    pass

# Wrong — ruff reports S110 on except, not pass
except Exception:
    pass  # noqa: S110
```

## Protocols (Structural Typing)

Plugins use `typing.Protocol` rather than ABCs:

```python
class PolicyLoader(Protocol):
    def load_for_request(self, subject, action, resource_type) -> list[Policy]: ...
    def load_all(self) -> list[Policy]: ...
```

This avoids forcing inheritance on third-party implementations.

## Singletons and the Lazy Pattern

Module-level singletons use a lazy proxy:

```python
class _LazyEngine:
    def __init__(self) -> None:
        self._engine: PBACEngine | None = None

    def _get_engine(self) -> PBACEngine:
        if self._engine is None:
            self._engine = _build_engine()
        return self._engine

pbac_engine: _LazyEngine = _LazyEngine()
```

This prevents import-time Django setup errors when the module is imported before `django.setup()`.

## Settings Access

Settings are accessed through `pbac_settings` (a `PBACSettings` proxy):

```python
from django_pbac.conf import pbac_settings

value = pbac_settings.CACHE_TTL
```

Never import directly from `django.conf.settings` in the package.

## Error Handling

- Exceptions that bubble to user code use the `PBACError` hierarchy
- Internal errors during plugin loading/execution are caught and logged (never crash)
- `logging.getLogger(__name__)` used throughout — never `print()`

## Testing Conventions

- pytest with `pytest-django`
- No factory_boy dependency in core tests — use builder functions in `tests/fixtures/factories.py`
- `conftest.py` at the top level provides shared fixtures
- Tests in `tests/core/` have no Django DB access (pure unit tests)
- Tests that require DB are marked `@pytest.mark.django_db`

## mypy Strict Compliance

The project runs `mypy` with `strict = true`. Key patterns:

### Generic Django base classes
Always supply type parameters:
```python
class PolicyQuerySet(models.QuerySet[Any]): ...
class PolicyManager(models.Manager[Any]): ...
class PolicyAdmin(admin.ModelAdmin[PolicyModel]): ...
class ConditionInline(admin.TabularInline[ConditionModel, PolicyModel]): ...
ClassVar[list[Any]]            # not bare ClassVar[list]
```

### Callable decorator factories
```python
def require_policy(...) -> Callable[..., Any]:
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]: ...
```

### `no-any-return`
Wrap `Any`-returning expressions with `cast` or `bool()`:
```python
return cast(list[Policy], pickle.loads(raw))   # noqa: S301
return bool(actual == expected)                # in operator functions
return cast(Policy, loader.get_by_id(id))      # generic protocol call sites
```

### `has_*_permission` methods in admin
Use `request: HttpRequest` (not `request: object`) — django-stubs now correctly
types these, so `# type: ignore[override]` is no longer needed.

### `Model.objects` outside `db/models.py`
Calls like `SomeModel.objects.create(...)` from non-model files require
`# type: ignore[attr-defined]` because django-stubs does not resolve `.objects`
without a full stub-generation pass.

---

## Import Order

Follows ruff/isort conventions:
1. Standard library
2. Third-party (Django, PyYAML, PyJWT)
3. Local imports (`from django_pbac.xxx import ...`)

Within the package, imports must not create cycles:
- `core/` imports nothing from the package
- `engine.py` imports from `core/`, `loaders/`, `audit/`, `cache/`
- `integration/` imports from `engine.py`
- `db/` imports from `core/`

## File Naming

- `snake_case.py` for all Python files
- `yaml_loader.py` (not `yaml.py` — avoids shadowing stdlib yaml)
- `json_serializer.py` (not `json.py`)
- `null.py` for no-op / null object pattern implementations
