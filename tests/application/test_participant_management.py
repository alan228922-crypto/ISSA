from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.utils import timezone

from accounts.models import User
from competitions.models import BulkImportBatch, CompetitionEvent, EventMembership
from competitions import participant_services as service
from tests.application.test_physical_draft import context as physical_context


@pytest.fixture
def management_context(db):
    now = timezone.now()
    event = CompetitionEvent.objects.create(name='进行中', event_code='SINGLE', competition_date=now.date(),
                                            starts_at=now, ends_at=now + timedelta(days=1), status='ACTIVE')
    actor = User.objects.create_user('manager', role='MANAGER')
    EventMembership.objects.create(user=actor, event=event, membership_type='MANAGER')
    target = User.objects.create_user('existing-team', password='synthetic-existing', must_change_password=True)
    return actor, event, target


def preview(context, operation, fields):
    actor, event, _ = context
    return service.preview_participant_change(actor=actor, event_id=event.pk, operation=operation, fields=fields)


def confirm(context, operation, ref):
    actor, event, _ = context
    return service.confirm_participant_change(actor=actor, event_id=event.pk, operation=operation, preview_ref=ref)


def join_fields(target):
    return {'username': target.username, 'same_team_verified': True}


def membership_fields(membership, operation):
    return {'membership_id': membership.pk, 'same_team_verified': True} if operation == 'REACTIVATE' else {
        'membership_id': membership.pk, 'confirmed': True,
    }


def test_active_manager_creates_user_and_membership_without_project(management_context):
    from projects.models import Project
    context = management_context
    result = preview(context, 'CREATE_USER', {'team_number': '04', 'captain_student_id': 'synthetic-new'})
    assert User.objects.count() == 2 and not Project.objects.exists()
    outcome = confirm(context, 'CREATE_USER', result['preview_ref'])
    user = User.objects.get(username=f'{context[1].competition_date:%Y%m%d}04')
    assert user.check_password('synthetic-new') and user.must_change_password
    assert user.role == 'USER' and user.is_active
    assert outcome == {'outcome': 'SUCCESS', 'created_count': 1, 'changed_membership_count': 1}
    assert EventMembership.objects.filter(user=user, event=context[1], membership_type='PARTICIPANT').count() == 1
    assert not Project.objects.exists()


def test_developer_participant_management(management_context):
    actor, event, target = management_context
    developer = User.objects.create_user('developer', role='DEVELOPER')
    context = developer, event, target
    result = preview(context, 'JOIN_EXISTING', join_fields(target))
    assert confirm(context, 'JOIN_EXISTING', result['preview_ref'])['outcome'] == 'SUCCESS'


def test_join_preserves_existing_user_and_other_events(management_context):
    actor, event, target = management_context
    other = CompetitionEvent.objects.create(name='其他', event_code='OTHER', competition_date=event.competition_date,
                                            starts_at=event.starts_at, ends_at=event.ends_at)
    membership = EventMembership.objects.create(user=target, event=other, membership_type='PARTICIPANT', is_active=False)
    before = User.objects.filter(pk=target.pk).values().get()
    result = preview(management_context, 'JOIN_EXISTING', join_fields(target))
    confirm(management_context, 'JOIN_EXISTING', result['preview_ref'])
    assert User.objects.filter(pk=target.pk).values().get() == before
    membership.refresh_from_db()
    assert membership.is_active is False


@pytest.mark.parametrize('operation', ['REACTIVATE', 'JOIN_EXISTING'])
def test_reactivate_reuses_original_membership(management_context, operation):
    actor, event, target = management_context
    membership = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT', is_active=False)
    fields = membership_fields(membership, operation) if operation == 'REACTIVATE' else join_fields(target)
    result = preview(management_context, operation, fields)
    confirm(management_context, operation, result['preview_ref'])
    membership.refresh_from_db()
    assert membership.is_active and EventMembership.objects.filter(user=target, event=event).count() == 1


@pytest.mark.parametrize('operation,active', [('JOIN_EXISTING', True), ('REACTIVATE', True), ('DEACTIVATE', False)])
def test_existing_active_membership_is_noop(management_context, operation, active):
    actor, event, target = management_context
    membership = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT', is_active=active)
    fields = join_fields(target) if operation == 'JOIN_EXISTING' else membership_fields(membership, operation)
    result = preview(management_context, operation, fields)
    outcome = confirm(management_context, operation, result['preview_ref'])
    assert outcome == {'outcome': 'NOOP', 'created_count': 0, 'changed_membership_count': 0}
    assert confirm(management_context, operation, result['preview_ref']) == outcome
    receipt = BulkImportBatch.objects.get().operation_details_json
    assert receipt['targets'][0]['before_active'] is active and receipt['targets'][0]['after_active'] is active


@pytest.mark.parametrize('change', ['manager', 'inactive', 'active-manager-membership', 'unverified', 'extra-field'])
def test_unsafe_existing_target_is_denied_without_business_receipt(management_context, change):
    actor, event, target = management_context
    fields = join_fields(target)
    if change == 'manager':
        target.role = 'MANAGER'
        target.save()
    elif change == 'inactive':
        target.is_active = False
        target.save()
    elif change == 'active-manager-membership':
        EventMembership.objects.create(user=target, event=event, membership_type='MANAGER')
    elif change == 'unverified':
        fields['same_team_verified'] = False
    else:
        fields['role'] = 'DEVELOPER'
    with pytest.raises(service.ParticipantManagementError):
        preview(management_context, 'JOIN_EXISTING', fields)
    assert not BulkImportBatch.objects.exists()


@pytest.mark.parametrize('change', ['role', 'inactive', 'username', 'date', 'membership'])
def test_changed_target_requires_fresh_preview(management_context, change):
    actor, event, target = management_context
    result = preview(management_context, 'JOIN_EXISTING', join_fields(target))
    if change == 'role':
        User.objects.filter(pk=target.pk).update(role='MANAGER')
    elif change == 'inactive':
        User.objects.filter(pk=target.pk).update(is_active=False)
    elif change == 'username':
        User.objects.filter(pk=target.pk).update(username='changed')
    elif change == 'date':
        CompetitionEvent.objects.filter(pk=event.pk).update(competition_date=event.competition_date + timedelta(days=1))
    else:
        EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT')
    with pytest.raises(service.ParticipantManagementError):
        confirm(management_context, 'JOIN_EXISTING', result['preview_ref'])
    assert not BulkImportBatch.objects.exists()


@pytest.mark.parametrize('failure', ['audit', 'consume'])
def test_single_failure_rolls_back_and_same_preview_can_retry(management_context, monkeypatch, failure):
    result = preview(management_context, 'JOIN_EXISTING', join_fields(management_context[2]))
    attribute = '_record_operation' if failure == 'audit' else 'consume_preview'
    original = getattr(service, attribute)
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(service, attribute, fail)
    with pytest.raises(RuntimeError):
        confirm(management_context, 'JOIN_EXISTING', result['preview_ref'])
    assert not EventMembership.objects.filter(user=management_context[2], event=management_context[1]).exists()
    assert not BulkImportBatch.objects.exists()
    assert Session.objects.get(session_key=result['preview_ref']).get_decoded()['participant_preview']['stage'] == 'PENDING'
    monkeypatch.setattr(service, attribute, original)
    assert confirm(management_context, 'JOIN_EXISTING', result['preview_ref'])['outcome'] == 'SUCCESS'


def test_new_user_collision_never_auto_joins(management_context):
    result = preview(management_context, 'CREATE_USER', {'team_number': '1', 'captain_student_id': 'preview-password'})
    user = User.objects.create_user(f'{management_context[1].competition_date:%Y%m%d}01', password='winning-password')
    with pytest.raises(service.ParticipantManagementError):
        confirm(management_context, 'CREATE_USER', result['preview_ref'])
    user.refresh_from_db()
    assert user.check_password('winning-password')
    assert not EventMembership.objects.filter(user=user).exists() and not BulkImportBatch.objects.exists()


@pytest.mark.parametrize('operation', ['CREATE_USER', 'JOIN_EXISTING', 'REACTIVATE', 'DEACTIVATE'])
@pytest.mark.parametrize('status', ['DRAFT', 'ACTIVE', 'FINISHED_GRACE', 'PURGED'])
def test_all_single_operations_respect_lifecycle(management_context, operation, status):
    actor, event, target = management_context
    membership = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT')
    CompetitionEvent.objects.filter(pk=event.pk).update(status=status)
    fields = {'team_number': '8', 'captain_student_id': 'synthetic'} if operation == 'CREATE_USER' else (
        join_fields(target) if operation == 'JOIN_EXISTING' else membership_fields(membership, operation))
    if status in {'FINISHED_GRACE', 'PURGED'}:
        with pytest.raises(service.ParticipantManagementError):
            preview(management_context, operation, fields)
        assert not BulkImportBatch.objects.exists()
    else:
        assert preview(management_context, operation, fields)['preview_ref']


def test_existing_password_changed_after_preview_is_not_overwritten(management_context):
    target = management_context[2]
    result = preview(management_context, 'JOIN_EXISTING', join_fields(target))
    target.set_password('changed-synthetic-password')
    target.must_change_password = False
    target.save()
    before = target.password
    confirm(management_context, 'JOIN_EXISTING', result['preview_ref'])
    target.refresh_from_db()
    assert target.password == before and target.must_change_password is False


def test_consumed_reactivate_does_not_reverse_later_deactivation(management_context):
    actor, event, target = management_context
    member = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT', is_active=False)
    first = preview(management_context, 'REACTIVATE', membership_fields(member, 'REACTIVATE'))
    original_result = confirm(management_context, 'REACTIVATE', first['preview_ref'])
    second = preview(management_context, 'DEACTIVATE', membership_fields(member, 'DEACTIVATE'))
    confirm(management_context, 'DEACTIVATE', second['preview_ref'])
    assert confirm(management_context, 'REACTIVATE', first['preview_ref']) == original_result
    member.refresh_from_db()
    assert member.is_active is False and BulkImportBatch.objects.count() == 2


@pytest.mark.parametrize('initial,stale_operation', [(False, 'REACTIVATE'), (True, 'DEACTIVATE')])
def test_pending_preview_rejects_intervening_qualification_cycle(management_context, initial, stale_operation):
    actor, event, target = management_context
    member = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT', is_active=initial)
    stale = preview(management_context, stale_operation, membership_fields(member, stale_operation))
    other = User.objects.create_user('other-developer', role='DEVELOPER')
    other_context = other, event, target
    for operation in (stale_operation, 'DEACTIVATE' if stale_operation == 'REACTIVATE' else 'REACTIVATE'):
        fresh = preview(other_context, operation, membership_fields(member, operation))
        confirm(other_context, operation, fresh['preview_ref'])
    with pytest.raises(service.ParticipantManagementError, match='PREVIEW_STATE_CHANGED'):
        confirm(management_context, stale_operation, stale['preview_ref'])
    member.refresh_from_db()
    assert member.is_active is initial
    assert BulkImportBatch.objects.count() == 2


def test_noop_receipt_does_not_invalidate_pending_change(management_context):
    actor, event, target = management_context
    member = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT')
    pending = preview(management_context, 'DEACTIVATE', membership_fields(member, 'DEACTIVATE'))
    noop = preview(management_context, 'JOIN_EXISTING', join_fields(target))
    assert confirm(management_context, 'JOIN_EXISTING', noop['preview_ref'])['outcome'] == 'NOOP'
    assert confirm(management_context, 'DEACTIVATE', pending['preview_ref'])['outcome'] == 'SUCCESS'


def test_other_target_receipt_does_not_invalidate_pending_change(management_context):
    actor, event, target = management_context
    member = EventMembership.objects.create(user=target, event=event, membership_type='PARTICIPANT')
    pending = preview(management_context, 'DEACTIVATE', membership_fields(member, 'DEACTIVATE'))
    other = User.objects.create_user('other-target')
    joined = preview(management_context, 'JOIN_EXISTING', join_fields(other))
    confirm(management_context, 'JOIN_EXISTING', joined['preview_ref'])
    assert confirm(management_context, 'DEACTIVATE', pending['preview_ref'])['outcome'] == 'SUCCESS'


def test_membership_from_another_event_cannot_be_reactivated(management_context):
    actor, event, target = management_context
    other = CompetitionEvent.objects.create(name='其他', event_code='OTHER', competition_date=event.competition_date,
                                            starts_at=event.starts_at, ends_at=event.ends_at)
    member = EventMembership.objects.create(user=target, event=other, membership_type='PARTICIPANT', is_active=False)
    with pytest.raises(service.ParticipantManagementError, match='MEMBERSHIP_NOT_FOUND'):
        preview(management_context, 'REACTIVATE', membership_fields(member, 'REACTIVATE'))
    assert not BulkImportBatch.objects.exists()


def test_deactivate_preserves_project_draft_history_and_resources(physical_context, client):
    from analysis.orchestration import analyze_project
    from modeling.services import save_physical_draft
    from projects.workspace import _draft
    from tests.application.test_node_joint_draft import v2_payload, v2_project
    owner, project, material, section = physical_context
    v2_project(project)
    payload = v2_payload(material, section)
    payload['node_loads'][0].update(fx_N=100, fy_N=0)
    payload['supports'].append({'client_key': 's2', 'target_node_client_key': 'n2', 'support_type': 'ROLLER', 'restrained_axis': 'Y'})
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    assert run.status == 'SUCCESS'
    event = project.event
    event.status = 'ACTIVE'
    event.save()
    actor = User.objects.create_user('manager', role='MANAGER')
    EventMembership.objects.create(user=actor, event=event, membership_type='MANAGER')
    context = actor, event, owner
    member = EventMembership.objects.get(user=owner, event=event, membership_type='PARTICIPANT')
    before = (_draft(project), project.draft_version, project.owner_user_id, run.result_json, run.model_revision.physical_snapshot_json)
    result = preview(context, 'DEACTIVATE', membership_fields(member, 'DEACTIVATE'))
    confirm(context, 'DEACTIVATE', result['preview_ref'])
    client.force_login(owner)
    assert client.get(f'/projects/{project.pk}/workspace/').status_code == 404
    from projects.creation import ProjectCreationError, create_or_open_project
    with pytest.raises(ProjectCreationError):
        create_or_open_project(actor=owner, event_id=event.pk, name='must not create')
    for path in ('model/check/', 'analyze/'):
        assert client.post(f'/projects/{project.pk}/{path}', {'expected_draft_version': 1}, content_type='application/json').status_code == 403
    project.refresh_from_db()
    run.refresh_from_db()
    assert (_draft(project), project.draft_version, project.owner_user_id, run.result_json, run.model_revision.physical_snapshot_json) == before
    assert material.__class__.objects.filter(pk=material.pk, owner_user=owner).exists()
    assert section.__class__.objects.filter(pk=section.pk, owner_user=owner).exists()
    restored = preview(context, 'REACTIVATE', membership_fields(member, 'REACTIVATE'))
    confirm(context, 'REACTIVATE', restored['preview_ref'])
    assert client.get(f'/projects/{project.pk}/workspace/').status_code == 200
