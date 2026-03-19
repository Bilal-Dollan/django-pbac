"""Example views demonstrating django-pbac decorator and mixin usage."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from django_pbac.core.models import Resource
from django_pbac.integration.decorators import require_policy
from django_pbac.integration.mixins import PBACQuerySetMixin, PBACViewMixin

from .models import Document


@require_policy(action="documents:read", resource_type="document")
def document_list(request: HttpRequest) -> JsonResponse:
    """Return all documents the user can read (engine filters via queryset)."""
    docs = Document.objects.all().values("id", "title", "classification")
    return JsonResponse({"documents": list(docs)})


@require_policy(action="documents:read", resource_type="document")
def document_detail(request: HttpRequest, pk: int) -> JsonResponse:
    doc = get_object_or_404(Document, pk=pk)
    return JsonResponse({"id": doc.pk, "title": doc.title, "body": doc.body})


class DocumentEditView(PBACViewMixin, View):
    """CBV that enforces documents:edit permission."""

    pbac_action = "documents:edit"
    pbac_resource_type = "document"

    def get_pbac_resource(self, request: HttpRequest, **kwargs) -> Resource:
        doc = get_object_or_404(Document, pk=kwargs["pk"])
        return Resource(
            id=f"doc:{doc.pk}",
            type="document",
            attributes={
                "owner": f"user:{doc.owner_id}",
                "classification": doc.classification,
            },
        )

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        doc = get_object_or_404(Document, pk=pk)
        doc.title = request.POST.get("title", doc.title)
        doc.save()
        return HttpResponse("Updated")
