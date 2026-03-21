"""
DatabasePolicyLoader — loads policies from the Django ORM.

Converts PolicyModel ORM objects to core Policy dataclasses.
Uses select_related / prefetch_related to avoid N+1 queries.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from django_pbac.core.models import (
    Condition,
    Policy,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.types import (
    ConflictResolution,
    Effect,
    PolicySourceType,
    SubjectType,
)

logger = logging.getLogger(__name__)


class DatabasePolicyLoader:
    """
    Loads policies from the Django database via ``PolicyModel``.

    Query strategy:
    - Filters for active, temporally valid policies.
    - Filters by resource type using a JSON contains query.
    - Uses select_related + prefetch_related to avoid N+1 queries.
    - Deserializes ORM models to immutable core Policy dataclasses.
    """

    def load_for_request(
        self,
        subject: Subject,
        action: str,
        resource_type: str,
    ) -> list[Policy]:
        """Load policies applicable to this (subject, action, resource_type) triple."""
        from django_pbac.db.models import PolicyModel

        now = datetime.now(UTC)
        qs = (
            PolicyModel.objects.active()
            .valid_at(now)
            .for_resource_type(resource_type)
            .prefetch_related("conditions")
            .select_related()
        )
        return [self._to_policy(m) for m in qs]

    def load_all(self) -> list[Policy]:
        """Load all active policies."""
        from django_pbac.db.models import PolicyModel

        qs = PolicyModel.objects.active().prefetch_related("conditions").select_related()
        return [self._to_policy(m) for m in qs]

    def get_by_id(self, policy_id: str) -> Policy | None:
        """Return Policy by ID, or None."""
        from django_pbac.db.models import PolicyModel

        try:
            m = PolicyModel.objects.prefetch_related("conditions").get(id=policy_id)
            return self._to_policy(m)
        except PolicyModel.DoesNotExist:
            return None

    def save(self, policy: Policy) -> Policy:
        """Persist a Policy dataclass to the database."""
        from django_pbac.db.models import ConditionModel, PolicyModel

        defaults = {
            "name": policy.name,
            "description": policy.description,
            "effect": policy.effect.value,
            "priority": policy.priority,
            "conflict_resolution": policy.conflict_resolution.value,
            "is_active": policy.is_active,
            "valid_from": policy.valid_from,
            "valid_until": policy.valid_until,
            "version": policy.version,
            "created_by": policy.created_by,
            "tags": list(policy.tags),
            # Actions stored as JSON list
            "actions": list(policy.actions),
            # Subject matcher fields (first matcher only — DB model is single-matcher)
            **self._subject_matcher_to_db(policy),
            # Resource matcher fields (first matcher only — DB model is single-matcher)
            **self._resource_matcher_to_db(policy),
        }

        obj, _ = PolicyModel.objects.update_or_create(id=policy.id, defaults=defaults)

        # Sync conditions
        obj.conditions.all().delete()
        for cond in policy.conditions:
            ConditionModel.objects.create(  # type: ignore[attr-defined]
                policy=obj,
                operator=cond.operator,
                attribute=cond.attribute,
                value=cond.value,
                negate=cond.negate,
            )

        return self._to_policy(obj)

    def _subject_matcher_to_db(self, policy: Policy) -> dict[str, object]:
        sm = policy.subject_matchers[0] if policy.subject_matchers else SubjectMatcher()
        return {
            "subject_user_ids": [sm.id] if sm.id else [],
            "subject_types": [t.value for t in (sm.subject_types or [])],
            "subject_roles": list(sm.roles),
            "subject_groups": list(sm.groups or []),
            "subject_attribute_conditions": sm.attributes or {},
        }

    def _resource_matcher_to_db(self, policy: Policy) -> dict[str, object]:
        rm = policy.resource_matchers[0] if policy.resource_matchers else ResourceMatcher()
        return {
            "resource_types": [rm.types] if rm.types else [],
            "resource_ids": [rm.id] if rm.id else [],
            "resource_attribute_conditions": rm.attributes or {},
            "resource_ancestor_conditions": rm.ancestor_conditions or [],
        }

    def delete(self, policy_id: str) -> None:
        from django_pbac.db.models import PolicyModel

        PolicyModel.objects.filter(id=policy_id).delete()

    def _to_policy(self, m: object) -> Policy:
        """Convert a PolicyModel instance to a Policy dataclass."""
        # All attribute accesses use object protocol — m is a PolicyModel at runtime
        def attr(name: str) -> Any:
            return getattr(m, name)

        # Subject matcher
        subject_matcher = SubjectMatcher(
            id=attr("subject_user_ids")[0] if attr("subject_user_ids") else None,
            subject_types=(
                frozenset(SubjectType(t) for t in attr("subject_types"))
                if attr("subject_types")
                else None
            ),
            roles=frozenset(attr("subject_roles")) if attr("subject_roles") else frozenset(),
            groups=frozenset(attr("subject_groups")) if attr("subject_groups") else None,
            attributes=attr("subject_attribute_conditions") or None,
        )

        # Resource matcher
        resource_matcher = ResourceMatcher(
            types=attr("resource_types")[0] if attr("resource_types") else None,
            id=attr("resource_ids")[0] if attr("resource_ids") else None,
            attributes=attr("resource_attribute_conditions") or None,
            ancestor_conditions=attr("resource_ancestor_conditions") or None,
        )

        # Conditions
        conditions = tuple(
            Condition(
                operator=c.operator,
                attribute=c.attribute,
                value=c.value,
                negate=c.negate,
            )
            for c in attr("conditions").all()
        )

        return Policy(
            id=str(attr("id")),
            name=attr("name"),
            description=attr("description") or "",
            effect=Effect(attr("effect")),
            subject_matchers=(subject_matcher,),
            actions=frozenset(attr("actions")),
            resource_matchers=(resource_matcher,),
            conditions=conditions,
            priority=attr("priority"),
            conflict_resolution=ConflictResolution(attr("conflict_resolution")),
            is_active=attr("is_active"),
            valid_from=attr("valid_from"),
            valid_until=attr("valid_until"),
            version=attr("version"),
            created_by=attr("created_by") or "system",
            tags=frozenset(attr("tags") or []),
            source=PolicySourceType.DATABASE,
        )
