from copy import deepcopy
from datetime import timedelta

import pytest
from django.db import transaction
from django.utils import timezone


def receipt():
    return {
        'schema_version': 'participant-operation-audit-v1',
        'request_key': 'a' * 64, 'operation': 'CREATE_USER',
        'outcome': 'SUCCESS', 'reason_code': 'CREATED',
        'targets': [{'target_user_ref': 1, 'target_membership_ref': 2,
                     'before_active': None, 'after_active': True,
                     'outcome': 'SUCCESS', 'reason_code': 'CREATED'}],
    }


def test_operation_details_accepts_only_versioned_allowlisted_shape():
    from competitions.participant_audit import validate_operation_details
    details = receipt()
    validated = validate_operation_details(details)
    assert validated == details
    validated['targets'][0]['after_active'] = False
    assert details['targets'][0]['after_active'] is True


@pytest.mark.parametrize('alter', [
    lambda d: d.update(password='secret'),
    lambda d: d.update(hash='encoded'),
    lambda d: d.update(preview_ref='ref'),
    lambda d: d.update(raw_csv='rows'),
    lambda d: d.update(message='arbitrary'),
    lambda d: d.pop('schema_version'),
    lambda d: d.update(schema_version='unknown'),
    lambda d: d.update(operation='DRAFT_CSV_CREATE'),
    lambda d: d.update(outcome='DENIED'),
    lambda d: d.update(reason_code='PERMISSION_DENIED'),
    lambda d: d.update(request_key='not-a-digest'),
    lambda d: d.update(targets=[]),
    lambda d: d['targets'][0].update(target_user_ref=True),
    lambda d: d['targets'][0].update(target_membership_ref=-1),
    lambda d: d['targets'][0].update(after_active='true'),
    lambda d: d['targets'][0].update(password_hash='encoded'),
    lambda d: d['targets'][0].update(outcome='DENIED'),
    lambda d: d.update(operation='DEACTIVATE'),
])
def test_invalid_audit_shape_is_rejected(alter):
    from competitions.participant_audit import validate_operation_details
    details = deepcopy(receipt())
    alter(details)
    with pytest.raises(ValueError):
        validate_operation_details(details)


@pytest.mark.django_db(transaction=True)
def test_success_audit_requires_transaction_and_rollback():
    from accounts.models import User
    from competitions.models import BulkImportBatch, CompetitionEvent
    from competitions.participant_audit import _record_operation
    now = timezone.now()
    actor = User.objects.create_user('dev', role='DEVELOPER')
    event = CompetitionEvent.objects.create(
        name='审计', event_code='AUDIT', competition_date=now.date(),
        starts_at=now, ends_at=now + timedelta(days=1),
    )
    kwargs = dict(actor=actor, event=event, details=receipt(), row_count=1,
                  created_count=1, source_filename='../../teams.csv')
    with pytest.raises(ValueError, match='TRANSACTION_REQUIRED'):
        _record_operation(**kwargs)
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            batch = _record_operation(**kwargs)
            assert batch.success and batch.source_filename == 'teams.csv'
            assert batch.operation_details_json == receipt()
            raise RuntimeError('rollback')
    assert not BulkImportBatch.objects.exists()
    with transaction.atomic():
        _record_operation(**kwargs)
    assert BulkImportBatch.objects.count() == 1


@pytest.mark.django_db
def test_legacy_batch_details_remain_empty():
    from competitions.models import BulkImportBatch
    assert BulkImportBatch._meta.get_field('operation_details_json').get_default() == {}
