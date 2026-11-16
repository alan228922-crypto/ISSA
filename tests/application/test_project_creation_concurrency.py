from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, local

import pytest
from django.db import connection, close_old_connections, transaction, OperationalError
from django.db.models import F
from django.utils import timezone

from tests.application.test_project_creation import context, creation_context

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def file_database_only():
    if 'memory' in str(connection.settings_dict['NAME']):
        pytest.skip('Run with --ds=m7_concurrency_settings and M7_TEST_DB_PATH for real file SQLite')


def thread_create(owner, event, name='我的模型'):
    from projects.creation import create_or_open_project
    close_old_connections()
    try:
        return create_or_open_project(actor=owner, event_id=event.pk, name=name)
    finally:
        connection.close()


def test_concurrent_creates_share_one_project(creation_context, monkeypatch):
    from projects import creation
    from projects.models import Project
    owner, event, _, _ = creation_context
    barrier, calls = Barrier(2), local()
    original = creation.project_creation_error

    def synchronized_policy(**kwargs):
        result = original(**kwargs)
        if not getattr(calls, 'seen', False):
            calls.seen = True
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(creation, 'project_creation_error', synchronized_policy)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(thread_create, owner, event, name) for name in ('模型 A', '模型 B')]
        results = [future.result(timeout=15) for future in futures]
    assert results[0].project.pk == results[1].project.pk
    assert sorted(result.created for result in results) == [False, True]
    assert Project.objects.count() == 1
    winner = next(result for result in results if result.created)
    assert Project.objects.get().name == winner.project.name


@pytest.mark.parametrize('change,code', [
    ('membership', 'PROJECT_CREATE_DENIED'), ('user', 'PROJECT_CREATE_DENIED'),
    ('event', 'EVENT_NOT_ACTIVE'), ('expired', 'EVENT_ACCESS_EXPIRED'),
])
def test_authorization_change_while_waiting_denies_create(creation_context, monkeypatch, change, code):
    from accounts.models import User
    from competitions.models import CompetitionEvent, EventMembership
    from projects import creation
    from projects.models import Project
    owner, event, _, _ = creation_context
    preflight_done = Event()
    original = creation.project_creation_error

    def observed_policy(**kwargs):
        result = original(**kwargs)
        preflight_done.set()
        return result

    monkeypatch.setattr(creation, 'project_creation_error', observed_policy)
    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            CompetitionEvent.objects.filter(pk=event.pk).update(status=F('status'))
            future = executor.submit(thread_create, owner, event)
            assert preflight_done.wait(timeout=10)
            if change == 'membership':
                EventMembership.objects.filter(user=owner, event=event).update(is_active=False)
            elif change == 'user':
                User.objects.filter(pk=owner.pk).update(is_active=False)
            elif change == 'event':
                CompetitionEvent.objects.filter(pk=event.pk).update(status='FINISHED_GRACE')
            else:
                CompetitionEvent.objects.filter(pk=event.pk).update(purge_at=timezone.now())
        with pytest.raises(creation.ProjectCreationError) as exc:
            future.result(timeout=15)
    assert exc.value.code == code
    assert Project.objects.count() == 0


def test_locked_retry_restarts_whole_transaction(creation_context, monkeypatch):
    from projects.creation import create_or_open_project
    from projects.models import Project
    owner, event, _, _ = creation_context
    attempts = []

    def fail_first_insert(execute, sql, params, many, context):
        if sql.startswith('INSERT INTO "projects_project"'):
            attempts.append(sql)
            if len(attempts) == 1:
                raise OperationalError('database is locked')
        return execute(sql, params, many, context)

    with connection.execute_wrapper(fail_first_insert):
        result = create_or_open_project(actor=owner, event_id=event.pk, name='重试')
    assert result.created is True
    assert len(attempts) == 2
    assert Project.objects.count() == 1


def test_lock_exhaustion_returns_busy_without_partial_write(creation_context):
    from projects.creation import create_or_open_project, ProjectCreationError
    from projects.models import Project
    owner, event, _, _ = creation_context
    attempts = []

    def always_locked(execute, sql, params, many, context):
        if sql.startswith('INSERT INTO "projects_project"'):
            attempts.append(sql)
            raise OperationalError('database is locked')
        return execute(sql, params, many, context)

    with connection.execute_wrapper(always_locked), pytest.raises(ProjectCreationError) as exc:
        create_or_open_project(actor=owner, event_id=event.pk, name='繁忙')
    assert (exc.value.code, exc.value.status_code) == ('PROJECT_CREATE_BUSY', 503)
    assert len(attempts) == 5
    assert Project.objects.count() == 0
