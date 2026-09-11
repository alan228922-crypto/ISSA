from django.conf import settings
from django.db import models
from projects.models import Project

class ModelRevision(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='model_revisions')
    revision_number=models.PositiveIntegerField()
    analysis_type=models.CharField(max_length=20)
    source_draft_version=models.PositiveIntegerField()
    physical_snapshot_schema_version=models.CharField(max_length=64)
    physical_snapshot_json=models.JSONField()
    model_hash=models.CharField(max_length=64)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='model_revisions')
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['project','revision_number'],name='unique_project_revision_number')]
