"""
StructuredLogAuditLogger — emits PolicyDecisions as structured JSON log records.

Uses Python's standard ``logging`` module. Log records include all decision
fields as ``extra`` attributes, making them compatible with JSON log formatters
(e.g., python-json-logger, structlog).

Logger name: ``django_pbac.audit``
Log level:   INFO for PERMIT, WARNING for DENY
"""
from __future__ import annotations

import logging

from django_pbac.core.models import PolicyDecision
from django_pbac.core.types import Effect


audit_logger = logging.getLogger("django_pbac.audit")


class StructuredLogAuditLogger:
    """
    Emits audit records to Python's standard logging infrastructure.

    Each log record carries the full decision context as ``extra`` fields.
    Compatible with JSON log formatters for SIEM/log aggregation.

    Example log record (JSON)::

        {
          "level": "WARNING",
          "logger": "django_pbac.audit",
          "message": "PBAC DENY: subject=42 action=documents:delete resource=document/doc-1",
          "pbac_effect": "DENY",
          "pbac_subject_id": "42",
          "pbac_action": "documents:delete",
          "pbac_resource_type": "document",
          "pbac_resource_id": "doc-1",
          "pbac_denied_by": "Global Document Delete Deny",
          "pbac_request_id": "abc-123",
          "pbac_eval_time_ms": 1.23
        }
    """

    def log(self, decision: PolicyDecision) -> None:
        req = decision.request
        extra = {
            "pbac_effect": decision.effect.value,
            "pbac_reason": decision.reason,
            "pbac_subject_id": req.subject.id,
            "pbac_subject_type": req.subject.type.value,
            "pbac_action": req.action,
            "pbac_resource_type": req.resource.type,
            "pbac_resource_id": req.resource.id or "",
            "pbac_request_id": req.context.request_id,
            "pbac_ip_address": req.context.ip_address or "",
            "pbac_denied_by": decision.denied_by or "",
            "pbac_permitted_by": decision.permitted_by or "",
            "pbac_matched_policies": list(decision.matched_policies),
            "pbac_eval_time_ms": round(decision.evaluation_time_ms, 3),
            "pbac_policy_count": decision.evaluated_policy_count,
        }

        msg = (
            f"PBAC {decision.effect.value}: "
            f"subject={req.subject.id} "
            f"action={req.action} "
            f"resource={req.resource.type}/{req.resource.id or '*'}"
        )

        if decision.effect == Effect.DENY:
            audit_logger.warning(msg, extra=extra)
        else:
            audit_logger.info(msg, extra=extra)
