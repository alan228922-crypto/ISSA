from io import StringIO
from datetime import date, datetime

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings
from django.utils import timezone


def demo_counts():
    from accounts.models import User
    from analysis.models import AnalysisRun
    from competitions.models import CompetitionEvent, EventMembership
    from learning.models import Prediction, Reflection
    from modeling.models import Connection, GeometryNode, NodeLoad, PhysicalMember, Support
    from projects.models import Project

    return {
        "users": User.objects.filter(username="demo_student").count(),
        "events": CompetitionEvent.objects.filter(event_code="DEMO-TRUSS-2026").count(),
        "memberships": EventMembership.objects.filter(user__username="demo_student", event__event_code="DEMO-TRUSS-2026").count(),
        "projects": Project.objects.filter(owner_user__username="demo_student", event__event_code="DEMO-TRUSS-2026", name="B/T01 桁架 Demo").count(),
        "blank_projects": Project.objects.filter(owner_user__username="demo_student", event__event_code="DEMO-TRUSS-2026", name="空白建模 Demo").count(),
        "nodes": GeometryNode.objects.filter(project__owner_user__username="demo_student", project__event__event_code="DEMO-TRUSS-2026").count(),
        "members": PhysicalMember.objects.filter(project__owner_user__username="demo_student", project__event__event_code="DEMO-TRUSS-2026").count(),
        "connections": Connection.objects.filter(project__owner_user__username="demo_student", project__event__event_code="DEMO-TRUSS-2026").count(),
        "supports": Support.objects.filter(project__owner_user__username="demo_student", project__event__event_code="DEMO-TRUSS-2026").count(),
        "loads": NodeLoad.objects.filter(project__owner_user__username="demo_student", project__event__event_code="DEMO-TRUSS-2026").count(),
        "runs": AnalysisRun.objects.count(),
        "predictions": Prediction.objects.count(),
        "reflections": Reflection.objects.count(),
    }


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_seed_demo_requires_explicit_confirmation_without_writing():
    before = demo_counts()

    with pytest.raises(CommandError, match="--confirm"):
        call_command("seed_demo", stdout=StringIO())

    assert demo_counts() == before


@pytest.mark.django_db
def test_seed_demo_refuses_non_debug_settings_without_writing():
    before = demo_counts()

    with override_settings(DEBUG=False):
        with pytest.raises(CommandError, match="DEBUG=True"):
            call_command("seed_demo", "--confirm", stdout=StringIO())

    assert demo_counts() == before


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_seed_demo_creates_analyzable_project_without_learning_or_analysis_records(client):
    from analysis.orchestration import analyze_project, check_project
    from projects.models import Project
    from projects.services import can_view_project

    output = StringIO()
    call_command("seed_demo", "--confirm", stdout=output)

    project = Project.objects.get(
        owner_user__username="demo_student",
        event__event_code="DEMO-TRUSS-2026",
        name="B/T01 桁架 Demo",
        analysis_type=Project.AnalysisType.TRUSS_2D,
    )
    owner = project.owner_user
    assert demo_counts() == {
        "users": 1, "events": 1, "memberships": 1, "projects": 1, "blank_projects": 1,
        "nodes": 2, "members": 1, "connections": 2, "supports": 2, "loads": 1,
        "runs": 0, "predictions": 0, "reflections": 0,
    }
    assert can_view_project(owner, project) is True
    client.force_login(owner)
    assert "B/T01 桁架 Demo" in client.get("/events/").content.decode()
    assert client.get(f"/projects/{project.id}/workspace/").status_code == 200
    assert check_project(project=project, actor=owner, expected_draft_version=project.draft_version)["ok"] is True
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    assert run.status == "SUCCESS"
    assert "Demo data ready." in output.getvalue()
    assert f"/projects/{project.id}/workspace/" in output.getvalue()
    assert "空白建模 Demo" in output.getvalue()
    assert "手动验收" in output.getvalue()


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_seed_demo_is_idempotent_and_does_not_modify_unrelated_data():
    from accounts.models import User
    from competitions.models import CompetitionEvent

    other = User.objects.create_user("real-student")
    other_event = CompetitionEvent.objects.create(
        name="真实赛事",
        event_code="REAL-EVENT",
        competition_date=date(2026, 11, 7),
        starts_at=timezone.make_aware(datetime(2026, 11, 7)),
        ends_at=timezone.make_aware(datetime(2026, 11, 8)),
    )
    before_other = (other.id, other_event.id, other_event.name, other_event.status)

    call_command("seed_demo", "--confirm", stdout=StringIO())
    first = demo_counts()
    call_command("seed_demo", "--confirm", stdout=StringIO())

    other.refresh_from_db()
    other_event.refresh_from_db()
    assert demo_counts() == first
    assert (other.id, other_event.id, other_event.name, other_event.status) == before_other
