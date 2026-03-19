# django-pbac

**Django-first Policy-Based Access Control (PBAC) library.**

django-pbac provides a production-grade PBAC engine that integrates closely with Django's
authentication system while remaining flexible enough to handle complex, attribute-based
authorization rules.

## Key Features

- **Policy-Based Access Control** — define allow/deny rules as data, not code
- **Multiple policy sources** — load policies from DB, YAML files, or Python code
- **Attribute-based conditions** — evaluate any attribute on subject, resource, or context
- **22 built-in operators** — string, numeric, collection, boolean, IP, date/time operators
- **Flexible conflict resolution** — DENY_OVERRIDE, PERMIT_OVERRIDE, or FIRST_APPLICABLE
- **Django integration** — middleware, decorators, CBV mixins, template tags
- **DRF integration** — `PBACPermission` and `PBACObjectPermission`
- **Queryset filtering** — auto-filter querysets to only permitted resources
- **Pluggable caching & audit logging**
- **Pure-Python core** — the evaluation engine has zero Django dependencies

## Quick Example

```python
# views.py
from django_pbac.integration.decorators import require_policy

@require_policy(action="documents:read", resource_type="document")
def document_detail(request, pk):
    doc = Document.objects.get(pk=pk)
    return render(request, "docs/detail.html", {"doc": doc})
```

```yaml
# policies/documents.yaml
policies:
  - id: viewer-read-docs
    effect: PERMIT
    actions:
      - "documents:read"
    subject_matchers:
      - roles:
          - viewer
    resource_matchers:
      - type: document
```

## Installation

```bash
pip install django-pbac
```

See the [Installation Guide](getting-started/installation.md) for full setup instructions.

## License

MIT License. See [LICENSE](https://github.com/yourusername/django-pbac/blob/main/LICENSE).
