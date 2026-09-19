import pytest
from django.urls import reverse

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
def test_report_endpoint_includes_backward_compatible_completeness(analyzed_project, client):
    owner, project, run = analyzed_project
    client.force_login(owner)

    response = client.get(reverse(
        "projects:analysis_report",
        kwargs={"project_id": project.id, "run_id": run.id},
    ))

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["report"]["metadata"]["analysis_run_id"] == run.id
    assert body["completeness"]["overall"]["status"] == "READY"
    assert "student_authored_reasoning" not in body["completeness"]
