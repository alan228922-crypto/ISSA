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


def endpoint(project, run_id):
    return reverse("projects:analysis_report", kwargs={"project_id": project.id, "run_id": run_id})


def runs_endpoint(project):
    return reverse("projects:analysis_runs", kwargs={"project_id": project.id})


@pytest.mark.django_db
def test_authorized_run_discovery_is_read_only_deterministic_and_preserves_status(analyzed_project, client):
    from analysis.models import AnalysisRun

    owner, project, success_run = analyzed_project
    failed_run = AnalysisRun.objects.create(
        project=project,
        model_revision=success_run.model_revision,
        solver_version=success_run.solver_version,
        input_schema_version=success_run.input_schema_version,
        input_hash="failed-input-hash",
        solver_input_json=success_run.solver_input_json,
        status=AnalysisRun.Status.VALIDATION_FAILED,
        failure_code="INVALID_DRAFT",
        created_by=owner,
    )
    client.force_login(owner)

    response = client.get(runs_endpoint(project))

    assert response.status_code == 200
    runs = response.json()["runs"]
    assert runs == [
        {
            "analysis_run_id": failed_run.id,
            "status": "VALIDATION_FAILED",
            "created_at": runs[0]["created_at"],
            "model_revision_id": success_run.model_revision_id,
            "source_draft_version": success_run.model_revision.source_draft_version,
            "is_stale": False,
        },
        {
            "analysis_run_id": success_run.id,
            "status": "SUCCESS",
            "created_at": runs[1]["created_at"],
            "model_revision_id": success_run.model_revision_id,
            "source_draft_version": success_run.model_revision.source_draft_version,
            "is_stale": False,
        },
    ]
    assert all(run["created_at"].endswith("Z") for run in runs)
    assert "result_json" not in response.json()["runs"][0]


@pytest.mark.django_db
def test_owner_gets_report_for_explicit_run_and_no_latest_selection(analyzed_project, client):
    owner, project, run = analyzed_project
    client.force_login(owner)

    response = client.get(endpoint(project, run.id))

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["report"]["metadata"]["analysis_run_id"] == run.id
    assert client.get(endpoint(project, 999999)).status_code == 404


@pytest.mark.django_db
def test_report_uses_existing_project_read_policy(analyzed_project, client):
    from accounts.models import User
    from competitions.models import EventMembership

    owner, project, run = analyzed_project
    manager = User.objects.create_user("report-manager", role=User.Role.MANAGER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    client.force_login(manager)

    assert client.get(endpoint(project, run.id)).status_code == 200

    client.force_login(User.objects.create_user("report-outsider"))
    assert client.get(endpoint(project, run.id)).status_code == 403


@pytest.mark.django_db
def test_anonymous_report_request_keeps_existing_authentication_behavior(analyzed_project, client):
    _, project, run = analyzed_project
    response = client.get(endpoint(project, run.id))
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_run_project_mismatch_is_rejected(analyzed_project, context, client):
    from accounts.models import User
    from projects.models import Project

    _, project, run = analyzed_project
    other_project = Project.objects.create(event=project.event, owner_user=project.owner_user, name="other")
    developer = User.objects.create_user("report-developer", role=User.Role.DEVELOPER)
    client.force_login(developer)

    assert client.get(endpoint(other_project, run.id)).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["VALIDATION_FAILED", "SOLVER_FAILED"])
def test_failed_run_returns_report_unavailable_error(analyzed_project, client, status):
    owner, project, run = analyzed_project
    run.status = status
    run.failure_code = "SINGULAR_GLOBAL_STIFFNESS" if status == "VALIDATION_FAILED" else "SOLVER_FAILED"
    run.result_json = None
    run.save(update_fields=["status", "failure_code", "result_json"])
    client.force_login(owner)

    response = client.get(endpoint(project, run.id))

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error": {
            "code": "REPORT_ANALYSIS_NOT_SUCCESS",
            "message": "该分析尚未成功完成，暂时无法生成计算书资料。",
            "details": {"analysis_run_id": run.id, "analysis_status": status},
        },
    }
