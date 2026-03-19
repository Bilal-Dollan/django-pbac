"""Tests for YAMLPolicyLoader."""
from __future__ import annotations

import pathlib
import textwrap

import pytest

from django_pbac.loaders.yaml_loader import YAMLPolicyLoader


SAMPLE_YAML = textwrap.dedent("""\
policies:
  - id: yaml:read-doc
    effect: PERMIT
    actions:
      - "documents:read"
    subject_matchers:
      - roles:
          - viewer
    resource_matchers:
      - type: document
    conditions: []
    priority: 10
    enabled: true
""")


@pytest.fixture
def yaml_policy_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(SAMPLE_YAML)
    return tmp_path


@pytest.fixture
def yaml_loader(yaml_policy_dir) -> YAMLPolicyLoader:
    return YAMLPolicyLoader(directories=[str(yaml_policy_dir)])


class TestYAMLPolicyLoader:
    def test_load_all(self, yaml_loader) -> None:
        policies = yaml_loader.load_all()
        assert len(policies) == 1
        assert policies[0].id == "yaml:read-doc"

    def test_policy_effect(self, yaml_loader) -> None:
        from django_pbac.core.types import Effect

        policies = yaml_loader.load_all()
        assert policies[0].effect is Effect.PERMIT

    def test_policy_actions(self, yaml_loader) -> None:
        policies = yaml_loader.load_all()
        assert "documents:read" in policies[0].actions

    def test_load_for_request(self, yaml_loader) -> None:
        from django_pbac.core.models import Subject
        from django_pbac.core.types import SubjectType

        subject = Subject(
            id="user:alice",
            type=SubjectType.USER,
            roles=frozenset({"viewer"}),
        )
        policies = yaml_loader.load_for_request(
            subject=subject,
            action="documents:read",
            resource_type="document",
        )
        assert len(policies) >= 1

    def test_get_by_id(self, yaml_loader) -> None:
        policy = yaml_loader.get_by_id("yaml:read-doc")
        assert policy is not None

    def test_get_by_id_missing(self, yaml_loader) -> None:
        policy = yaml_loader.get_by_id("nonexistent")
        assert policy is None

    def test_empty_directory(self, tmp_path) -> None:
        loader = YAMLPolicyLoader(directories=[str(tmp_path)])
        assert loader.load_all() == []

    def test_reload(self, yaml_loader, yaml_policy_dir) -> None:
        """After reload, policies should still be loadable."""
        yaml_loader.reload()
        assert len(yaml_loader.load_all()) == 1
