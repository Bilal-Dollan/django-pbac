"""
Django ORM models for django-pbac.

These models are the persistence layer. The authoritative types are the
core dataclasses in django_pbac.core.models — these ORM models are only
used for serialization to/from the database.

Models:
  PolicyModel          — A single access control policy
  ConditionModel       — A condition attached to a policy
  PolicyVersionModel   — Immutable version history for policy changes
  AuditLogModel        — Immutable record of every policy decision
"""
from __future__ import annotations

import uuid

from django.db import models

from django_pbac.db.managers import PolicyManager


class PolicyModel(models.Model):
    """
    Persistence model for a PBAC policy.

    Subject and resource matchers are stored as JSON fields for flexibility.
    Actions and resource_types are stored as JSON array fields for efficient
    filtering using ``__contains`` queries.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, default="")

    # Effect
    EFFECT_CHOICES = [("PERMIT", "Permit"), ("DENY", "Deny")]
    effect = models.CharField(max_length=10, choices=EFFECT_CHOICES, db_index=True)

    # Actions (JSON array): ["documents:read", "documents:*"]
    actions = models.JSONField(default=list)

    # Subject matcher fields
    subject_user_ids = models.JSONField(default=list, blank=True)
    subject_types = models.JSONField(default=list, blank=True)
    subject_roles = models.JSONField(default=list, blank=True)
    subject_groups = models.JSONField(default=list, blank=True)
    subject_attribute_conditions = models.JSONField(default=dict, blank=True)

    # Resource matcher fields
    resource_types = models.JSONField(default=list, db_index=True)
    resource_ids = models.JSONField(default=list, blank=True)
    resource_attribute_conditions = models.JSONField(default=dict, blank=True)
    resource_ancestor_conditions = models.JSONField(default=list, blank=True)

    # Policy metadata
    priority = models.IntegerField(default=0, db_index=True)
    CONFLICT_CHOICES = [
        ("deny_override", "Deny Override"),
        ("permit_override", "Permit Override"),
        ("first_applicable", "First Applicable"),
    ]
    conflict_resolution = models.CharField(
        max_length=20,
        choices=CONFLICT_CHOICES,
        default="deny_override",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    valid_from = models.DateTimeField(null=True, blank=True, db_index=True)
    valid_until = models.DateTimeField(null=True, blank=True, db_index=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.CharField(max_length=255, default="system", blank=True)
    tags = models.JSONField(default=list, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PolicyManager()

    class Meta:
        app_label = "django_pbac"
        verbose_name = "Policy"
        verbose_name_plural = "Policies"
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["is_active", "effect"]),
            models.Index(fields=["is_active", "valid_from", "valid_until"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.effect})"


class ConditionModel(models.Model):
    """A single condition attached to a PolicyModel."""

    policy = models.ForeignKey(
        PolicyModel,
        on_delete=models.CASCADE,
        related_name="conditions",
    )
    operator = models.CharField(max_length=50)
    attribute = models.CharField(max_length=255)
    value = models.JSONField()
    negate = models.BooleanField(default=False)

    class Meta:
        app_label = "django_pbac"
        verbose_name = "Condition"
        verbose_name_plural = "Conditions"

    def __str__(self) -> str:
        neg = "NOT " if self.negate else ""
        return f"{neg}{self.attribute} {self.operator} {self.value!r}"


class PolicyVersionModel(models.Model):
    """
    Immutable snapshot of a PolicyModel at a point in time.

    Created automatically when a policy is saved (if versioning is enabled).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_id = models.UUIDField(db_index=True)
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()  # full serialized policy
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=255, default="system")
    change_reason = models.TextField(blank=True, default="")

    class Meta:
        app_label = "django_pbac"
        verbose_name = "Policy Version"
        verbose_name_plural = "Policy Versions"
        ordering = ["-version"]
        unique_together = [("policy_id", "version")]

    def __str__(self) -> str:
        return f"Policy {self.policy_id} v{self.version}"


class AuditLogModel(models.Model):
    """
    Immutable audit log of every policy decision.

    Never update or delete these records. Use database-level immutability
    (triggers, RLS) in production environments.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Decision
    EFFECT_CHOICES = [("PERMIT", "Permit"), ("DENY", "Deny")]
    effect = models.CharField(max_length=10, choices=EFFECT_CHOICES, db_index=True)
    reason = models.CharField(max_length=500)

    # Subject
    subject_id = models.CharField(max_length=255, db_index=True)
    subject_type = models.CharField(max_length=50)

    # Request
    action = models.CharField(max_length=255, db_index=True)
    resource_type = models.CharField(max_length=255, db_index=True)
    resource_id = models.CharField(max_length=255, blank=True, db_index=True)
    request_id = models.CharField(max_length=255, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Performance
    evaluation_time_ms = models.FloatField(default=0.0)
    evaluated_policy_count = models.IntegerField(default=0)

    # Policy info
    matched_policies = models.JSONField(default=list)
    denied_by = models.CharField(max_length=255, blank=True)
    permitted_by = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = "django_pbac"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["subject_id", "action", "timestamp"]),
            models.Index(fields=["effect", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id", "timestamp"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.effect} | {self.subject_id} | {self.action} | "
            f"{self.resource_type}/{self.resource_id} | {self.timestamp}"
        )
