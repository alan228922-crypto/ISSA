"""Versioned learning artifacts keep old interpretation frozen."""

import pytest

from tests.application.test_analysis_acceptance import save_bt01_draft
from tests.application.test_node_joint_draft import v2_payload, v2_project
from tests.application.test_physical_draft import context


def prediction_payload():
    return {
        "schema_version": "prediction-v2",
        "member_judgments": [{"physical_member_client_key": "m1", "predicted_state": "TENSION"}],
        "max_displacement_location": {"kind": "NODE", "node_client_key": "n2"},
        "representative_load_path": [
            {"kind": "NODE", "node_client_key": "n1"},
            {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m1"},
            {"kind": "NODE", "node_client_key": "n2"},
        ],
    }


def save_v2_bt01(owner, project, material, section):
    from modeling.services import save_physical_draft

    v2_project(project)
    payload = v2_payload(material, section)
    payload["supports"].append({"client_key": "s2", "target_node_client_key": "n2", "support_type": "ROLLER", "restrained_axis": "Y"})
    payload["node_loads"][0].update(fx_N=100.0, fy_N=0.0)
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()


@pytest.mark.django_db
def test_prediction_v2_references_node_and_adjacent_member_path(context):
    from learning.services import create_prediction, complete_prediction

    owner, project, material, section = context
    save_v2_bt01(owner, project, material, section)
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=1)
    assert prediction.prediction_schema_version == "prediction-v2"
    completed = complete_prediction(prediction=prediction, actor=owner, expected_draft_version=1, payload=prediction_payload())
    assert completed.status == "COMPLETED"
    assert completed.payload_json["max_displacement_location"] == {"kind": "NODE", "node_client_key": "n2"}


@pytest.mark.django_db
def test_prediction_v2_rejects_geometry_only_path(context):
    from learning.services import PredictionError, validate_prediction_payload

    _, project, material, section = context
    save_v2_bt01(context[0], project, material, section)
    payload = prediction_payload()
    payload["representative_load_path"][-1]["node_client_key"] = "n1"
    with pytest.raises(PredictionError, match="INVALID_LOAD_PATH"):
        validate_prediction_payload(project, payload)


@pytest.mark.django_db
def test_v2_comparison_report_and_node_provenance(context):
    from analysis.orchestration import analyze_project
    from analysis.reporting import build_report_package
    from learning.comparison import build_comparison
    from learning.services import create_prediction, complete_prediction

    owner, project, material, section = context
    save_v2_bt01(owner, project, material, section)
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=1)
    prediction = complete_prediction(prediction=prediction, actor=owner, expected_draft_version=1, payload=prediction_payload())
    run = analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.pk)
    assert run.status == "SUCCESS"
    comparison = build_comparison(run=run)
    assert comparison["comparison_available"] is True
    assert comparison["maximum_displacement"]["predicted_point"]["kind"] == "NODE"
    report = build_report_package(run=run, actor=owner)
    assert report["geometry_connectivity"]["nodes"]
    assert "connections" not in report["geometry_connectivity"]
    assert report["geometry_connectivity"]["member_joint_incidences"] == []
    from analysis.report_completeness import evaluate_report_completeness

    assert evaluate_report_completeness(report)["blocks"]["model"]["status"] == "READY"


@pytest.mark.django_db
def test_v1_run_remains_readable_after_project_converts(context):
    from analysis.orchestration import analyze_project
    from analysis.reporting import build_report_package
    from modeling.node_joint_migration import convert_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    before = build_report_package(run=run, actor=owner)
    assert convert_project(project_id=project.pk, expected_draft_version=1, actor=owner).status == "CONVERTED"
    after = build_report_package(run=run, actor=owner)
    assert before["geometry_connectivity"] == after["geometry_connectivity"]
    assert "connections" in after["geometry_connectivity"]


@pytest.mark.django_db
def test_v1_prediction_comparison_and_explanation_remain_frozen_after_conversion(context):
    from analysis.orchestration import analyze_project
    from learning.comparison import build_comparison
    from learning.explanation import build_explanation
    from learning.services import create_prediction, complete_prediction
    from modeling.node_joint_migration import convert_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=1)
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
    prediction = complete_prediction(prediction=prediction, actor=owner, expected_draft_version=1, payload=payload)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.pk)
    before = build_comparison(run=run), build_explanation(run=run)
    assert convert_project(project_id=project.pk, expected_draft_version=1, actor=owner).status == "CONVERTED"
    assert before == (build_comparison(run=run), build_explanation(run=run))
    prediction.refresh_from_db()
    assert prediction.payload_json == payload


@pytest.mark.django_db
def test_mixed_schema_prediction_cannot_enter_analysis(context):
    from analysis.orchestration import AnalysisError, analyze_project
    from learning.models import Prediction

    owner, project, material, section = context
    save_v2_bt01(owner, project, material, section)
    Prediction.objects.create(project=project, source_draft_version=1, created_by=owner, prediction_schema_version="prediction-v1", status=Prediction.Status.COMPLETED, payload_json={})
    with pytest.raises(AnalysisError, match="PREDICTION_NOT_ELIGIBLE"):
        analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=Prediction.objects.get(project=project).pk)
