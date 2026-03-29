# Changelog

All notable changes to `django-pbac` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Root-level Django admin module so PBAC models are auto-discovered in admin.
- Cache invalidation signals for policy and condition changes.
- Production-oriented PBAC settings helper and recommended logging config.
- VS Code `validate` task for running Ruff, mypy, and pytest locally.

### Changed
- DRF `PBACPermission` now supports a direct `pbac_action` attribute on API views.
- DRF usage examples now recommend permission classes for JSON 403 responses instead of `PBACViewMixin` on `APIView`.
- Packaging cleanup: generated `egg-info` metadata is no longer tracked in git.

### Fixed
- Database policy loading now avoids backend-specific JSON `contains` lookups during request evaluation.
- Conflict resolution values now parse correctly from lowercase database/admin values like `deny_override`.
- Database audit logging now degrades safely when PBAC audit tables are not migrated yet.
- Django admin registrations now load reliably across supported Django versions.
- PBAC cache is invalidated when policies are changed in the admin.
- Removed stale mypy `type: ignore` comments flagged as unused.

## [0.1.0] - 2026-03-19

### Added
- Initial release of django-pbac
- Core PBAC evaluation engine (pure Python, no Django dependency)
- `PolicyEvaluator` with DENY_OVERRIDE, PERMIT_OVERRIDE, FIRST_APPLICABLE conflict resolution
- Frozen dataclasses: `Subject`, `Resource`, `Context`, `PolicyRequest`, `Policy`,
  `Condition`, `SubjectMatcher`, `ResourceMatcher`, `PolicyDecision`, `EvaluationStep`
- Full operator registry with 22 built-in operators (string, numeric, collection,
  boolean, network CIDR, datetime)
- Cross-reference conditions (`{"ref": "subject.attributes.tenant_id"}`)
- Three policy loaders: `DatabasePolicyLoader`, `CodeDefinedPolicyLoader`, `YAMLPolicyLoader`
- `CompositePolicyLoader` merging all sources
- Django ORM models: `PolicyModel`, `AuditLogModel`, `PolicyVersionModel`
- Full Django admin for all models
- Django cache integration via `DjangoCacheBackend`
- Audit logging: `DatabaseAuditLogger`, `StructuredLogAuditLogger`, `CompositeAuditLogger`
- Context injectors: `UserAttributeInjector`, `JWTClaimsInjector`,
  `RequestMetadataInjector`, `ResourceAttributeInjector`
- Django integration: `PBACMiddleware`, `@require_policy`, `@deny_policy`
- DRF permission classes: `PBACPermission`, `PBACObjectPermission`
- Template tags: `{% can %}`, `{% cannot %}`
- `PBACQuerySetMixin` for automatic queryset filtering
- `pbac_engine` singleton wired from Django settings
- JSON and YAML policy serializers
- Model adapter registry
- Example Django project: document management system
- Full test suite with factory-boy factories
- MkDocs documentation
- GitHub Actions CI/CD pipelines
