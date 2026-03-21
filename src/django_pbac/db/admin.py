"""
Django admin registrations for django-pbac models.

Provides rich admin interfaces for:
  - PolicyModel: full CRUD with inline conditions
  - AuditLogModel: read-only audit trail
  - PolicyVersionModel: read-only version history
"""
from __future__ import annotations

from typing import Any, ClassVar

from django.contrib import admin
from django.http import HttpRequest
from django.utils.html import format_html

from django_pbac.db.models import AuditLogModel, ConditionModel, PolicyModel, PolicyVersionModel

# ---------------------------------------------------------------------------
# Inline: Conditions
# ---------------------------------------------------------------------------

class ConditionInline(admin.TabularInline[ConditionModel, PolicyModel]):
    model = ConditionModel
    extra = 1
    fields = ("attribute", "operator", "value", "negate")


# ---------------------------------------------------------------------------
# PolicyModel admin
# ---------------------------------------------------------------------------

@admin.register(PolicyModel)
class PolicyAdmin(admin.ModelAdmin[PolicyModel]):
    list_display = (
        "name",
        "effect_badge",
        "priority",
        "is_active",
        "conflict_resolution",
        "valid_from",
        "valid_until",
        "version",
        "updated_at",
    )
    list_filter = ("effect", "is_active", "conflict_resolution", "resource_types")
    search_fields = ("name", "description", "subject_roles", "resource_types")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-priority", "name")
    inlines: ClassVar[list[Any]] = [ConditionInline]

    fieldsets = (
        (
            "Identity",
            {
                "fields": ("id", "name", "description", "effect", "priority",
                           "conflict_resolution", "is_active", "tags")
            },
        ),
        (
            "Validity",
            {"fields": ("valid_from", "valid_until", "version", "created_by")},
        ),
        (
            "Actions",
            {"fields": ("actions",)},
        ),
        (
            "Subject Matcher",
            {
                "fields": (
                    "subject_user_ids", "subject_types", "subject_roles",
                    "subject_groups", "subject_attribute_conditions",
                )
            },
        ),
        (
            "Resource Matcher",
            {
                "fields": (
                    "resource_types", "resource_ids",
                    "resource_attribute_conditions", "resource_ancestor_conditions",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def effect_badge(self, obj: PolicyModel) -> str:
        color = "green" if obj.effect == "PERMIT" else "red"
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>', color, obj.effect
        )

    effect_badge.short_description = "Effect"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# AuditLogModel admin (read-only)
# ---------------------------------------------------------------------------

@admin.register(AuditLogModel)
class AuditLogAdmin(admin.ModelAdmin[AuditLogModel]):
    list_display = (
        "timestamp",
        "effect_badge",
        "subject_id",
        "action",
        "resource_type",
        "resource_id",
        "ip_address",
        "evaluation_time_ms",
    )
    list_filter = ("effect", "resource_type", "action")
    search_fields = ("subject_id", "action", "resource_id", "request_id", "denied_by")
    readonly_fields: ClassVar[list[Any]] = [f.name for f in AuditLogModel._meta.fields]
    ordering = ("-timestamp",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False

    def effect_badge(self, obj: AuditLogModel) -> str:
        color = "green" if obj.effect == "PERMIT" else "red"
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>', color, obj.effect
        )

    effect_badge.short_description = "Effect"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# PolicyVersionModel admin (read-only)
# ---------------------------------------------------------------------------

@admin.register(PolicyVersionModel)
class PolicyVersionAdmin(admin.ModelAdmin[PolicyVersionModel]):
    list_display = ("policy_id", "version", "created_by", "created_at", "change_reason")
    list_filter = ("created_by",)
    search_fields = ("policy_id", "created_by", "change_reason")
    readonly_fields: ClassVar[list[Any]] = [f.name for f in PolicyVersionModel._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False
