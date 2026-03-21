"""
Policy Evaluation Engine (PDP — Policy Decision Point).

This module is pure Python — no Django imports allowed.

The PolicyEvaluator is stateless: all dependencies are injected. Given the
same inputs it always produces the same output (pure function semantics).

Usage::

    from django_pbac.core.evaluator import PolicyEvaluator
    from django_pbac.core.operators import operator_registry
    from django_pbac.core.types import ConflictResolution

    evaluator = PolicyEvaluator(
        conflict_resolution=ConflictResolution.DENY_OVERRIDE,
        operator_registry=operator_registry,
    )
    decision = evaluator.evaluate(request, policies)
"""
from __future__ import annotations

import logging
import time as _time
from typing import Any

from django_pbac.core.exceptions import ConfigurationError
from django_pbac.core.matchers import (
    action_matches,
    resource_matcher_matches,
    subject_matcher_matches,
)
from django_pbac.core.models import (
    EvaluationStep,
    Policy,
    PolicyDecision,
    PolicyRequest,
    ResourceFilter,
    Subject,
)
from django_pbac.core.operators import OperatorRegistry, resolve_attribute, resolve_condition_value
from django_pbac.core.operators import operator_registry as default_registry
from django_pbac.core.types import ConflictResolution, Effect

logger = logging.getLogger(__name__)


class PolicyEvaluator:
    """
    The Policy Decision Point (PDP).

    Evaluates a PolicyRequest against a list of Policy objects and returns
    a PolicyDecision.

    This class is stateless — instantiate once and reuse across requests.
    """

    def __init__(
        self,
        conflict_resolution: ConflictResolution = ConflictResolution.DENY_OVERRIDE,
        operator_registry: OperatorRegistry = default_registry,
        enable_trace: bool = True,
    ) -> None:
        self.conflict_resolution = conflict_resolution
        self.operator_registry = operator_registry
        self.enable_trace = enable_trace

    # ------------------------------------------------------------------
    # Main evaluate method
    # ------------------------------------------------------------------

    def evaluate(
        self,
        request: PolicyRequest,
        policies: list[Policy],
    ) -> PolicyDecision:
        """
        Evaluate a PolicyRequest against the given policies.

        Algorithm:
            1. Filter active & temporally valid policies.
            2. Filter applicable policies (action, resource type, subject, resource).
            3. Evaluate conditions for each applicable policy.
            4. Separate into PERMIT and DENY sets.
            5. Apply conflict resolution strategy.
            6. Build and return PolicyDecision with trace.
        """
        start = _time.perf_counter()
        trace: list[EvaluationStep] = []

        # Step 1: Active + valid policies
        active = [
            p for p in policies
            if p.is_active and p.is_valid_at(request.context.timestamp)
        ]

        # Step 2 + 3: Find applicable + condition-matched policies
        permit_policies: list[Policy] = []
        deny_policies: list[Policy] = []

        for policy in active:
            step, condition_passed = self._evaluate_policy(policy, request)
            if self.enable_trace:
                trace.append(step)

            if condition_passed:
                if policy.effect == Effect.PERMIT:
                    permit_policies.append(policy)
                else:
                    deny_policies.append(policy)

        # Step 5: Apply conflict resolution
        elapsed_ms = (_time.perf_counter() - start) * 1000
        decision = self._resolve_conflict(
            request=request,
            permit_policies=permit_policies,
            deny_policies=deny_policies,
            trace=trace,
            elapsed_ms=elapsed_ms,
            evaluated_count=len(active),
        )
        return decision

    # ------------------------------------------------------------------
    # Per-policy evaluation
    # ------------------------------------------------------------------

    def _evaluate_policy(
        self,
        policy: Policy,
        request: PolicyRequest,
    ) -> tuple[EvaluationStep, bool]:
        """
        Evaluate a single policy against the request.

        Returns (EvaluationStep, condition_matched: bool).
        """
        # Action matching
        action_matched = any(
            action_matches(pat, request.action) for pat in policy.actions
        )
        if not action_matched:
            return (
                EvaluationStep(
                    policy_id=policy.id,
                    policy_name=policy.name,
                    matched=False,
                    effect=None,
                    reason="Action not matched.",
                ),
                False,
            )

        # Resource type matching (fast path)
        type_matched = any(
            m.types is None or m.types == request.resource.type
            for m in policy.resource_matchers
        )
        if not type_matched:
            return (
                EvaluationStep(
                    policy_id=policy.id,
                    policy_name=policy.name,
                    matched=False,
                    effect=None,
                    reason=f"Resource type {request.resource.type!r} not in policy types.",
                ),
                False,
            )

        # Subject matching
        if not any(subject_matcher_matches(m, request) for m in policy.subject_matchers):
            return (
                EvaluationStep(
                    policy_id=policy.id,
                    policy_name=policy.name,
                    matched=False,
                    effect=None,
                    reason="Subject did not match policy subject selector.",
                ),
                False,
            )

        # Resource matching
        if not any(resource_matcher_matches(m, request) for m in policy.resource_matchers):
            return (
                EvaluationStep(
                    policy_id=policy.id,
                    policy_name=policy.name,
                    matched=False,
                    effect=None,
                    reason="Resource did not match policy resource selector.",
                ),
                False,
            )

        # Conditions
        conditions_passed, condition_reason = self.evaluate_conditions(policy, request)
        if not conditions_passed:
            return (
                EvaluationStep(
                    policy_id=policy.id,
                    policy_name=policy.name,
                    matched=False,
                    effect=None,
                    reason=f"Condition failed: {condition_reason}",
                ),
                False,
            )

        return (
            EvaluationStep(
                policy_id=policy.id,
                policy_name=policy.name,
                matched=True,
                effect=policy.effect,
                reason=f"Policy matched. Effect: {policy.effect.value}",
            ),
            True,
        )

    def evaluate_conditions(
        self,
        policy: Policy,
        request: PolicyRequest,
    ) -> tuple[bool, str]:
        """
        Evaluate all conditions of a policy against the request.

        Returns (all_passed: bool, failure_reason: str).
        The failure_reason is empty if all conditions passed.
        """
        for condition in policy.conditions:
            actual = resolve_attribute(condition.attribute, request)
            expected = resolve_condition_value(condition.value, request)

            try:
                result = self.operator_registry.evaluate(
                    condition.operator, actual, expected
                )
            except ConfigurationError:
                logger.warning(
                    "Policy %r references unknown operator %r. "
                    "Treating condition as failed.",
                    policy.name,
                    condition.operator,
                )
                result = False

            if condition.negate:
                result = not result

            if not result:
                return (
                    False,
                    f"Condition [{condition.attribute} {condition.operator} "
                    f"{expected!r}] failed (actual={actual!r}, negate={condition.negate}).",
                )

        return True, ""

    # ------------------------------------------------------------------
    # Conflict resolution
    # ------------------------------------------------------------------

    def _resolve_conflict(
        self,
        request: PolicyRequest,
        permit_policies: list[Policy],
        deny_policies: list[Policy],
        trace: list[EvaluationStep],
        elapsed_ms: float,
        evaluated_count: int,
    ) -> PolicyDecision:
        """Apply the configured conflict resolution strategy."""
        strategy = self.conflict_resolution
        trace_tuple = tuple(trace)
        all_matched = [p.id for p in permit_policies + deny_policies]

        match strategy:
            case ConflictResolution.DENY_OVERRIDE:
                return self._resolve_deny_override(
                    request, permit_policies, deny_policies,
                    trace_tuple, all_matched, elapsed_ms, evaluated_count,
                )
            case ConflictResolution.PERMIT_OVERRIDE:
                return self._resolve_permit_override(
                    request, permit_policies, deny_policies,
                    trace_tuple, all_matched, elapsed_ms, evaluated_count,
                )
            case ConflictResolution.FIRST_APPLICABLE:
                return self._resolve_first_applicable(
                    request, permit_policies, deny_policies,
                    trace_tuple, all_matched, elapsed_ms, evaluated_count,
                )

    def _resolve_deny_override(
        self,
        request: PolicyRequest,
        permit_policies: list[Policy],
        deny_policies: list[Policy],
        trace: tuple[EvaluationStep, ...],
        matched_ids: list[str],
        elapsed_ms: float,
        evaluated_count: int,
    ) -> PolicyDecision:
        """DENY wins if any DENY policy matched."""
        if deny_policies:
            # Sort by priority DESC, take highest priority deny
            best_deny = sorted(deny_policies, key=lambda p: p.priority, reverse=True)[0]
            return PolicyDecision(
                effect=Effect.DENY,
                reason=f"Denied by policy: {best_deny.name!r} (deny_override).",
                request=request,
                matched_policies=tuple(matched_ids),
                denied_by=best_deny.name,
                trace=trace,
                evaluation_time_ms=elapsed_ms,
                evaluated_policy_count=evaluated_count,
            )

        if permit_policies:
            best_permit = sorted(permit_policies, key=lambda p: p.priority, reverse=True)[0]
            return PolicyDecision(
                effect=Effect.PERMIT,
                reason=f"Permitted by policy: {best_permit.name!r}.",
                request=request,
                matched_policies=tuple(matched_ids),
                permitted_by=best_permit.name,
                trace=trace,
                evaluation_time_ms=elapsed_ms,
                evaluated_policy_count=evaluated_count,
            )

        return PolicyDecision(
            effect=Effect.DENY,
            reason="No matching policy found. Default deny.",
            request=request,
            trace=trace,
            evaluation_time_ms=elapsed_ms,
            evaluated_policy_count=evaluated_count,
        )

    def _resolve_permit_override(
        self,
        request: PolicyRequest,
        permit_policies: list[Policy],
        deny_policies: list[Policy],
        trace: tuple[EvaluationStep, ...],
        matched_ids: list[str],
        elapsed_ms: float,
        evaluated_count: int,
    ) -> PolicyDecision:
        """PERMIT wins if any PERMIT policy matched."""
        if permit_policies:
            best_permit = sorted(permit_policies, key=lambda p: p.priority, reverse=True)[0]
            return PolicyDecision(
                effect=Effect.PERMIT,
                reason=f"Permitted by policy: {best_permit.name!r} (permit_override).",
                request=request,
                matched_policies=tuple(matched_ids),
                permitted_by=best_permit.name,
                trace=trace,
                evaluation_time_ms=elapsed_ms,
                evaluated_policy_count=evaluated_count,
            )

        if deny_policies:
            best_deny = sorted(deny_policies, key=lambda p: p.priority, reverse=True)[0]
            return PolicyDecision(
                effect=Effect.DENY,
                reason=f"Denied by policy: {best_deny.name!r}.",
                request=request,
                matched_policies=tuple(matched_ids),
                denied_by=best_deny.name,
                trace=trace,
                evaluation_time_ms=elapsed_ms,
                evaluated_policy_count=evaluated_count,
            )

        return PolicyDecision(
            effect=Effect.DENY,
            reason="No matching policy found. Default deny.",
            request=request,
            trace=trace,
            evaluation_time_ms=elapsed_ms,
            evaluated_policy_count=evaluated_count,
        )

    def _resolve_first_applicable(
        self,
        request: PolicyRequest,
        permit_policies: list[Policy],
        deny_policies: list[Policy],
        trace: tuple[EvaluationStep, ...],
        matched_ids: list[str],
        elapsed_ms: float,
        evaluated_count: int,
    ) -> PolicyDecision:
        """First matching policy by priority wins."""
        all_matched = sorted(
            permit_policies + deny_policies,
            key=lambda p: p.priority,
            reverse=True,
        )

        if not all_matched:
            return PolicyDecision(
                effect=Effect.DENY,
                reason="No matching policy found. Default deny.",
                request=request,
                trace=trace,
                evaluation_time_ms=elapsed_ms,
                evaluated_policy_count=evaluated_count,
            )

        first = all_matched[0]
        if first.effect == Effect.PERMIT:
            return PolicyDecision(
                effect=Effect.PERMIT,
                reason=f"Permitted by first applicable policy: {first.name!r}.",
                request=request,
                matched_policies=tuple(matched_ids),
                permitted_by=first.name,
                trace=trace,
                evaluation_time_ms=elapsed_ms,
                evaluated_policy_count=evaluated_count,
            )
        else:
            return PolicyDecision(
                effect=Effect.DENY,
                reason=f"Denied by first applicable policy: {first.name!r}.",
                request=request,
                matched_policies=tuple(matched_ids),
                denied_by=first.name,
                trace=trace,
                evaluation_time_ms=elapsed_ms,
                evaluated_policy_count=evaluated_count,
            )

    # ------------------------------------------------------------------
    # QuerySet filter generation
    # ------------------------------------------------------------------

    def get_permitted_resource_filter(
        self,
        subject: Subject,
        action: str,
        resource_type: str,
        policies: list[Policy],
    ) -> ResourceFilter:
        """
        Analyze PERMIT policies and produce a ResourceFilter for queryset filtering.

        Algorithm:
            1. Find all active PERMIT policies matching (subject, action, resource_type).
            2. Check for blanket DENY policies (no resource conditions).
            3. If any PERMIT policy has no resource attribute conditions → permit_all.
            4. Build Q() objects from PERMIT policy conditions.
            5. OR all Q() objects together.

        v1 Limitations:
            - Only "eq" and "in" resource attribute conditions are supported for Q()
              conversion. Complex operators (regex, ip_in_cidr, time_between, etc.)
              fall back to permit_all with a WARNING logged.
            - DENY policies with resource conditions are not subtracted from Q()
              in v1 — only blanket DENY policies (deny_all) are detected.
        """
        from django_pbac.core.models import Context, PolicyRequest, Resource

        # Build a synthetic PolicyRequest for subject/action matching
        dummy_resource = Resource(type=resource_type)
        dummy_context = Context()
        dummy_request = PolicyRequest(
            subject=subject,
            action=action,
            resource=dummy_resource,
            context=dummy_context,
        )

        active_policies = [
            p for p in policies
            if p.is_active and p.is_valid_at(dummy_context.timestamp)
        ]

        # Filter to policies that match subject + action + resource type
        relevant_permit: list[Policy] = []
        relevant_deny_blanket: list[Policy] = []

        for policy in active_policies:
            # Check action
            if not any(action_matches(pat, action) for pat in policy.actions):
                continue
            # Check resource type
            if not any(
                m.types is None or m.types == resource_type
                for m in policy.resource_matchers
            ):
                continue
            # Check subject
            if not any(subject_matcher_matches(m, subject) for m in policy.subject_matchers):
                continue

            if policy.effect == Effect.PERMIT:
                relevant_permit.append(policy)
            elif policy.effect == Effect.DENY:
                # Blanket deny: no resource attribute conditions
                first_rm = policy.resource_matchers[0] if policy.resource_matchers else None
                if first_rm and not first_rm.attributes and not first_rm.id:
                    conditions_pass, _ = self.evaluate_conditions(policy, dummy_request)
                    if conditions_pass:
                        relevant_deny_blanket.append(policy)

        # Blanket deny wins
        if relevant_deny_blanket:
            return ResourceFilter(
                deny_all=True,
                filter_explanation=(
                    f"Blanket DENY policy active: "
                    f"{relevant_deny_blanket[0].name!r}"
                ),
            )

        if not relevant_permit:
            return ResourceFilter(
                deny_all=True,
                filter_explanation="No matching PERMIT policy found.",
            )

        # Check for unrestricted permit
        for policy in relevant_permit:
            first_rm = policy.resource_matchers[0] if policy.resource_matchers else None
            has_resource_conditions = bool(
                first_rm and (first_rm.attributes or first_rm.id)
            )
            if not has_resource_conditions:
                return ResourceFilter(
                    permit_all=True,
                    filter_explanation=f"Unrestricted PERMIT: {policy.name!r}",
                )

        # Build Q() from resource conditions
        q_objects = self._build_q_filters(relevant_permit, subject)
        if q_objects is None:
            # Fell back to permit_all due to unsupported operators
            return ResourceFilter(
                permit_all=True,
                filter_explanation=(
                    "Unsupported operator in resource conditions — "
                    "falling back to permit_all. Review your policies."
                ),
            )

        return ResourceFilter(
            q_filter=q_objects,
            filter_explanation=f"Q() filter from {len(relevant_permit)} PERMIT policy/ies.",
        )

    def _build_q_filters(
        self,
        permit_policies: list[Policy],
        subject: Subject,
    ) -> Any:
        """
        Build a combined Django Q() object from PERMIT policies.

        Returns None if any unsupported operator is encountered (triggers permit_all).
        Multiple policies are OR'd; multiple conditions within a policy are AND'd.

        Django Q is imported here (only method requiring Django dependency in evaluator).
        This import is deferred and only runs when queryset filtering is used.
        """
        try:
            from django.db.models import Q
        except ImportError:
            return None  # Not in Django context — return None to signal permit_all

        supported_operators = {"eq", "in"}

        combined_q = Q()
        any_added = False

        for policy in permit_policies:
            first_rm = policy.resource_matchers[0] if policy.resource_matchers else None
            if not (first_rm and first_rm.attributes):
                continue

            policy_q = Q()
            policy_valid = True

            for attr_key, expected in first_rm.attributes.items():
                resolved = self._resolve_ref_in_filter(expected, subject)

                if isinstance(resolved, dict):
                    # Operator dict
                    for op_name, op_value in resolved.items():
                        if op_name not in supported_operators:
                            logger.warning(
                                "django-pbac queryset filter: operator %r is not supported "
                                "for Q() conversion in v1. Falling back to permit_all. "
                                "Policy: %r",
                                op_name,
                                policy.name,
                            )
                            return None
                        if op_name == "eq":
                            policy_q &= Q(**{attr_key: op_value})
                        elif op_name == "in":
                            policy_q &= Q(**{f"{attr_key}__in": op_value})
                else:
                    policy_q &= Q(**{attr_key: resolved})

            if policy_valid:
                combined_q |= policy_q
                any_added = True

        if not any_added:
            return Q()

        return combined_q

    def _resolve_ref_in_filter(self, value: Any, subject: Subject) -> Any:
        """Resolve cross-references against the subject during Q() building."""
        if isinstance(value, dict) and "ref" in value:
            ref_path = value["ref"]
            parts = ref_path.split(".")
            if parts[0] == "subject":
                if len(parts) >= 3 and parts[1] == "attributes":
                    return subject.attributes.get(parts[2])
                elif len(parts) == 2 and parts[1] == "id":
                    return subject.id
        return value
