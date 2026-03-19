# django-pbac

[![CI](https://github.com/django-pbac/django-pbac/actions/workflows/ci.yml/badge.svg)](https://github.com/django-pbac/django-pbac/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/django-pbac.svg)](https://pypi.org/project/django-pbac/)
[![Python](https://img.shields.io/pypi/pyversions/django-pbac.svg)](https://pypi.org/project/django-pbac/)
[![Django](https://img.shields.io/badge/Django-4.2%2B-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)]()

Production-grade **Policy-Based Access Control (PBAC)** for Django.

---

## What is django-pbac?

`django-pbac` is a fully-featured, Django-native authorization library implementing the
**Policy-Based Access Control (PBAC)** model — the same security model used by AWS IAM,
Azure RBAC, Google Cloud IAM, and enterprise security systems.

Unlike simple role-based access control (RBAC), PBAC evaluates **rich, contextual policies**:

```yaml
- name: "Senior Finance Staff can approve invoices during business hours"
  effect: PERMIT
  subjects:
    roles: [finance_manager, finance_director]
    attribute_conditions:
      clearance_level: {gte: 3}
  actions: ["invoices:approve"]
  resources:
    types: [invoice]
    attribute_conditions:
      status: {in: [pending, review]}
      tenant_id: {ref: "subject.attributes.tenant_id"}
  conditions:
    - operator: time_between
      attribute: context.timestamp
      value: {start: "08:00", end: "18:00"}
```

## Key Features

- **Three policy sources**: Database (Django admin editable), Python code, YAML files
- **Queryset filtering**: Automatically filter Django querysets to only permitted resources
- **DRF integration**: Drop-in `PBACPermission` and `PBACObjectPermission` classes
- **Middleware**: Request-level enforcement with audit logging
- **Decorators**: `@require_policy` / `@deny_policy` view decorators
- **Template tags**: `{% can %}` / `{% cannot %}` for UI rendering
- **Audit logging**: Full decision trace to DB or structured JSON logs
- **Context injectors**: Plug in JWT claims, tenant info, request metadata
- **Multi-tenancy**: First-class support via cross-reference conditions
- **Hierarchical resources**: Ancestor-based policy matching
- **Conflict resolution**: DENY_OVERRIDE (default), PERMIT_OVERRIDE, FIRST_APPLICABLE

## Quick Start

```bash
pip install django-pbac
# With DRF support:
pip install django-pbac[drf]
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_pbac",
]

PBAC = {
    "CONFLICT_RESOLUTION": "deny_override",
    "POLICY_LOADERS": [
        "django_pbac.loaders.db.DatabasePolicyLoader",
        "django_pbac.loaders.yaml_loader.YAMLPolicyLoader",
    ],
    "YAML_POLICY_DIRS": [BASE_DIR / "policies"],
    "AUDIT_LOGGERS": [
        "django_pbac.audit.db.DatabaseAuditLogger",
    ],
    "CONTEXT_INJECTORS": [
        "django_pbac.injectors.user.UserAttributeInjector",
        "django_pbac.injectors.request_meta.RequestMetadataInjector",
    ],
}
```

```python
# views.py
from django_pbac.integration.decorators import require_policy

@require_policy("documents:read", resource_type="document")
def document_detail(request, pk):
    ...
```

## Documentation

Full documentation: [https://django-pbac.readthedocs.io](https://django-pbac.readthedocs.io)

- [Quickstart](docs/quickstart.md)
- [Core Concepts](docs/concepts.md)
- [Writing Policies](docs/policies.md)
- [Django Integration](docs/django-integration.md)
- [Queryset Filtering](docs/queryset-filtering.md)
- [Audit Logging](docs/audit-logging.md)
- [Configuration Reference](docs/configuration.md)

## Architecture

```
Request → ContextInjectors → PolicyLoader → PolicyEvaluator → PolicyDecision
                                  ↑                ↑
                           PolicyCache         OperatorRegistry
                                                    ↓
                                              AuditLogger
```

The evaluation engine (`core/`) is pure Python with zero Django dependencies,
making it independently testable and potentially reusable outside Django.

## Security

This library is designed for security-critical use. Please report vulnerabilities
to security@django-pbac.dev. Do not open public issues for security bugs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
