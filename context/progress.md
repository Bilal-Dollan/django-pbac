# Implementation Progress Log

## Status: ✅ COMPLETE

All files specified in the original specification have been created.

---

## Phase 1 — Config & Project Structure

**Completed files:**
- `pyproject.toml` — full build config (hatchling, dependencies, dev extras, ruff, mypy)
- `LICENSE` — MIT
- `README.md` — comprehensive with usage examples and config reference
- `CHANGELOG.md` — initial v0.1.0 entry
- `CONTRIBUTING.md` — contribution guidelines (setup, tests, PR process)

---

## Phase 2 — Core Engine (pure Python)

**Completed files:**
- `src/django_pbac/core/types.py`
- `src/django_pbac/core/exceptions.py`
- `src/django_pbac/core/models.py` (11 frozen dataclasses)
- `src/django_pbac/core/operators.py` (OperatorRegistry + 22 operators)
- `src/django_pbac/core/matchers.py`
- `src/django_pbac/core/evaluator.py` (PolicyEvaluator + ResourceFilter generation)

---

## Phase 3 — Policy Loaders

**Completed files:**
- `src/django_pbac/loaders/base.py` (PolicyLoader Protocol)
- `src/django_pbac/loaders/db.py` (DatabasePolicyLoader)
- `src/django_pbac/loaders/code.py` (BaseCodePolicy + CodePolicySet + CodeDefinedPolicyLoader)
- `src/django_pbac/loaders/yaml_loader.py` (YAMLPolicyLoader)
- `src/django_pbac/loaders/composite.py` (CompositePolicyLoader.from_settings())

---

## Phase 4 — Context Injectors

**Completed files:**
- `src/django_pbac/injectors/base.py` (ContextInjector Protocol)
- `src/django_pbac/injectors/user.py` (UserAttributeInjector)
- `src/django_pbac/injectors/jwt.py` (JWTClaimsInjector)
- `src/django_pbac/injectors/request_meta.py` (RequestMetadataInjector)
- `src/django_pbac/injectors/resource.py` (ResourceAttributeInjector)

---

## Phase 5 — Cache & Audit

**Completed files:**
- `src/django_pbac/cache/` (base, django_cache, null)
- `src/django_pbac/audit/` (base, db, structured_log, composite)

---

## Phase 6 — Database Layer

**Completed files:**
- `src/django_pbac/db/models.py` (PolicyModel, ConditionModel, PolicyVersionModel, AuditLogModel)
- `src/django_pbac/db/managers.py` (PolicyQuerySet with chainable filters)
- `src/django_pbac/db/admin.py`
- `src/django_pbac/db/migrations/0001_initial.py`

---

## Phase 7 — Django Integration

**Completed files:**
- `src/django_pbac/integration/middleware.py` (PBACMiddleware)
- `src/django_pbac/integration/decorators.py` (@require_policy, @deny_policy)
- `src/django_pbac/integration/mixins.py` (PBACViewMixin, PBACQuerySetMixin)
- `src/django_pbac/integration/templatetags/pbac_tags.py` ({% can %} tag)
- `src/django_pbac/integration/drf/permissions.py` (PBACPermission, PBACObjectPermission)

---

## Phase 8 — Adapters, Serializers, Engine

**Completed files:**
- `src/django_pbac/adapters/base.py` (ModelAdapter Protocol)
- `src/django_pbac/adapters/registry.py` (AdapterRegistry + adapter_registry)
- `src/django_pbac/serializers/json_serializer.py`
- `src/django_pbac/serializers/yaml_serializer.py`
- `src/django_pbac/engine.py` (PBACEngine + _LazyEngine + pbac_engine)

---

## Phase 9 — Tests

**Completed files:**
- `tests/__init__.py`
- `tests/conftest.py` (shared fixtures: subjects, resources, policies, evaluator)
- `tests/settings.py` (minimal Django settings for tests)
- `pytest.ini` (pytest config with DJANGO_SETTINGS_MODULE)

---

## Phase 10 — Bug Fixes & Test Suite Stabilisation

**Status: ✅ All 126 tests passing**

A full test-suite audit surfaced mismatches between the generated source and the
test-defined API contract. All issues were resolved; tests are the authoritative
spec.

### Build / Config

| File | Fix |
|---|---|
| `pyproject.toml` | `build-backend` corrected to `setuptools.build_meta` |
| `pytest.ini` | Converted from TOML to INI format; added `pythonpath = . src` |

### `core/types.py`
- All enum values changed to UPPERCASE strings:  
  `ConflictResolution.DENY_OVERRIDE` / `PERMIT_OVERRIDE` / `FIRST_APPLICABLE`  
  `SubjectType.USER` / `SERVICE` / `API_KEY` / `ANONYMOUS`

### `core/models.py`
- **`Subject`**: added `roles: frozenset[str] = field(default_factory=frozenset)` as a
  first-class field; `has_role()` / `has_any_role()` read from this field.
- **`SubjectMatcher`**: renamed `user_ids` → `id: str | None`; added
  `type: SubjectType | None`; renamed `attribute_conditions` → `attributes`;
  `roles` default changed from `None` to `frozenset()`.
- **`ResourceMatcher`**: `types` is now `str | None` (single string, `None` = match any);
  renamed `ids` → `id: str | None`; renamed `attribute_conditions` → `attributes`;
  added `@property type` as an alias for `types`.
- **`Policy`**: `subjects` → `subject_matchers: tuple[SubjectMatcher, ...]`;
  `resources` → `resource_matchers: tuple[ResourceMatcher, ...]`;
  `name` now has a default of `""`.
- **`Context`**: `extra` renamed to `environment`; `with_extra()` → `with_environment()`.
- **`PolicyDecision`**: `evaluation_trace` renamed to `trace`; `reason` now has
  default `""`.

### `core/operators.py`
- `OperatorRegistry.get(name)` now raises `KeyError` for unknown operators (was silent
  `None`).
- `resolve_attribute` / `_resolve_context`: added support for `context.environment.<key>`
  path (legacy `context.extra.<key>` also kept for compatibility).

### `core/matchers.py`
- `subject_matcher_matches` / `resource_matcher_matches` now accept `PolicyRequest`
  directly in addition to plain `Subject` / `Resource`.
- All field references updated to new names (`id`, `attributes`, `type`).

### `core/evaluator.py`
- `_evaluate_policy`: iterates `policy.subject_matchers` and `policy.resource_matchers`
  (was single-item `policy.subjects` / `policy.resources`).
- All `PolicyDecision` construction uses `trace=` (was `evaluation_trace=`).
- `get_permitted_resource_filter` updated for new matcher structure.

### `loaders/code.py`
- `BaseCodePolicy`: class attribute renamed `id` → `policy_id`; `subject` /
  `resources` replaced by `subject_matchers` / `resource_matchers` (lists).
- `CodePolicySet.unregister(policy_id)` method **added**.
- `CodeDefinedPolicyLoader.load_for_request`: replaced stale `policy.resources.types`
  lookup with iteration over `policy.resource_matchers`.

### `loaders/yaml_loader.py`
- `__init__` parameter renamed `dirs` → `directories`.
- `_parse_policy`: `name` field is now optional (defaults to `""`).
- Parser supports both list-of-matchers format (`subject_matchers:` /
  `resource_matchers:`) and legacy dict format (`subject:` / `resources:`).
- Uppercase enum values used throughout.

### `injectors/user.py`
- `user.groups.values_list("name", flat=True)` → `[g.name for g in user.groups.all()]`
  (compatible with non-standard user models).
- `Subject` constructed with `roles=frozenset(groups)`.

### `injectors/request_meta.py`
- `inject_context` now copies `ip` and `user_agent` into `context.environment` dict
  in addition to setting dedicated `ip_address` / `user_agent` fields.

### `integration/middleware.py`
- Module-level `pbac_engine` import wrapped in a try/except to prevent startup
  failures when settings are not yet configured.

### `tests/conftest.py`
- `ResourceMatcher(type=...)` call-site corrected to `ResourceMatcher(types=...)`.
- `context_default` fixture uses `environment=` kwarg.
- `tests/core/__init__.py`
- `tests/core/test_types.py`
- `tests/core/test_models.py`
- `tests/core/test_operators.py`
- `tests/core/test_matchers.py`
- `tests/core/test_evaluator.py`
- `tests/loaders/__init__.py`
- `tests/loaders/test_code_loader.py`
- `tests/loaders/test_yaml_loader.py`
- `tests/loaders/test_composite_loader.py`
- `tests/injectors/__init__.py`
- `tests/injectors/test_injectors.py`
- `tests/integration/__init__.py`
- `tests/integration/test_middleware.py`
- `tests/audit/__init__.py`
- `tests/audit/test_audit_logger.py`
- `tests/fixtures/policies.yaml`
- `tests/fixtures/factories.py`

---

## Phase 10 — Example Project

**Completed files:**
- `example/settings.py`
- `example/urls.py`
- `example/docs_app/__init__.py`
- `example/docs_app/models.py` (Document model)
- `example/docs_app/views.py` (decorator + mixin examples)
- `example/docs_app/urls.py`
- `example/policies/documents.yaml` (sample policies)

---

## Phase 11 — Docs & CI

**Completed files:**
- `mkdocs.yml` (Material theme, full nav)
- `docs/index.md`
- `.github/workflows/ci.yml` (test matrix Python 3.11/3.12/3.13 × Django 4.2/5.0/5.1)
- `.github/workflows/publish.yml` (OIDC trusted publishing to PyPI)

---

## Phase 12 — Context & Rules Folders

**Completed files:**
- `context/README.md`
- `context/architecture.md`
- `context/modules.md`
- `context/conventions.md`
- `context/progress.md` ← this file
- `context/decisions.md`
- `rules/README.md`
- `rules/evaluation.md`
- `rules/conventions.md`
- `rules/settings.md`
- `rules/testing.md`
