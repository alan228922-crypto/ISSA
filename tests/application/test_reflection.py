import json

import pytest
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from accounts.models import User
from analysis.models import AnalysisRun
from competitions.models import CompetitionEvent, EventMembership
from tests.application.test_prediction import owner, project, success_run


def reflection_model():
    import learning.models

    assert hasattr(learning.models, "Reflection"), "Reflection persistence model is missing"
    return learning.models.Reflection


def activate(project):
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    project.refresh_from_db()


def reveal_for(project, run, owner):
    from learning.services import record_student_result_reveal

    return record_student_result_reveal(project=project, run=run, actor=owner)


@pytest.mark.django_db
def test_reflection_defaults_to_draft_and_uses_reflection_v1(success_run, owner):
    """A missing default or provenance field would make this fail."""
    Reflection = reflection_model()

    reflection = Reflection.objects.create(analysis_run=success_run, created_by=owner)

    assert reflection.status == Reflection.Status.DRAFT
    assert reflection.reflection_schema_version == "reflection-v1"
    assert reflection.completed_at is None
    assert reflection.created_by == owner
    assert reflection.created_at is not None
    assert reflection.updated_at is not None


@pytest.mark.django_db
def test_one_analysis_run_allows_at_most_one_reflection(success_run, owner):
    """Removing the run uniqueness constraint would make this fail."""
    Reflection = reflection_model()
    Reflection.objects.create(analysis_run=success_run, created_by=owner)

    with pytest.raises(IntegrityError):
        Reflection.objects.create(analysis_run=success_run, created_by=owner)


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["DRAFT", "COMPLETED"])
def test_reflection_persists_each_allowed_status(success_run, owner, status):
    """Removing either allowed database status would make this fail."""
    Reflection = reflection_model()

    reflection = Reflection.objects.create(
        analysis_run=success_run,
        created_by=owner,
        status=status,
    )

    assert reflection.status == status


@pytest.mark.django_db
def test_reflection_rejects_an_arbitrary_status_at_the_database(success_run, owner):
    """Removing the database status check would make this fail."""
    Reflection = reflection_model()

    with pytest.raises(IntegrityError):
        Reflection.objects.create(
            analysis_run=success_run,
            created_by=owner,
            status="INVALIDATED",
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_name",
    ["original_reasoning", "unexpected_results", "next_iteration_intent"],
)
def test_each_reflection_text_field_enforces_2000_character_contract(success_run, owner, field_name):
    """Changing any student-text maximum would make this fail."""
    Reflection = reflection_model()
    reflection = Reflection.objects.create(analysis_run=success_run, created_by=owner)
    setattr(reflection, field_name, "x" * 2001)

    with pytest.raises(ValidationError):
        reflection.full_clean()


@pytest.mark.django_db
def test_reflection_persistence_contains_no_analysis_snapshot_columns(success_run, owner):
    """Adding copied result, comparison, or explanation data would make this fail."""
    Reflection = reflection_model()
    reflection = Reflection.objects.create(analysis_run=success_run, created_by=owner)

    persisted_values = reflection.__dict__
    assert not {
        "result_json",
        "comparison_json",
        "explanation_json",
        "physical_snapshot_json",
        "solver_input_json",
        "material_snapshot_json",
        "section_snapshot_json",
    } & persisted_values.keys()


def test_learning_app_has_no_separate_design_rationale_model():
    """Reintroducing a second rationale persistence lifecycle would make this fail."""
    model_names = {model.__name__ for model in apps.get_app_config("learning").get_models()}

    assert "DesignRationale" not in model_names
    assert "DesignIteration" not in model_names


@pytest.mark.django_db
def test_supported_project_purge_removes_reflection_and_preserves_user(project, owner, success_run):
    """Omitting Reflection from ordered purge would leave a protected Run child behind."""
    Reflection = reflection_model()
    reflection = Reflection.objects.create(
        analysis_run=success_run,
        created_by=owner,
        original_reasoning="原始反思不得进入审计回执",
    )
    from projects.models import ProjectOperationalPurgeAudit
    from projects.services import purge_project_operational_data

    audit = purge_project_operational_data(project_id=project.id, actor_id=owner.id)

    assert not Reflection.objects.filter(pk=reflection.pk).exists()
    assert User.objects.filter(pk=owner.id).exists()
    assert audit.deletion_counts_json["learning.Reflection"] == 1
    persisted_audit = ProjectOperationalPurgeAudit.objects.get(pk=audit.pk)
    assert "原始反思不得进入审计回执" not in json.dumps(
        persisted_audit.deletion_counts_json,
        ensure_ascii=False,
    )


@pytest.mark.django_db
def test_success_run_with_same_draft_reveal_creates_owner_draft(project, owner, success_run):
    """Removing reveal eligibility or server-owned defaults would make this fail."""
    from learning.services import create_reflection

    activate(project)
    reveal_for(project, success_run, owner)
    reflection = create_reflection(run=success_run, actor=owner)

    assert reflection.analysis_run_id == success_run.id
    assert reflection.created_by_id == owner.id
    assert reflection.status == "DRAFT"
    assert reflection.reflection_schema_version == "reflection-v1"


@pytest.mark.django_db
def test_duplicate_reflection_creation_returns_stable_conflict(project, owner, success_run):
    """Replacing the one-run service guard would make this fail."""
    from learning.services import ReflectionError, create_reflection

    activate(project); reveal_for(project, success_run, owner)
    create_reflection(run=success_run, actor=owner)
    with pytest.raises(ReflectionError, match="REFLECTION_ALREADY_EXISTS"):
        create_reflection(run=success_run, actor=owner)


@pytest.mark.django_db
def test_success_run_without_reveal_is_denied(project, owner, success_run):
    from learning.services import ReflectionError, create_reflection

    activate(project)
    with pytest.raises(ReflectionError, match="REFLECTION_NOT_ELIGIBLE"):
        create_reflection(run=success_run, actor=owner)


@pytest.mark.django_db
def test_failed_run_is_denied_even_when_draft_is_revealed(project, owner, success_run):
    from learning.services import ReflectionError, create_reflection

    activate(project)
    reveal_for(project, success_run, owner)
    AnalysisRun.objects.filter(pk=success_run.pk).update(status=AnalysisRun.Status.SOLVER_FAILED)
    with pytest.raises(ReflectionError, match="REFLECTION_RUN_NOT_SUCCESS"):
        create_reflection(run=success_run, actor=owner)


@pytest.mark.django_db
def test_same_draft_second_success_run_is_eligible_without_first_run_match(project, owner, success_run):
    from learning.services import create_reflection

    activate(project)
    reveal = reveal_for(project, success_run, owner)
    second_run = AnalysisRun.objects.create(
        project=project, model_revision=success_run.model_revision, solver_version=success_run.solver_version,
        input_schema_version="truss2d-input-v1", input_hash="c" * 64,
        status=AnalysisRun.Status.SUCCESS, solver_input_json={}, created_by=owner,
    )
    reflection = create_reflection(run=second_run, actor=owner)

    assert reflection.analysis_run_id == second_run.id
    assert reveal.first_analysis_run_id == success_run.id


@pytest.mark.django_db
def test_owner_updates_and_clears_partial_draft(project, owner, success_run):
    from learning.services import create_reflection, update_reflection

    activate(project); reveal_for(project, success_run, owner)
    reflection = create_reflection(run=success_run, actor=owner)
    assert update_reflection(reflection=reflection, actor=owner, fields={"original_reasoning": "初始判断"}).original_reasoning == "初始判断"
    assert update_reflection(reflection=reflection, actor=owner, fields={"original_reasoning": ""}).original_reasoning == ""


@pytest.mark.django_db
def test_update_rejects_unknown_or_overlong_fields(project, owner, success_run):
    from learning.services import ReflectionError, create_reflection, update_reflection

    activate(project); reveal_for(project, success_run, owner)
    reflection = create_reflection(run=success_run, actor=owner)
    for fields in ({"status": "COMPLETED"}, {"original_reasoning": "x" * 2001}):
        with pytest.raises(ReflectionError, match="REFLECTION_INVALID_FIELDS"):
            update_reflection(reflection=reflection, actor=owner, fields=fields)


@pytest.mark.django_db
def test_completion_requires_three_trimmed_values_and_is_immutable(project, owner, success_run):
    from learning.services import ReflectionError, complete_reflection, create_reflection, update_reflection

    activate(project); reveal_for(project, success_run, owner)
    reflection = create_reflection(run=success_run, actor=owner)
    with pytest.raises(ReflectionError, match="REFLECTION_INCOMPLETE"):
        complete_reflection(reflection=reflection, actor=owner)
    update_reflection(reflection=reflection, actor=owner, fields={
        "original_reasoning": " 原因 ", "unexpected_results": " 意外 ", "next_iteration_intent": " 下一步 ",
    })
    completed = complete_reflection(reflection=reflection, actor=owner)
    assert completed.status == "COMPLETED" and completed.completed_at is not None
    assert completed.original_reasoning == " 原因 "
    with pytest.raises(ReflectionError, match="REFLECTION_ALREADY_COMPLETED"):
        update_reflection(reflection=completed, actor=owner, fields={"original_reasoning": "改写"})


@pytest.mark.django_db
def test_authoring_denies_other_manager_and_developer(project, owner, success_run):
    from learning.services import ReflectionError, create_reflection

    activate(project); reveal_for(project, success_run, owner)
    other = User.objects.create_user("reflection-other")
    manager = User.objects.create_user("reflection-manager", role=User.Role.MANAGER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    developer = User.objects.create_user("reflection-developer", role=User.Role.DEVELOPER)
    for actor in (other, manager, developer):
        with pytest.raises(ReflectionError, match="REFLECTION_WRITE_DENIED"):
            create_reflection(run=success_run, actor=actor)


@pytest.mark.django_db
def test_draft_is_private_completed_is_readable_to_manager_and_developer(project, owner, success_run):
    from learning.services import ReflectionError, complete_reflection, create_reflection, get_reflection_for_read, update_reflection

    activate(project); reveal_for(project, success_run, owner)
    reflection = create_reflection(run=success_run, actor=owner)
    manager = User.objects.create_user("reflection-read-manager", role=User.Role.MANAGER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    developer = User.objects.create_user("reflection-read-developer", role=User.Role.DEVELOPER)
    other = User.objects.create_user("reflection-read-other")
    assert get_reflection_for_read(reflection=reflection, actor=owner).pk == reflection.pk
    for actor in (manager, developer, other):
        with pytest.raises(ReflectionError, match="REFLECTION_READ_DENIED"):
            get_reflection_for_read(reflection=reflection, actor=actor)
    update_reflection(reflection=reflection, actor=owner, fields={
        "original_reasoning": "a", "unexpected_results": "b", "next_iteration_intent": "c",
    })
    complete_reflection(reflection=reflection, actor=owner)
    assert get_reflection_for_read(reflection=reflection, actor=manager).pk == reflection.pk
    assert get_reflection_for_read(reflection=reflection, actor=developer).pk == reflection.pk


@pytest.mark.django_db
@pytest.mark.parametrize("status", [CompetitionEvent.Status.FINISHED_GRACE, CompetitionEvent.Status.PURGED])
def test_finished_grace_and_purged_deny_all_authoring(project, owner, success_run, status):
    from learning.services import ReflectionError, complete_reflection, create_reflection, update_reflection

    activate(project); reveal_for(project, success_run, owner)
    reflection = create_reflection(run=success_run, actor=owner)
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=status)
    for operation in (
        lambda: create_reflection(run=success_run, actor=owner),
        lambda: update_reflection(reflection=reflection, actor=owner, fields={"original_reasoning": "x"}),
        lambda: complete_reflection(reflection=reflection, actor=owner),
    ):
        with pytest.raises(ReflectionError, match="REFLECTION_EVENT_NOT_ACTIVE"):
            operation()
