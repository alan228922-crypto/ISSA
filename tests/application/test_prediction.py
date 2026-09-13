from copy import deepcopy
from datetime import date, datetime, timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from analysis.models import AnalysisRun, ModelRevision, SolverVersion
from accounts.models import User
from competitions.models import CompetitionEvent, EventMembership
from projects.models import Project


def complete_payload(*, state="TENSION"):
    return {
        "schema_version": "prediction-v1",
        "member_judgments": [
            {"physical_member_client_key": "m1", "predicted_state": state},
            {"physical_member_client_key": "m2", "predicted_state": "UNSURE"},
        ],
        "max_displacement_location": {
            "kind": "CONNECTION",
            "connection_client_key": "c1",
        },
        "representative_load_path": [
            {"kind": "CONNECTION", "connection_client_key": "c1"},
            {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m1"},
            {"kind": "CONNECTION", "connection_client_key": "c2"},
        ],
    }


@pytest.fixture
def owner(db):
    user = User.objects.create_user("prediction-owner")
    event = CompetitionEvent.objects.create(
        name="赛事",
        event_code="PR",
        competition_date=date(2026, 11, 7),
        starts_at=timezone.make_aware(datetime(2026, 11, 7)),
        ends_at=timezone.make_aware(datetime(2026, 11, 8)),
    )
    EventMembership.objects.create(
        user=user,
        event=event,
        membership_type=EventMembership.Type.PARTICIPANT,
    )
    return user


@pytest.fixture
def project(owner):
    return Project.objects.create(
        event=EventMembership.objects.get(user=owner).event,
        owner_user=owner,
        name="预测",
    )


@pytest.fixture
def success_run(project, owner):
    revision = ModelRevision.objects.create(
        project=project,
        revision_number=1,
        analysis_type="TRUSS_2D",
        source_draft_version=7,
        physical_snapshot_schema_version="physical-snapshot-v1",
        physical_snapshot_json={},
        model_hash="a" * 64,
        created_by=owner,
    )
    solver_version = SolverVersion.objects.create(solver_version="prediction-test-v1")
    return AnalysisRun.objects.create(
        project=project,
        model_revision=revision,
        solver_version=solver_version,
        input_schema_version="truss2d-input-v1",
        input_hash="b" * 64,
        status=AnalysisRun.Status.SUCCESS,
        solver_input_json={},
        created_by=owner,
    )


@pytest.fixture
def project_with_two_members(project, owner):
    from materials.models import Material
    from materials.services import create_section
    from modeling.services import save_physical_draft

    material = Material.objects.create(
        owner_user=owner, name="预测竹材", E_MPa=2000, density_g_per_mm3=0.0007,
        source_type="MEASURED",
    )
    section = create_section(
        owner=owner, name="预测矩形",
        definition={"schema_version": "section-definition-v1", "type": "rectangle", "width_mm": 1, "height_mm": 6, "density_g_per_mm3": 0.0007},
    )
    save_physical_draft(actor=owner, project=project, payload={
        "schema_version": "physical-draft-v1", "expected_draft_version": 0,
        "nodes": [
            {"client_key": "n1", "x_mm": 0, "y_mm": 0, "label": "左"},
            {"client_key": "n2", "x_mm": 100, "y_mm": 0, "label": "中"},
            {"client_key": "n3", "x_mm": 0, "y_mm": 0, "label": "同坐标自由端"},
        ],
        "physical_members": [
            {"client_key": "m1", "start_node_client_key": "n1", "end_node_client_key": "n2", "material_id": material.id, "section_id": section.id, "label": "主杆", "is_active": True},
            {"client_key": "m2", "start_node_client_key": "n2", "end_node_client_key": "n3", "material_id": material.id, "section_id": section.id, "label": "副杆", "is_active": True},
        ],
        "connections": [
            {"client_key": "c1", "geometry_node_client_key": "n1", "participating_member_client_keys": ["m1"]},
            {"client_key": "c2", "geometry_node_client_key": "n2", "participating_member_client_keys": ["m1", "m2"]},
        ],
        "supports": [], "node_loads": [],
    })
    return project


@pytest.fixture
def project_with_connection_and_free_endpoint(project_with_two_members):
    return project_with_two_members


@pytest.mark.django_db
def test_prediction_persists_its_full_draft_contract(project, owner):
    from learning.models import Prediction

    completed_at = timezone.now()
    invalidated_at = completed_at + timedelta(minutes=1)
    payload = {"member_judgments": [{"physical_member_client_key": "m1"}]}
    prediction = Prediction.objects.create(
        project=project,
        source_draft_version=7,
        created_by=owner,
        prediction_schema_version="prediction-v1",
        payload_json=payload,
        completed_at=completed_at,
        invalidated_at=invalidated_at,
        invalidation_code="SOURCE_DRAFT_CHANGED",
    )
    prediction.refresh_from_db()

    assert prediction.status == Prediction.Status.DRAFT
    assert prediction.project == project
    assert prediction.source_draft_version == 7
    assert prediction.prediction_schema_version == "prediction-v1"
    assert prediction.payload_json == payload
    assert prediction.created_by == owner
    assert prediction.created_at is not None
    assert prediction.completed_at == completed_at
    assert prediction.invalidated_at == invalidated_at
    assert prediction.invalidation_code == "SOURCE_DRAFT_CHANGED"


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["DRAFT", "COMPLETED", "INVALIDATED"])
def test_prediction_persists_each_allowed_status(project, owner, status):
    from learning.models import Prediction

    prediction = Prediction.objects.create(
        project=project,
        source_draft_version=7,
        created_by=owner,
        prediction_schema_version="prediction-v1",
        payload_json={},
        status=status,
    )

    assert prediction.status == status


@pytest.mark.django_db
def test_prediction_rejects_an_arbitrary_status_at_the_database(project, owner):
    from learning.models import Prediction

    with pytest.raises(IntegrityError):
        Prediction.objects.create(
            project=project,
            source_draft_version=7,
            created_by=owner,
            prediction_schema_version="prediction-v1",
            payload_json={},
            status="NOT_A_PREDICTION_STATUS",
        )


@pytest.mark.django_db
def test_result_reveal_is_unique_per_project_draft(project, owner, success_run):
    from learning.models import StudentResultReveal

    StudentResultReveal.objects.create(
        project=project,
        source_draft_version=7,
        first_analysis_run=success_run,
        revealed_to_user=owner,
    )

    with pytest.raises(IntegrityError):
        StudentResultReveal.objects.create(
            project=project,
            source_draft_version=7,
            first_analysis_run=success_run,
            revealed_to_user=owner,
        )


@pytest.mark.django_db
def test_project_deletion_removes_prediction(project, owner):
    from learning.models import Prediction

    prediction = Prediction.objects.create(
        project=project,
        source_draft_version=7,
        created_by=owner,
        prediction_schema_version="prediction-v1",
        payload_json={},
    )
    project.delete()

    assert not Prediction.objects.filter(pk=prediction.pk).exists()


@pytest.mark.django_db
def test_payload_requires_every_active_member_once(project_with_two_members):
    from learning.services import PredictionError, validate_prediction_payload

    assert validate_prediction_payload(project_with_two_members, complete_payload())["schema_version"] == "prediction-v1"

    missing = complete_payload()
    missing["member_judgments"] = missing["member_judgments"][:1]
    with pytest.raises(PredictionError, match="PREDICTION_INCOMPLETE"):
        validate_prediction_payload(project_with_two_members, missing)

    duplicate = complete_payload()
    duplicate["member_judgments"][1]["physical_member_client_key"] = "m1"
    with pytest.raises(PredictionError, match="PREDICTION_INCOMPLETE"):
        validate_prediction_payload(project_with_two_members, duplicate)


@pytest.mark.django_db
@pytest.mark.parametrize("student_predicted_state", ["TENSION", "COMPRESSION", "ZERO_FORCE", "UNSURE"])
def test_payload_accepts_each_documented_student_predicted_state(
    project_with_two_members, student_predicted_state
):
    """Regression guard: removing any allowed student state must reject that payload."""
    from learning.services import validate_prediction_payload

    payload = complete_payload(state=student_predicted_state)

    assert validate_prediction_payload(project_with_two_members, payload)["member_judgments"][0][
        "predicted_state"
    ] == student_predicted_state


@pytest.mark.django_db
def test_point_and_path_are_physical_not_solver_rules(project_with_connection_and_free_endpoint):
    from learning.services import PredictionError, validate_prediction_payload

    free_endpoint = complete_payload(state="COMPRESSION")
    free_endpoint["max_displacement_location"] = {
        "kind": "MEMBER_ENDPOINT", "physical_member_client_key": "m2", "endpoint": "END",
    }
    validate_prediction_payload(project_with_connection_and_free_endpoint, free_endpoint)

    connected_endpoint_as_free = complete_payload()
    connected_endpoint_as_free["max_displacement_location"] = {
        "kind": "MEMBER_ENDPOINT", "physical_member_client_key": "m1", "endpoint": "START",
    }
    with pytest.raises(PredictionError, match="INVALID_PHYSICAL_POINT_REF"):
        validate_prediction_payload(project_with_connection_and_free_endpoint, connected_endpoint_as_free)

    broken_path = complete_payload()
    broken_path["representative_load_path"] = [
        {"kind": "CONNECTION", "connection_client_key": "c1"},
        {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m2"},
        {"kind": "CONNECTION", "connection_client_key": "c2"},
    ]
    with pytest.raises(PredictionError, match="INVALID_LOAD_PATH"):
        validate_prediction_payload(project_with_connection_and_free_endpoint, broken_path)


@pytest.mark.django_db
def test_payload_rejects_unknown_cross_project_and_invalid_schema_references(project_with_two_members, owner):
    from learning.services import PredictionError, validate_prediction_payload
    from modeling.models import Connection

    foreign_project = Project.objects.create(
        event=project_with_two_members.event, owner_user=owner, name="其他预测",
    )
    foreign_connection = Connection.objects.get(project=project_with_two_members, client_key="c1")
    Connection.objects.create(
        project=foreign_project,
        client_key="foreign-c1",
        geometry_node=foreign_connection.geometry_node,
    )

    unknown_member = complete_payload()
    unknown_member["member_judgments"][1]["physical_member_client_key"] = "missing"
    with pytest.raises(PredictionError, match="PREDICTION_INCOMPLETE"):
        validate_prediction_payload(project_with_two_members, unknown_member)

    foreign_point = complete_payload()
    foreign_point["max_displacement_location"] = {"kind": "CONNECTION", "connection_client_key": "foreign-c1"}
    with pytest.raises(PredictionError, match="INVALID_PHYSICAL_POINT_REF"):
        validate_prediction_payload(project_with_two_members, foreign_point)

    invalid_schema = complete_payload()
    invalid_schema["schema_version"] = "prediction-v2"
    with pytest.raises(PredictionError, match="PREDICTION_INVALID_SCHEMA") as error:
        validate_prediction_payload(project_with_two_members, invalid_schema)
    assert error.value.status_code == 400


@pytest.mark.django_db
def test_load_path_rejects_cross_project_connection_reference(project_with_two_members, owner):
    """Regression guard: path references must remain scoped to the current project."""
    from learning.services import PredictionError, validate_prediction_payload
    from modeling.models import Connection

    foreign_project = Project.objects.create(
        event=project_with_two_members.event, owner_user=owner, name="路径外部项目",
    )
    local_connection = Connection.objects.get(project=project_with_two_members, client_key="c1")
    Connection.objects.create(
        project=foreign_project,
        client_key="foreign-c1",
        geometry_node=local_connection.geometry_node,
    )
    payload = complete_payload()
    payload["representative_load_path"][0]["connection_client_key"] = "foreign-c1"

    with pytest.raises(PredictionError, match="INVALID_LOAD_PATH"):
        validate_prediction_payload(project_with_two_members, payload)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("mutate", "error_code"),
    [
        (lambda payload: payload.update({"solver_result": {"stress": 1}}), "PREDICTION_INVALID_SCHEMA"),
        (lambda payload: payload["member_judgments"][0].update({"physical_member_id": 1}), "PREDICTION_INVALID_SCHEMA"),
        (lambda payload: payload["max_displacement_location"].update({"geometry_node_id": 1, "x_mm": 0}), "PREDICTION_INVALID_SCHEMA"),
        (lambda payload: payload["representative_load_path"][1].update({"analysis_node_id": "a1"}), "INVALID_LOAD_PATH"),
    ],
)
def test_payload_rejects_forbidden_metadata(project_with_two_members, mutate, error_code):
    from learning.services import PredictionError, validate_prediction_payload

    payload = deepcopy(complete_payload())
    mutate(payload)

    with pytest.raises(PredictionError, match=error_code):
        validate_prediction_payload(project_with_two_members, payload)


@pytest.mark.django_db
def test_load_path_rejects_wrong_alternating_position_and_duplicate_entity(project_with_two_members):
    from learning.services import PredictionError, validate_prediction_payload

    wrong_position = complete_payload()
    wrong_position["representative_load_path"][1] = {
        "kind": "CONNECTION", "connection_client_key": "c2",
    }
    with pytest.raises(PredictionError, match="INVALID_LOAD_PATH"):
        validate_prediction_payload(project_with_two_members, wrong_position)

    duplicate = complete_payload()
    duplicate["representative_load_path"] = [
        {"kind": "CONNECTION", "connection_client_key": "c1"},
        {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m1"},
        {"kind": "CONNECTION", "connection_client_key": "c2"},
        {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m1"},
        {"kind": "CONNECTION", "connection_client_key": "c1"},
    ]
    with pytest.raises(PredictionError, match="INVALID_LOAD_PATH"):
        validate_prediction_payload(project_with_two_members, duplicate)


@pytest.mark.django_db
def test_payload_accepts_documented_history_display_shapes(project_with_two_members):
    from learning.services import validate_prediction_payload

    connection_point = complete_payload()
    connection_point["member_judgments"][0]["display"] = {"member_label": "主杆"}
    connection_point["max_displacement_location"]["display"] = {
        "geometry_node_client_key": "n1",
        "geometry_node_label": "荷载点",
    }
    validate_prediction_payload(project_with_two_members, connection_point)

    endpoint_point = complete_payload()
    endpoint_point["max_displacement_location"] = {
        "kind": "MEMBER_ENDPOINT",
        "physical_member_client_key": "m2",
        "endpoint": "END",
        "display": {
            "member_label": "副杆",
            "geometry_node_client_key": "n3",
            "geometry_node_label": "同坐标自由端",
        },
    }
    validate_prediction_payload(project_with_two_members, endpoint_point)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["member_judgments"][0].update({"display": {"member_label": "主杆", "member_id": 1}}),
        lambda payload: payload["max_displacement_location"].update({"display": {"geometry_node_client_key": "n1", "x_mm": 0}}),
        lambda payload: payload.update({"max_displacement_location": {"kind": "MEMBER_ENDPOINT", "physical_member_client_key": "m2", "endpoint": "END", "display": {"member_label": "副杆", "analysis_node_id": "a1"}}}),
    ],
)
def test_payload_rejects_unexpected_history_display_fields(project_with_two_members, mutate):
    from learning.services import PredictionError, validate_prediction_payload

    payload = deepcopy(complete_payload())
    mutate(payload)

    with pytest.raises(PredictionError, match="PREDICTION_INVALID_SCHEMA"):
        validate_prediction_payload(project_with_two_members, payload)


@pytest.mark.django_db
def test_owner_completes_current_draft_once(project_with_two_members, owner):
    """A completed prediction is immutable evidence for its source draft."""
    from learning.services import PredictionError, complete_prediction, create_prediction

    project_with_two_members.refresh_from_db()
    prediction = create_prediction(
        project=project_with_two_members,
        actor=owner,
        expected_draft_version=project_with_two_members.draft_version,
    )
    assert prediction.status == prediction.Status.DRAFT
    assert prediction.source_draft_version == project_with_two_members.draft_version
    assert prediction.created_by == owner
    complete_prediction(
        prediction=prediction,
        actor=owner,
        expected_draft_version=project_with_two_members.draft_version,
        payload=complete_payload(),
    )
    prediction.refresh_from_db()

    assert prediction.status == prediction.Status.COMPLETED
    assert prediction.completed_at is not None
    from learning.models import StudentResultReveal
    assert not StudentResultReveal.objects.filter(project=project_with_two_members).exists()
    with pytest.raises(PredictionError, match="PREDICTION_ALREADY_COMPLETED"):
        complete_prediction(
            prediction=prediction,
            actor=owner,
            expected_draft_version=project_with_two_members.draft_version,
            payload=complete_payload(),
        )


@pytest.mark.django_db
def test_only_active_participant_owner_may_create_prediction(project_with_two_members, owner):
    """Replacing owner-participant authorization with broad project writes leaks evidence to Developers."""
    from learning.services import PredictionError, create_prediction

    project_with_two_members.refresh_from_db()
    other = User.objects.create_user("prediction-other")
    manager = User.objects.create_user("prediction-manager", role=User.Role.MANAGER)
    developer = User.objects.create_user("prediction-developer", role=User.Role.DEVELOPER)
    EventMembership.objects.create(
        user=manager, event=project_with_two_members.event, membership_type=EventMembership.Type.MANAGER
    )

    for actor in (other, manager, developer):
        with pytest.raises(PredictionError, match="PROJECT_WRITE_DENIED"):
            create_prediction(
                project=project_with_two_members,
                actor=actor,
                expected_draft_version=project_with_two_members.draft_version,
            )
    EventMembership.objects.filter(
        user=owner,
        event=project_with_two_members.event,
        membership_type=EventMembership.Type.PARTICIPANT,
    ).update(is_active=False)
    with pytest.raises(PredictionError, match="PROJECT_WRITE_DENIED"):
        create_prediction(
            project=project_with_two_members,
            actor=owner,
            expected_draft_version=project_with_two_members.draft_version,
        )


@pytest.mark.django_db
def test_non_owner_cannot_complete_owner_prediction(project_with_two_members, owner):
    from learning.services import PredictionError, complete_prediction, create_prediction

    project_with_two_members.refresh_from_db()
    prediction = create_prediction(
        project=project_with_two_members, actor=owner, expected_draft_version=project_with_two_members.draft_version
    )
    developer = User.objects.create_user("prediction-complete-developer", role=User.Role.DEVELOPER)

    with pytest.raises(PredictionError, match="PROJECT_WRITE_DENIED"):
        complete_prediction(
            prediction=prediction,
            actor=developer,
            expected_draft_version=project_with_two_members.draft_version,
            payload=complete_payload(),
        )
    prediction.refresh_from_db()
    assert prediction.status == prediction.Status.DRAFT


@pytest.mark.django_db
def test_prediction_lifecycle_blocks_purged_projects(project_with_two_members, owner):
    from learning.services import PredictionError, create_prediction

    project_with_two_members.event.status = CompetitionEvent.Status.PURGED
    project_with_two_members.event.save(update_fields=["status"])
    project_with_two_members.refresh_from_db()

    with pytest.raises(PredictionError, match="PROJECT_WRITE_DENIED"):
        create_prediction(
            project=project_with_two_members,
            actor=owner,
            expected_draft_version=project_with_two_members.draft_version,
        )


@pytest.mark.django_db
def test_changed_draft_invalidates_draft_but_preserves_completed_history(project_with_two_members, owner):
    from learning.models import Prediction
    from learning.services import PredictionError, complete_prediction, create_prediction

    project_with_two_members.refresh_from_db()
    old_completed = Prediction.objects.create(
        project=project_with_two_members,
        source_draft_version=0,
        status=Prediction.Status.COMPLETED,
        created_by=owner,
        payload_json={"historical": True},
        completed_at=timezone.now(),
    )
    draft = create_prediction(
        project=project_with_two_members,
        actor=owner,
        expected_draft_version=project_with_two_members.draft_version,
    )
    project_with_two_members.draft_version += 1
    project_with_two_members.save(update_fields=["draft_version"])

    with pytest.raises(PredictionError, match="PREDICTION_STALE_DRAFT"):
        complete_prediction(
            prediction=draft,
            actor=owner,
            expected_draft_version=project_with_two_members.draft_version,
            payload=complete_payload(),
        )
    draft.refresh_from_db()
    old_completed.refresh_from_db()
    assert draft.status == Prediction.Status.INVALIDATED
    assert draft.invalidation_code == "PREDICTION_STALE_DRAFT"
    assert old_completed.status == Prediction.Status.COMPLETED


@pytest.mark.django_db
def test_invalid_completion_keeps_prediction_draft(project_with_two_members, owner):
    from learning.models import Prediction
    from learning.services import PredictionError, complete_prediction, create_prediction

    project_with_two_members.refresh_from_db()
    prediction = create_prediction(
        project=project_with_two_members, actor=owner, expected_draft_version=project_with_two_members.draft_version
    )
    incomplete = complete_payload()
    incomplete["member_judgments"] = incomplete["member_judgments"][:1]

    with pytest.raises(PredictionError, match="PREDICTION_INCOMPLETE"):
        complete_prediction(
            prediction=prediction,
            actor=owner,
            expected_draft_version=project_with_two_members.draft_version,
            payload=incomplete,
        )
    with pytest.raises(PredictionError, match="PREDICTION_INVALID_SCHEMA"):
        complete_prediction(
            prediction=prediction,
            actor=owner,
            expected_draft_version=project_with_two_members.draft_version,
            payload={"schema_version": "prediction-v2"},
        )
    prediction.refresh_from_db()
    assert prediction.status == Prediction.Status.DRAFT
    assert prediction.completed_at is None


@pytest.mark.django_db
def test_result_reveal_blocks_completion_without_creating_another_reveal(project_with_two_members, owner, success_run):
    from learning.models import StudentResultReveal
    from learning.services import PredictionError, complete_prediction, create_prediction

    project_with_two_members.refresh_from_db()
    prediction = create_prediction(
        project=project_with_two_members, actor=owner, expected_draft_version=project_with_two_members.draft_version
    )
    StudentResultReveal.objects.create(
        project=project_with_two_members,
        source_draft_version=project_with_two_members.draft_version,
        first_analysis_run=success_run,
        revealed_to_user=owner,
    )

    with pytest.raises(PredictionError, match="PREDICTION_AFTER_RESULT_REVEAL"):
        complete_prediction(
            prediction=prediction,
            actor=owner,
            expected_draft_version=project_with_two_members.draft_version,
            payload=complete_payload(),
        )
    prediction.refresh_from_db()
    assert prediction.status == prediction.Status.DRAFT
    assert StudentResultReveal.objects.filter(project=project_with_two_members).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("role", [User.Role.MANAGER, User.Role.DEVELOPER])
def test_privileged_owner_participant_cannot_create_prediction(project_with_two_members, owner, role):
    """Privileged roles cannot create student learning evidence, even as owner-participants."""
    from learning.models import Prediction
    from learning.services import PredictionError, create_prediction

    project_with_two_members.refresh_from_db()
    owner.role = role
    owner.save(update_fields=["role"])

    with pytest.raises(PredictionError, match="PROJECT_WRITE_DENIED"):
        create_prediction(
            project=project_with_two_members,
            actor=owner,
            expected_draft_version=project_with_two_members.draft_version,
        )
    assert not Prediction.objects.filter(project=project_with_two_members).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("role", [User.Role.MANAGER, User.Role.DEVELOPER])
def test_privileged_owner_participant_cannot_complete_prediction(project_with_two_members, owner, role):
    """A privileged role change cannot mutate the owner's existing DRAFT evidence."""
    from learning.services import PredictionError, complete_prediction, create_prediction

    project_with_two_members.refresh_from_db()
    prediction = create_prediction(
        project=project_with_two_members,
        actor=owner,
        expected_draft_version=project_with_two_members.draft_version,
    )
    owner.role = role
    owner.save(update_fields=["role"])

    with pytest.raises(PredictionError, match="PROJECT_WRITE_DENIED"):
        complete_prediction(
            prediction=prediction,
            actor=owner,
            expected_draft_version=project_with_two_members.draft_version,
            payload=complete_payload(),
        )
    prediction.refresh_from_db()
    assert prediction.status == prediction.Status.DRAFT
    assert prediction.payload_json == {}
    assert prediction.completed_at is None
