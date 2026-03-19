"""
Policy ↔ JSON dict serializer.

Converts Policy dataclasses to JSON-serializable dicts and back.
Used for export, API responses, and policy versioning snapshots.
"""
from __future__ import annotations

from typing import Any

from django_pbac.core.models import Condition, Policy, ResourceMatcher, SubjectMatcher
from django_pbac.core.types import ConflictResolution, Effect, PolicySourceType, SubjectType


class PolicyJSONSerializer:
    """Serialize and deserialize Policy dataclasses to/from JSON-compatible dicts."""

    def serialize(self, policy: Policy) -> dict[str, Any]:
        """Convert a Policy dataclass to a JSON-serializable dict."""
        return {
            "id": policy.id,
            "name": policy.name,
            "description": policy.description,
            "effect": policy.effect.value,
            "actions": sorted(policy.actions),
            "subject": self._serialize_subject_matcher(policy.subjects),
            "resources": self._serialize_resource_matcher(policy.resources),
            "conditions": [self._serialize_condition(c) for c in policy.conditions],
            "priority": policy.priority,
            "conflict_resolution": policy.conflict_resolution.value,
            "is_active": policy.is_active,
            "valid_from": policy.valid_from.isoformat() if policy.valid_from else None,
            "valid_until": policy.valid_until.isoformat() if policy.valid_until else None,
            "version": policy.version,
            "created_by": policy.created_by,
            "tags": sorted(policy.tags),
            "source": policy.source.value,
        }

    def deserialize(self, data: dict[str, Any]) -> Policy:
        """Create a Policy dataclass from a JSON dict."""
        from datetime import datetime

        valid_from = None
        if data.get("valid_from"):
            valid_from = datetime.fromisoformat(data["valid_from"])

        valid_until = None
        if data.get("valid_until"):
            valid_until = datetime.fromisoformat(data["valid_until"])

        return Policy(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            effect=Effect(data["effect"]),
            actions=frozenset(data["actions"]),
            subjects=self._deserialize_subject_matcher(data.get("subject", {})),
            resources=self._deserialize_resource_matcher(data["resources"]),
            conditions=tuple(
                self._deserialize_condition(c) for c in data.get("conditions", [])
            ),
            priority=int(data.get("priority", 0)),
            conflict_resolution=ConflictResolution(
                data.get("conflict_resolution", "deny_override")
            ),
            is_active=bool(data.get("is_active", True)),
            valid_from=valid_from,
            valid_until=valid_until,
            version=int(data.get("version", 1)),
            created_by=data.get("created_by", "system"),
            tags=frozenset(data.get("tags", [])),
            source=PolicySourceType(data.get("source", "database")),
        )

    def _serialize_subject_matcher(self, sm: SubjectMatcher) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if sm.user_ids is not None:
            result["user_ids"] = sorted(sm.user_ids)
        if sm.subject_types is not None:
            result["subject_types"] = sorted(t.value for t in sm.subject_types)
        if sm.roles is not None:
            result["roles"] = sorted(sm.roles)
        if sm.groups is not None:
            result["groups"] = sorted(sm.groups)
        if sm.attribute_conditions is not None:
            result["attribute_conditions"] = sm.attribute_conditions
        return result

    def _deserialize_subject_matcher(self, data: dict[str, Any]) -> SubjectMatcher:
        return SubjectMatcher(
            user_ids=frozenset(data["user_ids"]) if "user_ids" in data else None,
            subject_types=(
                frozenset(SubjectType(t) for t in data["subject_types"])
                if "subject_types" in data
                else None
            ),
            roles=frozenset(data["roles"]) if "roles" in data else None,
            groups=frozenset(data["groups"]) if "groups" in data else None,
            attribute_conditions=data.get("attribute_conditions"),
        )

    def _serialize_resource_matcher(self, rm: ResourceMatcher) -> dict[str, Any]:
        result: dict[str, Any] = {"types": sorted(rm.types)}
        if rm.ids is not None:
            result["ids"] = sorted(rm.ids)
        if rm.attribute_conditions is not None:
            result["attribute_conditions"] = rm.attribute_conditions
        if rm.ancestor_conditions is not None:
            result["ancestor_conditions"] = rm.ancestor_conditions
        return result

    def _deserialize_resource_matcher(self, data: dict[str, Any]) -> ResourceMatcher:
        return ResourceMatcher(
            types=frozenset(data.get("types", [])),
            ids=frozenset(data["ids"]) if "ids" in data else None,
            attribute_conditions=data.get("attribute_conditions"),
            ancestor_conditions=data.get("ancestor_conditions"),
        )

    def _serialize_condition(self, c: Condition) -> dict[str, Any]:
        return {
            "operator": c.operator,
            "attribute": c.attribute,
            "value": c.value,
            "negate": c.negate,
        }

    def _deserialize_condition(self, data: dict[str, Any]) -> Condition:
        return Condition(
            operator=data["operator"],
            attribute=data["attribute"],
            value=data["value"],
            negate=bool(data.get("negate", False)),
        )
