import pytest
from django.urls import reverse

from tests.application.test_analysis_acceptance import save_bt01_draft
from tests.application.test_physical_draft import context


@pytest.fixture
def successful_run(context):
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    project.refresh_from_db()
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    assert run.status == "SUCCESS"
    return owner, project, run


@pytest.mark.django_db
def test_owner_gets_blank_optional_reasoning_for_explicit_successful_run(successful_run, client):
    owner, project, run = successful_run
    client.force_login(owner)

    response = client.get(reverse("learning:reasoning_detail", kwargs={"project_id": project.id, "run_id": run.id}))

    assert response.status_code == 200
    assert response.json()["exists"] is False
    assert response.json()["analysis_run_id"] == run.id
    assert response.json()["reasoning"] == {
        "modeling_rationale": "", "material_section_rationale": "", "support_load_rationale": "", "result_interpretation": "", "design_change_rationale": "", "scheme_comparison": "", "final_conclusion": "",
    }


@pytest.mark.django_db
def test_owner_saves_partial_reasoning_and_updates_the_same_run(successful_run, client):
    owner, project, run = successful_run
    url = reverse("learning:reasoning_detail", kwargs={"project_id": project.id, "run_id": run.id})
    client.force_login(owner)

    first = client.post(url, data='{"modeling_rationale":"MY EXACT TEXT"}', content_type="application/json")
    second = client.post(url, data='{"final_conclusion":"SECOND TEXT"}', content_type="application/json")

    assert first.status_code == second.status_code == 200
    assert client.get(url).json()["reasoning"] == {
        "modeling_rationale": "MY EXACT TEXT", "material_section_rationale": "", "support_load_rationale": "", "result_interpretation": "", "design_change_rationale": "", "scheme_comparison": "", "final_conclusion": "SECOND TEXT",
    }


@pytest.mark.django_db
def test_non_owner_and_failed_run_cannot_access_or_create_reasoning(successful_run, client):
    from accounts.models import User
    from analysis.models import AnalysisRun
    from competitions.models import EventMembership

    owner, project, run = successful_run
    manager = User.objects.create_user("reasoning-manager", role=User.Role.MANAGER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    url = reverse("learning:reasoning_detail", kwargs={"project_id": project.id, "run_id": run.id})
    client.force_login(manager)
    assert client.get(url).status_code == 403
    assert client.post(url, data="{}", content_type="application/json").status_code == 403

    run.status = AnalysisRun.Status.VALIDATION_FAILED
    run.save(update_fields=["status"])
    client.force_login(owner)
    assert client.get(url).status_code == 422
    assert client.post(url, data="{}", content_type="application/json").status_code == 422
