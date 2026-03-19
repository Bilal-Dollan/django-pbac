# Settings Rules

Rules governing the `PBAC` settings dictionary.

---

## Complete Settings Reference

```python
PBAC = {
    # Conflict resolution strategy when PERMIT and DENY both match
    # Options: "DENY_OVERRIDE" | "PERMIT_OVERRIDE" | "FIRST_APPLICABLE"
    "CONFLICT_RESOLUTION": "DENY_OVERRIDE",

    # Cache backend (dotted import path)
    "CACHE_BACKEND": "django_pbac.cache.django_cache.DjangoCacheBackend",

    # Cache TTL in seconds
    "CACHE_TTL": 300,

    # List of AuditLogger dotted import paths
    # Empty list = no audit logging
    "AUDIT_LOGGERS": [
        "django_pbac.audit.structured_log.StructuredLogAuditLogger",
    ],

    # List of PolicyLoader configurations
    # Each entry is {"BACKEND": "...", "OPTIONS": {...}}
    "POLICY_LOADERS": [
        {
            "BACKEND": "django_pbac.loaders.db.DatabasePolicyLoader",
        },
        {
            "BACKEND": "django_pbac.loaders.yaml_loader.YAMLPolicyLoader",
            "OPTIONS": {"directories": ["/path/to/policies/"]},
        },
    ],

    # List of ContextInjector dotted import paths
    # Applied in order when building Subject/Context from a HttpRequest
    "CONTEXT_INJECTORS": [
        "django_pbac.injectors.user.UserAttributeInjector",
        "django_pbac.injectors.request_meta.RequestMetadataInjector",
    ],

    # Include evaluation trace in PolicyDecision.trace
    # Disable in production for performance
    "ENABLE_EVALUATION_TRACE": False,

    # If True, no matching policies → DENY (secure default)
    "DEFAULT_DENY": True,
}
```

---

## RULE-SETTINGS-001: DENY_OVERRIDE is the default — do not change without review

Changing to `PERMIT_OVERRIDE` dramatically lowers security.
Requires explicit security review and documentation.

---

## RULE-SETTINGS-002: NullCache in tests, DjangoCacheBackend in production

```python
# tests/settings.py
PBAC = {
    "CACHE_BACKEND": "django_pbac.cache.null.NullCache",
}
```

Using `NullCache` in tests prevents cache pollution between test runs.

---

## RULE-SETTINGS-003: ENABLE_EVALUATION_TRACE should be False in production

The trace generates `EvaluationStep` objects for every evaluated policy.
In high-throughput environments, disable it to reduce memory allocation.

---

## RULE-SETTINGS-004: ContextInjectors are applied in declaration order

Injectors are applied in the order listed in `CONTEXT_INJECTORS`.
The Subject/Context returned by each injector is passed to the next.
Later injectors can override earlier ones' values.
