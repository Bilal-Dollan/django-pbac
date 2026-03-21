"""
RequestMetadataInjector — inject HTTP request metadata into Context.

Injects:
  - ip_address: client IP (respects X-Forwarded-For)
  - user_agent: User-Agent header
  - request_id: from X-Request-ID header or generated
  - timestamp: datetime.now(UTC)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from django_pbac.core.models import Context, Subject


logger = logging.getLogger(__name__)


class RequestMetadataInjector:
    """
    Injects HTTP request metadata into the Context.

    Extracts client IP, User-Agent, and request ID from the Django request.
    """

    def inject_subject(self, subject: Subject, request: Any) -> Subject:
        """No subject enrichment — only context is enriched."""
        return subject

    def inject_context(self, context: Context, request: Any) -> Context:
        """Enrich Context with request metadata."""
        from django_pbac.conf import pbac_settings

        meta = getattr(request, "META", {})

        # IP address — respect proxy headers
        ip = (
            meta.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or meta.get("HTTP_X_REAL_IP", "")
            or meta.get("REMOTE_ADDR", "")
            or None
        )

        user_agent = meta.get("HTTP_USER_AGENT") or None

        # Request ID — from header or generate new
        request_id_header = pbac_settings.REQUEST_ID_HEADER.upper().replace("-", "_")
        if not request_id_header.startswith("HTTP_"):
            request_id_header = f"HTTP_{request_id_header}"
        request_id = (
            meta.get(request_id_header)
            or getattr(request, "request_id", None)
            or str(uuid.uuid4())
        )

        env = dict(context.environment)
        if ip:
            env["ip"] = ip
        if user_agent:
            env["user_agent"] = user_agent

        return context.__class__(
            timestamp=datetime.now(timezone.utc),
            ip_address=ip,
            user_agent=user_agent,
            request_id=request_id,
            environment=env,
        )
