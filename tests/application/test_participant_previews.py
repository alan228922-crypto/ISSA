import json
import re
from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core import signing
from django.core.management import call_command
from django.utils import timezone

from accounts.models import User
from competitions.models import BulkImportBatch, CompetitionEvent, EventMembership
from competitions.provisioning import ProvisioningError, confirm_team_import, preview_team_import

SECRET = 'SYNTHETIC-M8-CREDENTIAL-CANARY'


@pytest.fixture
def context(db):
    now = timezone.now()
    event = CompetitionEvent.objects.create(name='预览', event_code='PREVIEW', competition_date=now.date(),
                                            starts_at=now, ends_at=now + timedelta(days=1))
    actor = User.objects.create_user('manager', role='MANAGER')
    EventMembership.objects.create(user=actor, event=event, membership_type='MANAGER')
    return actor, event


def preview(context, number=1):
    actor, event = context
    return preview_team_import(actor, event, '../../teams.csv',
                               f'team_number,captain_student_id\n{number},{SECRET}\n')


def test_preview_response_contains_only_opaque_reference(context, caplog):
    result = preview(context)
    assert set(result) == {'rows', 'errors', 'preview_ref', 'audit'}
    ref = result['preview_ref']
    assert re.fullmatch('[a-z0-9]{32}', ref)
    assert SECRET not in json.dumps(result)
    with pytest.raises(signing.BadSignature):
        signing.loads(ref, salt='team-import')
    stored = Session.objects.get(session_key=ref).get_decoded()
    assert set(stored) == {'participant_preview'}
    state = stored['participant_preview']
    assert state['schema_version'] == 'participant-preview-v1'
    assert check_password(SECRET, state['targets'][0]['password_hash'])
    assert SECRET not in json.dumps(stored)
    assert SECRET not in caplog.text
    assert not BulkImportBatch.objects.exists()


def test_tabs_and_consumed_retry_are_independent_and_hash_free(context):
    first, second = preview(context), preview(context, 2)
    assert first['preview_ref'] != second['preview_ref']
    actor, event = context
    result = confirm_team_import(actor, event, first['preview_ref'])
    assert confirm_team_import(actor, event, first['preview_ref']) == result
    state = Session.objects.get(session_key=first['preview_ref']).get_decoded()['participant_preview']
    assert state['stage'] == 'CONSUMED'
    assert 'password_hash' not in json.dumps(state)
    assert BulkImportBatch.objects.count() == 1
    assert Session.objects.get(session_key=second['preview_ref']).get_decoded()['participant_preview']['stage'] == 'PENDING'
    assert SECRET not in str(list(BulkImportBatch.objects.values()))


@pytest.mark.parametrize('tamper', ['actor', 'event', 'operation', 'old-token', 'invalid'])
def test_preview_binding_rejects_tampering_without_consuming(context, tamper):
    actor, event = context
    ref = preview(context)['preview_ref']
    if tamper == 'actor':
        actor = User.objects.create_user('other-dev', role='DEVELOPER')
    elif tamper == 'event':
        event = CompetitionEvent.objects.create(name='另一场', event_code='OTHER', competition_date=event.competition_date,
                                                starts_at=event.starts_at, ends_at=event.ends_at)
        EventMembership.objects.create(user=actor, event=event, membership_type='MANAGER')
    elif tamper == 'operation':
        from competitions.participant_services import ParticipantManagementError, confirm_participant_change
        with pytest.raises(ParticipantManagementError):
            confirm_participant_change(actor=actor, event_id=event.pk, operation='CREATE_USER', preview_ref=ref)
        assert BulkImportBatch.objects.count() == 0
        return
    elif tamper == 'old-token':
        ref = signing.dumps({'event_id': event.pk, 'rows': [{'captain_student_id': SECRET}]}, salt='team-import')
    else:
        ref = 'not-a-reference'
    with pytest.raises(ProvisioningError):
        confirm_team_import(actor, event, ref)
    assert BulkImportBatch.objects.count() == 0
    assert not User.objects.filter(username__startswith=f'{event.competition_date:%Y%m%d}').exists()


def expire(ref):
    row = Session.objects.get(session_key=ref)
    data = row.get_decoded()
    data['participant_preview']['expires_at'] = (timezone.now() - timedelta(seconds=1)).timestamp()
    row.session_data = SessionStore().encode(data)
    row.expire_date = timezone.now() - timedelta(seconds=1)
    row.save()


def test_encountered_expired_preview_refuses_and_removes_credentials(context):
    actor, event = context
    ref = preview(context)['preview_ref']
    expire(ref)
    with pytest.raises(ProvisioningError, match='EXPIRED_PREVIEW'):
        confirm_team_import(actor, event, ref)
    row = Session.objects.filter(session_key=ref).first()
    assert row is None or 'password_hash' not in json.dumps(row.get_decoded())
    assert not BulkImportBatch.objects.exists()


def test_abandoned_expired_preview_is_physically_removed_by_clearsessions(context):
    ref = preview(context)['preview_ref']
    expire(ref)
    assert Session.objects.filter(session_key=ref).exists()
    call_command('clearsessions', verbosity=0)
    assert not Session.objects.filter(session_key=ref).exists()


def test_exact_expiry_is_access_cutoff_and_cleanup_survives_refusal(context, monkeypatch):
    actor, event = context
    ref = preview(context)['preview_ref']
    row = Session.objects.get(session_key=ref)
    from datetime import datetime, timezone as utc
    cutoff = row.get_decoded()['participant_preview']['expires_at']
    monkeypatch.setattr('competitions.participant_services.timezone.now', lambda: datetime.fromtimestamp(cutoff, utc.utc))
    with pytest.raises(ProvisioningError, match='EXPIRED_PREVIEW'):
        confirm_team_import(actor, event, ref)
    assert not Session.objects.filter(session_key=ref).exists()


def test_expired_owned_credentials_are_removed_even_after_event_closes(context):
    actor, event = context
    ref = preview(context)['preview_ref']
    expire(ref)
    CompetitionEvent.objects.filter(pk=event.pk).update(status='FINISHED_GRACE')
    with pytest.raises(ProvisioningError):
        confirm_team_import(actor, event, ref)
    assert not Session.objects.filter(session_key=ref).exists()


def test_consumption_failure_rolls_back_credential_and_business_state(context, monkeypatch):
    actor, event = context
    ref = preview(context)['preview_ref']
    from competitions import participant_services
    original = participant_services.consume_preview
    def fail(*args):
        raise RuntimeError('synthetic consume failure')
    monkeypatch.setattr(participant_services, 'consume_preview', fail)
    with pytest.raises(RuntimeError):
        confirm_team_import(actor, event, ref)
    assert User.objects.count() == 1 and not BulkImportBatch.objects.exists()
    state = Session.objects.get(session_key=ref).get_decoded()['participant_preview']
    assert state['stage'] == 'PENDING'
    monkeypatch.setattr(participant_services, 'consume_preview', original)
    assert confirm_team_import(actor, event, ref)['created_count'] == 1


@pytest.mark.parametrize('text', [
    '', 'team_number,captain_student_id\n', 'team_number\n1\n',
    'team_number,captain_student_id,role\n1,secret,MANAGER\n',
    'team_number,captain_student_id\n1,a\n01,b\n',
    'team_number,captain_student_id\n١,a\n',
    'team_number,captain_student_id\n1,\n',
    'team_number,captain_student_id\n1,' + 'a' * 129 + '\n',
    'team_number,captain_student_id\n' + ''.join(f'{i},a\n' for i in range(1, 101)),
    'team_number,captain_student_id\n1,' + 'a' * (1024 * 1024),
], ids=['empty', 'header-only', 'missing-column', 'extra-column', 'normalized-duplicate',
        'non-ascii-number', 'missing-secret', 'long-secret', 'row-limit', 'byte-limit'])
def test_invalid_csv_creates_no_confirmable_preview_or_business_receipt(context, text):
    actor, event = context
    result = preview_team_import(actor, event, 'teams.csv', text)
    assert result['errors']
    assert result['preview_ref'] is None
    assert not Session.objects.exists()
    assert not BulkImportBatch.objects.exists()


@pytest.mark.parametrize('change', ['revoke', 'disable', 'grace', 'purged', 'active'])
def test_confirm_reauthorizes_after_preview(context, change):
    actor, event = context
    ref = preview(context)['preview_ref']
    if change == 'revoke':
        EventMembership.objects.filter(user=actor).update(is_active=False)
    elif change == 'disable':
        User.objects.filter(pk=actor.pk).update(is_active=False)
    else:
        CompetitionEvent.objects.filter(pk=event.pk).update(status={
            'grace': 'FINISHED_GRACE', 'purged': 'PURGED', 'active': 'ACTIVE',
        }[change])
    with pytest.raises(ProvisioningError):
        confirm_team_import(actor, event, ref)
    assert not BulkImportBatch.objects.exists()


def test_row_two_failure_rolls_back_users_memberships_audit_and_consumption(context, monkeypatch):
    actor, event = context
    result = preview_team_import(actor, event, 'teams.csv', 'team_number,captain_student_id\n1,a\n2,b\n')
    original = EventMembership.objects.create
    def fail_second(**kwargs):
        if kwargs['user'].username.endswith('02'):
            raise RuntimeError('synthetic failure')
        return original(**kwargs)
    monkeypatch.setattr(EventMembership.objects, 'create', fail_second)
    with pytest.raises(RuntimeError):
        confirm_team_import(actor, event, result['preview_ref'])
    assert User.objects.count() == 1
    assert not BulkImportBatch.objects.exists()
    assert Session.objects.get(session_key=result['preview_ref']).get_decoded()['participant_preview']['stage'] == 'PENDING'
