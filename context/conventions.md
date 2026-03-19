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
- `tuple` for ordered collections that must be immutable (matchers, conditions)
- `dict` is allowed for attributes since content immutability is not enforced
- `__post_init__` for validation — raise `ValueError` on invalid data

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
