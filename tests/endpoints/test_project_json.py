import json

import pytest
from django.test import Client
from django.urls import reverse

from tests.application.test_physical_draft import context, valid_payload


def post_json(client, name, payload, **kwargs):
    return client.post(reverse(name, kwargs=kwargs), data=json.dumps(payload), content_type='application/json')


def save_bt01(client, project, material, section, *, version=0):
    payload = valid_payload(material, section, version=version)
    payload['connections'].append({'client_key': 'c2', 'geometry_node_client_key': 'n2', 'participating_member_client_keys': ['m1']})
    payload['supports'].append({'target_connection_client_key': 'c2', 'support_type': 'ROLLER', 'restrained_axis': 'Y'})
    payload['node_loads'][0].update({'target_connection_client_key': 'c2', 'fx_N': 100.0, 'fy_N': 0.0})
    response = post_json(client, 'projects:model_save', payload, project_id=project.id)
    project.refresh_from_db()
    assert response.status_code == 200


def singular_payload(material, section, *, version=0):
    payload = valid_payload(material, section, version=version)
    payload['nodes'].append({'client_key': 'nmid', 'x_mm': 400.0, 'y_mm': 0.0, 'label': '中点'})
    payload['connections'].extend([
        {'client_key': 'cmid', 'geometry_node_client_key': 'nmid', 'participating_member_client_keys': ['m1']},
        {'client_key': 'c2', 'geometry_node_client_key': 'n2', 'participating_member_client_keys': ['m1']},
    ])
    payload['supports'].append({'target_connection_client_key': 'c2', 'support_type': 'ROLLER', 'restrained_axis': 'Y'})
    payload['node_loads'][0].update({'target_connection_client_key': 'c2', 'fx_N': 0.0, 'fy_N': -100.0})
    return payload


@pytest.mark.django_db
def test_post_endpoints_require_csrf_after_authentication(context):
    owner, project, material, section = context
    client = Client(enforce_csrf_checks=True)
    client.force_login(owner)

    response = post_json(client, 'projects:model_save', valid_payload(material, section), project_id=project.id)

    assert response.status_code == 403


@pytest.mark.django_db
def test_all_project_json_endpoints_require_authenticated_user(context, client):
    _, project, material, section = context
    urls = [
        ('post', reverse('projects:model_save', kwargs={'project_id': project.id}), valid_payload(material, section)),
        ('post', reverse('projects:model_check', kwargs={'project_id': project.id}), {'expected_draft_version': 0}),
        ('post', reverse('projects:analyze', kwargs={'project_id': project.id}), {'expected_draft_version': 0}),
        ('get', reverse('projects:analysis_data', kwargs={'project_id': project.id, 'run_id': 999}), None),
        ('post', reverse('projects:section_preview', kwargs={'project_id': project.id}), {'schema_version': 'section-definition-v1'}),
    ]

    for method, url, payload in urls:
        response = getattr(client, method)(url, data=json.dumps(payload) if payload is not None else None, content_type='application/json')
        assert response.status_code == 302
        assert response.url.startswith('/accounts/login/')


@pytest.mark.django_db
def test_model_save_adapts_success_stale_validation_and_malformed_json(context, client):
    owner, project, material, section = context
    client.force_login(owner)
    payload = valid_payload(material, section)

    saved = post_json(client, 'projects:model_save', payload, project_id=project.id)
    stale = post_json(client, 'projects:model_save', payload, project_id=project.id)
    invalid = valid_payload(material, section, version=1)
    invalid['supports'][0]['restrained_axis'] = 'X'
    blocked = post_json(client, 'projects:model_save', invalid, project_id=project.id)
    malformed = client.post(reverse('projects:model_save', kwargs={'project_id': project.id}), data='{', content_type='application/json')

    assert saved.status_code == 200
    assert saved.json() == {'ok': True, 'project_id': project.id, 'draft_version': 1, 'schema_version': 'physical-draft-v1', 'validation': {'errors': [], 'warnings': []}}
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'STALE_DRAFT'
    assert blocked.status_code == 422 and blocked.json()['error']['code'] == 'INVALID_DRAFT'
    assert malformed.status_code == 400 and malformed.json()['error']['code'] == 'MALFORMED_JSON'
    project.refresh_from_db()
    assert project.draft_version == 1


@pytest.mark.django_db
def test_model_check_is_transient_and_maps_singular_result_to_chinese(context, client):
    from analysis.models import AnalysisRun, ModelRevision

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    before = (ModelRevision.objects.count(), AnalysisRun.objects.count(), project.draft_version)
    valid = post_json(client, 'projects:model_check', {'expected_draft_version': 1}, project_id=project.id)

    assert valid.status_code == 200
    assert valid.json() == {'ok': True, 'draft_version': 1, 'issues': []}
    project.refresh_from_db()
    assert (ModelRevision.objects.count(), AnalysisRun.objects.count(), project.draft_version) == before
    singular_saved = post_json(client, 'projects:model_save', singular_payload(material, section, version=1), project_id=project.id)
    singular_before = (ModelRevision.objects.count(), AnalysisRun.objects.count(), 2)
    singular = post_json(client, 'projects:model_check', {'expected_draft_version': 2}, project_id=project.id)

    assert singular_saved.status_code == 200
    assert singular.status_code == 200
    assert singular.json()['ok'] is False
    assert singular.json()['issues'][0]['code'] == 'SINGULAR_GLOBAL_STIFFNESS'
    assert singular.json()['issues'][0]['human_message'].isascii() is False
    project.refresh_from_db()
    assert (ModelRevision.objects.count(), AnalysisRun.objects.count(), project.draft_version) == singular_before


@pytest.mark.django_db
def test_analyze_returns_traceable_success_and_validation_failure(context, client):
    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)

    success = post_json(client, 'projects:analyze', {'expected_draft_version': 1}, project_id=project.id)
    stale = post_json(client, 'projects:analyze', {'expected_draft_version': 0}, project_id=project.id)

    assert success.status_code == 200
    body = success.json()
    assert body['ok'] is True and body['status'] == 'SUCCESS'
    assert body['analysis_run_id'] and body['model_revision_id']
    assert body['result_schema_version'] == 'truss2d-result-v1'
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'STALE_DRAFT'
    assert post_json(client, 'projects:model_save', singular_payload(material, section, version=1), project_id=project.id).status_code == 200
    failed = post_json(client, 'projects:analyze', {'expected_draft_version': 2}, project_id=project.id)
    assert failed.status_code == 422
    assert failed.json()['status'] == 'VALIDATION_FAILED'
    assert failed.json()['error']['code'] == 'SINGULAR_GLOBAL_STIFFNESS'


@pytest.mark.django_db
def test_analyze_http_accepts_null_and_completed_prediction_without_result_leakage(context, client):
    from learning.models import Prediction
    from learning.services import complete_prediction, create_prediction

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    payload = {
        'schema_version': 'prediction-v1',
        'member_judgments': [
            {'physical_member_client_key': 'm1', 'predicted_state': 'TENSION'},
        ],
        'max_displacement_location': {
            'kind': 'CONNECTION', 'connection_client_key': 'c2',
        },
        'representative_load_path': [
            {'kind': 'CONNECTION', 'connection_client_key': 'c1'},
            {'kind': 'PHYSICAL_MEMBER', 'physical_member_client_key': 'm1'},
            {'kind': 'CONNECTION', 'connection_client_key': 'c2'},
        ],
    }
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=1)
    prediction = complete_prediction(
        prediction=prediction, actor=owner, expected_draft_version=1, payload=payload,
    )

    omitted = post_json(client, 'projects:analyze', {'expected_draft_version': 1}, project_id=project.id)
    explicit_null = post_json(
        client, 'projects:analyze',
        {'expected_draft_version': 1, 'prediction_id': None}, project_id=project.id,
    )
    supplied = post_json(
        client, 'projects:analyze',
        {'expected_draft_version': 1, 'prediction_id': prediction.id}, project_id=project.id,
    )

    assert omitted.status_code == explicit_null.status_code == supplied.status_code == 200
    from analysis.models import AnalysisRun
    assert AnalysisRun.objects.get(pk=omitted.json()['analysis_run_id']).prediction_id is None
    assert AnalysisRun.objects.get(pk=explicit_null.json()['analysis_run_id']).prediction_id is None
    assert AnalysisRun.objects.get(pk=supplied.json()['analysis_run_id']).prediction_id == prediction.id
    for response in (omitted, explicit_null, supplied):
        body = response.json()
        assert set(body) == {
            'ok', 'analysis_run_id', 'model_revision_id', 'status', 'result_schema_version',
        }
        serialized = json.dumps(body)
        for forbidden in (
            'axial_force_N', 'axial_stress_MPa', 'node_displacements',
            'support_reactions', 'member_results', 'total_mass_g',
        ):
            assert forbidden not in serialized


@pytest.mark.django_db
def test_analyze_http_rejects_unknown_fields_and_noninteger_prediction_id(context, client):
    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)

    unknown = post_json(
        client, 'projects:analyze',
        {'expected_draft_version': 1, 'prediction_id': None, 'result': True},
        project_id=project.id,
    )
    invalid_id = post_json(
        client, 'projects:analyze',
        {'expected_draft_version': 1, 'prediction_id': '1'},
        project_id=project.id,
    )

    for response in (unknown, invalid_id):
        assert response.status_code == 400
        assert response.json()['error']['code'] == 'INVALID_REQUEST'


@pytest.mark.django_db
def test_analyze_http_maps_unexpected_prediction_service_failure_to_safe_json(
    context, monkeypatch
):
    import projects.views

    owner, project, _, _ = context
    boundary_client = Client(raise_request_exception=False)
    boundary_client.force_login(owner)

    def fail_analysis(**kwargs):
        raise RuntimeError('/private/server/path database secret result_json axial_force_N')

    monkeypatch.setattr(projects.views, 'analyze_project', fail_analysis)
    response = post_json(
        boundary_client,
        'projects:analyze',
        {'expected_draft_version': project.draft_version, 'prediction_id': 1},
        project_id=project.id,
    )

    assert response.status_code == 500
    assert response.headers['Content-Type'].startswith('application/json')
    assert response.json() == {
        'ok': False,
        'error': {
            'code': 'INTERNAL_ERROR',
            'message': '服务器暂时无法处理请求，请稍后重试。',
            'details': {},
        },
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('kind', 'expected_code', 'expected_status'),
    [
        ('DRAFT', 'PREDICTION_NOT_ELIGIBLE', 409),
        ('INVALIDATED', 'PREDICTION_NOT_ELIGIBLE', 409),
        ('STALE', 'PREDICTION_STALE_DRAFT', 409),
        ('CROSS_PROJECT', 'PREDICTION_NOT_FOUND', 404),
        ('MISSING', 'PREDICTION_NOT_FOUND', 404),
    ],
)
def test_analyze_http_explicit_invalid_prediction_fails_closed(
    context, client, kind, expected_code, expected_status
):
    from learning.models import Prediction
    from projects.models import Project

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    prediction_project = project
    source_version = 1
    status = Prediction.Status.COMPLETED
    if kind in {'DRAFT', 'INVALIDATED'}:
        status = kind
    elif kind == 'STALE':
        source_version = 0
    elif kind == 'CROSS_PROJECT':
        prediction_project = Project.objects.create(
            event=project.event, owner_user=owner, name='外部预测项目',
        )
    prediction = Prediction.objects.create(
        project=prediction_project,
        source_draft_version=source_version,
        status=status,
        created_by=owner,
        payload_json={},
    )
    prediction_id = prediction.id + 1000 if kind == 'MISSING' else prediction.id

    response = post_json(
        client, 'projects:analyze',
        {'expected_draft_version': 1, 'prediction_id': prediction_id},
        project_id=project.id,
    )

    assert response.status_code == expected_status
    assert response.json()['error']['code'] == expected_code


@pytest.mark.django_db
def test_result_data_enforces_read_scope_and_preserves_failed_metadata(context, client):
    from accounts.models import User
    from analysis.orchestration import analyze_project
    from learning.models import StudentResultReveal
    from projects.models import Project

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    other = User.objects.create_user('endpoint-other')
    client.force_login(other)
    denied = client.get(reverse('projects:analysis_data', kwargs={'project_id': project.id, 'run_id': run.id}))
    other_project = Project.objects.create(event=project.event, owner_user=owner, name='其他项目')
    client.force_login(owner)
    cross_project = client.get(reverse('projects:analysis_data', kwargs={'project_id': other_project.id, 'run_id': run.id}))

    assert denied.status_code == 403
    assert cross_project.status_code == 404
    assert cross_project.json()['error']['code'] == 'PROJECT_NOT_FOUND'
    assert not StudentResultReveal.objects.exists()

    data = client.get(reverse('projects:analysis_data', kwargs={'project_id': project.id, 'run_id': run.id}))

    assert data.status_code == 200
    assert data.json()['result_json']['schema_version'] == 'truss2d-result-v1'
    assert data.json()['input_hash'] == run.input_hash
    assert StudentResultReveal.objects.filter(
        project=project, source_draft_version=1, first_analysis_run=run,
    ).exists()


@pytest.mark.django_db
def test_owner_success_result_read_reveals_once_and_preserves_first_run(context, client):
    from analysis.models import AnalysisRun
    from learning.models import StudentResultReveal

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    first_analyze = post_json(
        client, 'projects:analyze', {'expected_draft_version': 1}, project_id=project.id,
    )
    first_run = AnalysisRun.objects.get(pk=first_analyze.json()['analysis_run_id'])
    first_url = reverse(
        'projects:analysis_data', kwargs={'project_id': project.id, 'run_id': first_run.id},
    )

    first = client.get(first_url)
    evidence = StudentResultReveal.objects.get(project=project, source_draft_version=1)
    original = StudentResultReveal.objects.values().get(pk=evidence.pk)
    repeated = client.get(first_url)
    second_analyze = post_json(
        client, 'projects:analyze', {'expected_draft_version': 1}, project_id=project.id,
    )
    second = client.get(
        reverse(
            'projects:analysis_data',
            kwargs={'project_id': project.id, 'run_id': second_analyze.json()['analysis_run_id']},
        )
    )

    assert first.status_code == repeated.status_code == second.status_code == 200
    assert first.json()['result_json']['schema_version'] == 'truss2d-result-v1'
    assert StudentResultReveal.objects.filter(project=project, source_draft_version=1).count() == 1
    assert StudentResultReveal.objects.values().get(pk=evidence.pk) == original
    assert evidence.first_analysis_run_id == first_run.id


@pytest.mark.django_db
def test_http_reveal_before_completion_blocks_the_draft_prediction(context, client):
    from analysis.models import AnalysisRun
    from learning.models import Prediction, StudentResultReveal

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    created = post_json(
        client, 'learning:prediction_create', {'expected_draft_version': 1},
        project_id=project.id,
    )
    prediction_id = created.json()['prediction_id']
    analyzed = post_json(
        client, 'projects:analyze', {'expected_draft_version': 1}, project_id=project.id,
    )
    run = AnalysisRun.objects.get(pk=analyzed.json()['analysis_run_id'])

    disclosed = client.get(
        reverse(
            'projects:analysis_data', kwargs={'project_id': project.id, 'run_id': run.id},
        )
    )
    completed = post_json(
        client, 'learning:prediction_complete',
        {
            'expected_draft_version': 1,
            'payload': {
                'schema_version': 'prediction-v1',
                'member_judgments': [
                    {'physical_member_client_key': 'm1', 'predicted_state': 'TENSION'},
                ],
                'max_displacement_location': {
                    'kind': 'CONNECTION', 'connection_client_key': 'c2',
                },
                'representative_load_path': [
                    {'kind': 'CONNECTION', 'connection_client_key': 'c1'},
                    {'kind': 'PHYSICAL_MEMBER', 'physical_member_client_key': 'm1'},
                    {'kind': 'CONNECTION', 'connection_client_key': 'c2'},
                ],
            },
        },
        project_id=project.id,
        prediction_id=prediction_id,
    )

    assert created.status_code == 201
    assert analyzed.status_code == disclosed.status_code == 200
    assert run.prediction_id is None
    assert StudentResultReveal.objects.filter(
        project=project, source_draft_version=1, first_analysis_run=run,
    ).exists()
    assert completed.status_code == 409
    assert completed.json()['error']['code'] == 'PREDICTION_AFTER_RESULT_REVEAL'
    prediction = Prediction.objects.get(pk=prediction_id)
    assert prediction.status == Prediction.Status.DRAFT
    assert prediction.payload_json == {}


@pytest.mark.django_db
def test_completed_prediction_http_flow_reveals_without_mutating_prediction(context, client):
    from analysis.models import AnalysisRun
    from learning.models import Prediction, StudentResultReveal

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    payload = {
        'schema_version': 'prediction-v1',
        'member_judgments': [
            {'physical_member_client_key': 'm1', 'predicted_state': 'TENSION'},
        ],
        'max_displacement_location': {
            'kind': 'CONNECTION', 'connection_client_key': 'c2',
        },
        'representative_load_path': [
            {'kind': 'CONNECTION', 'connection_client_key': 'c1'},
            {'kind': 'PHYSICAL_MEMBER', 'physical_member_client_key': 'm1'},
            {'kind': 'CONNECTION', 'connection_client_key': 'c2'},
        ],
    }
    created = post_json(
        client, 'learning:prediction_create', {'expected_draft_version': 1},
        project_id=project.id,
    )
    prediction_id = created.json()['prediction_id']
    completed = post_json(
        client, 'learning:prediction_complete',
        {'expected_draft_version': 1, 'payload': payload},
        project_id=project.id, prediction_id=prediction_id,
    )
    analyzed = post_json(
        client, 'projects:analyze',
        {'expected_draft_version': 1, 'prediction_id': prediction_id},
        project_id=project.id,
    )
    run = AnalysisRun.objects.get(pk=analyzed.json()['analysis_run_id'])

    disclosed = client.get(
        reverse(
            'projects:analysis_data', kwargs={'project_id': project.id, 'run_id': run.id},
        )
    )

    assert created.status_code == 201
    assert completed.status_code == analyzed.status_code == disclosed.status_code == 200
    assert run.prediction_id == prediction_id
    prediction = Prediction.objects.get(pk=prediction_id)
    assert prediction.status == Prediction.Status.COMPLETED
    assert prediction.payload_json == payload
    assert StudentResultReveal.objects.filter(
        project=project, source_draft_version=1, first_analysis_run=run,
    ).exists()


@pytest.mark.django_db
def test_owner_result_reads_create_separate_reveals_after_draft_change(context, client):
    from learning.models import StudentResultReveal

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    first = post_json(
        client, 'projects:analyze', {'expected_draft_version': 1}, project_id=project.id,
    )
    assert client.get(
        reverse(
            'projects:analysis_data',
            kwargs={'project_id': project.id, 'run_id': first.json()['analysis_run_id']},
        )
    ).status_code == 200

    save_bt01(client, project, material, section, version=1)
    second = post_json(
        client, 'projects:analyze', {'expected_draft_version': 2}, project_id=project.id,
    )
    assert client.get(
        reverse(
            'projects:analysis_data',
            kwargs={'project_id': project.id, 'run_id': second.json()['analysis_run_id']},
        )
    ).status_code == 200

    assert list(
        StudentResultReveal.objects.filter(project=project)
        .order_by('source_draft_version')
        .values_list('source_draft_version', flat=True)
    ) == [1, 2]


@pytest.mark.django_db
def test_manager_developer_and_failed_result_reads_do_not_reveal(context, client):
    from accounts.models import User
    from analysis.models import AnalysisRun
    from competitions.models import EventMembership
    from learning.models import StudentResultReveal

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    successful = post_json(
        client, 'projects:analyze', {'expected_draft_version': 1}, project_id=project.id,
    )
    success_run_id = successful.json()['analysis_run_id']
    manager = User.objects.create_user('reveal-http-manager', role=User.Role.MANAGER)
    developer = User.objects.create_user('reveal-http-developer', role=User.Role.DEVELOPER)
    EventMembership.objects.create(
        user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER,
    )

    for actor in (manager, developer):
        client.force_login(actor)
        response = client.get(
            reverse(
                'projects:analysis_data',
                kwargs={'project_id': project.id, 'run_id': success_run_id},
            )
        )
        assert response.status_code == 200
        assert not StudentResultReveal.objects.exists()

    client.force_login(owner)
    for failed_status in (
        AnalysisRun.Status.VALIDATION_FAILED,
        AnalysisRun.Status.SOLVER_FAILED,
    ):
        AnalysisRun.objects.filter(pk=success_run_id).update(
            status=failed_status,
            failure_code='CONTROLLED_FAILURE',
            result_json=None,
        )
        failed = client.get(
            reverse(
                'projects:analysis_data',
                kwargs={'project_id': project.id, 'run_id': success_run_id},
            )
        )
        assert failed.status_code == 200
        assert failed.json()['status'] == failed_status
        assert not StudentResultReveal.objects.exists()


@pytest.mark.django_db
def test_result_data_fails_closed_before_disclosure_if_reveal_persistence_fails(
    context, client, monkeypatch
):
    from analysis.models import AnalysisRun
    import projects.views

    owner, project, material, section = context
    client.force_login(owner)
    save_bt01(client, project, material, section)
    run = AnalysisRun.objects.get(
        pk=post_json(
            client, 'projects:analyze', {'expected_draft_version': 1}, project_id=project.id,
        ).json()['analysis_run_id']
    )

    def fail_reveal(**kwargs):
        raise RuntimeError('/private/server/path database secret')

    monkeypatch.setattr(projects.views, 'record_student_result_reveal', fail_reveal)
    response = client.get(
        reverse(
            'projects:analysis_data', kwargs={'project_id': project.id, 'run_id': run.id},
        )
    )

    assert response.status_code == 500
    assert response.json()['error']['code'] == 'RESULT_REVEAL_FAILED'
    serialized = json.dumps(response.json())
    assert 'result_json' not in serialized
    assert 'database secret' not in serialized
    assert '/private/server/path' not in serialized


@pytest.mark.django_db
def test_result_data_allows_assigned_manager_and_exposes_failed_run_traceability(context, client):
    from accounts.models import User
    from analysis.orchestration import analyze_project
    from competitions.models import EventMembership

    owner, project, material, section = context
    client.force_login(owner)
    assert post_json(client, 'projects:model_save', singular_payload(material, section), project_id=project.id).status_code == 200
    project.refresh_from_db()
    failed_run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    manager = User.objects.create_user('endpoint-result-manager', role=User.Role.MANAGER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    client.force_login(manager)
    response = client.get(reverse('projects:analysis_data', kwargs={'project_id': project.id, 'run_id': failed_run.id}))

    assert response.status_code == 200
    assert response.json()['status'] == 'VALIDATION_FAILED'
    assert response.json()['failure_code'] == 'SINGULAR_GLOBAL_STIFFNESS'
    assert response.json()['diagnostics']


@pytest.mark.django_db
def test_section_preview_uses_engine_without_persisting_or_mutating_project(context, client):
    from analysis.models import AnalysisRun, ModelRevision
    from materials.models import Section

    owner, project, _, _ = context
    client.force_login(owner)
    before = (Section.objects.count(), ModelRevision.objects.count(), AnalysisRun.objects.count(), project.draft_version)
    rectangle = {'schema_version': 'section-definition-v1', 'type': 'rectangle', 'width_mm': 2.0, 'height_mm': 6.0, 'density_g_per_mm3': 0.0007}
    preview = post_json(client, 'projects:section_preview', rectangle, project_id=project.id)
    overlapping = {'schema_version': 'section-definition-v1', 'type': 'composite', 'components': [rectangle, rectangle]}
    rejected = post_json(client, 'projects:section_preview', overlapping, project_id=project.id)
    project.refresh_from_db()

    assert preview.status_code == 200
    assert preview.json()['properties']['A_mm2'] == pytest.approx(12)
    assert preview.json()['properties']['Ix_mm4'] == pytest.approx(36)
    assert preview.json()['properties']['Iy_mm4'] == pytest.approx(4)
    assert rejected.status_code == 422 and rejected.json()['error']['code'] == 'OVERLAP_UNSUPPORTED'
    assert (Section.objects.count(), ModelRevision.objects.count(), AnalysisRun.objects.count(), project.draft_version) == before


@pytest.mark.django_db
def test_mutating_endpoints_deny_other_user_and_manager_without_expanding_policy(context, client):
    from accounts.models import User
    from competitions.models import EventMembership

    owner, project, material, section = context
    other = User.objects.create_user('endpoint-write-other')
    manager = User.objects.create_user('endpoint-write-manager', role=User.Role.MANAGER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    rectangle = {'schema_version': 'section-definition-v1', 'type': 'rectangle', 'width_mm': 2.0, 'height_mm': 6.0, 'density_g_per_mm3': 0.0007}
    for actor in (other, manager):
        client.force_login(actor)
        assert post_json(client, 'projects:model_save', valid_payload(material, section), project_id=project.id).status_code == 403
        assert post_json(client, 'projects:model_check', {'expected_draft_version': 0}, project_id=project.id).status_code == 403
        assert post_json(client, 'projects:analyze', {'expected_draft_version': 0}, project_id=project.id).status_code == 403
        assert post_json(client, 'projects:section_preview', rectangle, project_id=project.id).status_code == 403


@pytest.mark.django_db
def test_endpoint_authorization_respects_owner_manager_developer_and_purged_policy(context, client):
    from accounts.models import User
    from competitions.models import CompetitionEvent, EventMembership

    owner, project, material, section = context
    manager = User.objects.create_user('endpoint-manager', role=User.Role.MANAGER)
    developer = User.objects.create_user('endpoint-developer', role=User.Role.DEVELOPER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    client.force_login(manager)
    manager_analyze = post_json(client, 'projects:analyze', {'expected_draft_version': 0}, project_id=project.id)
    client.force_login(developer)
    developer_save = post_json(client, 'projects:model_save', valid_payload(material, section), project_id=project.id)
    project.event.status = CompetitionEvent.Status.PURGED
    project.event.save(update_fields=['status'])
    client.force_login(owner)
    purged_check = post_json(client, 'projects:model_check', {'expected_draft_version': 1}, project_id=project.id)

    assert manager_analyze.status_code == 403
    assert developer_save.status_code == 200
    assert purged_check.status_code == 403
