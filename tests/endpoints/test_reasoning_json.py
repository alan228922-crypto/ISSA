import json

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

    for username, role in (("reasoning-developer", User.Role.DEVELOPER), ("reasoning-unrelated", User.Role.USER)):
        client.force_login(User.objects.create_user(username, role=role))
        assert client.get(url).status_code == 403
        assert client.post(url, data="{}", content_type="application/json").status_code == 403

    run.status = AnalysisRun.Status.VALIDATION_FAILED
    run.save(update_fields=["status"])
    client.force_login(owner)
    assert client.get(url).status_code == 422
    assert client.post(url, data="{}", content_type="application/json").status_code == 422


@pytest.mark.django_db
@pytest.mark.parametrize(
    "event_status, expected",
    [("DRAFT", 200), ("ACTIVE", 200), ("FINISHED_GRACE", 200), ("PURGED", 403)],
)
def test_reasoning_write_reuses_project_authority_without_active_only_gate(successful_run, client, event_status, expected):
    owner, project, run = successful_run
    project.event.status = event_status
    project.event.save(update_fields=["status"])
    client.force_login(owner)

    response = client.post(
        reverse("learning:reasoning_detail", kwargs={"project_id": project.id, "run_id": run.id}),
        data="{}",
        content_type="application/json",
    )

    assert response.status_code == expected


@pytest.mark.django_db
def test_all_seven_reasoning_fields_are_optional_and_clearable(successful_run, client):
    owner, project, run = successful_run
    client.force_login(owner)
    url = reverse("learning:reasoning_detail", kwargs={"project_id": project.id, "run_id": run.id})
    fields = {
        "modeling_rationale": "", "material_section_rationale": "", "support_load_rationale": "",
        "result_interpretation": "", "design_change_rationale": "", "scheme_comparison": "",
        "final_conclusion": "",
    }

    response = client.post(url, data=json.dumps(fields), content_type="application/json")

    assert response.status_code == 200
    assert response.json()["reasoning"] == fields


@pytest.mark.django_db
def test_reasoning_read_requires_current_project_access_and_student_owner_role(successful_run, client):
    from accounts.models import User
    from competitions.models import EventMembership

    owner, project, run = successful_run
    url = reverse("learning:reasoning_detail", kwargs={"project_id": project.id, "run_id": run.id})
    client.force_login(owner)
    assert client.post(url, data='{"modeling_rationale":"PRIVATE"}', content_type="application/json").status_code == 200

    membership = EventMembership.objects.get(
        user=owner,
        event=project.event,
        membership_type=EventMembership.Type.PARTICIPANT,
    )
    membership.is_active = False
    membership.save(update_fields=["is_active"])
    assert client.get(url).status_code == 403

    membership.is_active = True
    membership.save(update_fields=["is_active"])
    for role in (User.Role.MANAGER, User.Role.DEVELOPER):
        owner.role = role
        owner.save(update_fields=["role"])
        response = client.get(url)
        assert response.status_code == 403
        assert "PRIVATE" not in response.content.decode()


@pytest.mark.django_db
def test_reasoning_isolated_by_explicit_historical_run_and_project(successful_run, client):
    from analysis.orchestration import analyze_project

    owner, project, run_one = successful_run
    from materials.models import Material, Section

    save_bt01_draft(
        owner,
        project,
        Material.objects.get(owner_user=owner),
        Section.objects.get(owner_user=owner),
        fx_N=125.0,
    )
    run_two = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    client.force_login(owner)
    url_one = reverse("learning:reasoning_detail", kwargs={"project_id": project.id, "run_id": run_one.id})
    url_two = reverse("learning:reasoning_detail", kwargs={"project_id": project.id, "run_id": run_two.id})
    assert client.post(url_one, data='{"final_conclusion":"RUN ONE"}', content_type="application/json").status_code == 200
    assert client.post(url_two, data='{"final_conclusion":"RUN TWO"}', content_type="application/json").status_code == 200
    assert client.get(url_one).json()["reasoning"]["final_conclusion"] == "RUN ONE"
    assert client.get(url_two).json()["reasoning"]["final_conclusion"] == "RUN TWO"

    other_project = project.__class__.objects.create(event=project.event, owner_user=owner, name="other")
    cross = client.get(reverse("learning:reasoning_detail", kwargs={"project_id": other_project.id, "run_id": run_one.id}))
    assert cross.status_code == 404
    assert "RUN ONE" not in cross.content.decode()


@pytest.mark.django_db
def test_reasoning_unexpected_failure_returns_safe_json(successful_run, client, monkeypatch):
    owner, project, run = successful_run
    client.force_login(owner)
    client.raise_request_exception = False
    monkeypatch.setattr("learning.views.reasoning_for_run", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("SECRET TRACE")))

    response = client.get(reverse("learning:reasoning_detail", kwargs={"project_id": project.id, "run_id": run.id}))

    assert response.status_code == 500
    assert response.headers["Content-Type"].startswith("application/json")
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "SECRET TRACE" not in response.content.decode()


@pytest.mark.django_db
def test_purge_deletes_reasoning_raw_text_and_keeps_only_counts(successful_run):
    from learning.models import CalculationReportReasoning
    from projects.services import purge_project_operational_data

    owner, project, run = successful_run
    reasoning = CalculationReportReasoning.objects.create(
        analysis_run=run,
        created_by=owner,
        modeling_rationale="RAW STUDENT TEXT",
    )

    audit = purge_project_operational_data(project_id=project.id, actor_id=owner.id)

    assert not CalculationReportReasoning.objects.filter(pk=reasoning.pk).exists()
    assert audit.deletion_counts_json["learning.CalculationReportReasoning"] == 1
    assert "RAW STUDENT TEXT" not in str(audit.deletion_counts_json)
    assert purge_project_operational_data(project_id=project.id).pk == audit.pk
