"""CompositeAuditLogger — fans out to multiple audit loggers."""
from __future__ import annotations

import logging
from typing import Any

from django_pbac.core.models import PolicyDecision


logger = logging.getLogger(__name__)


class CompositeAuditLogger:
    """
    Fans out each PolicyDecision to multiple AuditLogger implementations.

    If any individual logger raises, it is caught silently and the next
    logger is called. All loggers are always invoked.
    """

    def __init__(self, loggers: list[Any]) -> None:
        self._loggers = loggers

    def log(self, decision: PolicyDecision) -> None:
        for audit_logger in self._loggers:
            try:
                audit_logger.log(decision)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "CompositeAuditLogger: error in %s: %s",
                    type(audit_logger).__name__,
                    exc,
                )

    @classmethod
    def from_settings(cls) -> "CompositeAuditLogger":
        """Build a CompositeAuditLogger from Django settings."""
        from django.utils.module_loading import import_string
        from django_pbac.conf import pbac_settings

        loggers_config = pbac_settings.AUDIT_LOGGERS
        if isinstance(loggers_config, str):
            loggers_config = [loggers_config]

        audit_loggers = []
        for dotted_path in loggers_config:
            try:
                klass = import_string(dotted_path)
                audit_loggers.append(klass())
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to load audit logger %r: %s", dotted_path, exc)

        return cls(audit_loggers)
