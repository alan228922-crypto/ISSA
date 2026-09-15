import pytest
from tests.application.test_physical_draft import context, valid_payload


def completed_prediction_for(project, owner, source_draft_version, **overrides):
    """Create immutable learning evidence without involving analysis behavior."""
    from learning.models import Prediction

    values = {
        "project": project,
        "source_draft_version": source_draft_version,
        "status": Prediction.Status.COMPLETED,
        "created_by": owner,
        "prediction_schema_version": "prediction-v1",
        "payload_json": {},
    }
    values.update(overrides)
    return Prediction.objects.create(**values)


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
@pytest.mark.parametrize("supply_prediction", [False, True])
def test_identical_draft_save_binds_analysis_and_reveal_to_new_source(context, supply_prediction):
    """Hash-only revision reuse must not let disclosure leave the new draft open."""
    from analysis.models import ModelRevision
    from analysis.orchestration import analyze_project
    from learning.models import Prediction, StudentResultReveal
    from learning.services import PredictionError, complete_prediction, create_prediction, record_student_result_reveal

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    old_run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    assert old_run.status == "SUCCESS"
    old_revision = ModelRevision.objects.values().get(pk=old_run.model_revision_id)
    old_reveal = record_student_result_reveal(project=project, run=old_run, actor=owner)
    old_evidence = StudentResultReveal.objects.values().get(pk=old_reveal.pk)

    # The helper submits the same physical payload through save_physical_draft;
    # only its expected_draft_version advances, without changing model content.
    save_bt01_draft(owner, project, material, section)
    assert project.draft_version == 2
    payload = {
        "schema_version": "prediction-v1",
        "member_judgments": [{"physical_member_client_key": "m1", "predicted_state": "TENSION"}],
        "max_displacement_location": {"kind": "CONNECTION", "connection_client_key": "c2"},
        "representative_load_path": [
            {"kind": "CONNECTION", "connection_client_key": "c1"},
            {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m1"},
            {"kind": "CONNECTION", "connection_client_key": "c2"},
        ],
    }
    prediction = None
    if supply_prediction:
        prediction = create_prediction(project=project, actor=owner, expected_draft_version=2)
        prediction = complete_prediction(
            prediction=prediction, actor=owner, expected_draft_version=2, payload=payload,
        )

    current_run = analyze_project(
        project=project, actor=owner, expected_draft_version=2,
        prediction_id=prediction.pk if prediction else None,
    )
    assert current_run.status == "SUCCESS"
    assert current_run.model_revision_id != old_run.model_revision_id
    assert current_run.model_revision.source_draft_version == 2
    assert current_run.prediction_id == (prediction.pk if prediction else None)
    if prediction:
        assert current_run.model_revision.source_draft_version == prediction.source_draft_version
    assert current_run.model_revision.model_hash == old_run.model_revision.model_hash
    assert current_run.model_revision.physical_snapshot_json == old_run.model_revision.physical_snapshot_json
    assert current_run.solver_input_json == old_run.solver_input_json
    assert current_run.input_hash == old_run.input_hash
    assert current_run.result_json == old_run.result_json

    current_reveal = record_student_result_reveal(project=project, run=current_run, actor=owner)
    assert current_reveal.pk != old_reveal.pk
    assert current_reveal.source_draft_version == 2
    assert current_reveal.first_analysis_run_id == current_run.pk
    current_evidence = StudentResultReveal.objects.values().get(pk=current_reveal.pk)
    repeat_run = analyze_project(project=project, actor=owner, expected_draft_version=2)
    assert repeat_run.status == "SUCCESS"
    assert repeat_run.model_revision_id == current_run.model_revision_id
    assert record_student_result_reveal(project=project, run=repeat_run, actor=owner).pk == current_reveal.pk
    assert StudentResultReveal.objects.values().get(pk=current_reveal.pk) == current_evidence

    late_prediction = create_prediction(project=project, actor=owner, expected_draft_version=2)
    with pytest.raises(PredictionError, match="PREDICTION_AFTER_RESULT_REVEAL"):
        complete_prediction(
            prediction=late_prediction, actor=owner, expected_draft_version=2, payload=payload,
        )
    late_prediction.refresh_from_db()
    assert late_prediction.status == Prediction.Status.DRAFT
    assert late_prediction.completed_at is None
    assert record_student_result_reveal(project=project, run=old_run, actor=owner).pk == old_reveal.pk
    assert ModelRevision.objects.values().get(pk=old_run.model_revision_id) == old_revision
    assert StudentResultReveal.objects.values().get(pk=old_reveal.pk) == old_evidence
    assert ModelRevision.objects.filter(project=project).count() == 2
    assert set(StudentResultReveal.objects.filter(project=project).values_list("source_draft_version", flat=True)) == {1, 2}


@pytest.mark.django_db
def test_analyze_accepts_none_reuses_completed_prediction_and_preserves_solver_artifacts(context):
    """A completed learning record is linked as evidence, never solver input."""
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    plain = analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=None)
    prediction = completed_prediction_for(project, owner, 1)
    first = analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.id)
    second = analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.id)

    assert plain.prediction_id is None
    assert first.prediction_id == second.prediction_id == prediction.id
    for run in (first, second):
        assert run.solver_input_json == plain.solver_input_json
        assert run.input_hash == plain.input_hash
        assert run.model_revision.model_hash == plain.model_revision.model_hash
        assert run.result_json == plain.result_json


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["DRAFT", "INVALIDATED"])
def test_analyze_rejects_non_completed_prediction_before_creating_history(context, status):
    """Changing the completed-status check must reject explicit ineligible evidence."""
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project
    from learning.models import Prediction

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    prediction = completed_prediction_for(project, owner, 1, status=status)
    before = (ModelRevision.objects.count(), AnalysisRun.objects.count())

    with pytest.raises(AnalysisError, match="PREDICTION_NOT_ELIGIBLE") as error:
        analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.id)

    assert error.value.status_code == 409
    assert (ModelRevision.objects.count(), AnalysisRun.objects.count()) == before


@pytest.mark.django_db
def test_analyze_rejects_stale_completed_prediction_before_creating_history(context):
    """Changing the prediction source-version check must reject old evidence."""
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    prediction = completed_prediction_for(project, owner, 0)
    before = (ModelRevision.objects.count(), AnalysisRun.objects.count())

    with pytest.raises(AnalysisError, match="PREDICTION_STALE_DRAFT") as error:
        analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.id)

    assert error.value.status_code == 409
    assert (ModelRevision.objects.count(), AnalysisRun.objects.count()) == before


@pytest.mark.django_db
def test_analyze_rejects_prediction_with_stale_project_object_before_creating_history(context):
    """Validating the caller's cached draft must not attach old evidence to a new revision."""
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project
    from projects.models import Project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    prediction = completed_prediction_for(project, owner, 1)
    current_project = Project.objects.get(pk=project.pk)
    save_bt01_draft(owner, current_project, material, section, fx_N=125.0)
    assert project.draft_version == 1
    assert current_project.draft_version == 2
    before = (ModelRevision.objects.count(), AnalysisRun.objects.count())

    with pytest.raises(AnalysisError, match="PREDICTION_STALE_DRAFT") as error:
        analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.id)

    assert error.value.status_code == 409
    assert (ModelRevision.objects.count(), AnalysisRun.objects.count()) == before


@pytest.mark.django_db
def test_analyze_hides_cross_project_or_missing_prediction_before_creating_history(context):
    """Changing project scoping must not turn another project's evidence into a usable ID."""
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project
    from projects.models import Project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    other_project = Project.objects.create(event=project.event, owner_user=owner, name="其他分析项目")
    foreign = completed_prediction_for(other_project, owner, 1)
    before = (ModelRevision.objects.count(), AnalysisRun.objects.count())

    for prediction_id in (foreign.id, foreign.id + 1000):
        with pytest.raises(AnalysisError, match="PREDICTION_NOT_FOUND") as error:
            analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=prediction_id)
        assert error.value.status_code == 404

    assert (ModelRevision.objects.count(), AnalysisRun.objects.count()) == before


@pytest.mark.django_db
def test_analyze_rejects_foreign_prediction_owner_or_unsupported_schema_before_creating_history(context):
    """Changing owner or schema eligibility must fail closed rather than ignore explicit evidence."""
    from accounts.models import User
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    foreign_owner = User.objects.create_user("foreign-prediction-author")
    foreign_owner_prediction = completed_prediction_for(project, foreign_owner, 1)
    unsupported_schema_prediction = completed_prediction_for(
        project, owner, 1, prediction_schema_version="prediction-v2"
    )
    before = (ModelRevision.objects.count(), AnalysisRun.objects.count())

    for prediction in (foreign_owner_prediction, unsupported_schema_prediction):
        with pytest.raises(AnalysisError, match="PREDICTION_NOT_ELIGIBLE") as error:
            analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.id)
        assert error.value.status_code == 409

    assert (ModelRevision.objects.count(), AnalysisRun.objects.count()) == before


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
    prediction = completed_prediction_for(project, owner, 1)
    developer_run = analyze_project(
        project=project, actor=developer, expected_draft_version=1, prediction_id=prediction.id
    )
    assert developer_run.status == 'SUCCESS'
    assert developer_run.prediction_id == prediction.id
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
