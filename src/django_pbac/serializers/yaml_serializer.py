"""Policy ↔ YAML serializer."""
from __future__ import annotations

import yaml

from django_pbac.core.models import Policy
from django_pbac.serializers.json_serializer import PolicyJSONSerializer


class PolicyYAMLSerializer:
    """Serialize and deserialize Policy dataclasses to/from YAML strings."""

    def __init__(self) -> None:
        self._json = PolicyJSONSerializer()

    def serialize(self, policy: Policy) -> str:
        """Convert a Policy to a YAML string."""
        data = self._json.serialize(policy)
        return yaml.dump({"policies": [data]}, default_flow_style=False, allow_unicode=True)

    def serialize_many(self, policies: list[Policy]) -> str:
        """Convert multiple Policies to a YAML string."""
        data = [self._json.serialize(p) for p in policies]
        return yaml.dump({"policies": data}, default_flow_style=False, allow_unicode=True)

    def deserialize(self, yaml_str: str) -> Policy:
        """Parse a YAML string containing a single policy definition."""
        data = yaml.safe_load(yaml_str)
        if "policies" in data:
            data = data["policies"][0]
        return self._json.deserialize(data)

    def deserialize_many(self, yaml_str: str) -> list[Policy]:
        """Parse a YAML string containing multiple policy definitions."""
        data = yaml.safe_load(yaml_str)
        policies = data.get("policies", [data])
        return [self._json.deserialize(p) for p in policies]
