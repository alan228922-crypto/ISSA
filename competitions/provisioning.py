"""DRAFT CSV 兼容入口；统一服务持有凭证与变更 authority。"""
from django.views.decorators.debug import sensitive_variables

from accounts.models import User
from .participant_services import ParticipantManagementError, confirm_participant_change, preview_csv_participants


class ProvisioningError(ParticipantManagementError):
    pass


@sensitive_variables()
def preview_team_import(actor, event, source_filename, csv_text, requested_role=User.Role.USER):
    if requested_role != User.Role.USER:
        raise ProvisioningError('ROLE_NOT_ALLOWED', 403)
    try:
        return preview_csv_participants(actor=actor, event_id=event.pk, source_filename=source_filename, csv_text=csv_text)
    except ParticipantManagementError as exc:
        raise ProvisioningError(exc.code, exc.status_code) from None


@sensitive_variables()
def confirm_team_import(actor, event, preview_ref):
    try:
        return confirm_participant_change(actor=actor, event_id=event.pk, operation='DRAFT_CSV_CREATE', preview_ref=preview_ref)
    except ParticipantManagementError as exc:
        raise ProvisioningError(exc.code, exc.status_code) from None
