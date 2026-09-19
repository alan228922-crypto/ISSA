import pytest

from tests.application.test_analysis_acceptance import save_bt01_draft
from tests.application.test_physical_draft import context


@pytest.fixture
def analyzed_project(context):
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    assert run.status == "SUCCESS"
    return owner, project, run


@pytest.mark.django_db
def test_successful_report_is_bound_to_explicit_run_and_authoritative_sources(analyzed_project):
    from analysis.reporting import build_report_package

    owner, project, run = analyzed_project
    package = build_report_package(run=run, actor=owner)

    assert package["metadata"]["analysis_run_id"] == run.id
    assert package["metadata"]["model_revision_id"] == run.model_revision_id
    assert package["metadata"]["solver_version"] == run.solver_version.solver_version
    assert package["provenance"]["input_hash"] == run.input_hash
    assert package["provenance"]["model_hash"] == run.model_revision.model_hash
    assert package["assumptions"] == {
        "analysis_type": "TRUSS_2D",
        "kinematics": "2D_LINEAR_ELASTIC_SMALL_DISPLACEMENT",
        "joint_model": "PIN_JOINTED",
        "member_behavior": "AXIAL_ONLY",
        "degrees_of_freedom": ["ux", "uy"],
        "load_model": "NODAL_FX_FY",
        "units": {"length": "mm", "force": "N", "stress": "MPa", "mass": "g"},
    }


@pytest.mark.django_db
def test_report_uses_historical_snapshot_not_current_mutable_material_or_draft(analyzed_project):
    from analysis.reporting import build_report_package

    owner, project, run = analyzed_project
    member = run.model_revision.physical_snapshot_json["physical_members"][0]
    old_e = member["material"]["E_MPa"]
    old_a = member["section"]["A_mm2"]

    material = project.physical_members.select_related("material").get(client_key="m1").material
    material.E_MPa = 999999
    material.save(update_fields=["E_MPa", "updated_at"])
    project.draft_version = 2
    project.save(update_fields=["draft_version", "updated_at"])

    package = build_report_package(run=run, actor=owner)
    assert package["materials_sections"]["materials"][0]["E_MPa"] == old_e
    assert package["materials_sections"]["sections"][0]["A_mm2"] == old_a
    assert package["provenance"]["is_stale"] is True
    assert package["provenance"]["source_draft_version"] == 1
    assert package["provenance"]["current_draft_version"] == 2


@pytest.mark.django_db
def test_report_results_equal_persisted_result_and_preserve_physical_analysis_boundary(analyzed_project):
    from analysis.reporting import build_report_package

    owner, _, run = analyzed_project
    package = build_report_package(run=run, actor=owner)

    assert package["node_results"]["items"] == run.result_json["node_displacements"]
    assert package["member_results"]["items"] == run.result_json["member_results"]
    assert package["results_summary"]["total_mass_g"] == run.result_json["total_mass_g"]
    assert package["geometry_connectivity"]["physical_members"][0]["id"] == "m1"
    assert package["member_results"]["items"][0]["physical_member_id"] == "m1"
    assert package["member_results"]["items"][0]["analysis_member_id"] != "m1"
    assert package["validation_limitations"]["euler"]["status"] == "UNAVAILABLE"


@pytest.mark.django_db
def test_report_does_not_invoke_solver_or_create_prediction_or_reflection(analyzed_project, monkeypatch):
    from analysis.reporting import build_report_package
    from mechanics.truss2d.solver import Truss2DSolver

    owner, _, run = analyzed_project

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Report construction must not invoke Solver")

    monkeypatch.setattr(Truss2DSolver, "solve", fail_if_called)
    package = build_report_package(run=run, actor=owner)
    assert "student_authored_reasoning" not in package


@pytest.mark.django_db
def test_missing_result_field_is_not_replaced_with_zero(analyzed_project):
    from analysis.reporting import build_report_package

    owner, _, run = analyzed_project
    result = dict(run.result_json)
    result.pop("support_reactions")
    run.result_json = result
    run.save(update_fields=["result_json"])

    package = build_report_package(run=run, actor=owner)
    assert package["node_results"]["status"] == "MISSING"
    assert package["node_results"]["items"] is None
    assert package["results_summary"]["total_mass_g"] != 0


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["VALIDATION_FAILED", "SOLVER_FAILED"])
def test_failed_analysis_run_is_report_unavailable_and_never_reanalyzed(analyzed_project, status, monkeypatch):
    from analysis.models import AnalysisRun
    from analysis.reporting import ReportError, build_report_package

    owner, _, run = analyzed_project
    run.status = status
    run.failure_code = "SINGULAR_GLOBAL_STIFFNESS" if status == "VALIDATION_FAILED" else "SOLVER_FAILED"
    run.result_json = None
    run.save(update_fields=["status", "failure_code", "result_json"])

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Failed Report construction must not re-analyze")

    monkeypatch.setattr("analysis.orchestration.analyze_project", fail_if_called)
    with pytest.raises(ReportError) as error:
        build_report_package(run=run, actor=owner)
    assert error.value.code == "REPORT_ANALYSIS_NOT_SUCCESS"
    assert error.value.status_code == 422
    assert error.value.details == {"analysis_run_id": run.id, "analysis_status": status}
    assert AnalysisRun.objects.get(pk=run.id).status == status
