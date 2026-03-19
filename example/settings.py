"""
Example: django-pbac document management demo settings.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "example-demo-secret-key-change-in-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_pbac",
    "example.docs_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_pbac.integration.middleware.PBACMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "example.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "example.db",
    }
}

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

PBAC = {
    "CONFLICT_RESOLUTION": "DENY_OVERRIDE",
    "CACHE_BACKEND": "django_pbac.cache.null.NullCache",
    "CACHE_TTL": 300,
    "AUDIT_LOGGERS": [
        "django_pbac.audit.structured_log.StructuredLogAuditLogger",
    ],
    "POLICY_LOADERS": [
        {
            "BACKEND": "django_pbac.loaders.yaml_loader.YAMLPolicyLoader",
            "OPTIONS": {
                "directories": [str(BASE_DIR / "example" / "policies")],
            },
        },
    ],
    "CONTEXT_INJECTORS": [
        "django_pbac.injectors.user.UserAttributeInjector",
        "django_pbac.injectors.request_meta.RequestMetadataInjector",
    ],
    "ENABLE_EVALUATION_TRACE": True,
    "DEFAULT_DENY": True,
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "example" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
