import pytest
from django.contrib.auth.models import AnonymousUser

from tests.application.test_physical_draft import context


@pytest.mark.django_db
@pytest.mark.parametrize('status,read,write', [
    ('DRAFT', True, True), ('ACTIVE', True, True),
    ('FINISHED_GRACE', True, False), ('PURGED', False, False),
])
@pytest.mark.parametrize('role', ['USER', 'DEVELOPER'])
def test_event_operational_policy(context, status, read, write, role):
    from competitions.authorization import can_view_event
    from projects.services import can_view_project, can_modify_project
    owner, project, _, _ = context
    owner.role = role
    owner.save()
    project.event.status = status
    project.event.save()
    assert can_view_event(owner, project.event) is read
    assert can_view_project(owner, project) is read
    assert can_modify_project(owner, project) is write


@pytest.mark.django_db
def test_inactive_and_anonymous_have_no_operational_access(context):
    from projects.services import can_view_project, can_modify_project
    owner, project, _, _ = context
    owner.is_active = False
    owner.save()
    for actor in (owner, AnonymousUser()):
        assert can_view_project(actor, project) is False
        assert can_modify_project(actor, project) is False


@pytest.mark.django_db
def test_stale_project_event_cannot_bypass_closed_state(context):
    from competitions.models import CompetitionEvent
    from projects.services import can_view_project, can_modify_project
    owner, project, _, _ = context
    _ = project.event
    CompetitionEvent.objects.filter(pk=project.event_id).update(status='FINISHED_GRACE')
    assert can_modify_project(owner, project) is False
    CompetitionEvent.objects.filter(pk=project.event_id).update(status='PURGED')
    assert can_view_project(owner, project) is False


@pytest.mark.django_db
@pytest.mark.parametrize('explicit_actor', [True, False])
def test_direct_prediction_discovery_denies_purged_residual_rows(context, explicit_actor):
    from competitions.models import CompetitionEvent
    from learning.services import create_prediction, discover_current_prediction, PredictionError
    owner, project, _, _ = context
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=0)
    assert prediction.pk
    # Preserve the caller's cached Event to exercise a real stale-object boundary.
    CompetitionEvent.objects.filter(pk=project.event_id).update(status='PURGED')
    with pytest.raises(PredictionError) as exc:
        discover_current_prediction(project, owner if explicit_actor else None)
    assert (exc.value.code, exc.value.status_code) == ('PROJECT_READ_DENIED', 403)


@pytest.mark.django_db
def test_direct_prediction_discovery_rejects_unrelated_actor(context):
    from accounts.models import User
    from learning.services import create_prediction, discover_current_prediction, PredictionError
    owner, project, _, _ = context
    create_prediction(project=project, actor=owner, expected_draft_version=0)
    unrelated = User.objects.create_user('unrelated-reader')
    with pytest.raises(PredictionError):
        discover_current_prediction(project, unrelated)
