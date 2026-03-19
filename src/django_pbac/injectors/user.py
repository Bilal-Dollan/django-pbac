"""
UserAttributeInjector — enriches Subject from Django's request.user.

Injects:
  - roles: list of user group names
  - groups: same as roles (for RBAC compatibility)
  - is_staff: bool
  - is_superuser: bool
  - email: str
  - department: from user profile if available
  - tenant_id: from user profile if available
"""
from __future__ import annotations

import logging
from typing import Any

from django_pbac.core.models import Context, Subject
from django_pbac.core.types import SubjectType


logger = logging.getLogger(__name__)


class UserAttributeInjector:
    """
    Injects Django user attributes into the Subject.

    Reads from ``request.user``. Gracefully handles anonymous users
    (returns Subject.anonymous()).

    Profile attributes (department, tenant_id, etc.) are read via
    ``user.pbac_profile`` if available, or from ``user.profile`` as
    a fallback. This allows projects to attach arbitrary attributes
    to users without modifying the User model.
    """

    def inject_subject(self, subject: Subject, request: Any) -> Subject:
        """Inject user attributes into the subject."""
        user = getattr(request, "user", None)

        if user is None or not getattr(user, "is_authenticated", False):
            return Subject.anonymous()

        # Base attributes
        groups = list(user.groups.values_list("name", flat=True))
        attrs: dict[str, Any] = {
            "roles": groups,  # use group names as roles
            "groups": groups,
            "is_staff": getattr(user, "is_staff", False),
            "is_superuser": getattr(user, "is_superuser", False),
            "email": getattr(user, "email", ""),
            "username": getattr(user, "username", ""),
        }

        # Profile attributes (optional)
        profile = getattr(user, "pbac_profile", None) or getattr(user, "profile", None)
        if profile is not None:
            for attr_name in [
                "department", "tenant_id", "clearance_level",
                "cost_center", "manager_id",
            ]:
                val = getattr(profile, attr_name, None)
                if val is not None:
                    attrs[attr_name] = val

        return Subject(
            id=str(user.pk),
            type=SubjectType.USER,
            attributes=attrs,
        )

    def inject_context(self, context: Context, request: Any) -> Context:
        """No context enrichment from user injector."""
        return context
