import json

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from analysis.models import AnalysisRun
from competitions.models import CompetitionEvent, EventMembership
from learning.models import Reflection, StudentResultReveal
from projects.models import Project
from tests.application.test_prediction import owner, project, success_run


def activate(project):
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    project.refresh_from_db()


def reveal(project, run, owner):
    from learning.services import record_student_result_reveal
    return record_student_result_reveal(project=project, run=run, actor=owner)


def url(project, run, *, complete=False):
    return reverse(
        "learning:reflection_complete" if complete else "learning:reflection_detail",
        kwargs={"project_id": project.id, "run_id": run.id},
    )


def post(client, endpoint, body):
    return client.post(endpoint, data=json.dumps(body), content_type="application/json")


@pytest.mark.django_db
def test_reflection_post_requires_authentication_and_csrf(project, owner, success_run):
    endpoint = url(project, success_run)
    assert endpoint == f"/projects/{project.id}/analyses/{success_run.id}/reflection/"
    assert Client().post(endpoint, data="{}", content_type="application/json").status_code == 302
    client = Client(enforce_csrf_checks=True); client.force_login(owner)
    assert post(client, endpoint, {}).status_code == 403


@pytest.mark.django_db
def test_owner_creates_updates_reads_and_completes_reflection(project, owner, success_run, client):
    activate(project); reveal(project, success_run, owner); client.force_login(owner)
    endpoint = url(project, success_run)
    created = post(client, endpoint, {"original_reasoning": "A", "unexpected_results": "B"})
    assert created.status_code == 201 and created.json()["status"] == "DRAFT"
    updated = post(client, endpoint, {"unexpected_results": ""})
    assert updated.status_code == 200
    body = updated.json(); assert body["original_reasoning"] == "A" and body["unexpected_results"] == ""
    assert client.get(endpoint).status_code == 200
    post(client, endpoint, {"unexpected_results": "B", "next_iteration_intent": "C"})
    completed = post(client, url(project, success_run, complete=True), {})
    assert completed.status_code == 200 and completed.json()["status"] == "COMPLETED"
    assert completed.json()["completed_at"] is not None
    assert not {"result_json", "solver_input_json", "comparison", "explanation", "created_by"} & completed.json().keys()


@pytest.mark.django_db
def test_reflection_http_rejects_malformed_unknown_and_completed_authoring(project, owner, success_run, client):
    activate(project); reveal(project, success_run, owner); client.force_login(owner); endpoint = url(project, success_run)
    assert client.post(endpoint, data="{", content_type="application/json").json()["error"]["code"] == "MALFORMED_JSON"
    assert post(client, endpoint, {"status": "COMPLETED"}).json()["error"]["code"] == "INVALID_REQUEST"
    assert client.post(url(project, success_run, complete=True), data="{", content_type="application/json").json()["error"]["code"] == "MALFORMED_JSON"
    post(client, endpoint, {"original_reasoning": "A", "unexpected_results": "B", "next_iteration_intent": "C"})
    assert post(client, url(project, success_run, complete=True), {}).status_code == 200
    assert post(client, endpoint, {}).status_code == 409


@pytest.mark.django_db
def test_reflection_read_visibility_and_no_reveal_side_effect(project, owner, success_run, client):
    activate(project); reveal(project, success_run, owner)
    reflection = Reflection.objects.create(analysis_run=success_run, created_by=owner)
    manager = User.objects.create_user("reflection-http-manager", role=User.Role.MANAGER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    developer = User.objects.create_user("reflection-http-developer", role=User.Role.DEVELOPER)
    other = User.objects.create_user("reflection-http-other")
    endpoint = url(project, success_run)
    before = StudentResultReveal.objects.count()
    for actor in (manager, developer, other):
        client.force_login(actor); assert client.get(endpoint).status_code == 403
    Reflection.objects.filter(pk=reflection.pk).update(status="COMPLETED")
    for actor in (manager, developer):
        client.force_login(actor); assert client.get(endpoint).status_code == 200
    assert StudentResultReveal.objects.count() == before


@pytest.mark.django_db
def test_reflection_absence_cross_project_and_authoring_denial_are_safe(project, owner, success_run, client):
    endpoint = url(project, success_run); client.force_login(owner)
    assert client.get(endpoint).status_code == 404
    other_project = Project.objects.create(event=project.event, owner_user=owner, name="other")
    assert client.get(url(other_project, success_run)).status_code == 404
    activate(project); reveal(project, success_run, owner)
    for actor in (User.objects.create_user("reflection-http-other"), User.objects.create_user("reflection-http-developer", role=User.Role.DEVELOPER)):
        client.force_login(actor); assert post(client, endpoint, {}).status_code == 403


@pytest.mark.django_db
def test_reflection_complete_maps_incomplete_and_does_not_block_analysis(project, owner, success_run, client):
    from analysis.orchestration import analyze_project
    activate(project); reveal(project, success_run, owner); client.force_login(owner)
    endpoint = url(project, success_run)
    post(client, endpoint, {"original_reasoning": "   "})
    assert post(client, url(project, success_run, complete=True), {}).status_code == 422
    assert not Reflection.objects.filter(analysis_run=success_run, status="COMPLETED").exists()
