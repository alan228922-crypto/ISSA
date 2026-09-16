import json

import pytest
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from accounts.models import User
from tests.application.test_prediction import owner, project, success_run


def reflection_model():
    import learning.models

    assert hasattr(learning.models, "Reflection"), "Reflection persistence model is missing"
    return learning.models.Reflection


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
