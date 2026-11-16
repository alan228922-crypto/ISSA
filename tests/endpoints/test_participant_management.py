import re
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import User
from competitions.models import BulkImportBatch, CompetitionEvent, EventMembership


@pytest.fixture
def management(client, db):
    now = timezone.now()
    event = CompetitionEvent.objects.create(name='HTTP赛事', event_code='HTTP', competition_date=now.date(),
                                            starts_at=now, ends_at=now + timedelta(days=1))
    actor = User.objects.create_user('manager', role='MANAGER')
    EventMembership.objects.create(user=actor, event=event, membership_type='MANAGER')
    client.force_login(actor)
    return client, actor, event


def test_csv_public_preview_contains_no_credential_and_confirms_opaque_reference(management):
    client, actor, event = management
    canary = 'HTTP-SYNTHETIC-SECRET'
    response = client.post(f'/competitions/{event.pk}/accounts/preview/', {
        'csv_file': SimpleUploadedFile('teams.csv', f'team_number,captain_student_id\n1,{canary}\n'.encode()),
    })
    html = response.content.decode()
    assert response.status_code == 200
    assert canary not in html and 'name="token"' not in html
    ref = re.search(r'name="preview_ref" value="([a-z0-9]{32})"', html).group(1)
    response = client.post(f'/competitions/{event.pk}/accounts/confirm/', {'preview_ref': ref})
    assert response.status_code in {200, 302}
    assert BulkImportBatch.objects.count() == 1


def test_csv_errors_are_safe_and_old_token_field_is_rejected(management):
    client, actor, event = management
    response = client.post(f'/competitions/{event.pk}/accounts/confirm/', {'token': 'obsolete-secret'})
    assert response.status_code == 400
    assert 'obsolete-secret' not in response.content.decode()
    response = client.post(f'/competitions/{event.pk}/accounts/preview/', {
        'csv_file': SimpleUploadedFile('teams.csv', b'\xff\xfe'),
    })
    assert response.status_code == 400
    assert 'UnicodeDecodeError' not in response.content.decode()
    assert not BulkImportBatch.objects.exists()


def test_authorized_landing_has_management_entry_and_create_preview_prg(management):
    client, actor, event = management
    CompetitionEvent.objects.filter(pk=event.pk).update(status='ACTIVE')
    base = f'/competitions/{event.pk}'
    landing = client.get('/events/')
    assert f'{base}/manage/' in landing.content.decode()
    assert client.get(base + '/manage/').status_code == 200
    form = client.get(base + '/participants/new/')
    assert form.status_code == 200
    response = client.post(base + '/participants/new/', {'team_number': '4', 'captain_student_id': 'synthetic-secret'})
    assert response.status_code == 200
    html = response.content.decode()
    assert 'synthetic-secret' not in html and 'password_hash' not in html
    assert User.objects.count() == 1 and not BulkImportBatch.objects.exists()
    ref = re.search(r'name="preview_ref" value="([a-z0-9]{32})"', html).group(1)
    response = client.post(base + '/participants/confirm/', {'operation': 'CREATE_USER', 'preview_ref': ref})
    assert response.status_code == 302 and response.url == base + '/participants/'
    assert client.get(response.url).status_code == 200
    assert client.get(response.url).status_code == 200 and BulkImportBatch.objects.count() == 1


def test_join_reactivate_deactivate_use_scoped_explicit_preview(management):
    client, actor, event = management
    target = User.objects.create_user('existing-team', password='unchanged')
    base = f'/competitions/{event.pk}/participants'
    before = target.password
    for operation, path, fields in [
        ('JOIN_EXISTING', '/join/', {'username': target.username, 'same_team_verified': 'on'}),
        ('DEACTIVATE', None, {'confirmed': 'on'}),
        ('REACTIVATE', None, {'same_team_verified': 'on'}),
    ]:
        member = EventMembership.objects.filter(user=target, event=event).first()
        if path is None:
            path = f'/{member.pk}/{operation.lower()}/preview/'
        response = client.post(base + path, fields)
        assert response.status_code == 200
        ref = re.search(r'name="preview_ref" value="([a-z0-9]{32})"', response.content.decode()).group(1)
        assert client.post(base + '/confirm/', {'operation': operation, 'preview_ref': ref}).status_code == 302
    member.refresh_from_db()
    target.refresh_from_db()
    assert member.is_active and target.password == before
    assert EventMembership.objects.filter(user=target, event=event).count() == 1


@pytest.mark.parametrize('status,expected', [('FINISHED_GRACE', 200), ('PURGED', 403)])
def test_roster_lifecycle_is_readonly_or_denied(management, status, expected):
    client, actor, event = management
    CompetitionEvent.objects.filter(pk=event.pk).update(status=status)
    base = f'/competitions/{event.pk}/participants'
    response = client.get(base + '/')
    assert response.status_code == expected
    if expected == 200:
        html = response.content.decode()
        assert '只读' in html and '新增队伍' not in html and '加入既有账号' not in html
    assert client.post(base + '/new/', {'team_number': '1', 'captain_student_id': 'synthetic'}).status_code == 403
    assert not BulkImportBatch.objects.exists()


@pytest.mark.parametrize('actor_kind', ['ordinary', 'user-with-manager-membership', 'unassigned', 'inactive', 'mixed'])
def test_forged_direct_management_access_fails_closed(management, actor_kind):
    client, actor, event = management
    if actor_kind in {'ordinary', 'user-with-manager-membership'}:
        actor.role = 'USER'
        actor.save()
        if actor_kind == 'ordinary':
            EventMembership.objects.filter(user=actor).delete()
    elif actor_kind == 'unassigned':
        EventMembership.objects.filter(user=actor).update(is_active=False)
    elif actor_kind == 'inactive':
        actor.is_active = False
        actor.save()
    else:
        EventMembership.objects.create(user=actor, event=event, membership_type='PARTICIPANT')
    base = f'/competitions/{event.pk}'
    for path in ['/manage/', '/participants/', '/participants/new/', '/participants/join/']:
        assert client.get(base + path).status_code in {302, 403}
    assert client.post(base + '/participants/new/', {'team_number': '1', 'captain_student_id': 'synthetic'}).status_code in {302, 403}
    assert not BulkImportBatch.objects.exists()


def test_confirm_get_csrf_unknown_fields_and_unknown_operations_do_not_mutate(management):
    from django.test import Client
    client, actor, event = management
    path = f'/competitions/{event.pk}/participants/confirm/'
    assert client.get(path).status_code == 405
    assert client.post(path, {'operation': 'PROMOTE', 'preview_ref': 'a' * 32}).status_code == 400
    assert client.post(path, {'operation': 'CREATE_USER', 'preview_ref': 'a' * 32, 'role': 'DEVELOPER'}).status_code == 400
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(actor)
    assert csrf_client.post(path, {'operation': 'CREATE_USER', 'preview_ref': 'a' * 32}).status_code == 403
    assert not BulkImportBatch.objects.exists()


def test_unknown_exception_has_safe_copy_without_canary_or_traceback(management, monkeypatch, caplog):
    client, actor, event = management
    canary = 'SYNTHETIC-EXCEPTION-CREDENTIAL'
    def fail(**kwargs):
        raise RuntimeError(canary)
    monkeypatch.setattr('competitions.views.preview_participant_change', fail, raising=False)
    response = client.post(f'/competitions/{event.pk}/participants/new/', {
        'team_number': '1', 'captain_student_id': canary,
    })
    assert response.status_code == 500
    html = response.content.decode()
    assert '请' in html and canary not in html and 'Traceback' not in html
    assert canary not in caplog.text and not BulkImportBatch.objects.exists()


@pytest.mark.parametrize('code', [
    'PERMISSION_DENIED', 'ROLE_NOT_ALLOWED', 'EVENT_PURGED', 'EVENT_STATUS_NOT_ALLOWED',
    'EVENT_ACCESS_EXPIRED', 'PROVISIONING_STATUS_POLICY_GAP', 'INVALID_PROVISIONING_ROW',
    'DUPLICATE_INPUT', 'ACCOUNT_ALREADY_EXISTS', 'INVALID_PREVIEW', 'EXPIRED_PREVIEW',
    'PREVIEW_STATE_CHANGED', 'PARTICIPANT_MANAGEMENT_BUSY', 'USER_ROLE_CONFLICT',
    'ACCOUNT_INACTIVE', 'MEMBERSHIP_NOT_FOUND',
])
def test_known_service_error_is_safe_in_public_page(management, monkeypatch, caplog, code):
    from competitions.participant_services import ParticipantManagementError
    client, actor, event = management
    def fail(**kwargs):
        raise ParticipantManagementError(code, 403)
    monkeypatch.setattr('competitions.views.preview_participant_change', fail)
    response = client.post(f'/competitions/{event.pk}/participants/new/', {
        'team_number': '1', 'captain_student_id': 'SYNTHETIC-SECRET',
    })
    assert response.status_code == 403
    html = response.content.decode()
    assert '请' in html and code not in html and 'SYNTHETIC-SECRET' not in html
    assert 'Traceback' not in caplog.text and 'SYNTHETIC-SECRET' not in caplog.text


def test_noop_confirm_clearly_says_no_repeat_mutation(management):
    client, actor, event = management
    target = User.objects.create_user('already-participant')
    EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT')
    base = f'/competitions/{event.pk}/participants'
    response = client.post(base + '/join/', {'username': target.username, 'same_team_verified': 'on'})
    ref = re.search(r'name="preview_ref" value="([a-z0-9]{32})"', response.content.decode()).group(1)
    result = client.post(base + '/confirm/', {'operation': 'JOIN_EXISTING', 'preview_ref': ref}, follow=True)
    assert result.status_code == 200 and '未重复变更' in result.content.decode()
    assert BulkImportBatch.objects.get().operation_details_json['outcome'] == 'NOOP'


def test_csv_render_failure_never_discloses_preview_or_debug_context(management, monkeypatch, settings):
    settings.DEBUG = True
    client, actor, event = management
    def fail(*args, **kwargs):
        raise RuntimeError('SYNTHETIC-RENDER-EXCEPTION')
    monkeypatch.setattr('competitions.views.render', fail)
    client.raise_request_exception = False
    response = client.post(f'/competitions/{event.pk}/accounts/preview/', {
        'csv_file': SimpleUploadedFile('teams.csv', b'team_number,captain_student_id\n1,SYNTHETIC-SECRET\n'),
    })
    assert response.status_code == 500
    html = response.content.decode()
    for forbidden in ('Traceback', 'preview_ref', 'SYNTHETIC-RENDER-EXCEPTION', 'SYNTHETIC-SECRET'):
        assert forbidden not in html
    assert '请' in html


def test_csv_handler_multipart_parse_failure_has_safe_copy(management, settings):
    settings.DEBUG = True
    client, actor, event = management
    client.raise_request_exception = False
    response = client.post(f'/competitions/{event.pk}/accounts/preview/', {
        **{f'extra-{i}': 'value' for i in range(1001)},
        'csv_file': SimpleUploadedFile('teams.csv', b'team_number,captain_student_id\n1,synthetic\n'),
    })
    assert response.status_code == 400
    html = response.content.decode()
    assert 'Traceback' not in html and 'TooManyFieldsSent' not in html and '请' in html
