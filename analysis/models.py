from django.conf import settings
from django.db import models
from projects.models import Project

class ModelRevision(models.Model):
    # Revision 是某一版模型的固定副本。之後即使學生繼續編輯，也不會改變這次分析使用的資料。
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

class SolverVersion(models.Model):
    analysis_type=models.CharField(max_length=20,default='TRUSS_2D')
    solver_version=models.CharField(max_length=64,unique=True)
    input_schema_version=models.CharField(max_length=64,default='truss2d-input-v1')
    result_schema_version=models.CharField(max_length=64,default='truss2d-result-v1')
    build_reference=models.CharField(max_length=128,null=True,blank=True)
    activated_at=models.DateTimeField(auto_now_add=True)

class AnalysisRun(models.Model):
    class Status(models.TextChoices):
        PENDING='PENDING'; SUCCESS='SUCCESS'; VALIDATION_FAILED='VALIDATION_FAILED'; SOLVER_FAILED='SOLVER_FAILED'
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='analysis_runs')
    prediction=models.ForeignKey('learning.Prediction',on_delete=models.PROTECT,related_name='analysis_runs',null=True,blank=True)
    model_revision=models.ForeignKey(ModelRevision,on_delete=models.PROTECT,related_name='analysis_runs')
    analysis_type=models.CharField(max_length=20,default='TRUSS_2D')
    solver_version=models.ForeignKey(SolverVersion,on_delete=models.PROTECT,related_name='analysis_runs')
    input_schema_version=models.CharField(max_length=64)
    input_hash=models.CharField(max_length=64)
    status=models.CharField(max_length=32,choices=Status.choices,default=Status.PENDING)
    started_at=models.DateTimeField(auto_now_add=True); finished_at=models.DateTimeField(null=True,blank=True)
    solver_input_json=models.JSONField(); result_schema_version=models.CharField(max_length=64,null=True,blank=True)
    result_json=models.JSONField(null=True,blank=True); diagnostics_json=models.JSONField(default=dict); failure_code=models.CharField(max_length=128,null=True,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='analysis_runs')

    # AnalysisRun 記錄一次完整分析：使用哪個模型、哪個 Solver，以及最後得到什麼結果。

class ValidationLog(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='validation_logs')
    model_revision=models.ForeignKey(ModelRevision,on_delete=models.SET_NULL,null=True,blank=True)
    analysis_run=models.ForeignKey(AnalysisRun,on_delete=models.SET_NULL,null=True,blank=True)
    stage=models.CharField(max_length=32); code=models.CharField(max_length=128); severity=models.CharField(max_length=16)
    category=models.CharField(max_length=64,blank=True); entity_refs=models.JSONField(default=list); numeric_context=models.JSONField(default=dict); created_at=models.DateTimeField(auto_now_add=True)
