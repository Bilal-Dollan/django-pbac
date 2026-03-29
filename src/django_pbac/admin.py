"""
Expose django-pbac admin registrations for Django's autodiscovery.

Django's admin autodiscovery looks for ``admin.py`` at the root of each
installed app.  The actual registrations live in ``db/admin.py``; this
module re-exports them so they are picked up automatically when
``django.contrib.admin`` is in INSTALLED_APPS.
"""
from django_pbac.db.admin import (  # noqa: F401
    AuditLogAdmin,
    ConditionInline,
    PolicyAdmin,
    PolicyVersionAdmin,
)
