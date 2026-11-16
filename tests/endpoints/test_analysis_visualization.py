"""AV-01 saved-Run facts and readonly HTTP disclosure contract."""
from copy import deepcopy
import json

import pytest
from django.urls import reverse

from tests.application.test_physical_draft import context
from tests.application.test_analysis_acceptance import save_bt01_draft
from tests.application.test_node_joint_learning import save_v2_bt01


@pytest.fixture(params=['v1', 'v2'])
def saved_context(context, request):
    from analysis.orchestration import analyze_project
    owner, project, material, section = context
    # Normal saved-run fixtures must remain readable as the calendar advances.
    # Access-matrix expiry cases still set their own expired purge_at explicitly.
    from datetime import timedelta
    from django.utils import timezone
    project.event.starts_at = timezone.now() - timedelta(days=1)
    project.event.ends_at = timezone.now() + timedelta(days=1)
    project.event.save()
    (save_bt01_draft if request.param == 'v1' else save_v2_bt01)(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    assert run.status == 'SUCCESS'
    return owner, project, run, material, section


def frozen_artifacts(run):
    run.refresh_from_db()
    run.model_revision.refresh_from_db()
    return json.dumps({
        'run': {'input': run.solver_input_json, 'result': run.result_json,
                'input_hash': run.input_hash, 'status': run.status,
                'revision': run.model_revision_id, 'project': run.project_id},
        'revision': {'snapshot': run.model_revision.physical_snapshot_json,
                     'hash': run.model_revision.model_hash,
                     'source': run.model_revision.source_draft_version},
    }, sort_keys=True, ensure_ascii=False)


@pytest.mark.django_db
def test_existing_saved_run_fields_support_visualization(saved_context):
    """Losing saved u/R/N, graph or historical Revision binding breaks AV-01."""
    _, project, run, _, _ = saved_context
    graph = run.solver_input_json
    assert [(n['x_mm'], n['y_mm']) for n in graph['nodes']] == [(0.0, 0.0), (1000.0, 0.0)]
    assert len(graph['members']) == 1
    member = graph['members'][0]
    assert {member['node_i'], member['node_j']} == {n['id'] for n in graph['nodes']}
    assert graph['physical_member_mapping'] == {'m1:1': 'm1'}
    assert len(graph['supports']) == 2
    assert graph['loads'][0]['fx_N'] == 100.0 and graph['loads'][0]['fy_N'] == 0.0
    result = run.result_json
    u = {row['analysis_node_id']: row for row in result['node_displacements']}
    right = member['node_j']
    assert u[right]['ux_mm'] == pytest.approx(100.0 * 1000.0 / (2000.0 * 6.0))
    assert u[right]['uy_mm'] == 0.0
    assert sorted(row['rx_N'] for row in result['support_reactions']) == pytest.approx([-100.0, 0.0])
    assert all(row['ry_N'] == 0.0 for row in result['support_reactions'])
    assert result['member_results'][0]['axial_force_N'] == pytest.approx(100.0)
    assert result['member_results'][0]['physical_member_id'] == 'm1'
    assert run.model_revision.project_id == project.pk
    assert run.model_revision.source_draft_version == 1


@pytest.mark.django_db
def test_saved_run_geometry_and_facts_survive_draft_and_library_edits(saved_context):
    """Historical A must not be rebuilt from changed Draft/library B."""
    from analysis.orchestration import analyze_project
    from modeling.services import save_physical_draft
    from projects.workspace import _draft
    owner, project, run_a, material, _ = saved_context
    before = frozen_artifacts(run_a)
    material.E_MPa = 4000
    material.save(update_fields=['E_MPa'])
    payload = deepcopy(_draft(project))
    payload['expected_draft_version'] = project.draft_version
    payload['nodes'][1]['x_mm'] = 2000.0
    payload['node_loads'][0]['fx_N'] = 200.0
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    run_b = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    assert run_b.status == 'SUCCESS' and run_b.pk != run_a.pk
    assert run_b.model_revision_id != run_a.model_revision_id
    assert run_b.solver_input_json['nodes'][1]['x_mm'] == 2000.0
    assert run_b.result_json['member_results'][0]['axial_force_N'] == pytest.approx(200.0)
    assert frozen_artifacts(run_a) == before


def url(project,run):
    return reverse('projects:analysis_visualization',kwargs={'project_id':project.pk,'run_id':run.pk})


def reveal(client,project,run):
    response=client.get(reverse('projects:analysis_data',kwargs={'project_id':project.pk,'run_id':run.pk}))
    assert response.status_code==200


@pytest.mark.django_db
def test_student_projection_requires_existing_disclosure(saved_context,client):
    from learning.models import StudentResultReveal
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    owner,project,run,_,_=saved_context;client.force_login(owner)
    response=client.get(url(project,run))
    assert response.status_code==409
    assert response.json()['error']['code']=='VISUALIZATION_REVEAL_REQUIRED'
    assert 'visualization' not in response.json() and not StudentResultReveal.objects.exists()
    reveal(client,project,run);before=frozen_artifacts(run)
    with CaptureQueriesContext(connection) as queries:response=client.get(url(project,run))
    assert response.status_code==200 and response.json()['visualization']['status']=='READY'
    assert all(not q['sql'].lstrip().upper().startswith(('INSERT','UPDATE','DELETE','REPLACE')) for q in queries)
    assert StudentResultReveal.objects.count()==1 and frozen_artifacts(run)==before
    assert 'private' in response['Cache-Control'] and 'no-store' in response['Cache-Control']


@pytest.mark.django_db
def test_reveal_failure_cannot_unlock_projection(saved_context,client,monkeypatch):
    import projects.views
    owner,project,run,_,_=saved_context;client.force_login(owner)
    def fail(**kwargs):raise RuntimeError('private reveal failure')
    monkeypatch.setattr(projects.views,'record_student_result_reveal',fail)
    response=client.get(reverse('projects:analysis_data',kwargs={'project_id':project.pk,'run_id':run.pk}))
    assert response.status_code==500
    assert client.get(url(project,run)).status_code==409
    assert b'private reveal failure' not in client.get(url(project,run)).content


@pytest.mark.django_db
@pytest.mark.parametrize('role',['MANAGER','DEVELOPER'])
def test_visualization_readonly_roles_do_not_create_student_reveal(saved_context,client,role):
    from accounts.models import User
    from competitions.models import EventMembership
    from learning.models import StudentResultReveal
    _,project,run,_,_=saved_context
    actor=User.objects.create_user('av01-reader',role=role)
    if role=='MANAGER':EventMembership.objects.create(user=actor,event=project.event,membership_type='MANAGER')
    client.force_login(actor);response=client.get(url(project,run))
    assert response.status_code==200 and response.json()['visualization']['provenance']['readonly'] is True
    assert not StudentResultReveal.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize('case,expected',[('anonymous',302),('outsider',403),('inactive',302),('membership',403),('wrong_project',404),('wrong_run',404),('purged',403),('expired_active',403),('unsuccessful',422)])
def test_visualization_access_matrix(saved_context,client,case,expected):
    from accounts.models import User
    from competitions.models import CompetitionEvent,EventMembership
    from analysis.models import AnalysisRun
    from django.utils import timezone
    from datetime import timedelta
    owner,project,run,_,_=saved_context;target=url(project,run)
    if case!='anonymous':client.force_login(owner)
    if case=='outsider':client.force_login(User.objects.create_user('av01-outsider'))
    elif case=='inactive':owner.is_active=False;owner.save(update_fields=['is_active'])
    elif case=='membership':EventMembership.objects.filter(user=owner,event=project.event).update(is_active=False)
    elif case=='wrong_project':target=target.replace(f'/projects/{project.pk}/','/projects/999999/')
    elif case=='wrong_run':target=target.replace(f'/analyses/{run.pk}/','/analyses/999999/')
    elif case=='purged':CompetitionEvent.objects.filter(pk=project.event_id).update(status='PURGED')
    elif case=='expired_active':CompetitionEvent.objects.filter(pk=project.event_id).update(status='ACTIVE',purge_at=timezone.now()-timedelta(seconds=1))
    elif case=='unsuccessful':AnalysisRun.objects.filter(pk=run.pk).update(status='SOLVER_FAILED')
    response=client.get(target)
    assert response.status_code==expected
    assert 'no-store' in response['Cache-Control']
    assert 'visualization' not in (response.json() if expected!=302 else {})


@pytest.mark.django_db
def test_grace_uses_existing_disclosure_and_no_visualization_writes(saved_context,client):
    from competitions.models import CompetitionEvent
    from learning.models import StudentResultReveal
    owner,project,run,_,_=saved_context
    CompetitionEvent.objects.filter(pk=project.event_id).update(status='FINISHED_GRACE')
    client.force_login(owner)
    assert client.get(url(project,run)).status_code==409
    reveal(client,project,run)
    assert client.get(url(project,run)).status_code==200
    assert StudentResultReveal.objects.count()==1


@pytest.mark.django_db
def test_visualization_endpoint_never_invokes_solver_or_writes_reveal(saved_context,client,monkeypatch):
    from analysis import orchestration
    from mechanics.truss2d.solver import Truss2DSolver
    owner,project,run,_,_=saved_context;client.force_login(owner);reveal(client,project,run)
    def forbidden(*a,**k):raise AssertionError('forbidden compute/write')
    monkeypatch.setattr(orchestration,'idealize',forbidden);monkeypatch.setattr(Truss2DSolver,'solve',forbidden)
    import projects.views
    monkeypatch.setattr(projects.views,'record_student_result_reveal',forbidden)
    response=client.get(url(project,run))
    assert response.status_code==200


@pytest.mark.django_db
def test_bootstrap_exposes_only_exact_run_url_template(saved_context,client):
    owner,project,run,_,_=saved_context;client.force_login(owner)
    response=client.get(reverse('projects:workspace',kwargs={'project_id':project.pk}))
    assert response.status_code==200
    assert response.context['bootstrap']['urls']['visualization_template']==f'/projects/{project.pk}/analyses/{{run_id}}/visualization/'


@pytest.mark.django_db
def test_exact_historical_a_b_a_does_not_follow_latest_draft(saved_context,client):
    from analysis.orchestration import analyze_project
    from modeling.services import save_physical_draft
    from projects.workspace import _draft
    owner,project,run_a,material,_=saved_context;client.force_login(owner);reveal(client,project,run_a)
    a=client.get(url(project,run_a)).json()['visualization']
    payload=deepcopy(_draft(project));payload['expected_draft_version']=project.draft_version
    payload['nodes'][1]['x_mm']=2000.0;payload['node_loads'][0]['fx_N']=200.0
    save_physical_draft(actor=owner,project=project,payload=payload);project.refresh_from_db()
    run_b=analyze_project(project=project,actor=owner,expected_draft_version=project.draft_version);reveal(client,project,run_b)
    b=client.get(url(project,run_b)).json()['visualization'];again=client.get(url(project,run_a)).json()['visualization']
    assert again==a and b['provenance']['analysis_run_id']==run_b.pk
    assert a['nodes'][1]['x_mm']==1000.0 and b['nodes'][1]['x_mm']==2000.0
    assert b['segments'][0]['axial_force_N']!=a['segments'][0]['axial_force_N']


@pytest.mark.django_db
def test_run_from_other_existing_project_and_post_are_rejected(saved_context,client):
    from projects.models import Project
    owner,project,run,_,_=saved_context;client.force_login(owner)
    other=Project.objects.create(event=project.event,owner_user=owner,name='另一个合成项目')
    assert client.get(url(other,run)).status_code==404
    assert client.post(url(project,run),data={}).status_code==405
