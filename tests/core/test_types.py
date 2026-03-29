"""Tests for django_pbac.core.types enumerations."""
from __future__ import annotations

import pytest

from django_pbac.core.types import (
    ConflictResolution,
    Effect,
    PolicySourceType,
    SubjectType,
    parse_conflict_resolution,
)


class TestEffect:
    def test_permit_value(self) -> None:
        assert Effect.PERMIT.value == "PERMIT"

    def test_deny_value(self) -> None:
        assert Effect.DENY.value == "DENY"

    def test_roundtrip(self) -> None:
        assert Effect("PERMIT") is Effect.PERMIT
        assert Effect("DENY") is Effect.DENY

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            Effect("ALLOW")


class TestConflictResolution:
    def test_all_members(self) -> None:
        assert ConflictResolution.DENY_OVERRIDE
        assert ConflictResolution.PERMIT_OVERRIDE
        assert ConflictResolution.FIRST_APPLICABLE

    def test_roundtrip(self) -> None:
        assert ConflictResolution("DENY_OVERRIDE") is ConflictResolution.DENY_OVERRIDE

    def test_parse_lowercase_db_value(self) -> None:
        assert parse_conflict_resolution("deny_override") is ConflictResolution.DENY_OVERRIDE

    def test_parse_enum_name_value(self) -> None:
        assert parse_conflict_resolution("PERMIT_OVERRIDE") is ConflictResolution.PERMIT_OVERRIDE


class TestSubjectType:
    def test_standard_types(self) -> None:
        assert SubjectType.USER.value == "USER"
        assert SubjectType.SERVICE.value == "SERVICE"
        assert SubjectType.ANONYMOUS.value == "ANONYMOUS"


class TestPolicySourceType:
    def test_all_members(self) -> None:
        assert PolicySourceType.DATABASE
        assert PolicySourceType.CODE
        assert PolicySourceType.YAML
