"""
YAMLPolicyLoader — load policies from YAML files.

YAML policy format::

    policies:
      - id: "yaml-doc-read-01"
        name: "Document Read — Authenticated Users"
        effect: PERMIT
        actions:
          - "documents:read"
          - "documents:list"
        subject:
          subject_types: [user, service]
          roles: [viewer, editor, admin]
        resources:
          types: [document]
          attribute_conditions:
            status: {in: [published, draft]}
            tenant_id: {ref: "subject.attributes.tenant_id"}
        conditions:
          - operator: time_between
            attribute: context.timestamp
            value:
              start: "00:00"
              end: "23:59"
        description: "Allow authenticated users to read documents."
        priority: 10
        tags: [documents, read-access]
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import yaml

from django_pbac.core.exceptions import ConfigurationError
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


class YAMLPolicyLoader:
    """
    Loads policies from YAML files.

    Scans the configured ``YAML_POLICY_DIRS`` for ``*.yaml`` and ``*.yml``
    files and parses them as policy definitions.

    Files are loaded at instantiation and cached in memory. Call
    ``reload()`` to re-read from disk.
    """

    def __init__(self, directories: list[str | Path] | None = None) -> None:
        self._dirs: list[Path] = []
        self._policies: dict[str, Policy] = {}

        if directories:
            for d in directories:
                self._dirs.append(Path(d))
        else:
            self._load_from_settings()

        self._load_all_files()

    def _load_from_settings(self) -> None:
        try:
            from django_pbac.conf import pbac_settings

            for d in pbac_settings.YAML_POLICY_DIRS:
                self._dirs.append(Path(d))
        except Exception:  # noqa: BLE001
            pass

    def _load_all_files(self) -> None:
        for directory in self._dirs:
            if not directory.exists():
                logger.warning("YAML policy directory does not exist: %s", directory)
                continue
            for path in sorted(directory.rglob("*.yaml")) + sorted(directory.rglob("*.yml")):
                self._load_file(path)

    def _load_file(self, path: Path) -> None:
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if not data or "policies" not in data:
                return
            for raw in data["policies"]:
                policy = self._parse_policy(raw, source_file=str(path))
                if policy.id in self._policies:
                    logger.warning(
                        "YAML policy ID %r from %s conflicts with existing policy. "
                        "Overwriting.",
                        policy.id,
                        path,
                    )
                self._policies[policy.id] = policy
        except yaml.YAMLError as exc:
            logger.error("Failed to parse YAML policy file %s: %s", path, exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error loading policy file %s: %s", path, exc)

    def reload(self) -> None:
        """Re-read all YAML files from disk."""
        self._policies.clear()
        self._load_all_files()

    def load_for_request(
        self,
        subject: Subject,
        action: str,
        resource_type: str,
    ) -> list[Policy]:
        return [
            p for p in self._policies.values()
            if p.is_active and any(
                m.types is None or m.types == resource_type
                for m in p.resource_matchers
            )
        ]

    def load_all(self) -> list[Policy]:
        return list(self._policies.values())

    def get_by_id(self, policy_id: str) -> Policy | None:
        return self._policies.get(policy_id)

    def save(self, policy: Policy) -> Policy:
        """In-memory save only. YAML files are read-only at runtime."""
        self._policies[policy.id] = policy
        return policy

    def delete(self, policy_id: str) -> None:
        self._policies.pop(policy_id, None)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_policy(self, raw: dict[str, Any], source_file: str = "") -> Policy:
        """Parse a raw YAML dict into a Policy dataclass."""
        try:
            policy_id = str(raw.get("id") or str(uuid.uuid4()))
            name = raw.get("name", "")
            effect = Effect(raw["effect"].upper())
            actions = frozenset(raw["actions"])

            subject_raw = raw.get("subject", {})
            # Support both 'subject_matchers' list format and legacy 'subject' dict format
            subject_matchers_raw = raw.get("subject_matchers", None)
            if subject_matchers_raw is not None:
                subject_matchers = tuple(
                    self._parse_subject_matcher(sm) for sm in subject_matchers_raw
                )
            else:
                subject_matchers = (self._parse_subject_matcher(subject_raw),)

            resource_matchers_raw = raw.get("resource_matchers", None)
            if resource_matchers_raw is not None:
                resource_matchers = tuple(
                    self._parse_resource_matcher(rm) for rm in resource_matchers_raw
                )
            else:
                resource_raw = raw.get("resources", {})
                resource_matchers = (self._parse_resource_matcher(resource_raw),)

            conditions = tuple(
                self._parse_condition(c) for c in raw.get("conditions", [])
            )

            return Policy(
                id=policy_id,
                name=name,
                effect=effect,
                subject_matchers=subject_matchers,
                actions=actions,
                resource_matchers=resource_matchers,
                conditions=conditions,
                description=raw.get("description", ""),
                priority=int(raw.get("priority", 0)),
                conflict_resolution=ConflictResolution(
                    raw.get("conflict_resolution", "DENY_OVERRIDE")
                ),
                is_active=bool(raw.get("is_active", raw.get("enabled", True))),
                created_by=raw.get("created_by", "yaml"),
                tags=frozenset(raw.get("tags", [])),
                source=PolicySourceType.YAML,
            )
        except (KeyError, ValueError) as exc:
            raise ConfigurationError(
                f"Invalid policy definition in {source_file!r}: {exc}"
            ) from exc

    def _parse_subject_matcher(self, raw: dict[str, Any]) -> SubjectMatcher:
        return SubjectMatcher(
            id=raw.get("id") or (raw["user_ids"][0] if "user_ids" in raw else None),
            subject_types=(
                frozenset(SubjectType(t.upper()) for t in raw["subject_types"])
                if "subject_types" in raw
                else None
            ),
            roles=frozenset(raw["roles"]) if "roles" in raw else frozenset(),
            groups=frozenset(raw["groups"]) if "groups" in raw else None,
            attributes=raw.get("attributes") or raw.get("attribute_conditions"),
        )

    def _parse_resource_matcher(self, raw: dict[str, Any]) -> ResourceMatcher:
        return ResourceMatcher(
            types=raw.get("type") or (raw.get("types", [None])[0] if isinstance(raw.get("types"), list) else raw.get("types")),
            id=raw.get("id") or (raw["ids"][0] if "ids" in raw else None),
            attributes=raw.get("attributes") or raw.get("attribute_conditions"),
            ancestor_conditions=raw.get("ancestor_conditions"),
        )

    def _parse_condition(self, raw: dict[str, Any]) -> Condition:
        return Condition(
            operator=raw["operator"],
            attribute=raw["attribute"],
            value=raw["value"],
            negate=bool(raw.get("negate", False)),
        )
