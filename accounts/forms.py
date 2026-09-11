from django.contrib.auth.forms import PasswordChangeForm


class ForcedPasswordChangeForm(PasswordChangeForm):
    """使用 Django 正规改密与哈希流程，成功后解除首次改密状态。"""
