"""Tests for audit modules."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from django_pbac.audit.composite import CompositeAuditLogger
from django_pbac.audit.structured_log import StructuredLogAuditLogger
from django_pbac.core.models import (
    Context,
    Policy,
    PolicyDecision,
    PolicyRequest,
    Resource,
    ResourceMatcher,
    Subject,
    SubjectMatcher,
)
from django_pbac.core.types import Effect, SubjectType


@pytest.fixture
def permit_decision() -> PolicyDecision:
    subject = Subject(id="user:alice", type=SubjectType.USER)
    resource = Resource(id="doc:1", type="document")
    context = Context()
    request = PolicyRequest(
        subject=subject,
        action="documents:read",
        resource=resource,
        context=context,
    )
    policy = Policy(
        id="p1",
        effect=Effect.PERMIT,
        actions=frozenset({"documents:read"}),
        subject_matchers=(SubjectMatcher(),),
        resource_matchers=(ResourceMatcher(types="document"),),
        conditions=(),
    )
    return PolicyDecision(
        effect=Effect.PERMIT,
        request=request,
        matched_policies=(policy,),
        trace=(),
    )


@pytest.fixture
def deny_decision(permit_decision) -> PolicyDecision:
    return PolicyDecision(
        effect=Effect.DENY,
        request=permit_decision.request,
        matched_policies=(),
        trace=(),
        reason="No matching permit policy.",
    )


class TestStructuredLogAuditLogger:
    def test_logs_permit(self, permit_decision, caplog) -> None:
        with caplog.at_level(logging.INFO, logger="django_pbac.audit"):
            logger = StructuredLogAuditLogger()
            logger.log(permit_decision)
        assert any("PERMIT" in r.message or "permit" in r.message.lower() for r in caplog.records)

    def test_logs_deny(self, deny_decision, caplog) -> None:
        with caplog.at_level(logging.INFO, logger="django_pbac.audit"):
            logger = StructuredLogAuditLogger()
            logger.log(deny_decision)
        assert any("DENY" in r.message or "deny" in r.message.lower() for r in caplog.records)


class TestCompositeAuditLogger:
    def test_fans_out_to_all_loggers(self, permit_decision) -> None:
        mock_a = MagicMock()
        mock_b = MagicMock()
        composite = CompositeAuditLogger(loggers=[mock_a, mock_b])
        composite.log(permit_decision)
        mock_a.log.assert_called_once_with(permit_decision)
        mock_b.log.assert_called_once_with(permit_decision)

    def test_one_logger_failure_does_not_stop_others(self, permit_decision) -> None:
        failing_logger = MagicMock()
        failing_logger.log.side_effect = RuntimeError("Audit DB down")
        good_logger = MagicMock()

        composite = CompositeAuditLogger(loggers=[failing_logger, good_logger])
        composite.log(permit_decision)  # Should not raise

        good_logger.log.assert_called_once_with(permit_decision)

    def test_empty_composite(self, permit_decision) -> None:
        composite = CompositeAuditLogger(loggers=[])
        composite.log(permit_decision)  # Should not raise
