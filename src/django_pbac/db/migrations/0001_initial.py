"""Initial migration for django-pbac."""
from __future__ import annotations

import uuid
from typing import Any, ClassVar

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: ClassVar[list[Any]] = []

    operations = [  # noqa: RUF012
        migrations.CreateModel(
            name="PolicyModel",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),  # noqa: E501
                ("name", models.CharField(db_index=True, max_length=255, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("effect", models.CharField(choices=[("PERMIT", "Permit"), ("DENY", "Deny")], db_index=True, max_length=10)),  # noqa: E501
                ("actions", models.JSONField(default=list)),
                ("subject_user_ids", models.JSONField(blank=True, default=list)),
                ("subject_types", models.JSONField(blank=True, default=list)),
                ("subject_roles", models.JSONField(blank=True, default=list)),
                ("subject_groups", models.JSONField(blank=True, default=list)),
                ("subject_attribute_conditions", models.JSONField(blank=True, default=dict)),
                ("resource_types", models.JSONField(db_index=True, default=list)),
                ("resource_ids", models.JSONField(blank=True, default=list)),
                ("resource_attribute_conditions", models.JSONField(blank=True, default=dict)),
                ("resource_ancestor_conditions", models.JSONField(blank=True, default=list)),
                ("priority", models.IntegerField(db_index=True, default=0)),
                ("conflict_resolution", models.CharField(
                    choices=[
                        ("deny_override", "Deny Override"),
                        ("permit_override", "Permit Override"),
                        ("first_applicable", "First Applicable"),
                    ],
                    default="deny_override",
                    max_length=20,
                )),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("valid_from", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("valid_until", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_by", models.CharField(blank=True, default="system", max_length=255)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Policy",
                "verbose_name_plural": "Policies",
                "ordering": ["-priority", "name"],
            },
        ),
        migrations.CreateModel(
            name="ConditionModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),  # noqa: E501
                ("policy", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="conditions",
                    to="django_pbac.policymodel",
                )),
                ("operator", models.CharField(max_length=50)),
                ("attribute", models.CharField(max_length=255)),
                ("value", models.JSONField()),
                ("negate", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Condition",
                "verbose_name_plural": "Conditions",
            },
        ),
        migrations.CreateModel(
            name="PolicyVersionModel",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),  # noqa: E501
                ("policy_id", models.UUIDField(db_index=True)),
                ("version", models.PositiveIntegerField()),
                ("snapshot", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.CharField(default="system", max_length=255)),
                ("change_reason", models.TextField(blank=True, default="")),
            ],
            options={
                "verbose_name": "Policy Version",
                "verbose_name_plural": "Policy Versions",
                "ordering": ["-version"],
                "unique_together": {("policy_id", "version")},
            },
        ),
        migrations.CreateModel(
            name="AuditLogModel",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),  # noqa: E501
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("effect", models.CharField(
                    choices=[("PERMIT", "Permit"), ("DENY", "Deny")],
                    db_index=True,
                    max_length=10,
                )),
                ("reason", models.CharField(max_length=500)),
                ("subject_id", models.CharField(db_index=True, max_length=255)),
                ("subject_type", models.CharField(max_length=50)),
                ("action", models.CharField(db_index=True, max_length=255)),
                ("resource_type", models.CharField(db_index=True, max_length=255)),
                ("resource_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("request_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("evaluation_time_ms", models.FloatField(default=0.0)),
                ("evaluated_policy_count", models.IntegerField(default=0)),
                ("matched_policies", models.JSONField(default=list)),
                ("denied_by", models.CharField(blank=True, max_length=255)),
                ("permitted_by", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "Audit Log",
                "verbose_name_plural": "Audit Logs",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="policymodel",
            index=models.Index(fields=["is_active", "effect"], name="pbac_policy_active_effect"),
        ),
        migrations.AddIndex(
            model_name="policymodel",
            index=models.Index(
                fields=["is_active", "valid_from", "valid_until"],
                name="pbac_policy_active_validity",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogmodel",
            index=models.Index(
                fields=["subject_id", "action", "timestamp"],
                name="pbac_audit_subject_action",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogmodel",
            index=models.Index(
                fields=["effect", "timestamp"],
                name="pbac_audit_effect_ts",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogmodel",
            index=models.Index(
                fields=["resource_type", "resource_id", "timestamp"],
                name="pbac_audit_resource_ts",
            ),
        ),
    ]
