# django-pbac

> **⚠️ Work in Progress — Early Development**
>
> This project is currently under active development and is **not yet production-ready**.
> It may contain bugs, incomplete features, breaking API changes, and missing documentation.
> Use at your own risk. Feedback, bug reports, and contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

[![CI](https://github.com/Bilal-Dollan/django-pbac/actions/workflows/ci.yml/badge.svg)](https://github.com/Bilal-Dollan/django-pbac/actions/workflows/ci.yml)
[![Django](https://img.shields.io/badge/Django-4.2%2B-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Policy-Based Access Control (PBAC) for Django.

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
    "CONFLICT_RESOLUTION": "DENY_OVERRIDE",
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

Documentation is a work in progress. See [docs/index.md](docs/index.md) for the current overview,
and the [`example/`](example/) directory for a working Django project demonstrating the library.

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
by opening a [GitHub Security Advisory](https://github.com/Bilal-Dollan/django-pbac/security/advisories/new).
Do not open public issues for security bugs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
