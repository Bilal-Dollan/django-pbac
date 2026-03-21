# Module Inventory

All modules in `src/django_pbac/`. Status: ✅ Complete.

## Package Root

| File | Purpose | Status |
|---|---|---|
| `__init__.py` | Package exports: `pbac_engine`, `PolicyDecision`, `Subject`, etc. | ✅ |
| `apps.py` | `DjangoPbacConfig` — AppConfig, ready() signal | ✅ |
| `conf.py` | `PBACSettings` — typed settings with defaults | ✅ |
| `engine.py` | `PBACEngine` + `_LazyEngine` + `pbac_engine` singleton | ✅ |

## core/ (pure Python, no Django)

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | — | ✅ |
| `types.py` | `Effect`, `ConflictResolution`, `PolicySourceType`, `SubjectType` | ✅ |
| `exceptions.py` | `PBACError`, `PolicyNotFound`, `EvaluationError`, `ConfigurationError` | ✅ |
| `models.py` | `Subject`, `Resource`, `Context`, `PolicyRequest`, `Condition`, `SubjectMatcher`, `ResourceMatcher`, `Policy`, `PolicyDecision`, `EvaluationStep`, `ResourceFilter` | ✅ |
| `operators.py` | `OperatorRegistry`, `operator_registry`, 22 operators, `resolve_attribute`, `resolve_condition_value` — `get(name)` raises `KeyError` for unknown ops; `register()` returns fully-typed `Callable[[Callable[[Any,Any],bool]],...]`; `op_eq`/`op_neq` use `bool()` to prevent `no-any-return` | ✅ |
| `matchers.py` | `action_matches`, `subject_matcher_matches`, `resource_matcher_matches` — accept `PolicyRequest` directly; `subject_matcher_matches` signature is multi-line (split for line-length) | ✅ |
| `evaluator.py` | `PolicyEvaluator.evaluate()`, `get_permitted_resource_filter()` — iterates `subject_matchers`/`resource_matchers` tuples; `_build_q_filters()` uses `supported_operators` (lowercase) local variable | ✅ |

## loaders/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `base.py` | `PolicyLoader` Protocol | ✅ |
| `db.py` | `DatabasePolicyLoader` — `save()`/`_to_policy()` use `subject_matchers`/`resource_matchers` API; `ConditionModel.objects` calls carry `# type: ignore[attr-defined]` | ✅ |
| `code.py` | `BaseCodePolicy` (use `policy_id`/`subject_matchers`/`resource_matchers`), `CodePolicySet` (+ `unregister()`), `CodeDefinedPolicyLoader`, `code_policy_set` | ✅ |
| `yaml_loader.py` | `YAMLPolicyLoader(directories=[...])` — `name` field optional in YAML, supports list-of-matchers format | ✅ |
| `composite.py` | `CompositePolicyLoader`, `CompositePolicyLoader.from_settings()` — `get_by_id`/`save` return `cast(Policy, ...)` | ✅ |

## injectors/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `base.py` | `ContextInjector` Protocol | ✅ |
| `user.py` | `UserAttributeInjector` | ✅ |
| `jwt.py` | `JWTClaimsInjector` — uses `context.environment` / `dataclasses.replace`; `jwt.decode` result cast to `dict[str, Any]` | ✅ |
| `request_meta.py` | `RequestMetadataInjector` | ✅ |
| `resource.py` | `ResourceAttributeInjector` | ✅ |

## cache/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `base.py` | `PolicyCache` Protocol | ✅ |
| `django_cache.py` | `DjangoCacheBackend` — `pickle.loads` result cast to `list[Policy]` | ✅ |
| `null.py` | `NullCache` | ✅ |

## audit/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `base.py` | `AuditLogger` Protocol | ✅ |
| `db.py` | `DBAuditLogger` — `AuditLogModel.objects.create(...)` carries `# type: ignore[attr-defined]` | ✅ |
| `structured_log.py` | `StructuredLogAuditLogger` | ✅ |
| `composite.py` | `CompositeAuditLogger`, `.from_settings()` | ✅ |

## db/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `models.py` | `PolicyModel`, `ConditionModel`, `PolicyVersionModel`, `AuditLogModel` | ✅ |
| `managers.py` | `PolicyQuerySet(models.QuerySet[Any])`, `PolicyManager(models.Manager[Any])` | ✅ |
| `admin.py` | `PolicyAdmin(admin.ModelAdmin[PolicyModel])`, `AuditLogAdmin(admin.ModelAdmin[AuditLogModel])`, `PolicyVersionAdmin(admin.ModelAdmin[PolicyVersionModel])`, `ConditionInline(admin.TabularInline[ConditionModel, PolicyModel])` | ✅ |
| `migrations/__init__.py` | — | ✅ |
| `migrations/0001_initial.py` | Creates all 4 tables | ✅ |

## integration/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `middleware.py` | `PBACMiddleware` | ✅ |
| `decorators.py` | `@require_policy`, `@deny_policy` | ✅ |
| `mixins.py` | `PBACViewMixin`, `PBACQuerySetMixin` | ✅ |
| `templatetags/__init__.py` | — | ✅ |
| `templatetags/pbac_tags.py` | `{% can %}`, `{% cannot %}`, `{% endcan %}` — uses `from django.template.base import FilterExpression` directly (not `template.FilterExpression`) | ✅ |
| `drf/__init__.py` | — | ✅ |
| `drf/permissions.py` | `PBACPermission`, `PBACObjectPermission` | ✅ |

## adapters/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `base.py` | `ModelAdapter` Protocol | ✅ |
| `registry.py` | `AdapterRegistry`, `adapter_registry` | ✅ |

## serializers/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `json_serializer.py` | `PolicyJSONSerializer` — uses current API (`subject_matchers`, `resource_matchers`, field names `id`/`attributes`/`roles`/`types`) | ✅ |
| `yaml_serializer.py` | `PolicyYAMLSerializer` | ✅ |
