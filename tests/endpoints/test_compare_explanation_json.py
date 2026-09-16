import pytest
from django.urls import reverse

from tests.application.test_analysis_acceptance import save_bt01_draft
from tests.application.test_physical_draft import context


def prediction_payload():
    return {
        "schema_version": "prediction-v1",
        "member_judgments": [
            {"physical_member_client_key": "m1", "predicted_state": "TENSION"},
        ],
        "max_displacement_location": {"kind": "CONNECTION", "connection_client_key": "c2"},
        "representative_load_path": [
            {"kind": "CONNECTION", "connection_client_key": "c1"},
            {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m1"},
            {"kind": "CONNECTION", "connection_client_key": "c2"},
        ],
    }


@pytest.fixture
def analyzed_project(context):
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1)
    assert run.status == "SUCCESS"
    return owner, project, run


@pytest.fixture
def predicted_run(context):
    from analysis.orchestration import analyze_project
    from learning.services import complete_prediction, create_prediction

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=1)
    complete_prediction(
        prediction=prediction,
        actor=owner,
        expected_draft_version=1,
        payload=prediction_payload(),
    )
    run = analyze_project(
        project=project, actor=owner, expected_draft_version=1, prediction_id=prediction.id,
    )
    assert run.status == "SUCCESS"
    return owner, project, run


def endpoint(name, project, run):
    return reverse(f"projects:analysis_{name}", kwargs={"project_id": project.id, "run_id": run.id})


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["comparison", "explanation"])
def test_anonymous_reader_is_redirected_before_any_disclosure(predicted_run, client, name):
    """Removing authentication must not make classified or numerical facts public."""
    from learning.models import StudentResultReveal

    _, project, run = predicted_run
    response = client.get(endpoint(name, project, run))

    assert response.status_code == 302
    assert not StudentResultReveal.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "schema"),
    [("comparison", "comparison-v1"), ("explanation", "explanation-v1")],
)
def test_owner_receives_only_contract_payload_after_reveal(predicted_run, client, name, schema):
    """Removing the disclosure service or leaking run data must fail this endpoint boundary."""
    from learning.models import StudentResultReveal

    owner, project, run = predicted_run
    client.force_login(owner)

    response = client.get(endpoint(name, project, run))

    assert response.status_code == 200
    assert set(response.json()) == {"ok", name}
    assert response.json()[name]["schema_version"] == schema
    assert "result_json" not in response.json()
    assert StudentResultReveal.objects.filter(
        project=project, source_draft_version=1, first_analysis_run=run,
    ).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "schema"),
    [("comparison", "comparison-v1"), ("explanation", "explanation-v1")],
)
def test_owner_reveal_exists_when_success_response_is_constructed(predicted_run, client, monkeypatch, name, schema):
    """Moving reveal after JsonResponse construction would expose facts before durable disclosure."""
    from learning.models import StudentResultReveal
    from projects import views

    owner, project, run = predicted_run
    original = views.JsonResponse

    def checked_response(payload, *args, **kwargs):
        if payload.get("ok") and name in payload:
            assert StudentResultReveal.objects.filter(
                project=project, source_draft_version=1, first_analysis_run=run,
            ).exists()
        return original(payload, *args, **kwargs)

    monkeypatch.setattr(views, "JsonResponse", checked_response)
    client.force_login(owner)

    response = client.get(endpoint(name, project, run))

    assert response.status_code == 200
    assert response.json()[name]["schema_version"] == schema


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["comparison", "explanation"])
def test_no_prediction_is_a_legal_response_and_reveal_is_idempotent(analyzed_project, client, name):
    """Requiring Prediction or creating a second reveal changes the soft-gate contract."""
    from learning.models import StudentResultReveal

    owner, project, run = analyzed_project
    client.force_login(owner)
    first = client.get(endpoint(name, project, run))
    second = client.get(endpoint(name, project, run))

    assert first.status_code == second.status_code == 200
    payload = first.json()[name]
    if name == "comparison":
        assert payload == {
            "schema_version": "comparison-v1",
            "comparison_available": False,
            "reason": "NO_PREDICTION",
            "project_id": project.id,
            "analysis_run_id": run.id,
        }
    else:
        assert payload["schema_version"] == "explanation-v1"
        assert payload["comparison_available"] is False
        assert payload["comparison_reason"] == "NO_PREDICTION"
    assert StudentResultReveal.objects.filter(project=project, source_draft_version=1).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["comparison", "explanation"])
def test_second_success_run_preserves_first_reveal_evidence(analyzed_project, client, name):
    """Replacing first-run evidence on a later read would violate disclosure provenance."""
    from analysis.orchestration import analyze_project
    from learning.models import StudentResultReveal

    owner, project, first_run = analyzed_project
    client.force_login(owner)
    assert client.get(endpoint(name, project, first_run)).status_code == 200
    first = StudentResultReveal.objects.get(project=project, source_draft_version=1)
    original = StudentResultReveal.objects.values().get(pk=first.pk)
    second_run = analyze_project(project=project, actor=owner, expected_draft_version=1)

    assert client.get(endpoint(name, project, second_run)).status_code == 200
    assert StudentResultReveal.objects.filter(project=project, source_draft_version=1).count() == 1
    assert StudentResultReveal.objects.values().get(pk=first.pk) == original
    assert first.first_analysis_run_id == first_run.id


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["comparison", "explanation"])
@pytest.mark.parametrize("role", ["MANAGER", "DEVELOPER"])
def test_privileged_readers_receive_contract_without_student_reveal(predicted_run, client, name, role):
    """Changing M4A role semantics to disclose for staff must fail."""
    from accounts.models import User
    from competitions.models import EventMembership
    from learning.models import StudentResultReveal

    owner, project, run = predicted_run
    actor = User.objects.create_user(f"{role.lower()}-reader", role=role)
    if role == "MANAGER":
        EventMembership.objects.create(
            user=actor, event=project.event, membership_type=EventMembership.Type.MANAGER,
        )
    client.force_login(actor)

    response = client.get(endpoint(name, project, run))

    assert response.status_code == 200
    assert response.json()[name]["schema_version"] == f"{name}-v1"
    assert not StudentResultReveal.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["comparison", "explanation"])
def test_other_user_and_cross_project_run_cannot_disclose(predicted_run, client, name):
    """Dropping scoped authorization or run-project binding must fail closed."""
    from accounts.models import User
    from learning.models import StudentResultReveal
    from projects.models import Project

    owner, project, run = predicted_run
    other = User.objects.create_user("compare-other")
    client.force_login(other)
    denied = client.get(endpoint(name, project, run))
    other_project = Project.objects.create(event=project.event, owner_user=owner, name="其他项目")
    client.force_login(owner)
    crossed = client.get(endpoint(name, other_project, run))

    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "PROJECT_READ_DENIED"
    assert crossed.status_code == 404
    assert crossed.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert not StudentResultReveal.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["comparison", "explanation"])
def test_non_success_run_returns_frozen_error_without_reveal(analyzed_project, client, name):
    """Permitting teaching output for failed analysis must remain impossible."""
    from analysis.models import AnalysisRun
    from learning.models import StudentResultReveal

    owner, project, run = analyzed_project
    run.status = AnalysisRun.Status.VALIDATION_FAILED
    run.save(update_fields=["status"])
    client.force_login(owner)

    response = client.get(endpoint(name, project, run))

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error": {
            "code": "ANALYSIS_NOT_SUCCESS",
            "message": "分析尚未成功完成，暂无可用的比较或解释结果。",
            "details": {},
        },
    }
    assert not StudentResultReveal.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["comparison", "explanation"])
def test_reveal_from_endpoint_blocks_later_prediction_completion(analyzed_project, client, name):
    """Bypassing the reveal record would leave same-draft Prediction improperly completable."""
    from learning.services import PredictionError, complete_prediction, create_prediction

    owner, project, run = analyzed_project
    client.force_login(owner)
    assert client.get(endpoint(name, project, run)).status_code == 200
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=1)

    with pytest.raises(PredictionError, match="PREDICTION_AFTER_RESULT_REVEAL"):
        complete_prediction(
            prediction=prediction,
            actor=owner,
            expected_draft_version=1,
            payload=prediction_payload(),
        )


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["comparison", "explanation"])
def test_reveal_persistence_failure_returns_no_derived_facts(predicted_run, client, monkeypatch, name):
    """Returning a contract after a failed reveal record would violate fail-closed disclosure."""
    from learning import services
    from learning.models import StudentResultReveal

    owner, project, run = predicted_run

    def fail_reveal(**_kwargs):
        raise RuntimeError("database failure")

    monkeypatch.setattr(services, "record_student_result_reveal", fail_reveal)
    client.force_login(owner)
    response = client.get(endpoint(name, project, run))

    assert response.status_code == 500
    assert response.json() == {
        "ok": False,
        "error": {
            "code": "RESULT_REVEAL_FAILED",
            "message": "无法安全记录结果查看，请稍后重试。",
            "details": {},
        },
    }
    assert name not in response.json()
    assert not StudentResultReveal.objects.exists()
