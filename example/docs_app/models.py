"""Document model for the example app."""
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Document(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    classification = models.CharField(
        max_length=50,
        choices=[
            ("public", "Public"),
            ("internal", "Internal"),
            ("confidential", "Confidential"),
        ],
        default="internal",
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "example_document"

    def __str__(self) -> str:
        return f"{self.title} ({self.classification})"
