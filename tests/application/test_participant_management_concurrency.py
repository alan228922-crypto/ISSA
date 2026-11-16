from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event

import pytest
from django.db import close_old_connections, connection, transaction, OperationalError
from django.db.models import F
from django.utils import timezone

from accounts.models import User
from competitions.models import BulkImportBatch, CompetitionEvent, EventMembership
from competitions import participant_services as service

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def concurrent_context():
    if connection.vendor != 'sqlite' or 'mode=memory' in str(connection.settings_dict['NAME']) or str(connection.settings_dict['NAME']) == ':memory:':
        pytest.skip('dedicated file-SQLite run required')
    now = timezone.now()
    event = CompetitionEvent.objects.create(name='并发', event_code='CONCURRENT', competition_date=now.date(),
                                            starts_at=now, ends_at=now + timedelta(days=1), status='ACTIVE')
    manager = User.objects.create_user('manager', role='MANAGER')
    EventMembership.objects.create(user=manager, event=event, membership_type='MANAGER')
    developer = User.objects.create_user('developer', role='DEVELOPER')
    target = User.objects.create_user('existing-team')
    return manager, developer, event, target


def race(calls):
    barrier = Barrier(len(calls))
    def worker(call):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                return call()
            except service.ParticipantManagementError as exc:
                return exc.code
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        return list(pool.map(worker, calls))


def test_same_reference_concurrent_confirm_has_one_effect_and_receipt(concurrent_context):
    manager, _, event, _ = concurrent_context
    preview = service.preview_participant_change(actor=manager, event_id=event.pk, operation='CREATE_USER',
                                                 fields={'team_number': '1', 'captain_student_id': 'synthetic'})
    def call():
        return service.confirm_participant_change(actor=manager, event_id=event.pk, operation='CREATE_USER', preview_ref=preview['preview_ref'])
    results = race([call, call])
    assert results[0] == results[1] and results[0]['outcome'] == 'SUCCESS'
    assert BulkImportBatch.objects.count() == 1
    assert EventMembership.objects.filter(event=event, membership_type='PARTICIPANT').count() == 1


def test_distinct_create_previews_do_not_overwrite_winning_account(concurrent_context):
    manager, developer, event, _ = concurrent_context
    previews = [service.preview_participant_change(actor=actor, event_id=event.pk, operation='CREATE_USER',
                 fields={'team_number': number, 'captain_student_id': password})
                for actor, number, password in [(manager, '1', 'first-secret'), (developer, '01', 'second-secret')]]
    def call(actor, preview):
        return lambda: service.confirm_participant_change(actor=actor, event_id=event.pk, operation='CREATE_USER', preview_ref=preview['preview_ref'])
    results = race([call(manager, previews[0]), call(developer, previews[1])])
    assert sum(isinstance(value, dict) for value in results) == 1
    assert 'PREVIEW_STATE_CHANGED' in results
    user = User.objects.get(username=f'{event.competition_date:%Y%m%d}01')
    assert user.check_password('first-secret' if isinstance(results[0], dict) else 'second-secret')
    assert BulkImportBatch.objects.count() == 1


def test_concurrent_developer_manager_reactivate_is_stale_not_duplicate(concurrent_context):
    manager, developer, event, target = concurrent_context
    membership = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT', is_active=False)
    previews = [service.preview_participant_change(actor=actor, event_id=event.pk, operation='REACTIVATE',
                 fields={'membership_id': membership.pk, 'same_team_verified': True}) for actor in (manager, developer)]
    def call(actor, preview):
        return lambda: service.confirm_participant_change(actor=actor, event_id=event.pk, operation='REACTIVATE', preview_ref=preview['preview_ref'])
    results = race([call(manager, previews[0]), call(developer, previews[1])])
    assert sum(isinstance(value, dict) for value in results) == 1 and 'PREVIEW_STATE_CHANGED' in results
    membership.refresh_from_db()
    assert membership.is_active and BulkImportBatch.objects.count() == 1


def test_opposing_stale_preview_cannot_undo_committed_deactivation(concurrent_context):
    manager, developer, event, target = concurrent_context
    membership = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT')
    stale = service.preview_participant_change(actor=developer, event_id=event.pk, operation='REACTIVATE',
                                              fields={'membership_id': membership.pk, 'same_team_verified': True})
    deactivate = service.preview_participant_change(actor=manager, event_id=event.pk, operation='DEACTIVATE',
                                                   fields={'membership_id': membership.pk, 'confirmed': True})
    service.confirm_participant_change(actor=manager, event_id=event.pk, operation='DEACTIVATE', preview_ref=deactivate['preview_ref'])
    with pytest.raises(service.ParticipantManagementError, match='PREVIEW_STATE_CHANGED'):
        service.confirm_participant_change(actor=developer, event_id=event.pk, operation='REACTIVATE', preview_ref=stale['preview_ref'])
    membership.refresh_from_db()
    assert not membership.is_active and BulkImportBatch.objects.count() == 1


def test_concurrent_join_has_one_original_membership(concurrent_context):
    manager, developer, event, target = concurrent_context
    previews = [service.preview_participant_change(actor=actor, event_id=event.pk, operation='JOIN_EXISTING',
                 fields={'username': target.username, 'same_team_verified': True}) for actor in (manager, developer)]
    def call(actor, preview):
        return lambda: service.confirm_participant_change(actor=actor, event_id=event.pk, operation='JOIN_EXISTING', preview_ref=preview['preview_ref'])
    results = race([call(manager, previews[0]), call(developer, previews[1])])
    assert sum(isinstance(value, dict) for value in results) == 1 and 'PREVIEW_STATE_CHANGED' in results
    assert EventMembership.objects.filter(user=target, event=event).count() == 1
    assert BulkImportBatch.objects.count() == 1


def test_opposing_concurrent_preview_cannot_resurrect_deactivated_member(concurrent_context):
    manager, developer, event, target = concurrent_context
    membership = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT')
    first = service.preview_participant_change(actor=manager, event_id=event.pk, operation='DEACTIVATE',
                                              fields={'membership_id': membership.pk, 'confirmed': True})
    second = service.preview_participant_change(actor=developer, event_id=event.pk, operation='REACTIVATE',
                                               fields={'membership_id': membership.pk, 'same_team_verified': True})
    results = race([
        lambda: service.confirm_participant_change(actor=manager, event_id=event.pk, operation='DEACTIVATE', preview_ref=first['preview_ref']),
        lambda: service.confirm_participant_change(actor=developer, event_id=event.pk, operation='REACTIVATE', preview_ref=second['preview_ref']),
    ])
    assert results[0]['outcome'] == 'SUCCESS'
    assert results[1] == 'PREVIEW_STATE_CHANGED' or results[1]['outcome'] == 'NOOP'
    membership.refresh_from_db()
    assert not membership.is_active
    assert BulkImportBatch.objects.filter(operation_details_json__outcome='SUCCESS').count() == 1


@pytest.mark.parametrize('change,code', [
    ('actor', 'PERMISSION_DENIED'), ('membership', 'PERMISSION_DENIED'),
    ('event', 'EVENT_STATUS_NOT_ALLOWED'), ('expired', 'EVENT_ACCESS_EXPIRED'),
    ('target', 'USER_ROLE_CONFLICT'),
])
def test_authority_or_target_change_while_waiting_denies(concurrent_context, change, code):
    manager, _, event, target = concurrent_context
    preview = service.preview_participant_change(actor=manager, event_id=event.pk, operation='JOIN_EXISTING',
                                                 fields={'username': target.username, 'same_team_verified': True})
    reached_update = Event()
    def worker():
        close_old_connections()
        def observe(execute, sql, params, many, context):
            if sql.startswith('UPDATE "competitions_competitionevent"'):
                reached_update.set()
            return execute(sql, params, many, context)
        try:
            with connection.execute_wrapper(observe):
                return service.confirm_participant_change(actor=manager, event_id=event.pk, operation='JOIN_EXISTING', preview_ref=preview['preview_ref'])
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            CompetitionEvent.objects.filter(pk=event.pk).update(status=F('status'))
            future = pool.submit(worker)
            assert reached_update.wait(timeout=10)
            if change == 'actor':
                User.objects.filter(pk=manager.pk).update(is_active=False)
            elif change == 'membership':
                EventMembership.objects.filter(user=manager, event=event).update(is_active=False)
            elif change == 'event':
                CompetitionEvent.objects.filter(pk=event.pk).update(status='FINISHED_GRACE')
            elif change == 'expired':
                CompetitionEvent.objects.filter(pk=event.pk).update(purge_at=timezone.now())
            else:
                User.objects.filter(pk=target.pk).update(role='MANAGER')
        with pytest.raises(service.ParticipantManagementError) as exc:
            future.result(timeout=15)
    assert exc.value.code == code
    assert not EventMembership.objects.filter(user=target, event=event).exists()
    assert not BulkImportBatch.objects.exists()


@pytest.mark.parametrize('exhaust', [False, True])
def test_busy_retry_restarts_entire_mutation_or_exhausts_without_receipt(concurrent_context, exhaust):
    from django.contrib.sessions.models import Session
    manager, _, event, target = concurrent_context
    preview = service.preview_participant_change(actor=manager, event_id=event.pk, operation='JOIN_EXISTING',
                                                 fields={'username': target.username, 'same_team_verified': True})
    attempts = []
    def locked_after_mutation(execute, sql, params, many, context):
        if sql.startswith('INSERT INTO "competitions_bulkimportbatch"'):
            attempts.append(sql)
            if exhaust or len(attempts) == 1:
                raise OperationalError('database is locked')
        return execute(sql, params, many, context)
    with connection.execute_wrapper(locked_after_mutation):
        if exhaust:
            with pytest.raises(service.ParticipantManagementError) as exc:
                service.confirm_participant_change(actor=manager, event_id=event.pk, operation='JOIN_EXISTING', preview_ref=preview['preview_ref'])
            assert (exc.value.code, exc.value.status_code) == ('PARTICIPANT_MANAGEMENT_BUSY', 503)
        else:
            result = service.confirm_participant_change(actor=manager, event_id=event.pk, operation='JOIN_EXISTING', preview_ref=preview['preview_ref'])
            assert result['outcome'] == 'SUCCESS'
    assert len(attempts) == (5 if exhaust else 2)
    assert EventMembership.objects.filter(user=target, event=event).count() == (0 if exhaust else 1)
    assert BulkImportBatch.objects.count() == (0 if exhaust else 1)
    state = Session.objects.get(session_key=preview['preview_ref']).get_decoded()['participant_preview']
    assert state['stage'] == ('PENDING' if exhaust else 'CONSUMED')


def test_lost_success_response_retries_same_receipt(concurrent_context):
    manager, _, event, target = concurrent_context
    preview = service.preview_participant_change(actor=manager, event_id=event.pk, operation='JOIN_EXISTING',
                                                 fields={'username': target.username, 'same_team_verified': True})
    def submit():
        return service.confirm_participant_change(actor=manager, event_id=event.pk, operation='JOIN_EXISTING', preview_ref=preview['preview_ref'])
    original = submit()  # 提交已完成，模拟响应丢失后再次请求。
    assert submit() == original and BulkImportBatch.objects.count() == 1


def test_m7_create_waiting_on_event_observes_deactivation(concurrent_context, monkeypatch):
    from projects import creation
    from projects.models import Project
    manager, _, event, target = concurrent_context
    member = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT')
    preview = service.preview_participant_change(actor=manager, event_id=event.pk, operation='DEACTIVATE',
                                                 fields={'membership_id': member.pk, 'confirmed': True})
    preflight = Event()
    original = creation.project_creation_error
    def observed(**kwargs):
        result = original(**kwargs)
        preflight.set()
        return result
    monkeypatch.setattr(creation, 'project_creation_error', observed)
    def worker():
        close_old_connections()
        try:
            return creation.create_or_open_project(actor=target, event_id=event.pk, name='must not create')
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            CompetitionEvent.objects.filter(pk=event.pk).update(status=F('status'))
            future = pool.submit(worker)
            assert preflight.wait(timeout=10)
            service.confirm_participant_change(actor=manager, event_id=event.pk, operation='DEACTIVATE', preview_ref=preview['preview_ref'])
        with pytest.raises(creation.ProjectCreationError, match='PROJECT_CREATE_DENIED'):
            future.result(timeout=15)
    assert not Project.objects.exists()
