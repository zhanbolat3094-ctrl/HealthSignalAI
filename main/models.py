from django.conf import settings
from django.db import models


class Note(models.Model):
    title = models.CharField(max_length=120)
    content = models.TextField(blank=True)
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["is_done", "-created_at"]

    def __str__(self) -> str:
        return self.title


class AssessmentReport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_reports",
    )
    payload = models.JSONField()
    ai_report = models.TextField()
    pdf_file = models.FileField(upload_to="assessment_reports/%Y/%m/%d/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"AssessmentReport #{self.pk} for {self.user}"
