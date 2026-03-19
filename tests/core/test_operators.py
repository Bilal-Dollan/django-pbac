"""Tests for django_pbac.core.operators."""
from __future__ import annotations

import pytest

from django_pbac.core.models import Context, Resource, Subject
from django_pbac.core.operators import (
    OperatorRegistry,
    operator_registry,
    resolve_attribute,
)
from django_pbac.core.types import SubjectType


@pytest.fixture
def mock_request(subject_alice, resource_doc, context_default):
    from django_pbac.core.models import PolicyRequest

    return PolicyRequest(
        subject=subject_alice,
        action="documents:read",
        resource=resource_doc,
        context=context_default,
    )


class TestOperatorRegistry:
    def test_built_in_registered(self) -> None:
        assert operator_registry.get("eq") is not None
        assert operator_registry.get("neq") is not None
        assert operator_registry.get("in") is not None

    def test_register_custom(self) -> None:
        registry = OperatorRegistry()

        @registry.register("custom_op")
        def custom_op(a, b):
            return a == b

        assert registry.get("custom_op") is custom_op

    def test_unknown_operator_raises(self) -> None:
        with pytest.raises(KeyError):
            operator_registry.get("nonexistent_operator_xyz")

    def test_all_standard_operators_present(self) -> None:
        expected = [
            "eq", "neq", "eq_i", "startswith", "endswith", "contains",
            "regex", "gt", "gte", "lt", "lte",
            "in", "not_in", "contains_any", "contains_all",
            "is_true", "is_false", "is_null", "is_not_null",
        ]
        for op in expected:
            assert operator_registry.get(op) is not None, f"Missing operator: {op}"


class TestBuiltInOperators:
    def _op(self, name):
        return operator_registry.get(name)

    def test_eq(self) -> None:
        assert self._op("eq")("hello", "hello") is True
        assert self._op("eq")("hello", "world") is False

    def test_neq(self) -> None:
        assert self._op("neq")("hello", "world") is True
        assert self._op("neq")("hello", "hello") is False

    def test_eq_i(self) -> None:
        assert self._op("eq_i")("Hello", "hello") is True
        assert self._op("eq_i")("Hello", "HELLO") is True

    def test_startswith(self) -> None:
        assert self._op("startswith")("hello world", "hello") is True
        assert self._op("startswith")("hello world", "world") is False

    def test_endswith(self) -> None:
        assert self._op("endswith")("hello world", "world") is True

    def test_contains(self) -> None:
        assert self._op("contains")("hello world", "lo wo") is True

    def test_regex(self) -> None:
        assert self._op("regex")("hello123", r"\w+\d+") is True
        assert self._op("regex")("abc", r"^\d+$") is False

    def test_gt_lt(self) -> None:
        assert self._op("gt")(10, 5) is True
        assert self._op("lt")(5, 10) is True
        assert self._op("gte")(10, 10) is True
        assert self._op("lte")(9, 10) is True

    def test_in(self) -> None:
        assert self._op("in")("admin", ["admin", "editor"]) is True
        assert self._op("in")("guest", ["admin", "editor"]) is False

    def test_not_in(self) -> None:
        assert self._op("not_in")("guest", ["admin"]) is True

    def test_contains_any(self) -> None:
        assert self._op("contains_any")(["admin", "viewer"], ["admin"]) is True
        assert self._op("contains_any")(["user"], ["admin", "editor"]) is False

    def test_contains_all(self) -> None:
        assert self._op("contains_all")(["admin", "editor", "viewer"], ["admin", "editor"]) is True
        assert self._op("contains_all")(["admin"], ["admin", "editor"]) is False

    def test_is_true(self) -> None:
        assert self._op("is_true")(True, None) is True
        assert self._op("is_true")(False, None) is False

    def test_is_false(self) -> None:
        assert self._op("is_false")(False, None) is True

    def test_is_null(self) -> None:
        assert self._op("is_null")(None, None) is True
        assert self._op("is_null")("x", None) is False

    def test_is_not_null(self) -> None:
        assert self._op("is_not_null")("x", None) is True
        assert self._op("is_not_null")(None, None) is False


class TestResolveAttribute:
    def test_subject_id(self, mock_request) -> None:
        val = resolve_attribute("subject.id", mock_request)
        assert val == "user:alice"

    def test_subject_attribute(self, mock_request) -> None:
        val = resolve_attribute("subject.attributes.department", mock_request)
        assert val == "engineering"

    def test_resource_type(self, mock_request) -> None:
        val = resolve_attribute("resource.type", mock_request)
        assert val == "document"

    def test_context_attribute(self, mock_request) -> None:
        val = resolve_attribute("context.environment.ip", mock_request)
        assert val == "10.0.0.1"

    def test_missing_path_returns_none(self, mock_request) -> None:
        val = resolve_attribute("subject.attributes.nonexistent", mock_request)
        assert val is None

    def test_invalid_root_returns_none(self, mock_request) -> None:
        val = resolve_attribute("request.method", mock_request)
        assert val is None
