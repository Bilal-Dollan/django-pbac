"""Tests for DatabasePolicyLoader backend-portable filtering."""
from __future__ import annotations

from types import SimpleNamespace
from collections.abc import Sequence

from django_pbac.core.types import ConflictResolution
from django_pbac.core.models import Subject
from django_pbac.core.types import SubjectType
from django_pbac.loaders.db import DatabasePolicyLoader


class _FakePolicyQuerySet:
    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def valid_at(self, _dt):
        return self

    def prefetch_related(self, *_args):
        return self

    def select_related(self, *_args):
        return self

    def __iter__(self):
        return iter(self._rows)


class _FakePolicyManager:
    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def active(self):
        return _FakePolicyQuerySet(self._rows)


class TestDatabasePolicyLoader:
    def test_load_for_request_filters_action_and_resource_in_python(self, monkeypatch) -> None:
        rows = [
            SimpleNamespace(id="p-exact", actions=["documents:read"], resource_types=["document"]),
            SimpleNamespace(id="p-namespace", actions=["documents:*"], resource_types=["document"]),
            SimpleNamespace(id="p-global", actions=["*"], resource_types=["document"]),
            SimpleNamespace(id="p-wrong-action", actions=["documents:write"], resource_types=["document"]),
            SimpleNamespace(id="p-wrong-resource", actions=["documents:read"], resource_types=["invoice"]),
        ]

        fake_policy_model = SimpleNamespace(objects=_FakePolicyManager(rows))

        import django_pbac.db.models as db_models

        monkeypatch.setattr(db_models, "PolicyModel", fake_policy_model)

        loader = DatabasePolicyLoader()
        monkeypatch.setattr(loader, "_to_policy", lambda model: model)

        subject = Subject(id="user:1", type=SubjectType.USER)
        matched = loader.load_for_request(subject, "documents:read", "document")

        assert {p.id for p in matched} == {"p-exact", "p-namespace", "p-global"}

    def test_to_policy_accepts_lowercase_conflict_resolution(self) -> None:
        loader = DatabasePolicyLoader()

        fake_condition_qs = SimpleNamespace(all=lambda: [])
        model = SimpleNamespace(
            id="p1",
            name="Policy",
            description="",
            effect="PERMIT",
            actions=["documents:list"],
            subject_user_ids=[],
            subject_types=[],
            subject_roles=[],
            subject_groups=[],
            subject_attribute_conditions={},
            resource_types=["document"],
            resource_ids=[],
            resource_attribute_conditions={},
            resource_ancestor_conditions=[],
            conditions=fake_condition_qs,
            priority=100,
            conflict_resolution="deny_override",
            is_active=True,
            valid_from=None,
            valid_until=None,
            version=1,
            created_by="system",
            tags=[],
        )

        policy = loader._to_policy(model)
        assert policy.conflict_resolution is ConflictResolution.DENY_OVERRIDE
