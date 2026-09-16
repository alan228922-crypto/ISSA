import json

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from competitions.models import EventMembership
from learning.models import Prediction
from projects.models import Project
from tests.application.test_prediction import (
    complete_payload,
    owner,
    project,
    project_with_two_members,
)


def post_json(client, name, payload, **kwargs):
    return client.post(
        reverse(name, kwargs=kwargs),
        data=json.dumps(payload),
        content_type="application/json",
    )


def post_json_with_csrf(client, name, payload, **kwargs):
    token = "a" * 32
    client.cookies["csrftoken"] = token
    return client.post(
        reverse(name, kwargs=kwargs),
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )


def create_body(project):
    return {"expected_draft_version": project.draft_version}


def complete_body(project, payload=None):
    return {
        "expected_draft_version": project.draft_version,
        "payload": complete_payload() if payload is None else payload,
    }


@pytest.mark.django_db
def test_prediction_posts_require_authentication_and_csrf(project_with_two_members, owner):
    project_with_two_members.refresh_from_db()
    create_url = reverse(
        "learning:prediction_create", kwargs={"project_id": project_with_two_members.id}
    )
    assert create_url == f"/projects/{project_with_two_members.id}/predictions/"
    # Existing JSON endpoints redirect anonymous callers when CSRF enforcement
    # is not deliberately activated by the test client.
    anonymous = Client()

    response = anonymous.post(
        create_url,
        data=json.dumps(create_body(project_with_two_members)),
        content_type="application/json",
    )

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")

    client = Client(enforce_csrf_checks=True)
    client.force_login(owner)
    without_csrf = client.post(
        create_url,
        data=json.dumps(create_body(project_with_two_members)),
        content_type="application/json",
    )
    assert without_csrf.status_code == 403

    created = post_json_with_csrf(
        client,
        "learning:prediction_create",
        create_body(project_with_two_members),
        project_id=project_with_two_members.id,
    )
    assert created.status_code == 201
    prediction = Prediction.objects.get(pk=created.json()["prediction_id"])

    complete_url = reverse(
        "learning:prediction_complete",
        kwargs={"project_id": project_with_two_members.id, "prediction_id": prediction.id},
    )
    detail_url = reverse(
        "learning:prediction_detail",
        kwargs={"project_id": project_with_two_members.id, "prediction_id": prediction.id},
    )
    assert complete_url == (
        f"/projects/{project_with_two_members.id}/predictions/{prediction.id}/complete/"
    )
    assert detail_url == f"/projects/{project_with_two_members.id}/predictions/{prediction.id}/"
    without_csrf = client.post(
        complete_url,
        data=json.dumps(complete_body(project_with_two_members)),
        content_type="application/json",
    )
    assert without_csrf.status_code == 403


@pytest.mark.django_db
def test_owner_creates_completes_and_reads_minimal_prediction(project_with_two_members, owner, client):
    project_with_two_members.refresh_from_db()
    client.force_login(owner)

    created = post_json(
        client,
        "learning:prediction_create",
        create_body(project_with_two_members),
        project_id=project_with_two_members.id,
    )

    assert created.status_code == 201
    created_body = created.json()
    assert created_body["ok"] is True
    assert created_body["project_id"] == project_with_two_members.id
    assert created_body["source_draft_version"] == project_with_two_members.draft_version
    assert created_body["status"] == "DRAFT"
    assert created_body["prediction_schema_version"] == "prediction-v1"
    assert created_body["payload"] == {}
    prediction_id = created_body["prediction_id"]

    completed = post_json(
        client,
        "learning:prediction_complete",
        complete_body(project_with_two_members),
        project_id=project_with_two_members.id,
        prediction_id=prediction_id,
    )
    read = client.get(
        reverse(
            "learning:prediction_detail",
            kwargs={"project_id": project_with_two_members.id, "prediction_id": prediction_id},
        )
    )

    assert completed.status_code == 200
    assert read.status_code == 200
    body = read.json()
    assert body["status"] == "COMPLETED"
    assert body["payload"] == complete_payload()
    assert body["completed_at"] is not None
    assert body["invalidated_at"] is None
    assert body["invalidation_code"] is None
    serialized = json.dumps(body)
    for forbidden in (
        "physical_snapshot",
        "solver_input",
        "x_mm",
        "y_mm",
        "material",
        "section",
        "axial_force_N",
        "node_displacements",
        "support_reactions",
        "member_results",
        "total_mass_g",
    ):
        assert forbidden not in serialized


@pytest.mark.django_db
def test_prediction_create_rejects_malformed_missing_and_unknown_fields(
    project_with_two_members, owner, client
):
    project_with_two_members.refresh_from_db()
    client.force_login(owner)
    url = reverse(
        "learning:prediction_create", kwargs={"project_id": project_with_two_members.id}
    )

    malformed = client.post(url, data="{", content_type="application/json")
    missing = client.post(url, data="{}", content_type="application/json")
    unknown = post_json(
        client,
        "learning:prediction_create",
        {"expected_draft_version": project_with_two_members.draft_version, "status": "COMPLETED"},
        project_id=project_with_two_members.id,
    )
    stale = post_json(
        client,
        "learning:prediction_create",
        {"expected_draft_version": project_with_two_members.draft_version - 1},
        project_id=project_with_two_members.id,
    )

    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "MALFORMED_JSON"
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "INVALID_REQUEST"
    assert unknown.status_code == 400
    assert unknown.json()["error"]["code"] == "INVALID_REQUEST"
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "PREDICTION_STALE_DRAFT"
    assert not Prediction.objects.filter(project=project_with_two_members).exists()


@pytest.mark.django_db
def test_prediction_create_maps_unexpected_service_failure_to_safe_json(
    project_with_two_members, owner, client, monkeypatch
):
    import learning.views

    project_with_two_members.refresh_from_db()
    client.force_login(owner)

    def fail_create(**kwargs):
        raise RuntimeError('/private/server/path database secret')

    monkeypatch.setattr(learning.views, 'create_prediction', fail_create)
    response = post_json(
        client,
        'learning:prediction_create',
        create_body(project_with_two_members),
        project_id=project_with_two_members.id,
    )

    assert response.status_code == 500
    assert response.json()['error']['code'] == 'INTERNAL_ERROR'
    serialized = json.dumps(response.json())
    assert 'database secret' not in serialized
    assert '/private/server/path' not in serialized
    assert response.json()['error']['message'].isascii() is False


@pytest.mark.django_db
def test_prediction_authoring_denies_other_manager_and_developer(
    project_with_two_members, owner, client
):
    project_with_two_members.refresh_from_db()
    other = User.objects.create_user("prediction-http-other")
    manager = User.objects.create_user("prediction-http-manager", role=User.Role.MANAGER)
    developer = User.objects.create_user("prediction-http-developer", role=User.Role.DEVELOPER)
    EventMembership.objects.create(
        user=manager,
        event=project_with_two_members.event,
        membership_type=EventMembership.Type.MANAGER,
    )

    for actor in (other, manager, developer):
        client.force_login(actor)
        response = post_json(
            client,
            "learning:prediction_create",
            create_body(project_with_two_members),
            project_id=project_with_two_members.id,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PROJECT_WRITE_DENIED"

    client.force_login(owner)
    created = post_json(
        client,
        "learning:prediction_create",
        create_body(project_with_two_members),
        project_id=project_with_two_members.id,
    )
    prediction_id = created.json()["prediction_id"]
    for actor in (other, manager, developer):
        client.force_login(actor)
        completed = post_json(
            client,
            "learning:prediction_complete",
            complete_body(project_with_two_members),
            project_id=project_with_two_members.id,
            prediction_id=prediction_id,
        )
        read = client.get(
            reverse(
                "learning:prediction_detail",
                kwargs={
                    "project_id": project_with_two_members.id,
                    "prediction_id": prediction_id,
                },
            )
        )
        assert completed.status_code == 403
        assert completed.json()["error"]["code"] == "PROJECT_WRITE_DENIED"
        assert read.status_code == (403 if actor == other else 200)

    prediction = Prediction.objects.get(pk=prediction_id)
    assert prediction.status == Prediction.Status.DRAFT
    assert prediction.payload_json == {}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda payload: payload.update(
                {"member_judgments": payload["member_judgments"][:1]}
            ),
            "PREDICTION_INCOMPLETE",
        ),
        (lambda payload: payload.update({"schema_version": "prediction-v2"}), "PREDICTION_INVALID_SCHEMA"),
        (
            lambda payload: payload.update(
                {"max_displacement_location": {"kind": "CONNECTION", "connection_client_key": "missing"}}
            ),
            "INVALID_PHYSICAL_POINT_REF",
        ),
        (
            lambda payload: payload.update(
                {
                    "representative_load_path": [
                        {"kind": "CONNECTION", "connection_client_key": "c1"},
                        {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m2"},
                        {"kind": "CONNECTION", "connection_client_key": "c2"},
                    ]
                }
            ),
            "INVALID_LOAD_PATH",
        ),
    ],
)
def test_prediction_completion_maps_payload_validation_to_422(
    project_with_two_members, owner, client, mutate, code
):
    project_with_two_members.refresh_from_db()
    client.force_login(owner)
    prediction = Prediction.objects.create(
        project=project_with_two_members,
        source_draft_version=project_with_two_members.draft_version,
        created_by=owner,
        payload_json={},
    )
    payload = complete_payload()
    mutate(payload)

    response = post_json(
        client,
        "learning:prediction_complete",
        complete_body(project_with_two_members, payload),
        project_id=project_with_two_members.id,
        prediction_id=prediction.id,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    prediction.refresh_from_db()
    assert prediction.status == Prediction.Status.DRAFT


@pytest.mark.django_db
def test_prediction_completion_rejects_malformed_missing_and_unknown_fields(
    project_with_two_members, owner, client
):
    project_with_two_members.refresh_from_db()
    prediction = Prediction.objects.create(
        project=project_with_two_members,
        source_draft_version=project_with_two_members.draft_version,
        created_by=owner,
        payload_json={},
    )
    client.force_login(owner)
    kwargs = {
        "project_id": project_with_two_members.id,
        "prediction_id": prediction.id,
    }
    url = reverse("learning:prediction_complete", kwargs=kwargs)

    malformed = client.post(url, data="{", content_type="application/json")
    missing = post_json(
        client,
        "learning:prediction_complete",
        {"expected_draft_version": project_with_two_members.draft_version},
        **kwargs,
    )
    unknown = post_json(
        client,
        "learning:prediction_complete",
        {
            **complete_body(project_with_two_members),
            "completed_at": "client-controlled",
        },
        **kwargs,
    )

    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "MALFORMED_JSON"
    for response in (missing, unknown):
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_REQUEST"
    prediction.refresh_from_db()
    assert prediction.status == Prediction.Status.DRAFT
    assert prediction.payload_json == {}


@pytest.mark.django_db
def test_prediction_completion_maps_lifecycle_conflicts(project_with_two_members, owner, client):
    project_with_two_members.refresh_from_db()
    client.force_login(owner)
    current_version = project_with_two_members.draft_version
    completed = Prediction.objects.create(
        project=project_with_two_members,
        source_draft_version=current_version,
        status=Prediction.Status.COMPLETED,
        created_by=owner,
        payload_json=complete_payload(),
    )
    stale = Prediction.objects.create(
        project=project_with_two_members,
        source_draft_version=current_version - 1,
        created_by=owner,
        payload_json={},
    )
    invalidated = Prediction.objects.create(
        project=project_with_two_members,
        source_draft_version=current_version,
        status=Prediction.Status.INVALIDATED,
        created_by=owner,
        payload_json={},
    )

    expected = (
        (completed, "PREDICTION_ALREADY_COMPLETED"),
        (stale, "PREDICTION_STALE_DRAFT"),
        (invalidated, "PREDICTION_INVALIDATED"),
    )
    for prediction, code in expected:
        response = post_json(
            client,
            "learning:prediction_complete",
            complete_body(project_with_two_members),
            project_id=project_with_two_members.id,
            prediction_id=prediction.id,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == code


@pytest.mark.django_db
def test_prediction_read_and_completion_hide_cross_project_ids(
    project_with_two_members, owner, client
):
    project_with_two_members.refresh_from_db()
    other_project = Project.objects.create(
        event=project_with_two_members.event, owner_user=owner, name="另一个项目"
    )
    prediction = Prediction.objects.create(
        project=project_with_two_members,
        source_draft_version=project_with_two_members.draft_version,
        created_by=owner,
        payload_json={},
    )
    client.force_login(owner)

    for name, method in (
        ("learning:prediction_detail", "get"),
        ("learning:prediction_complete", "post"),
    ):
        kwargs = {"project_id": other_project.id, "prediction_id": prediction.id}
        if method == "get":
            response = client.get(reverse(name, kwargs=kwargs))
        else:
            response = post_json(client, name, complete_body(project_with_two_members), **kwargs)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PREDICTION_NOT_FOUND"

    missing = client.get(
        reverse(
            "learning:prediction_detail",
            kwargs={"project_id": project_with_two_members.id, "prediction_id": prediction.id + 1000},
        )
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "PREDICTION_NOT_FOUND"


@pytest.mark.django_db
def test_prediction_read_denies_unentitled_user(project_with_two_members, owner, client):
    project_with_two_members.refresh_from_db()
    prediction = Prediction.objects.create(
        project=project_with_two_members,
        source_draft_version=project_with_two_members.draft_version,
        created_by=owner,
        payload_json={},
    )
    client.force_login(User.objects.create_user("prediction-read-other"))

    response = client.get(
        reverse(
            "learning:prediction_detail",
            kwargs={"project_id": project_with_two_members.id, "prediction_id": prediction.id},
        )
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_READ_DENIED"
