"""
DatabaseAuditLogger — writes PolicyDecision to the AuditLogModel.
"""
from __future__ import annotations

import logging

from django.db.utils import OperationalError, ProgrammingError

from django_pbac.core.models import PolicyDecision

logger = logging.getLogger(__name__)


class DatabaseAuditLogger:
    """
    Writes every PolicyDecision to the ``AuditLogModel`` Django ORM model.

    Respects ``PBAC["AUDIT_ALL_DECISIONS"]`` — if False (default),
    only DENY decisions and (optionally) PERMIT decisions are logged based
    on ``PBAC["AUDIT_PERMIT_DECISIONS"]``.
    """

    def __init__(self) -> None:
        self._db_logging_disabled = False

    def log(self, decision: PolicyDecision) -> None:
        if self._db_logging_disabled:
            return

        try:
            from django_pbac.conf import pbac_settings
            from django_pbac.core.types import Effect
            from django_pbac.db.models import AuditLogModel

            should_log = pbac_settings.AUDIT_ALL_DECISIONS or (
                decision.effect == Effect.DENY
                or pbac_settings.AUDIT_PERMIT_DECISIONS
            )

            if not should_log:
                return

            AuditLogModel.objects.create(
                effect=decision.effect.value,
                reason=decision.reason[:500],
                subject_id=decision.request.subject.id,
                subject_type=decision.request.subject.type.value,
                action=decision.request.action,
                resource_type=decision.request.resource.type,
                resource_id=decision.request.resource.id or "",
                request_id=decision.request.context.request_id,
                ip_address=decision.request.context.ip_address or "",
                evaluation_time_ms=decision.evaluation_time_ms,
                evaluated_policy_count=decision.evaluated_policy_count,
                matched_policies=list(decision.matched_policies),
                denied_by=decision.denied_by or "",
                permitted_by=decision.permitted_by or "",
            )
        except (OperationalError, ProgrammingError) as exc:
            if self._is_missing_table_error(exc):
                self._db_logging_disabled = True
                logger.warning(
                    "DatabaseAuditLogger disabled: audit table is missing. "
                    "Run django-pbac migrations to enable DB audit logs. Original error: %s",
                    exc,
                )
                return
            logger.error("DatabaseAuditLogger failed: %s", exc)
        except Exception as exc:
            logger.error("DatabaseAuditLogger failed: %s", exc)

    @staticmethod
    def _is_missing_table_error(exc: Exception) -> bool:
        """Return True when exception indicates an undefined/missing table."""
        message = str(exc).lower()
        return any(
            token in message
            for token in (
                "no such table",
                "relation",
                "does not exist",
                "undefined table",
            )
        )
