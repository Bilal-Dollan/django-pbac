"""
Policy ↔ JSON dict serializer.

Converts Policy dataclasses to JSON-serializable dicts and back.
Used for export, API responses, and policy versioning snapshots.
"""
from __future__ import annotations

from typing import Any

from django_pbac.core.models import Condition, Policy, ResourceMatcher, SubjectMatcher
from django_pbac.core.types import (
    Effect,
    PolicySourceType,
    SubjectType,
    parse_conflict_resolution,
)


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
            "subject_matchers": [
                self._serialize_subject_matcher(sm) for sm in policy.subject_matchers
            ],
            "resource_matchers": [
                self._serialize_resource_matcher(rm) for rm in policy.resource_matchers
            ],
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

        # Support both new list-of-matchers format and legacy single-matcher format
        raw_subjects = data.get("subject_matchers") or [data.get("subject", {})]
        raw_resources = data.get("resource_matchers") or [data.get("resources", {})]

        return Policy(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            effect=Effect(data["effect"]),
            actions=frozenset(data["actions"]),
            subject_matchers=tuple(
                self._deserialize_subject_matcher(sm) for sm in raw_subjects
            ),
            resource_matchers=tuple(
                self._deserialize_resource_matcher(rm) for rm in raw_resources
            ),
            conditions=tuple(
                self._deserialize_condition(c) for c in data.get("conditions", [])
            ),
            priority=int(data.get("priority", 0)),
            conflict_resolution=parse_conflict_resolution(
                data.get("conflict_resolution", "DENY_OVERRIDE")
            ),
            is_active=bool(data.get("is_active", True)),
            valid_from=valid_from,
            valid_until=valid_until,
            version=int(data.get("version", 1)),
            created_by=data.get("created_by", "system"),
            tags=frozenset(data.get("tags", [])),
            source=PolicySourceType(data.get("source", "DATABASE")),
        )

    def _serialize_subject_matcher(self, sm: SubjectMatcher) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if sm.id is not None:
            result["id"] = sm.id
        if sm.subject_types is not None:
            result["subject_types"] = sorted(t.value for t in sm.subject_types)
        if sm.roles:
            result["roles"] = sorted(sm.roles)
        if sm.groups is not None:
            result["groups"] = sorted(sm.groups)
        if sm.attributes is not None:
            result["attributes"] = sm.attributes
        return result

    def _deserialize_subject_matcher(self, data: dict[str, Any]) -> SubjectMatcher:
        return SubjectMatcher(
            id=data.get("id"),
            subject_types=(
                frozenset(SubjectType(t) for t in data["subject_types"])
                if "subject_types" in data
                else None
            ),
            roles=frozenset(data["roles"]) if "roles" in data else frozenset(),
            groups=frozenset(data["groups"]) if "groups" in data else None,
            attributes=data.get("attributes"),
        )

    def _serialize_resource_matcher(self, rm: ResourceMatcher) -> dict[str, Any]:
        result: dict[str, Any] = {"types": rm.types}
        if rm.id is not None:
            result["id"] = rm.id
        if rm.attributes is not None:
            result["attributes"] = rm.attributes
        if rm.ancestor_conditions is not None:
            result["ancestor_conditions"] = rm.ancestor_conditions
        return result

    def _deserialize_resource_matcher(self, data: dict[str, Any]) -> ResourceMatcher:
        return ResourceMatcher(
            types=data.get("types"),
            id=data.get("id"),
            attributes=data.get("attributes"),
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
