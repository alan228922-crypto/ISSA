"""Selected-run HTTP facts: real analysis and persistence, no fabricated result."""

import json

import pytest
from django.urls import reverse

from tests.application.test_node_joint_learning import prediction_payload, save_v2_bt01
from tests.application.test_physical_draft import context


@pytest.fixture
def m9_run(context):
    from analysis.orchestration import analyze_project
    from learning.services import complete_prediction, create_prediction

    owner, project, material, section = context
    # This ordinary saved-run fixture must stay within its retention window.
    # Dedicated expired/purged access tests set those conditions explicitly.
    from datetime import timedelta
    from django.utils import timezone
    project.event.starts_at = timezone.now() - timedelta(days=1)
    project.event.ends_at = timezone.now() + timedelta(days=1)
    project.event.save()
    save_v2_bt01(owner, project, material, section)
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=1)
    complete_prediction(
        prediction=prediction, actor=owner, expected_draft_version=1,
        payload=prediction_payload(),
    )
    run = analyze_project(
        project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.pk,
    )
    assert run.status == "SUCCESS"
    return owner, project, run


def run_package(client, project, run):
    package = {}
    for name in ("data", "comparison", "explanation", "report"):
        response = client.get(reverse(
            f"projects:analysis_{name}", kwargs={"project_id": project.pk, "run_id": run.pk},
        ))
        assert response.status_code == 200, response.status_code
        package[name] = response.json()
    return package


@pytest.mark.django_db
def test_selected_run_endpoints_share_run_and_snapshot_authority(m9_run, client):
    """Wrong Run/revision binding or mutable geometry substitution must fail."""
    owner, project, run = m9_run
    client.force_login(owner)
    package = run_package(client, project, run)
    report = package["report"]["report"]
    assert package["data"]["analysis_run_id"] == run.pk
    assert package["data"]["model_revision_id"] == run.model_revision_id
    for value in (package["comparison"]["comparison"], package["explanation"]["explanation"], report["metadata"]):
        assert value["analysis_run_id"] == run.pk
        assert value["project_id"] == project.pk
        assert value["source_draft_version"] == 1
    assert report["provenance"]["model_revision_id"] == run.model_revision_id
    assert report["geometry_connectivity"]["nodes"] == run.model_revision.physical_snapshot_json["nodes"]
    assert report["geometry_connectivity"]["physical_members"] == run.model_revision.physical_snapshot_json["physical_members"]
    assert package["comparison"]["comparison"]["prediction_id"] == run.prediction_id
    assert "connections" not in report["geometry_connectivity"]


@pytest.mark.django_db
def test_no_prediction_package_remains_available(context, client):
    """Adding a prediction prerequisite must not disable the ordinary learning flow."""
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_v2_bt01(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    client.force_login(owner)
    package = run_package(client, project, run)
    assert run.prediction_id is None
    assert package["comparison"]["comparison"] == {
        "schema_version": "comparison-v1", "comparison_available": False,
        "reason": "NO_PREDICTION", "project_id": project.pk, "analysis_run_id": run.pk,
    }
    explanation = package["explanation"]["explanation"]
    assert explanation["explanation_available"] is True
    assert {block["type"] for block in explanation["blocks"]} == {
        "MEMBER_FORCE_STATE", "MAXIMUM_DISPLACEMENT",
    }


@pytest.mark.django_db
def test_selected_run_reads_do_not_mutate_result_artifacts(m9_run, client):
    """Presentation must not rewrite immutable numerical/history/prediction inputs."""
    owner, project, run = m9_run

    def frozen_bytes():
        run.refresh_from_db()
        run.model_revision.refresh_from_db()
        run.prediction.refresh_from_db()
        return json.dumps({
            "result": run.result_json, "input": run.solver_input_json,
            "snapshot": run.model_revision.physical_snapshot_json,
            "model_hash": run.model_revision.model_hash, "input_hash": run.input_hash,
            "prediction": run.prediction.payload_json,
        }, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()

    before = frozen_bytes()
    client.force_login(owner)
    run_package(client, project, run)
    run_package(client, project, run)
    assert frozen_bytes() == before
