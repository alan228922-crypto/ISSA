import pytest
from tests.application.test_physical_draft import context, valid_payload


def save_bt01_draft(owner, project, material, section, *, fx_N=100.0):
    """建立手算 B/T01 水平轴向杆，期望值不依赖生产 Solver。"""
    from modeling.services import save_physical_draft

    payload = valid_payload(material, section, version=project.draft_version)
    payload['connections'].append({
        'client_key': 'c2', 'geometry_node_client_key': 'n2',
        'participating_member_client_keys': ['m1'],
    })
    payload['supports'].append({
        'target_connection_client_key': 'c2', 'support_type': 'ROLLER',
        'restrained_axis': 'Y',
    })
    payload['node_loads'][0].update({
        'target_connection_client_key': 'c2', 'fx_N': fx_N, 'fy_N': 0.0,
    })
    result = save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    return result


def save_singular_draft(owner, project, material, section):
    """中间连接点保留无刚度 uy 自由度，预校验后由 Solver 识别奇异性。"""
    from modeling.services import save_physical_draft

    payload = valid_payload(material, section, version=project.draft_version)
    payload['nodes'].append({'client_key': 'nmid', 'x_mm': 400.0, 'y_mm': 0.0, 'label': '中点'})
    payload['connections'].extend([
        {
            'client_key': 'cmid', 'geometry_node_client_key': 'nmid',
            'participating_member_client_keys': ['m1'],
        },
        {
        'client_key': 'c2', 'geometry_node_client_key': 'n2',
        'participating_member_client_keys': ['m1'],
        },
    ])
    payload['supports'].append({
        'target_connection_client_key': 'c2', 'support_type': 'ROLLER',
        'restrained_axis': 'Y',
    })
    payload['node_loads'][0].update({
        'target_connection_client_key': 'c2', 'fx_N': 0.0, 'fy_N': -100.0,
    })
    result = save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    return result

@pytest.mark.django_db
def test_bt01_real_analysis_chain_and_prediction_is_optional(context):
    from analysis.orchestration import analyze_project
    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    project.refresh_from_db()
    run = analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=None)
    result = run.result_json

    # B/T01: P=100 N, L=1000 mm, E=2000 MPa, A=6 mm².
    assert run.status == 'SUCCESS'
    assert result['schema_version'] == 'truss2d-result-v1'
    assert result['node_displacements'][1]['ux_mm'] == pytest.approx(100 * 1000 / (2000 * 6), abs=1e-10)
    assert result['node_displacements'][1]['uy_mm'] == pytest.approx(0, abs=1e-10)
    assert result['member_results'][0]['axial_force_N'] == pytest.approx(100, abs=1e-10)
    assert result['member_results'][0]['axial_stress_MPa'] == pytest.approx(100 / 6, abs=1e-10)
    assert result['support_reactions'][0]['rx_N'] == pytest.approx(-100, abs=1e-10)
    assert result['support_reactions'][0]['ry_N'] == pytest.approx(0, abs=1e-10)
    assert result['total_mass_g'] == pytest.approx(0.0007 * 6 * 1000, abs=1e-10)
    assert result['member_results'][0]['buckling'] is None


@pytest.mark.django_db
def test_same_revision_creates_two_distinct_reproducible_runs(context):
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    first = analyze_project(project=project, actor=owner, expected_draft_version=1)
    second = analyze_project(project=project, actor=owner, expected_draft_version=1)

    assert ModelRevision.objects.filter(project=project).count() == 1
    assert AnalysisRun.objects.filter(project=project).count() == 2
    assert first.id != second.id
    assert first.model_revision_id == second.model_revision_id
    assert first.model_revision.model_hash == second.model_revision.model_hash
    assert first.input_hash == second.input_hash


@pytest.mark.django_db
def test_changed_solver_relevant_draft_creates_new_immutable_revision(context):
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section, fx_N=100.0)
    first = analyze_project(project=project, actor=owner, expected_draft_version=1)
    first_result = first.result_json
    first_hash = first.input_hash
    first_model_hash = first.model_revision.model_hash
    save_bt01_draft(owner, project, material, section, fx_N=125.0)
    second = analyze_project(project=project, actor=owner, expected_draft_version=2)

    assert ModelRevision.objects.filter(project=project).count() == 2
    assert AnalysisRun.objects.filter(project=project).count() == 2
    assert second.model_revision_id != first.model_revision_id
    assert second.model_revision.model_hash != first_model_hash
    assert second.input_hash != first_hash
    first.refresh_from_db()
    assert first.result_json == first_result


def test_input_hash_is_canonical_for_semantics_and_sensitive_to_solver_input():
    from analysis.hashing import model_hash
    from analysis.orchestration import canonical_solver_input
    from mechanics.truss2d.model import Member, Node, NodalLoad, Support, TrussModel

    base = TrussModel('truss2d-input-v1', (Node('a', 0, 0), Node('b', 1000, 0)), (Member('m', 'a', 'b', 2000, 6),), (Support('a', True, True), Support('b', False, True)), (NodalLoad('b', 100, 0),))
    reordered = TrussModel('truss2d-input-v1', tuple(reversed(base.nodes)), base.members, tuple(reversed(base.supports)), tuple(reversed(base.nodal_loads)))
    baseline = canonical_solver_input(base, {'m': 'pm'})
    assert model_hash(baseline) == model_hash({'physical_member_mapping': {'m': 'pm'}, 'loads': baseline['loads'], 'supports': baseline['supports'], 'members': baseline['members'], 'nodes': baseline['nodes'], 'schema_version': baseline['schema_version']})
    assert model_hash(baseline) == model_hash(canonical_solver_input(reordered, {'m': 'pm'}))
    for path, value in ((('loads', 0, 'fx_N'), 101), (('members', 0, 'E_MPa'), 2001), (('members', 0, 'A_mm2'), 7), (('supports', 1, 'restrain_uy'), False)):
        candidate = {key: [dict(item) for item in val] if isinstance(val, list) else val for key, val in baseline.items()}
        candidate[path[0]][path[1]][path[2]] = value
        assert model_hash(candidate) != model_hash(baseline)


@pytest.mark.django_db
def test_split_member_persists_segment_mass_without_physical_member_double_count(context):
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    from modeling.services import save_physical_draft
    payload = valid_payload(material, section)
    payload['nodes'].append({'client_key': 'nmid', 'x_mm': 400.0, 'y_mm': 0.0, 'label': '中点'})
    payload['connections'].extend([
        {'client_key': 'cmid', 'geometry_node_client_key': 'nmid', 'participating_member_client_keys': ['m1']},
        {'client_key': 'c2', 'geometry_node_client_key': 'n2', 'participating_member_client_keys': ['m1']},
    ])
    payload['supports'].append({'target_connection_client_key': 'c2', 'support_type': 'ROLLER', 'restrained_axis': 'Y'})
    payload['supports'].append({'target_connection_client_key': 'cmid', 'support_type': 'ROLLER', 'restrained_axis': 'Y'})
    payload['node_loads'][0].update({'target_connection_client_key': 'c2', 'fx_N': 100.0, 'fy_N': 0.0})
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    results = run.result_json['member_results']

    assert run.status == 'SUCCESS'
    assert [item['physical_member_id'] for item in results] == ['m1', 'm1']
    assert [item['mass_g'] for item in results] == pytest.approx([0.0007 * 6 * 400, 0.0007 * 6 * 600])
    assert run.result_json['total_mass_g'] == pytest.approx(0.0007 * 6 * 1000)


@pytest.mark.django_db
def test_controlled_solver_failure_is_traceable_after_revision_creation(context):
    from analysis.models import AnalysisRun, ValidationLog
    from analysis.orchestration import analyze_project

    class ControlledFailureSolver:
        def solve(self, model):
            raise RuntimeError('controlled test failure')

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1, solver=ControlledFailureSolver())

    assert run.status == AnalysisRun.Status.SOLVER_FAILED
    assert run.failure_code == 'SOLVER_FAILED'
    assert run.finished_at is not None
    assert run.diagnostics_json == {'stage': 'SOLVER'}
    assert ValidationLog.objects.get(analysis_run=run).model_revision_id == run.model_revision_id


@pytest.mark.django_db
def test_singular_analysis_is_validation_failure_with_traceability(context):
    from analysis.models import AnalysisRun, ModelRevision, ValidationLog
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_singular_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)

    assert ModelRevision.objects.filter(project=project).exists()
    assert run.status == AnalysisRun.Status.VALIDATION_FAILED
    assert run.failure_code == 'SINGULAR_GLOBAL_STIFFNESS'
    assert run.result_json is None
    assert ValidationLog.objects.filter(analysis_run=run, model_revision=run.model_revision).exists()


@pytest.mark.django_db
def test_model_check_valid_is_transient_and_does_not_pollute_analysis_history(context):
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import check_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    before = (ModelRevision.objects.count(), AnalysisRun.objects.count(), project.draft_version)
    response = check_project(project=project, actor=owner, expected_draft_version=1)
    project.refresh_from_db()

    assert response['ok'] is True
    assert (ModelRevision.objects.count(), AnalysisRun.objects.count(), project.draft_version) == before


@pytest.mark.django_db
def test_model_check_singular_is_transient_and_maps_machine_code_to_chinese(context):
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import check_project

    owner, project, material, section = context
    save_singular_draft(owner, project, material, section)
    before = (ModelRevision.objects.count(), AnalysisRun.objects.count(), project.draft_version)
    response = check_project(project=project, actor=owner, expected_draft_version=1)
    project.refresh_from_db()

    assert response['ok'] is False
    assert response['issues'][0]['code'] == 'SINGULAR_GLOBAL_STIFFNESS'
    assert response['issues'][0]['human_message'].isascii() is False
    assert response['issues'][0]['severity']
    assert response['issues'][0]['stage'] == 'MECHANICS'
    assert 'entity_refs' in response['issues'][0]
    assert (ModelRevision.objects.count(), AnalysisRun.objects.count(), project.draft_version) == before


@pytest.mark.django_db
def test_model_check_connection_off_member_maps_to_chinese_without_persistence(context):
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import check_project
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload['nodes'].append({'client_key': 'noff', 'x_mm': 500.0, 'y_mm': 1.0, 'label': '偏离'})
    payload['connections'].append({'client_key': 'coff', 'geometry_node_client_key': 'noff', 'participating_member_client_keys': ['m1']})
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    response = check_project(project=project, actor=owner, expected_draft_version=1)

    assert response['ok'] is False
    assert response['issues'][0]['code'] == 'CONNECTION_OFF_MEMBER'
    assert response['issues'][0]['human_message'].isascii() is False
    assert ModelRevision.objects.filter(project=project).count() == 0
    assert AnalysisRun.objects.filter(project=project).count() == 0


@pytest.mark.django_db
def test_server_side_authorization_and_purged_lifecycle_do_not_create_history(context):
    from accounts.models import User
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project, check_project
    from competitions.models import CompetitionEvent, EventMembership

    owner, project, material, section = context
    project.event.status = CompetitionEvent.Status.ACTIVE
    project.event.save(update_fields=['status'])
    save_bt01_draft(owner, project, material, section)
    other = User.objects.create_user('analysis-other')
    manager = User.objects.create_user('analysis-manager', role=User.Role.MANAGER)
    developer = User.objects.create_user('analysis-developer', role=User.Role.DEVELOPER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    for actor in (other, manager):
        with pytest.raises(AnalysisError, match='PROJECT_(ANALYZE|CHECK)_DENIED'):
            analyze_project(project=project, actor=actor, expected_draft_version=1)
        with pytest.raises(AnalysisError, match='PROJECT_(ANALYZE|CHECK)_DENIED'):
            check_project(project=project, actor=actor, expected_draft_version=1)
    assert analyze_project(project=project, actor=developer, expected_draft_version=1).status == 'SUCCESS'
    project.event.status = CompetitionEvent.Status.PURGED
    project.event.save(update_fields=['status'])
    with pytest.raises(AnalysisError, match='PROJECT_ANALYZE_DENIED'):
        analyze_project(project=project, actor=owner, expected_draft_version=1)
    with pytest.raises(AnalysisError, match='PROJECT_CHECK_DENIED'):
        check_project(project=project, actor=owner, expected_draft_version=1)
    assert ModelRevision.objects.filter(project=project).count() == 1
    assert AnalysisRun.objects.filter(project=project).count() == 1


@pytest.mark.django_db
def test_solver_version_is_stable_and_traced_by_successful_run(context):
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)

    assert run.solver_version.analysis_type == 'TRUSS_2D'
    assert run.solver_version.input_schema_version == 'truss2d-input-v1'
    assert run.solver_version.result_schema_version == 'truss2d-result-v1'
    assert run.input_schema_version == 'truss2d-input-v1'
