from django.conf import settings
from django.db import models

from competitions.models import CompetitionEvent


class Project(models.Model):
    class AnalysisType(models.TextChoices):
        TRUSS_2D = "TRUSS_2D", "二维桁架"
        FRAME_2D = "FRAME_2D", "二维刚架"

    event = models.ForeignKey(CompetitionEvent, on_delete=models.CASCADE, related_name="projects")
    owner_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=200)
    analysis_type = models.CharField(max_length=20, choices=AnalysisType.choices, default=AnalysisType.TRUSS_2D)
    draft_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ProjectOperationalPurgeAudit(models.Model):
    """Minimal durable purge receipt; no FK or payload from deleted operational data."""

    project_id = models.PositiveBigIntegerField(unique=True)
    event_id = models.PositiveBigIntegerField()
    actor_id = models.PositiveBigIntegerField(null=True, blank=True)
    purged_at = models.DateTimeField(auto_now_add=True)
    deletion_counts_json = models.JSONField()
