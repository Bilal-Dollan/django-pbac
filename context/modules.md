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
| `operators.py` | `OperatorRegistry`, `operator_registry`, 22 operators, `resolve_attribute`, `resolve_condition_value` | ✅ |
| `matchers.py` | `action_matches`, `subject_matcher_matches`, `resource_matcher_matches` | ✅ |
| `evaluator.py` | `PolicyEvaluator.evaluate()`, `get_permitted_resource_filter()` | ✅ |

## loaders/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `base.py` | `PolicyLoader` Protocol | ✅ |
| `db.py` | `DatabasePolicyLoader` | ✅ |
| `code.py` | `BaseCodePolicy`, `CodePolicySet`, `CodeDefinedPolicyLoader`, `code_policy_set` | ✅ |
| `yaml_loader.py` | `YAMLPolicyLoader` | ✅ |
| `composite.py` | `CompositePolicyLoader`, `CompositePolicyLoader.from_settings()` | ✅ |

## injectors/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `base.py` | `ContextInjector` Protocol | ✅ |
| `user.py` | `UserAttributeInjector` | ✅ |
| `jwt.py` | `JWTClaimsInjector` | ✅ |
| `request_meta.py` | `RequestMetadataInjector` | ✅ |
| `resource.py` | `ResourceAttributeInjector` | ✅ |

## cache/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `base.py` | `PolicyCache` Protocol | ✅ |
| `django_cache.py` | `DjangoCacheBackend` | ✅ |
| `null.py` | `NullCache` | ✅ |

## audit/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `base.py` | `AuditLogger` Protocol | ✅ |
| `db.py` | `DBAuditLogger` | ✅ |
| `structured_log.py` | `StructuredLogAuditLogger` | ✅ |
| `composite.py` | `CompositeAuditLogger`, `.from_settings()` | ✅ |

## db/

| File | Key Symbols | Status |
|---|---|---|
| `__init__.py` | re-exports | ✅ |
| `models.py` | `PolicyModel`, `ConditionModel`, `PolicyVersionModel`, `AuditLogModel` | ✅ |
| `managers.py` | `PolicyQuerySet` with chainable filters | ✅ |
| `admin.py` | `PolicyAdmin`, `AuditLogAdmin`, `PolicyVersionAdmin` | ✅ |
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
| `templatetags/pbac_tags.py` | `{% can %}`, `{% cannot %}`, `{% endcan %}` | ✅ |
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
| `json_serializer.py` | `PolicyJSONSerializer` | ✅ |
| `yaml_serializer.py` | `PolicyYAMLSerializer` | ✅ |
