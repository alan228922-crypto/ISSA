from django.conf import settings
from django.db import models

from analysis.models import AnalysisRun
from projects.models import Project


# 閱讀提示：這些資料保存學生的預測、結果揭示紀錄和分析後反思。


class Prediction(models.Model):
    # Prediction 先保存學生的預測，等模型分析完成後再與實際結果比較。
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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["DRAFT", "COMPLETED", "INVALIDATED"]),
                name="prediction_status_is_valid",
            ),
        ]


class StudentResultReveal(models.Model):
    # 每個模型版本只記錄第一次向學生揭示分析結果的時間和分析紀錄。
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


class Reflection(models.Model):
    # Reflection 保存學生看完結果後的想法，以及下一次修改模型的打算。
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        COMPLETED = "COMPLETED", "Completed"

    analysis_run = models.OneToOneField(
        AnalysisRun,
        on_delete=models.PROTECT,
        related_name="reflection",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reflections",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    original_reasoning = models.CharField(max_length=2000, blank=True, default="")
    unexpected_results = models.CharField(max_length=2000, blank=True, default="")
    next_iteration_intent = models.CharField(max_length=2000, blank=True, default="")
    reflection_schema_version = models.CharField(max_length=64, default="reflection-v1")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["DRAFT", "COMPLETED"]),
                name="reflection_status_is_valid",
            ),
        ]
