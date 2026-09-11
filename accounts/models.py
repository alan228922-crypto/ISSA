from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        DEVELOPER='DEVELOPER','开发者'
        MANAGER='MANAGER','管理员'
        USER='USER','用户'

    role=models.CharField(max_length=16,choices=Role.choices,default=Role.USER)
    must_change_password=models.BooleanField(default=False)
