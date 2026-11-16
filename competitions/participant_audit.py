"""参赛资格业务 receipt；不是拒绝访问或原始请求的日志。"""
from copy import deepcopy
import re

from django.db import connection

from .models import BulkImportBatch


def safe_filename(value):
    name = str(value).replace('\\', '/').rsplit('/', 1)[-1]
    return ''.join(c for c in name if c.isprintable())[:255] or 'upload.csv'


def validate_operation_details(details):
    def invalid():
        raise ValueError('INVALID_OPERATION_DETAILS')

    keys = {'schema_version', 'request_key', 'operation', 'outcome', 'reason_code', 'targets'}
    if type(details) is not dict or set(details) != keys:
        invalid()
    if details['schema_version'] != 'participant-operation-audit-v1':
        invalid()
    if type(details['request_key']) is not str or not re.fullmatch('[a-f0-9]{64}', details['request_key']):
        invalid()
    reasons = {
        'CREATE_USER': {'CREATED'}, 'JOIN_EXISTING': {'JOINED', 'ALREADY_ACTIVE', 'REACTIVATED'},
        'REACTIVATE': {'REACTIVATED', 'ALREADY_ACTIVE'},
        'DEACTIVATE': {'DEACTIVATED', 'ALREADY_INACTIVE'},
    }
    operation = details['operation']
    if type(operation) is not str or operation not in reasons:
        invalid()
    if details['outcome'] not in ('SUCCESS', 'NOOP') or details['reason_code'] not in reasons[operation]:
        invalid()
    targets = details['targets']
    if type(targets) is not list or not 1 <= len(targets) <= 99:
        invalid()
    if operation != 'CREATE_USER' and len(targets) != 1:
        invalid()
    target_keys = {'target_user_ref', 'target_membership_ref', 'before_active', 'after_active', 'outcome', 'reason_code'}
    for target in targets:
        if type(target) is not dict or set(target) != target_keys:
            invalid()
        for key in ('target_user_ref', 'target_membership_ref'):
            if type(target[key]) is not int or target[key] < 1:
                invalid()
        for key in ('before_active', 'after_active'):
            if target[key] is not None and type(target[key]) is not bool:
                invalid()
        if target['outcome'] != details['outcome'] or target['reason_code'] != details['reason_code']:
            invalid()
        reason = target['reason_code']
        expected = {
            'CREATED': (None, True), 'JOINED': (None, True),
            'REACTIVATED': (False, True), 'DEACTIVATED': (True, False),
            'ALREADY_ACTIVE': (True, True), 'ALREADY_INACTIVE': (False, False),
        }[reason]
        if (target['before_active'], target['after_active']) != expected:
            invalid()
        if (target['outcome'] == 'NOOP') != reason.startswith('ALREADY_'):
            invalid()
    return deepcopy(details)


def _record_operation(*, actor, event, details, row_count, created_count, source_filename):
    if not connection.in_atomic_block:
        raise ValueError('TRANSACTION_REQUIRED')
    validated = validate_operation_details(details)
    expected_created = len(validated['targets']) if validated['operation'] == 'CREATE_USER' else 0
    if type(row_count) is not int or row_count != len(validated['targets']):
        raise ValueError('INVALID_AUDIT_COUNTS')
    if type(created_count) is not int or created_count != expected_created:
        raise ValueError('INVALID_AUDIT_COUNTS')
    return BulkImportBatch.objects.create(
        actor=actor, event=event, source_filename=safe_filename(source_filename),
        row_count=row_count, success=True, created_account_count=created_count,
        validation_error_codes=[], operation_details_json=validated,
    )
