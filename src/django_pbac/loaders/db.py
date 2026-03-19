"""
DatabasePolicyLoader — loads policies from the Django ORM.

Converts PolicyModel ORM objects to core Policy dataclasses.
Uses select_related / prefetch_related to avoid N+1 queries.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

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

        now = datetime.now(timezone.utc)
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
        from django_pbac.db.models import PolicyModel, ConditionModel

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
            # Subject matcher fields
            "subject_user_ids": list(policy.subjects.user_ids or []),
            "subject_types": [t.value for t in (policy.subjects.subject_types or [])],
            "subject_roles": list(policy.subjects.roles or []),
            "subject_groups": list(policy.subjects.groups or []),
            "subject_attribute_conditions": policy.subjects.attribute_conditions or {},
            # Resource matcher fields
            "resource_types": list(policy.resources.types),
            "resource_ids": list(policy.resources.ids or []),
            "resource_attribute_conditions": policy.resources.attribute_conditions or {},
            "resource_ancestor_conditions": policy.resources.ancestor_conditions or [],
        }

        obj, _ = PolicyModel.objects.update_or_create(id=policy.id, defaults=defaults)

        # Sync conditions
        obj.conditions.all().delete()
        for cond in policy.conditions:
            ConditionModel.objects.create(
                policy=obj,
                operator=cond.operator,
                attribute=cond.attribute,
                value=cond.value,
                negate=cond.negate,
            )

        return self._to_policy(obj)

    def delete(self, policy_id: str) -> None:
        from django_pbac.db.models import PolicyModel

        PolicyModel.objects.filter(id=policy_id).delete()

    def _to_policy(self, m: object) -> Policy:  # type: ignore[override]
        """Convert a PolicyModel instance to a Policy dataclass."""
        from django_pbac.db.models import PolicyModel  # for type safety

        # Subject matcher
        subjects = SubjectMatcher(
            user_ids=frozenset(m.subject_user_ids) if m.subject_user_ids else None,  # type: ignore[attr-defined]
            subject_types=(
                frozenset(SubjectType(t) for t in m.subject_types)  # type: ignore[attr-defined]
                if m.subject_types  # type: ignore[attr-defined]
                else None
            ),
            roles=frozenset(m.subject_roles) if m.subject_roles else None,  # type: ignore[attr-defined]
            groups=frozenset(m.subject_groups) if m.subject_groups else None,  # type: ignore[attr-defined]
            attribute_conditions=m.subject_attribute_conditions or None,  # type: ignore[attr-defined]
        )

        # Resource matcher
        resources = ResourceMatcher(
            types=frozenset(m.resource_types),  # type: ignore[attr-defined]
            ids=frozenset(m.resource_ids) if m.resource_ids else None,  # type: ignore[attr-defined]
            attribute_conditions=m.resource_attribute_conditions or None,  # type: ignore[attr-defined]
            ancestor_conditions=m.resource_ancestor_conditions or None,  # type: ignore[attr-defined]
        )

        # Conditions
        conditions = tuple(
            Condition(
                operator=c.operator,  # type: ignore[attr-defined]
                attribute=c.attribute,  # type: ignore[attr-defined]
                value=c.value,  # type: ignore[attr-defined]
                negate=c.negate,  # type: ignore[attr-defined]
            )
            for c in m.conditions.all()  # type: ignore[attr-defined]
        )

        return Policy(
            id=str(m.id),  # type: ignore[attr-defined]
            name=m.name,  # type: ignore[attr-defined]
            description=m.description or "",  # type: ignore[attr-defined]
            effect=Effect(m.effect),  # type: ignore[attr-defined]
            subjects=subjects,
            actions=frozenset(m.actions),  # type: ignore[attr-defined]
            resources=resources,
            conditions=conditions,
            priority=m.priority,  # type: ignore[attr-defined]
            conflict_resolution=ConflictResolution(m.conflict_resolution),  # type: ignore[attr-defined]
            is_active=m.is_active,  # type: ignore[attr-defined]
            valid_from=m.valid_from,  # type: ignore[attr-defined]
            valid_until=m.valid_until,  # type: ignore[attr-defined]
            version=m.version,  # type: ignore[attr-defined]
            created_by=m.created_by or "system",  # type: ignore[attr-defined]
            tags=frozenset(m.tags or []),  # type: ignore[attr-defined]
            source=PolicySourceType.DATABASE,
        )
