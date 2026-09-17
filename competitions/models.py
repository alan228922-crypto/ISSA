from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# 閱讀提示：這裡保存競賽活動、活動成員，以及批次建立帳戶的紀錄。


class CompetitionEvent(models.Model):
    # 活動狀態會影響目前能做的事情，例如是否可以建立參賽帳戶。
    class Status(models.TextChoices):
        DRAFT='DRAFT','草稿'
        ACTIVE='ACTIVE','进行中'
        FINISHED_GRACE='FINISHED_GRACE','赛后宽限期'
        PURGED='PURGED','已清理'

    name=models.CharField(max_length=200)
    competition_date=models.DateField()
    event_code=models.CharField(max_length=64,unique=True)
    starts_at=models.DateTimeField()
    ends_at=models.DateTimeField()
    purge_at=models.DateTimeField(editable=False)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.DRAFT)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def clean(self):
        if self.ends_at and self.starts_at and self.ends_at < self.starts_at:
            raise ValidationError({'ends_at':'结束时间不得早于开始时间。'})

    def save(self,*args,**kwargs):
        if self.ends_at:
            self.purge_at=self.ends_at+timedelta(days=7)
        self.full_clean()
        return super().save(*args,**kwargs)


class EventMembership(models.Model):
    # 這筆資料表示某位使用者在某場活動中的身分，以及該身分是否仍有效。
    class Type(models.TextChoices):
        PARTICIPANT='PARTICIPANT','参赛队伍'
        MANAGER='MANAGER','赛事管理员'

    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    event=models.ForeignKey(CompetitionEvent,on_delete=models.CASCADE)
    membership_type=models.CharField(max_length=16,choices=Type.choices)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','event','membership_type'],name='unique_event_membership_type')]


class BulkImportBatch(models.Model):
    # 保存 CSV 批次處理的結果，但不保存隊長學號等敏感輸入內容。
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    event=models.ForeignKey(CompetitionEvent,on_delete=models.PROTECT)
    source_filename=models.CharField(max_length=255)
    row_count=models.PositiveIntegerField()
    success=models.BooleanField()
    created_account_count=models.PositiveIntegerField(default=0)
    validation_error_codes=models.JSONField(default=list)
    created_at=models.DateTimeField(auto_now_add=True)
