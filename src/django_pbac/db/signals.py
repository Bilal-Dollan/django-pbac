"""Signals for PBAC DB models."""
from __future__ import annotations

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from django_pbac.db.models import ConditionModel, PolicyModel
from django_pbac.engine import pbac_engine

logger = logging.getLogger(__name__)


def _invalidate_policy_cache() -> None:
    """Invalidate all policy cache entries after policy persistence changes."""
    try:
        pbac_engine.invalidate_cache()
    except Exception as exc:
        logger.warning("Failed to invalidate PBAC cache after policy change: %s", exc)


@receiver(post_save, sender=PolicyModel)
def on_policy_saved(sender: type[PolicyModel], **kwargs: object) -> None:
    _invalidate_policy_cache()


@receiver(post_delete, sender=PolicyModel)
def on_policy_deleted(sender: type[PolicyModel], **kwargs: object) -> None:
    _invalidate_policy_cache()


@receiver(post_save, sender=ConditionModel)
def on_condition_saved(sender: type[ConditionModel], **kwargs: object) -> None:
    _invalidate_policy_cache()


@receiver(post_delete, sender=ConditionModel)
def on_condition_deleted(sender: type[ConditionModel], **kwargs: object) -> None:
    _invalidate_policy_cache()
