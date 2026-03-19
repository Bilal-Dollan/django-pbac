"""
ContextInjector Protocol.

Injectors enrich the Subject and Context with additional attributes
before policy evaluation.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from django_pbac.core.models import Context, Subject


@runtime_checkable
class ContextInjector(Protocol):
    """
    Protocol for enriching Subject and Context before policy evaluation.

    Injectors are called in the order they are configured in ``PBAC["CONTEXT_INJECTORS"]``.
    Each injector receives the current Subject/Context and returns an enriched copy.
    Because Subject and Context are frozen dataclasses, use ``.with_attribute()``
    / ``.with_extra()`` to produce modified copies.
    """

    def inject_subject(
        self,
        subject: Subject,
        request: object,  # Django HttpRequest
    ) -> Subject:
        """Enrich the subject with additional attributes. Return updated Subject."""
        ...

    def inject_context(
        self,
        context: Context,
        request: object,  # Django HttpRequest
    ) -> Context:
        """Enrich the context with additional data. Return updated Context."""
        ...
