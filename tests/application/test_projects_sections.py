from datetime import date, datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone


@pytest.fixture
def event(db):
    from competitions.models import CompetitionEvent

    return CompetitionEvent.objects.create(
        name="赛事 A",
        event_code="M3-A",
        competition_date=date(2026, 11, 7),
        starts_at=timezone.make_aware(datetime(2026, 11, 7)),
        ends_at=timezone.make_aware(datetime(2026, 11, 8)),
    )


@pytest.fixture
def owner(event):
    from accounts.models import User
    from competitions.models import EventMembership

    user = User.objects.create_user("team-owner")
    EventMembership.objects.create(
        user=user, event=event, membership_type=EventMembership.Type.PARTICIPANT
    )
    return user


@pytest.mark.django_db
def test_project_persists_event_owner_and_truss_draft(event, owner):
    from projects.models import Project

    project = Project.objects.create(event=event, owner_user=owner, name="桁架方案")

    assert project.analysis_type == Project.AnalysisType.TRUSS_2D
    assert project.draft_version == 0
    assert project.event_id == event.id
    assert project.owner_user_id == owner.id


@pytest.mark.django_db
def test_project_reuses_existing_event_ownership_authorization(event, owner):
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project
    from projects.services import can_modify_project, can_view_project

    project = Project.objects.create(event=event, owner_user=owner, name="桁架方案")
    other = User.objects.create_user("other-team")
    manager = User.objects.create_user("assigned-manager", role=User.Role.MANAGER)
    developer = User.objects.create_user("developer", role=User.Role.DEVELOPER)
    EventMembership.objects.create(
        user=manager, event=event, membership_type=EventMembership.Type.MANAGER
    )

    assert can_view_project(owner, project) is True
    assert can_modify_project(owner, project) is True
    assert can_view_project(other, project) is False
    assert can_modify_project(other, project) is False
    assert can_view_project(manager, project) is True
    assert can_modify_project(manager, project) is False
    assert can_modify_project(developer, project) is True


@pytest.mark.django_db
def test_section_persists_rectangle_engine_properties_and_stable_definition_hash(owner):
    from materials.services import create_section

    definition = {
        "schema_version": "section-definition-v1",
        "type": "rectangle",
        "width_mm": 10.0,
        "height_mm": 2.0,
        "density_g_per_mm3": 0.0007,
        "center_x_mm": 0.0,
        "center_y_mm": 0.0,
        "angle_deg": 0.0,
    }
    section = create_section(owner=owner, name="矩形截面", definition=definition)
    same = create_section(owner=owner, name="相同截面", definition=dict(reversed(definition.items())))

    assert section.section_type == "RECTANGLE"
    assert section.properties_json["A_mm2"] == 20.0
    assert section.properties_json["Ix_mm4"] == pytest.approx(6.666666666666667)
    assert section.definition_hash == same.definition_hash


@pytest.mark.django_db
def test_section_persists_non_overlapping_composite_and_rejects_overlap(owner):
    from materials.services import SectionServiceError, create_section

    composite = {
        "schema_version": "section-definition-v1",
        "type": "composite",
        "components": [
            {"width_mm": 2.0, "height_mm": 2.0, "density_g_per_mm3": 0.0007, "center_x_mm": -2.0, "center_y_mm": 0.0, "angle_deg": 0.0},
            {"width_mm": 2.0, "height_mm": 2.0, "density_g_per_mm3": 0.0007, "center_x_mm": 2.0, "center_y_mm": 0.0, "angle_deg": 0.0},
        ],
    }
    section = create_section(owner=owner, name="组合截面", definition=composite)
    assert section.section_type == "COMPOSITE"
    assert section.properties_json["A_mm2"] == 8.0

    composite["components"][1]["center_x_mm"] = -1.0
    with pytest.raises(SectionServiceError, match="OVERLAP_UNSUPPORTED"):
        create_section(owner=owner, name="重叠截面", definition=composite)


@pytest.mark.django_db
def test_section_denies_cross_user_strip_reference(owner):
    from accounts.models import User
    from materials.models import Material, Strip
    from materials.services import SectionServiceError, create_section

    other = User.objects.create_user("other-owner")
    material = Material.objects.create(
        owner_user=other, name="竹材", E_MPa=Decimal("2000"),
        density_g_per_mm3=Decimal("0.0007"), source_type="MEASURED"
    )
    strip = Strip.objects.create(
        owner_user=other, material=material, name="条材", width_mm=1, thickness_mm=6
    )
    definition = {
        "schema_version": "section-definition-v1", "type": "rectangle",
        "width_mm": 1.0, "height_mm": 6.0, "density_g_per_mm3": 0.0007,
        "strip_id": strip.id,
    }
    with pytest.raises(SectionServiceError, match="FOREIGN_STRIP"):
        create_section(owner=owner, name="非法引用", definition=definition)
