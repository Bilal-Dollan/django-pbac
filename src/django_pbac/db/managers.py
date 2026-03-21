"""
Custom QuerySet and Manager for PolicyModel.

Provides chainable, expressive filters for building efficient policy queries.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db import models


class PolicyQuerySet(models.QuerySet[Any]):
    """Chainable QuerySet for PolicyModel."""

    def active(self) -> PolicyQuerySet:
        """Filter to active policies only."""
        return self.filter(is_active=True)

    def valid_at(self, dt: datetime) -> PolicyQuerySet:
        """Filter to policies that are valid at the given datetime."""
        return self.filter(
            models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=dt)
        ).filter(
            models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=dt)
        )

    def for_action(self, action: str) -> PolicyQuerySet:
        """
        Filter to policies that could match the given action.

        Returns policies containing the exact action, its namespace wildcard,
        or the global wildcard "*".
        """
        namespace = action.split(":")[0]
        return self.filter(
            models.Q(actions__contains=[action])
            | models.Q(actions__contains=[f"{namespace}:*"])
            | models.Q(actions__contains=["*"])
        )

    def for_resource_type(self, resource_type: str) -> PolicyQuerySet:
        """Filter to policies that include the given resource type."""
        return self.filter(resource_types__contains=[resource_type])

    def for_effect(self, effect: str) -> PolicyQuerySet:
        """Filter by PERMIT or DENY effect."""
        return self.filter(effect=effect.upper())

    def with_tag(self, tag: str) -> PolicyQuerySet:
        """Filter to policies that have the given tag."""
        return self.filter(tags__contains=[tag])


class PolicyManager(models.Manager[Any]):
    """Manager for PolicyModel using PolicyQuerySet."""

    def get_queryset(self) -> PolicyQuerySet:
        return PolicyQuerySet(self.model, using=self._db)

    def active(self) -> PolicyQuerySet:
        return self.get_queryset().active()

    def valid_at(self, dt: datetime) -> PolicyQuerySet:
        return self.get_queryset().valid_at(dt)

    def for_action(self, action: str) -> PolicyQuerySet:
        return self.get_queryset().for_action(action)

    def for_resource_type(self, resource_type: str) -> PolicyQuerySet:
        return self.get_queryset().for_resource_type(resource_type)
