"""参赛资格唯一变更边界：重新授权、Event 串行化、原子 receipt/preview。"""
import hashlib
import time

from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from accounts.models import User
from .authorization import participant_management_error
from .models import BulkImportBatch, CompetitionEvent, EventMembership
from .participant_audit import _record_operation, safe_filename
from .participant_inputs import create_target, csv_targets
from .participant_previews import consume_preview, create_preview, load_preview


class ParticipantManagementError(ValueError):
    def __init__(self, code, status_code=400):
        self.code, self.status_code = code, status_code
        super().__init__(code)


def _context(actor, event_id, operation):
    if not getattr(actor, 'is_authenticated', False) or not getattr(actor, 'is_active', False):
        raise ParticipantManagementError('PERMISSION_DENIED', 403)
    current_actor = User.objects.filter(pk=actor.pk).first()
    event = CompetitionEvent.objects.filter(pk=event_id).first()
    if current_actor is None or event is None:
        raise ParticipantManagementError('PERMISSION_DENIED', 403)
    if event.status == CompetitionEvent.Status.PURGED:
        raise ParticipantManagementError('EVENT_PURGED', 403)
    error = participant_management_error(actor=current_actor, event=event, operation=operation, now=timezone.now())
    if error:
        raise ParticipantManagementError(error, 403 if error != 'INVALID_PROVISIONING_ROW' else 400)
    return current_actor, event


def _preview_result(actor, event, operation, targets, errors, source_filename):
    ref = create_preview(actor=actor, event=event, operation=operation, targets=targets,
                         source_filename=source_filename) if not errors else None
    return {'rows': [{'username': target['username'], 'action': operation} for target in targets],
            'errors': errors, 'preview_ref': ref,
            'audit': {'source_filename': source_filename, 'row_count': len(targets), 'error_codes': errors}}


@sensitive_variables()
def preview_csv_participants(*, actor, event_id, source_filename, csv_text):
    actor, event = _context(actor, event_id, 'DRAFT_CSV_CREATE')
    targets, errors = csv_targets(event, csv_text)
    return _preview_result(actor, event, 'DRAFT_CSV_CREATE', targets, errors, safe_filename(source_filename))


def _safe_target(user, event):
    if user is None:
        raise ParticipantManagementError('MEMBERSHIP_NOT_FOUND')
    if not user.is_active:
        raise ParticipantManagementError('ACCOUNT_INACTIVE')
    if user.role != User.Role.USER or EventMembership.objects.filter(
        user=user, event=event, membership_type='MANAGER', is_active=True,
    ).exists():
        raise ParticipantManagementError('USER_ROLE_CONFLICT')


def _target_facts(user, event):
    membership = EventMembership.objects.filter(user=user, event=event, membership_type='PARTICIPANT').first()
    # 单笔资格变更的 SUCCESS receipt 是现有的单调 marker；NOOP 不改变状态。
    # CREATE/CSV 不会修改已存在的 Membership，故不参与此 marker。
    last_change = BulkImportBatch.objects.filter(
        event=event, success=True,
        operation_details_json__schema_version='participant-operation-audit-v1',
        operation_details_json__operation__in=['JOIN_EXISTING', 'REACTIVATE', 'DEACTIVATE'],
        operation_details_json__outcome='SUCCESS',
        operation_details_json__targets__0__target_membership_ref=membership.pk,
    ).order_by('-pk').values_list('pk', flat=True).first() if membership else None
    return {
        'user_ref': user.pk, 'username': user.username, 'role': user.role, 'active': user.is_active,
        'membership_ref': membership.pk if membership else None,
        'membership_active': membership.is_active if membership else None,
        'qualification_change_ref': last_change,
    }, membership


@sensitive_variables()
def preview_participant_change(*, actor, event_id, operation, fields):
    actor, event = _context(actor, event_id, operation)
    if operation == 'DRAFT_CSV_CREATE' or type(fields) is not dict:
        raise ParticipantManagementError('INVALID_PROVISIONING_ROW')
    if operation == 'CREATE_USER':
        try:
            target = create_target(event, fields)
        except ValueError as exc:
            raise ParticipantManagementError(str(exc)) from None
    else:
        if operation == 'JOIN_EXISTING':
            if set(fields) != {'username', 'same_team_verified'} or fields['same_team_verified'] is not True or type(fields['username']) is not str:
                raise ParticipantManagementError('INVALID_PROVISIONING_ROW')
            user = User.objects.filter(username=fields['username']).first()
        else:
            confirmation = 'same_team_verified' if operation == 'REACTIVATE' else 'confirmed'
            if set(fields) != {'membership_id', confirmation} or fields[confirmation] is not True or type(fields['membership_id']) is not int:
                raise ParticipantManagementError('INVALID_PROVISIONING_ROW')
            membership = EventMembership.objects.filter(pk=fields['membership_id'], event=event, membership_type='PARTICIPANT').select_related('user').first()
            if membership is None:
                raise ParticipantManagementError('MEMBERSHIP_NOT_FOUND')
            user = membership.user
        _safe_target(user, event)
        facts, _ = _target_facts(user, event)
        target = {'username': user.username, 'user_ref': user.pk, 'expected': facts}
    return _preview_result(actor, event, operation, [target], [], 'single-entry')


@sensitive_variables()
def _apply_target(event, operation, target):
    if operation in {'CREATE_USER', 'DRAFT_CSV_CREATE'}:
        if User.objects.filter(username=target['username']).exists():
            raise ParticipantManagementError('PREVIEW_STATE_CHANGED')
        user = User.objects.create(username=target['username'], password=target['password_hash'],
                                   role=User.Role.USER, must_change_password=True)
        membership = EventMembership.objects.create(user=user, event=event, membership_type='PARTICIPANT')
        before, after, reason = None, True, 'CREATED'
    else:
        user = User.objects.filter(pk=target['user_ref']).first()
        _safe_target(user, event)
        facts, membership = _target_facts(user, event)
        if facts != target['expected']:
            raise ParticipantManagementError('PREVIEW_STATE_CHANGED')
        before = membership.is_active if membership else None
        after = operation != 'DEACTIVATE'
        if before is after:
            reason = 'ALREADY_ACTIVE' if after else 'ALREADY_INACTIVE'
        elif membership is None:
            if operation != 'JOIN_EXISTING':
                raise ParticipantManagementError('PREVIEW_STATE_CHANGED')
            membership = EventMembership.objects.create(user=user, event=event, membership_type='PARTICIPANT')
            reason = 'JOINED'
        else:
            membership.is_active = after
            membership.save(update_fields=['is_active'])
            reason = 'REACTIVATED' if after else 'DEACTIVATED'
    return {'target_user_ref': user.pk, 'target_membership_ref': membership.pk,
            'before_active': before, 'after_active': after,
            'outcome': 'NOOP' if before is after else 'SUCCESS', 'reason_code': reason}


def _result(receipt):
    details = receipt.operation_details_json
    return {'outcome': details['outcome'], 'created_count': receipt.created_account_count,
            'changed_membership_count': sum(target['before_active'] != target['after_active'] for target in details['targets'])}


@sensitive_variables()
def _confirm_once(actor, event_id, operation, preview_ref):
    with transaction.atomic():
        CompetitionEvent.objects.filter(pk=event_id).update(status=F('status'))
        row, state = load_preview(preview_ref)
        if not state or (state.get('actor_ref'), state.get('event_ref'), state.get('operation')) != (actor.pk, event_id, operation):
            raise ParticipantManagementError('INVALID_PREVIEW')
        if timezone.now().timestamp() >= state['expires_at'] or timezone.now() >= row.expire_date:
            row.delete()
            return ParticipantManagementError('EXPIRED_PREVIEW')
        actor, event = _context(actor, event_id, operation)
        request_key = hashlib.sha256(preview_ref.encode('ascii')).hexdigest()
        if state.get('stage') == 'CONSUMED':
            receipt = BulkImportBatch.objects.filter(pk=state.get('receipt_ref'), actor=actor, event=event).first()
            if not receipt or receipt.operation_details_json.get('request_key') != request_key:
                raise ParticipantManagementError('INVALID_PREVIEW')
            expected_operation = 'CREATE_USER' if operation == 'DRAFT_CSV_CREATE' else operation
            if receipt.operation_details_json.get('operation') != expected_operation:
                raise ParticipantManagementError('INVALID_PREVIEW')
            for target in receipt.operation_details_json['targets']:
                user = User.objects.filter(pk=target['target_user_ref']).first()
                _safe_target(user, event)
                if not EventMembership.objects.filter(pk=target['target_membership_ref'], event=event, user=user, membership_type='PARTICIPANT').exists():
                    raise ParticipantManagementError('PREVIEW_STATE_CHANGED')
            return _result(receipt)
        if state.get('stage') != 'PENDING' or state.get('competition_date') != event.competition_date.isoformat():
            raise ParticipantManagementError('PREVIEW_STATE_CHANGED')
        targets = [_apply_target(event, operation, target) for target in state['targets']]
        business_operation = 'CREATE_USER' if operation == 'DRAFT_CSV_CREATE' else operation
        details = {'schema_version': 'participant-operation-audit-v1', 'request_key': request_key,
                   'operation': business_operation, 'outcome': targets[0]['outcome'],
                   'reason_code': targets[0]['reason_code'], 'targets': targets}
        receipt = _record_operation(actor=actor, event=event, details=details, row_count=len(targets),
                                    created_count=len(targets) if business_operation == 'CREATE_USER' else 0,
                                    source_filename=state['source_filename'])
        consume_preview(row, state, receipt)
        return _result(receipt)


@sensitive_variables()
def confirm_participant_change(*, actor, event_id, operation, preview_ref):
    if not getattr(actor, 'is_authenticated', False):
        raise ParticipantManagementError('PERMISSION_DENIED', 403)
    for attempt in range(5):
        try:
            result = _confirm_once(actor, event_id, operation, preview_ref)
            if isinstance(result, ParticipantManagementError):
                raise result
            return result
        except IntegrityError:
            raise ParticipantManagementError('PREVIEW_STATE_CHANGED') from None
        except OperationalError as exc:
            if not any(word in str(exc).lower() for word in ('locked', 'busy')):
                raise
            if attempt == 4:
                raise ParticipantManagementError('PARTICIPANT_MANAGEMENT_BUSY', 503) from None
            time.sleep(0.05 * (attempt + 1))
