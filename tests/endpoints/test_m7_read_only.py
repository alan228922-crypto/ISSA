import json

import pytest
from django.urls import reverse

from tests.application.test_physical_draft import context
from tests.endpoints.test_reasoning_json import successful_run


def graph_state(project):
    from analysis.models import AnalysisRun, ModelRevision, ValidationLog
    from learning.models import Prediction, Reflection, CalculationReportReasoning
    from modeling.models import GeometryNode, PhysicalMember, Connection, Support, NodeLoad
    project.refresh_from_db()
    return (project.draft_version, [list(model.objects.values().order_by('pk')) for model in (
        GeometryNode, PhysicalMember, Connection, Support, NodeLoad, AnalysisRun,
        ModelRevision, ValidationLog, Prediction, Reflection, CalculationReportReasoning,
    )])


@pytest.mark.django_db
@pytest.mark.parametrize('action', ['save', 'check', 'analyze', 'prediction',
    'prediction_complete', 'reflection', 'reflection_complete', 'reasoning', 'preview'])
def test_grace_denies_operational_writes_but_preserves_history(successful_run, client, action):
    from learning.services import create_prediction, record_student_result_reveal, create_reflection
    owner, project, run = successful_run
    project.event.status = 'ACTIVE'
    project.event.save()
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=project.draft_version)
    record_student_result_reveal(project=project, run=run, actor=owner)
    create_reflection(run=run, actor=owner)
    project.event.status = 'FINISHED_GRACE'
    project.event.save()
    base = f'/projects/{project.pk}'
    target, payload = {
        'save': (f'{base}/model/save/', {'schema_version': 'physical-draft-v1', 'expected_draft_version': project.draft_version}),
        'check': (f'{base}/model/check/', {'expected_draft_version': project.draft_version}),
        'analyze': (f'{base}/analyze/', {'expected_draft_version': project.draft_version}),
        'prediction': (f'{base}/predictions/', {'expected_draft_version': project.draft_version}),
        'prediction_complete': (f'{base}/predictions/{prediction.pk}/complete/', {'expected_draft_version': project.draft_version, 'payload': {}}),
        'reflection': (f'{base}/analyses/{run.pk}/reflection/', {'original_reasoning': 'new text'}),
        'reflection_complete': (f'{base}/analyses/{run.pk}/reflection/complete/', {}),
        'reasoning': (f'{base}/analyses/{run.pk}/reasoning/', {'final_conclusion': 'new text'}),
        'preview': (f'{base}/sections/preview/', {'schema_version': 'section-definition-v1', 'type': 'rectangle', 'width_mm': 1, 'height_mm': 2, 'density_g_per_mm3': 0.001}),
    }[action]
    before = graph_state(project)
    client.force_login(owner)
    response = client.post(target, json.dumps(payload), content_type='application/json')
    assert response.status_code == 403, response.content
    assert graph_state(project) == before


@pytest.mark.django_db
@pytest.mark.parametrize('role', ['USER', 'MANAGER', 'DEVELOPER'])
def test_purged_residual_rows_are_not_operationally_readable(successful_run, client, role):
    from accounts.models import User
    from competitions.models import EventMembership
    from learning.services import create_prediction
    owner, project, run = successful_run
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=project.draft_version)
    actor = owner
    if role != 'USER':
        actor = User.objects.create_user(f'reader-{role}', role=role)
        EventMembership.objects.create(user=actor, event=project.event, membership_type='MANAGER')
    project.event.status = 'PURGED'
    project.event.save()
    client.force_login(actor)
    base = f'/projects/{project.pk}'
    paths = [f'{base}/workspace/', f'{base}/model/legacy-export/', f'{base}/analyses/',
        f'{base}/predictions/current/', f'{base}/predictions/{prediction.pk}/']
    paths += [f'{base}/analyses/{run.pk}/{suffix}/' for suffix in (
        'data', 'report', 'comparison', 'explanation', 'reasoning', 'reflection')]
    for path in paths:
        response = client.get(path)
        assert response.status_code in {403, 404}, (path, response.status_code)
    assert f'{base}/workspace/' not in client.get('/events/').content.decode()


@pytest.mark.django_db
def test_first_historical_disclosure_in_grace_is_readable(successful_run, client):
    from learning.models import StudentResultReveal
    owner, project, run = successful_run
    assert StudentResultReveal.objects.count() == 0
    project.event.status = 'FINISHED_GRACE'
    project.event.save()
    before = graph_state(project)
    client.force_login(owner)
    for suffix in ('data', 'report', 'comparison', 'explanation'):
        response = client.get(f'/projects/{project.pk}/analyses/{run.pk}/{suffix}/')
        assert response.status_code == 200, response.content
    assert StudentResultReveal.objects.count() == 1
    assert graph_state(project) == before


@pytest.mark.django_db
def test_grace_workspace_is_read_only_with_results_navigation(successful_run, client):
    owner, project, _ = successful_run
    project.event.status = 'FINISHED_GRACE'
    project.event.save()
    client.force_login(owner)
    response = client.get(reverse('projects:workspace', args=[project.pk]))
    assert response.status_code == 200
    assert response.context['bootstrap']['read_only'] is True
    assert response.context['bootstrap']['access']['editable'] is False
    for key in ('result_template', 'comparison_template', 'explanation_template', 'report_template'):
        assert response.context['bootstrap']['urls'][key]


@pytest.mark.django_db
@pytest.mark.parametrize('action', ['materials/new', 'materials/edit', 'materials/delete', 'sections/new',
    'sections/composite/new', 'sections/edit', 'sections/delete', 'strips/material'])
def test_grace_blocks_every_project_resource_post(context, client, action):
    from materials.models import Strip
    from tests.application.test_m7_resource_guards import resource_state
    owner, project, material, section = context
    strip = Strip.objects.create(owner_user=owner, name='条材', width_mm=2, thickness_mm=1, material=material)
    project.event.status = 'FINISHED_GRACE'
    project.event.save()
    path = {'materials/edit':f'materials/{material.pk}/edit', 'materials/delete':f'materials/{material.pk}/delete',
        'sections/edit':f'sections/{section.pk}/edit', 'sections/delete':f'sections/{section.pk}/delete',
        'strips/material':f'strips/{strip.pk}/material'}.get(action, action)
    client.force_login(owner)
    before = resource_state()
    response = client.post(f'/projects/{project.pk}/{path}/', {'name':'更改', 'E_MPa':'2000',
        'density_g_per_mm3':'0.001', 'source_type':'MEASURED','width_mm':'2','height_mm':'4','material_id':''})
    assert response.status_code == 403
    assert resource_state() == before


@pytest.mark.django_db
def test_resource_gets_respect_purged_and_grace_readonly(context, client):
    owner, project, material, _ = context
    client.force_login(owner)
    project.event.status = 'FINISHED_GRACE'
    project.event.save()
    index = f'/projects/{project.pk}/materials/'
    response = client.get(index)
    assert response.status_code == 200
    assert '/new/' not in response.content.decode()
    assert '/edit/' not in response.content.decode()
    assert '/delete/' not in response.content.decode()
    assert client.get(f'{index}{material.pk}/edit/').status_code == 403
    project.event.status = 'PURGED'
    project.event.save()
    for path in (index, f'{index}new/', f'{index}{material.pk}/edit/'):
        assert client.get(path).status_code in {403,404}


@pytest.mark.django_db
def test_grace_owner_readonly_header_does_not_misidentify_owner(context, client):
    owner, project, _, _ = context
    project.event.status = 'FINISHED_GRACE'
    project.event.save()
    client.force_login(owner)
    response = client.get(f'/projects/{project.pk}/workspace/')
    assert '只读（项目所有者）' in response.content.decode()
    assert '只读（非项目所有者）' not in response.content.decode()
