import pytest

from tests.application.test_node_joint_draft import v2_payload, v2_project
from tests.application.test_physical_draft import context


@pytest.mark.django_db
def test_v2_snapshot_freezes_explicit_topology_and_properties(context):
    from modeling.services import save_physical_draft
    from modeling.snapshot import build_physical_snapshot

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["nodes"].append({"client_key": "mid", "x_mm": 500, "y_mm": 0})
    payload["member_joint_incidences"] = [{"member_client_key": "m1", "node_client_key": "mid"}]
    save_physical_draft(actor=owner, project=project, payload=payload)
    frozen = build_physical_snapshot(project)
    assert frozen["schema_version"] == "physical-snapshot-v2"
    assert frozen["member_joint_incidences"] == [{"member_id": "m1", "node_id": "mid"}]
    assert frozen["supports"][0]["node_id"] == "n1"
    assert frozen["node_loads"][0]["node_id"] == "n2"
    assert frozen["units"] == {"length": "mm", "force": "N", "stress": "MPa", "mass": "g"}


@pytest.mark.django_db
def test_v2_snapshot_rejects_inconsistent_draft(context):
    from modeling.models import GeometryNode, PhysicalMember
    from modeling.snapshot import build_physical_snapshot

    _, project, _, _ = context
    v2_project(project)
    first = GeometryNode.objects.create(project=project, client_key="a", x_mm=0, y_mm=0)
    last = GeometryNode.objects.create(project=project, client_key="b", x_mm=1000, y_mm=0)
    GeometryNode.objects.create(project=project, client_key="mid", x_mm=500, y_mm=0)
    PhysicalMember.objects.create(project=project, client_key="m", start_geometry_node=first, end_geometry_node=last)
    with pytest.raises(ValueError, match="INCOMPLETE_DRAFT"):
        build_physical_snapshot(project)


@pytest.mark.django_db
def test_v2_model_check_reports_unrepresented_node_before_snapshot(context):
    from analysis.models import ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project, check_project
    from modeling.models import GeometryNode, PhysicalMember

    owner, project, material, section = context
    v2_project(project)
    first = GeometryNode.objects.create(project=project, client_key="a", x_mm=0, y_mm=0)
    last = GeometryNode.objects.create(project=project, client_key="b", x_mm=1000, y_mm=0)
    GeometryNode.objects.create(project=project, client_key="mid", x_mm=500, y_mm=0)
    PhysicalMember.objects.create(project=project, client_key="m", start_geometry_node=first, end_geometry_node=last, material=material, section=section)
    result = check_project(project=project, actor=owner, expected_draft_version=0)
    assert {issue["code"] for issue in result["issues"]} == {"MEMBER_PASSES_THROUGH_NODE_WITHOUT_INCIDENCE"}
    with pytest.raises(AnalysisError, match="INCOMPLETE_DRAFT"):
        analyze_project(project=project, actor=owner, expected_draft_version=0)
    assert not ModelRevision.objects.filter(project=project).exists()


@pytest.mark.django_db
def test_v2_model_check_reports_unaudited_same_coordinate_nodes(context):
    from analysis.models import ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project, check_project
    from modeling.models import GeometryNode

    owner, project, _, _ = context
    v2_project(project)
    GeometryNode.objects.create(project=project, client_key="a", x_mm=12.4, y_mm=7.6)
    GeometryNode.objects.create(project=project, client_key="b", x_mm=12.4, y_mm=7.6)
    issues = check_project(project=project, actor=owner, expected_draft_version=0)["issues"]
    assert "DUPLICATE_NODE_COORDINATE" in {issue["code"] for issue in issues}
    with pytest.raises(AnalysisError, match="INCOMPLETE_DRAFT"):
        analyze_project(project=project, actor=owner, expected_draft_version=0)
    assert not ModelRevision.objects.filter(project=project).exists()


@pytest.mark.django_db
def test_v2_analysis_uses_unchanged_solver_contract(context):
    from analysis.orchestration import analyze_project
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["node_loads"][0]["fx_N"] = 100
    payload["node_loads"][0]["fy_N"] = 0
    payload["supports"].append({"client_key": "s2", "target_node_client_key": "n2", "support_type": "ROLLER", "restrained_axis": "Y"})
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    assert run.status == "SUCCESS"
    assert run.input_schema_version == "truss2d-input-v1"
    assert run.model_revision.physical_snapshot_json["schema_version"] == "physical-snapshot-v2"
    assert run.result_json["member_results"][0]["axial_force_N"] == pytest.approx(100)


@pytest.mark.django_db
def test_v2_support_on_unattached_node_is_preflight_issue_without_revision(context):
    from analysis.models import ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project, check_project
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["nodes"].append({"client_key": "orphan", "x_mm": 500.0, "y_mm": 500.0, "label": "孤立"})
    payload["supports"].append({"client_key": "s2", "target_node_client_key": "orphan", "support_type": "ROLLER", "restrained_axis": "Y"})
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    issues = check_project(project=project, actor=owner, expected_draft_version=1)["issues"]
    assert {issue["code"] for issue in issues} == {"UNATTACHED_SUPPORT_NODE"}
    with pytest.raises(AnalysisError, match="INCOMPLETE_DRAFT"):
        analyze_project(project=project, actor=owner, expected_draft_version=1)
    assert not ModelRevision.objects.filter(project=project).exists()
