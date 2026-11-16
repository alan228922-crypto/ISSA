from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from tests.application.test_physical_draft import context

pytestmark = pytest.mark.django_db


@pytest.fixture
def creation_context(context):
    owner, project, material, section = context
    event = project.event
    project.delete()
    event.status = 'ACTIVE'
    event.save()
    return owner, event, material, section


def test_active_participant_creates_empty_v2_project(creation_context):
    from accounts.models import User
    from analysis.models import AnalysisRun, ModelRevision
    from competitions.models import EventMembership
    from learning.models import Prediction
    from materials.models import Material, Section
    from modeling.models import GeometryNode, PhysicalMember, Connection, MemberJointIncidence, Support, NodeLoad
    from projects.creation import create_or_open_project
    owner, event, _, _ = creation_context
    models = (User, EventMembership, Material, Section)
    before = [model.objects.count() for model in models]
    result = create_or_open_project(actor=owner, event_id=event.pk, name=' 我的结构方案 ')
    assert result.created is True
    assert (result.project.owner_user_id, result.project.event_id) == (owner.pk, event.pk)
    assert (result.project.analysis_type, result.project.draft_schema_version, result.project.draft_version) == ('TRUSS_2D', 'physical-draft-v2', 0)
    assert result.project.name == '我的结构方案'
    assert [model.objects.count() for model in models] == before
    for model in (GeometryNode, PhysicalMember, Connection, MemberJointIncidence, Support, NodeLoad, AnalysisRun, ModelRevision, Prediction):
        assert model.objects.count() == 0


@pytest.mark.parametrize('condition', ['anonymous', 'inactive', 'manager', 'developer', 'missing', 'membership_inactive', 'wrong_event', 'wrong_type'])
def test_create_policy_matrix(creation_context, condition):
    from competitions.models import EventMembership
    from projects.creation import ProjectCreationError, create_or_open_project
    from projects.models import Project
    owner, event, _, _ = creation_context
    membership = EventMembership.objects.get(user=owner, event=event)
    if condition == 'anonymous':
        owner = AnonymousUser()
    elif condition == 'inactive':
        owner.is_active = False
        owner.save()
    elif condition in {'manager', 'developer'}:
        owner.role = condition.upper()
        owner.save()
    elif condition == 'membership_inactive':
        membership.is_active = False
        membership.save()
    elif condition == 'wrong_type':
        membership.membership_type = 'MANAGER'
        membership.save()
    else:
        membership.delete()
        if condition == 'wrong_event':
            from competitions.models import CompetitionEvent
            other = CompetitionEvent.objects.create(name='other', event_code='OTHER', competition_date=event.competition_date, starts_at=event.starts_at, ends_at=event.ends_at)
            EventMembership.objects.create(user=owner, event=other, membership_type='PARTICIPANT')
    with pytest.raises(ProjectCreationError) as exc:
        create_or_open_project(actor=owner, event_id=event.pk, name='不应建立')
    assert exc.value.status_code == 403
    assert Project.objects.count() == 0


@pytest.mark.parametrize('status', ['DRAFT', 'FINISHED_GRACE', 'PURGED'])
def test_non_active_event_denies_create(creation_context, status):
    from projects.creation import ProjectCreationError, create_or_open_project
    owner, event, _, _ = creation_context
    event.status = status
    event.save()
    with pytest.raises(ProjectCreationError) as exc:
        create_or_open_project(actor=owner, event_id=event.pk, name='项目')
    assert exc.value.status_code == 403


@pytest.mark.parametrize('offset,expected', [(-1, None), (0, 'EVENT_ACCESS_EXPIRED'), (1, 'EVENT_ACCESS_EXPIRED')])
def test_purge_cutoff_is_exact(creation_context, offset, expected):
    from projects.creation import project_creation_error
    owner, event, _, _ = creation_context
    assert project_creation_error(actor=owner, event=event, now=event.purge_at + timedelta(microseconds=offset)) == expected


@pytest.mark.parametrize('schema', ['physical-draft-v1', 'physical-draft-v2'])
def test_duplicate_returns_same_project_without_mutation(creation_context, schema):
    from modeling.models import GeometryNode
    from projects.creation import create_or_open_project
    from projects.models import Project
    owner, event, _, _ = creation_context
    existing = Project.objects.create(owner_user=owner, event=event, name='原名称', draft_schema_version=schema, draft_version=7)
    GeometryNode.objects.create(project=existing, client_key='node-4', x_mm=12.4, y_mm=7.6)
    before = list(Project.objects.values())
    result = create_or_open_project(actor=owner, event_id=event.pk, name='新名称')
    assert result.created is False
    assert result.project.pk == existing.pk
    assert list(Project.objects.values()) == before
    assert GeometryNode.objects.get().x_mm == 12.4


@pytest.mark.parametrize('kind', ['multiple', 'frame', 'unsupported', 'blocked'])
def test_legacy_cardinality_and_unavailable_project_fail_closed(creation_context, kind):
    from modeling.models import DraftMigrationAudit
    from projects.creation import create_or_open_project, ProjectCreationError
    from projects.models import Project
    owner, event, _, _ = creation_context
    existing = Project.objects.create(owner_user=owner, event=event, name='legacy', draft_schema_version='physical-draft-v1')
    if kind == 'multiple':
        Project.objects.create(owner_user=owner, event=event, name='another')
    elif kind == 'frame':
        existing.analysis_type = 'FRAME_2D'
        existing.save()
    elif kind == 'unsupported':
        existing.draft_schema_version = 'unknown'
        existing.save()
    else:
        DraftMigrationAudit.objects.create(project=existing, status='BLOCKED', source_draft_version=0,
            source_hash='test-source', source_payload_json={})
    before = list(Project.objects.values())
    with pytest.raises(ProjectCreationError) as exc:
        create_or_open_project(actor=owner, event_id=event.pk, name='new')
    assert exc.value.code == ('PROJECT_MULTIPLE_EXISTING' if kind == 'multiple' else 'PROJECT_EXISTING_UNAVAILABLE')
    assert exc.value.status_code == 409
    assert list(Project.objects.values()) == before


@pytest.mark.parametrize('name', ['', '   ', 'x' * 201, None, 12])
def test_invalid_name_does_not_create(creation_context, name):
    from projects.creation import create_or_open_project, ProjectCreationError
    from projects.models import Project
    owner, event, _, _ = creation_context
    with pytest.raises(ProjectCreationError):
        create_or_open_project(actor=owner, event_id=event.pk, name=name)
    assert Project.objects.count() == 0


def test_create_failure_rolls_back_saved_row(creation_context, monkeypatch):
    from projects.creation import create_or_open_project
    from projects.models import Project
    owner, event, _, _ = creation_context
    original = Project.objects.create

    def failing_create(**kwargs):
        original(**kwargs)
        raise RuntimeError('simulated downstream failure')

    monkeypatch.setattr(Project.objects, 'create', failing_create)
    with pytest.raises(RuntimeError):
        create_or_open_project(actor=owner, event_id=event.pk, name='项目')
    assert Project.objects.count() == 0
