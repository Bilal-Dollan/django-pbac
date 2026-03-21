"""
JWTClaimsInjector — inject JWT claims into Subject and Context.

Reads the Authorization header, decodes the JWT (using PyJWT),
and merges all claims into subject.attributes and context.extra.

Configuration (in PBAC settings):
  JWT_HEADER: "HTTP_AUTHORIZATION"
  JWT_PREFIX: "Bearer"
  JWT_SECRET: "your-secret" (None = no signature verification, dev only)
  JWT_ALGORITHMS: ["HS256"]
"""
from __future__ import annotations

import logging
from typing import Any

from django_pbac.core.models import Context, Subject

logger = logging.getLogger(__name__)


class JWTClaimsInjector:
    """
    Decodes a JWT from the Authorization header and injects its claims.

    Claims are merged into ``subject.attributes`` and ``context.extra``.
    Standard JWT claims (sub, iss, exp, iat, aud) are stored in ``context.extra``
    under the ``jwt_`` prefix. Custom claims are stored in ``subject.attributes``.

    .. warning::
        Set ``JWT_SECRET`` in production. ``JWT_SECRET=None`` disables
        signature verification and should only be used in development.
    """

    def inject_subject(self, subject: Subject, request: Any) -> Subject:
        claims = self._get_claims(request)
        if not claims:
            return subject

        subject_id = claims.get("sub") or subject.id
        attrs = {**subject.attributes}

        # Standard claim extraction
        roles = claims.get("roles") or claims.get("groups") or []
        if roles:
            attrs["roles"] = roles if isinstance(roles, list) else [roles]

        tenant_id = claims.get("tenant_id") or claims.get("tid")
        if tenant_id:
            attrs["tenant_id"] = tenant_id

        department = claims.get("department") or claims.get("dept")
        if department:
            attrs["department"] = department

        clearance = claims.get("clearance_level")
        if clearance is not None:
            attrs["clearance_level"] = clearance

        # Merge all remaining custom claims
        for k, v in claims.items():
            if k not in ("sub", "iss", "exp", "iat", "aud", "nbf", "jti"):
                attrs.setdefault(k, v)

        return Subject(
            id=str(subject_id),
            type=subject.type,
            attributes=attrs,
        )

    def inject_context(self, context: Context, request: Any) -> Context:
        claims = self._get_claims(request)
        if not claims:
            return context

        extra = {**context.extra}
        for k in ("iss", "aud", "exp", "iat", "jti"):
            if k in claims:
                extra[f"jwt_{k}"] = claims[k]

        return context.with_extra("jwt_claims", claims).__class__(
            timestamp=context.timestamp,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            request_id=context.request_id,
            extra={**context.extra, **extra},
        )

    def _get_claims(self, request: Any) -> dict[str, Any] | None:
        try:
            import jwt  # PyJWT

            from django_pbac.conf import pbac_settings

            header_name = pbac_settings.JWT_HEADER
            prefix = pbac_settings.JWT_PREFIX
            secret = pbac_settings.JWT_SECRET
            algorithms = pbac_settings.JWT_ALGORITHMS

            header_val = getattr(request, "META", {}).get(header_name, "")
            if not header_val or not header_val.startswith(f"{prefix} "):
                return None

            token = header_val[len(prefix) + 1:]

            if secret is None:
                # No-verification decode (dev only)
                return jwt.decode(
                    token,
                    options={"verify_signature": False},
                    algorithms=algorithms,
                )
            return jwt.decode(token, secret, algorithms=algorithms)

        except ImportError:
            logger.debug(
                "PyJWT not installed. JWTClaimsInjector requires: pip install PyJWT"
            )
            return None
        except Exception as exc:
            logger.debug("JWT decode failed: %s", exc)
            return None
