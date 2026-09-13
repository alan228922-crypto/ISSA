from django.conf import settings
from django.db import models

from analysis.models import AnalysisRun
from projects.models import Project


class Prediction(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        COMPLETED = "COMPLETED", "Completed"
        INVALIDATED = "INVALIDATED", "Invalidated"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="predictions")
    source_draft_version = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="predictions")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    invalidation_code = models.CharField(max_length=128, null=True, blank=True)
    prediction_schema_version = models.CharField(max_length=64, default="prediction-v1")
    payload_json = models.JSONField()


class StudentResultReveal(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="student_result_reveals")
    source_draft_version = models.PositiveIntegerField()
    first_analysis_run = models.ForeignKey(AnalysisRun, on_delete=models.PROTECT, related_name="student_result_reveals")
    revealed_to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="student_result_reveals")
    first_revealed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "source_draft_version"],
                name="unique_project_result_reveal_draft",
            ),
        ]
