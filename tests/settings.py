"""
Minimal Django settings for the django-pbac test suite.
"""
from __future__ import annotations

SECRET_KEY = "django-pbac-test-secret-key-not-for-production"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_pbac",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

PBAC = {
    "CONFLICT_RESOLUTION": "DENY_OVERRIDE",
    "CACHE_BACKEND": "django_pbac.cache.null.NullCache",
    "CACHE_TTL": 300,
    "AUDIT_LOGGERS": [],
    "POLICY_LOADERS": [],
    "CONTEXT_INJECTORS": [],
    "ENABLE_EVALUATION_TRACE": True,
    "DEFAULT_DENY": True,
}

USE_TZ = True
TIME_ZONE = "UTC"
