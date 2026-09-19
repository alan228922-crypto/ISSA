from copy import deepcopy

import pytest

from tests.application.test_analysis_acceptance import save_bt01_draft
from tests.application.test_physical_draft import context


@pytest.fixture
def report_package(context):
    from analysis.orchestration import analyze_project
    from analysis.reporting import build_report_package

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    assert run.status == "SUCCESS"
    return build_report_package(run=run, actor=owner)


def evaluate(package):
    from analysis.report_completeness import evaluate_report_completeness

    return evaluate_report_completeness(package)


@pytest.mark.django_db
def test_complete_authoritative_technical_package_is_ready(report_package):
    result = evaluate(report_package)

    assert result["overall"]["status"] == "READY"
    assert all(
        block["status"] == "READY"
        for name, block in result["blocks"].items()
        if name != "student_reasoning"
    )
    assert result["blocks"]["student_reasoning"]["status"] == "NOT_APPLICABLE"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        ("results_summary", "maximum_displacement"),
        ("node_results", "items"),
        ("node_results", "support_reactions"),
        ("member_results", "items"),
    ],
)
def test_legitimate_zero_values_are_not_missing(report_package, path):
    package = deepcopy(report_package)
    if path == ("results_summary", "maximum_displacement"):
        package[path[0]][path[1]] = {
            "maximum_displacement": {
                "maximum_displacement_mm": 0.0,
                "candidate_analysis_node_ids": ["an1"],
            }
        }
    elif path == ("node_results", "items"):
        package[path[0]][path[1]] = [{"analysis_node_id": "an1", "ux_mm": 0.0, "uy_mm": 0.0}]
    elif path == ("node_results", "support_reactions"):
        package[path[0]][path[1]] = [{"analysis_node_id": "an1", "rx_N": 0.0, "ry_N": 0.0}]
    else:
        package["member_results"]["items"] = [{
            "analysis_member_id": "am1",
            "physical_member_id": "m1",
            "axial_force_N": 0.0,
            "axial_stress_MPa": 0.0,
            "mass_g": 0.0,
            "state": "ZERO_FORCE",
        }]

    result = evaluate(package)
    assert result["overall"]["status"] == "READY"
    assert result["blocks"]["results"]["status"] == "READY"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path,issue_code",
    [
        (("metadata", "analysis_run_id"), "MISSING_ANALYSIS_RUN"),
        (("metadata", "model_revision_id"), "MISSING_MODEL_REVISION"),
        (("metadata", "solver_version"), "MISSING_SOLVER_VERSION"),
        (("metadata", "model_hash"), "MISSING_MODEL_HASH"),
        (("provenance", "input_hash"), "MISSING_INPUT_HASH"),
        (("materials_sections", "materials"), "MISSING_MATERIAL_EVIDENCE"),
        (("materials_sections", "sections"), "MISSING_SECTION_EVIDENCE"),
        (("geometry_connectivity", "physical_members"), "MISSING_GEOMETRY_EVIDENCE"),
        (("supports_loads", "supports"), "MISSING_SUPPORT_EVIDENCE"),
        (("supports_loads", "loads"), "MISSING_LOAD_EVIDENCE"),
        (("node_results", "items"), "MISSING_NODE_RESULTS"),
        (("node_results", "support_reactions"), "MISSING_REACTION_RESULTS"),
        (("member_results", "items"), "MISSING_MEMBER_RESULTS"),
    ],
)
def test_missing_required_evidence_is_reported_without_fake_values(report_package, path, issue_code):
    package = deepcopy(report_package)
    if path[0] == "metadata":
        package[path[0]][path[1]] = None
    elif path[0] == "provenance":
        package[path[0]][path[1]] = None
    elif path[0] == "materials_sections":
        package[path[0]][path[1]] = []
    elif path[0] == "geometry_connectivity":
        package[path[0]][path[1]] = []
    elif path[0] == "supports_loads":
        package[path[0]][path[1]] = []
    elif path[0] == "node_results":
        package[path[0]][path[1]] = None
    else:
        package[path[0]][path[1]] = None

    result = evaluate(package)

    assert result["overall"]["status"] == "MISSING"
    assert any(issue["code"] == issue_code for issue in result["blocks"][
        "analysis_provenance" if path[0] in {"metadata", "provenance"}
        else "materials_sections" if path[0] == "materials_sections"
        else "model" if path[0] == "geometry_connectivity"
        else "supports_loads" if path[0] == "supports_loads"
        else "results"
    ]["issues"])


@pytest.mark.django_db
def test_euler_is_unavailable_but_does_not_make_base_report_missing(report_package):
    result = evaluate(report_package)

    assert result["overall"]["status"] == "READY"
    assert result["blocks"]["limitations"]["status"] == "READY"
    assert any(
        limitation["code"] == "EULER_STABILITY_UNAVAILABLE"
        and limitation["status"] == "UNAVAILABLE"
        for limitation in result["blocks"]["limitations"]["limitations"]
    )


@pytest.mark.django_db
def test_not_applicable_limitations_do_not_count_as_missing(report_package):
    result = evaluate(report_package)

    assert result["overall"]["status"] == "READY"
    assert any(
        limitation["code"] == "REPORT_NOT_CODE_COMPLIANCE_REVIEW"
        and limitation["status"] == "NOT_APPLICABLE"
        for limitation in result["blocks"]["limitations"]["limitations"]
    )


@pytest.mark.django_db
def test_stale_report_remains_complete(report_package):
    package = deepcopy(report_package)
    package["provenance"]["is_stale"] = True
    package["provenance"]["current_draft_version"] = package["provenance"]["source_draft_version"] + 1

    result = evaluate(package)

    assert result["overall"]["status"] == "READY"
    assert result["stale"] is True
    assert result["blocks"]["analysis_provenance"]["status"] == "READY"


@pytest.mark.django_db
def test_student_reasoning_is_not_generated_and_reflection_is_not_a_hard_gate(report_package):
    result = evaluate(report_package)

    assert result["blocks"]["student_reasoning"] == {
        "status": "NOT_APPLICABLE",
        "issues": [{"code": "STUDENT_AUTHORED_POLICY_PENDING"}],
    }
    assert "reflection" not in result["blocks"]


@pytest.mark.django_db
def test_completeness_evaluator_does_not_invoke_solver_or_read_current_draft(report_package, monkeypatch):
    from mechanics.truss2d.solver import Truss2DSolver

    monkeypatch.setattr(Truss2DSolver, "solve", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("Completeness must not invoke Solver")
    ))
    result = evaluate(report_package)

    assert result["overall"]["status"] == "READY"
