from datetime import date, datetime

import pytest
from django.db import IntegrityError
from django.utils import timezone

from analysis.models import AnalysisRun, ModelRevision, SolverVersion
from accounts.models import User
from competitions.models import CompetitionEvent, EventMembership
from projects.models import Project


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


@pytest.mark.django_db
def test_prediction_defaults_draft_and_reveal_is_unique(project, owner, success_run):
    from learning.models import Prediction, StudentResultReveal

    prediction = Prediction.objects.create(
        project=project,
        source_draft_version=7,
        created_by=owner,
        prediction_schema_version="prediction-v1",
        payload_json={},
    )

    assert prediction.status == Prediction.Status.DRAFT

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
