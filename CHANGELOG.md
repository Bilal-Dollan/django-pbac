# Changelog

All notable changes to `django-pbac` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
