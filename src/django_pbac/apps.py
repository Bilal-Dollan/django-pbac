"""AppConfig for django_pbac."""
from __future__ import annotations

from django.apps import AppConfig


class DjangoPbacConfig(AppConfig):
    """Django application configuration for django-pbac."""

    name = "django_pbac"
    verbose_name = "Django PBAC"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Perform initialization when Django starts."""
        # Import to ensure signal handlers and registry entries are loaded.
        from django_pbac import conf  # noqa: F401
        from django_pbac.db import signals  # noqa: F401
        from django_pbac.engine import pbac_engine  # noqa: F401

        # Trigger registration of any code-defined policies via autodiscovery.
        self._autodiscover_policies()

    def _autodiscover_policies(self) -> None:
        """Auto-discover code-defined policy modules in installed apps."""
        from django.utils.module_loading import autodiscover_modules

        autodiscover_modules("pbac_policies")
