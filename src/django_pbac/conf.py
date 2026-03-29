"""
django-pbac settings with defaults.

All settings are accessed via ``from django_pbac.conf import pbac_settings``.
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.test.signals import setting_changed

DEFAULTS: dict[str, Any] = {
    # Conflict resolution strategy: deny_override | permit_override | first_applicable
    "CONFLICT_RESOLUTION": "deny_override",
    # Ordered list of policy loader dotted paths
    "POLICY_LOADERS": [
        "django_pbac.loaders.db.DatabasePolicyLoader",
    ],
    # Directories to scan for YAML policy files (list of Path/str)
    "YAML_POLICY_DIRS": [],
    # Cache backend dotted path
    "CACHE_BACKEND": "django_pbac.cache.django_cache.DjangoCacheBackend",
    # Django cache alias to use for policy caching
    "CACHE_ALIAS": "default",
    # Cache TTL in seconds (0 = disabled)
    "CACHE_TTL": 300,
    # Audit logger dotted path(s) — single string or list
    "AUDIT_LOGGERS": [
        "django_pbac.audit.structured_log.StructuredLogAuditLogger",
    ],
    # Context injector dotted path(s)
    "CONTEXT_INJECTORS": [
        "django_pbac.injectors.user.UserAttributeInjector",
        "django_pbac.injectors.request_meta.RequestMetadataInjector",
    ],
    # If True, attach full evaluation trace to every PolicyDecision
    "ENABLE_EVALUATION_TRACE": True,
    # Default action namespace separator
    "ACTION_SEPARATOR": ":",
    # Response class to raise on permission denied
    "PERMISSION_DENIED_EXCEPTION": "django.core.exceptions.PermissionDenied",
    # Whether to log ALL decisions (not just denials)
    "AUDIT_ALL_DECISIONS": False,
    # Whether to audit permit decisions explicitly
    "AUDIT_PERMIT_DECISIONS": True,
    # Request header to read request ID from
    "REQUEST_ID_HEADER": "X-Request-ID",
    # JWT header / claim settings (used by JWTClaimsInjector)
    "JWT_HEADER": "HTTP_AUTHORIZATION",
    "JWT_PREFIX": "Bearer",
    "JWT_SECRET": None,  # If None, decodes without verification (dev only)
    "JWT_ALGORITHMS": ["HS256"],
}


class PBACSettings:
    """
    Wrapper for PBAC settings that provides attribute access and
    re-loads on ``setting_changed`` signal (for test overrides).
    """

    def __init__(self, defaults: dict[str, Any]) -> None:
        self._defaults = defaults
        self._cached: dict[str, Any] = {}

    def __getattr__(self, name: str) -> Any:
        if name not in self._defaults:
            raise AttributeError(f"Invalid PBAC setting: {name!r}")
        if name not in self._cached:
            user_settings: dict[str, Any] = getattr(settings, "PBAC", {})
            self._cached[name] = user_settings.get(name, self._defaults[name])
        return self._cached[name]

    def reload(self) -> None:
        self._cached.clear()


pbac_settings = PBACSettings(DEFAULTS)


def _reload_pbac_settings(*, setting: str, **kwargs: Any) -> None:
    if setting == "PBAC":
        pbac_settings.reload()


setting_changed.connect(_reload_pbac_settings)


def get_production_pbac_settings() -> dict[str, Any]:
    """
    Return a production-ready PBAC settings dict.

    Merge this into your project's ``PBAC`` setting::

        from django_pbac.conf import get_production_pbac_settings
        PBAC = get_production_pbac_settings()
        PBAC["YAML_POLICY_DIRS"] = [BASE_DIR / "policies"]

    Key differences from development defaults:
    - Evaluation trace disabled (lower overhead per request).
    - Only deny decisions are audited by default (reduce write load).
    - DB audit logger used instead of structured log.
    """
    return {
        "CONFLICT_RESOLUTION": "deny_override",
        "POLICY_LOADERS": [
            "django_pbac.loaders.db.DatabasePolicyLoader",
        ],
        "YAML_POLICY_DIRS": [],
        "CACHE_BACKEND": "django_pbac.cache.django_cache.DjangoCacheBackend",
        "CACHE_ALIAS": "default",
        "CACHE_TTL": 300,
        "AUDIT_LOGGERS": [
            "django_pbac.audit.db.DatabaseAuditLogger",
        ],
        "CONTEXT_INJECTORS": [
            "django_pbac.injectors.user.UserAttributeInjector",
            "django_pbac.injectors.request_meta.RequestMetadataInjector",
        ],
        # Disable per-request evaluation trace in production (saves memory/CPU).
        "ENABLE_EVALUATION_TRACE": False,
        "AUDIT_ALL_DECISIONS": False,
        "AUDIT_PERMIT_DECISIONS": False,
        "REQUEST_ID_HEADER": "X-Request-ID",
    }


RECOMMENDED_LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} - {message}",
            "style": "{",
        },
    },
    "loggers": {
        # Silence Django's default PermissionDenied (403) traceback noise.
        # 403s are expected access-control results, not server errors.
        # Only 5xx errors (ERROR level) will print a traceback.
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        # Surface PBAC warnings (e.g. missing table, loader errors).
        "django_pbac": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
