from datetime import date, datetime
from decimal import Decimal
from math import inf, nan

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone


@pytest.fixture
def context(db):
    from accounts.models import User
    from competitions.models import CompetitionEvent, EventMembership
    from materials.models import Material
    from materials.services import create_section
    from projects.models import Project

    owner = User.objects.create_user("physical-owner")
    event = CompetitionEvent.objects.create(name="赛事", event_code="PD", competition_date=date(2026, 11, 7), starts_at=timezone.make_aware(datetime(2026, 11, 7)), ends_at=timezone.make_aware(datetime(2026, 11, 8)))
    EventMembership.objects.create(user=owner, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    project = Project.objects.create(event=event, owner_user=owner, name="物理草稿")
    material = Material.objects.create(owner_user=owner, name="竹材", E_MPa=Decimal("2000"), density_g_per_mm3=Decimal("0.0007"), source_type="MEASURED")
    section = create_section(owner=owner, name="矩形", definition={"schema_version": "section-definition-v1", "type": "rectangle", "width_mm": 1.0, "height_mm": 6.0, "density_g_per_mm3": 0.0007})
    return owner, project, material, section


def valid_payload(material, section, *, version=0):
    return {
        "schema_version": "physical-draft-v1", "expected_draft_version": version,
        "nodes": [{"client_key": "n1", "x_mm": 0.0, "y_mm": 0.0, "label": "左"}, {"client_key": "n2", "x_mm": 1000.0, "y_mm": 0.0, "label": "右"}],
        "physical_members": [{"client_key": "m1", "start_node_client_key": "n1", "end_node_client_key": "n2", "material_id": material.id, "section_id": section.id, "label": "杆件", "is_active": True}],
        "connections": [{"client_key": "c1", "geometry_node_client_key": "n1", "participating_member_client_keys": ["m1"]}],
        "supports": [{"target_connection_client_key": "c1", "support_type": "PINNED", "restrained_axis": None}],
        "node_loads": [{"client_key": "l1", "target_connection_client_key": "c1", "fx_N": 0.0, "fy_N": -100.0, "label": "荷载"}],
    }


@pytest.mark.django_db
def test_geometry_node_rejects_duplicate_client_key_and_nonfinite_coordinates(context):
    from modeling.models import GeometryNode
    _, project, _, _ = context
    GeometryNode.objects.create(project=project, client_key="n1", x_mm=0, y_mm=0, label="A")
    duplicate = GeometryNode(project=project, client_key="n1", x_mm=1, y_mm=0, label="B")
    invalid = GeometryNode(project=project, client_key="n2", x_mm=nan, y_mm=0, label="C")
    with pytest.raises(ValidationError): duplicate.full_clean()
    with pytest.raises(ValidationError): invalid.full_clean()


@pytest.mark.django_db
def test_physical_member_rejects_foreign_or_zero_length_references(context):
    from accounts.models import User
    from modeling.models import GeometryNode, PhysicalMember
    from projects.models import Project
    owner, project, material, section = context
    n1 = GeometryNode.objects.create(project=project, client_key="n1", x_mm=0, y_mm=0, label="A")
    n2 = GeometryNode.objects.create(project=project, client_key="n2", x_mm=0, y_mm=0, label="B")
    zero = PhysicalMember(project=project, client_key="m1", start_geometry_node=n1, end_geometry_node=n2, material=material, section=section, label="零长")
    with pytest.raises(ValidationError): zero.full_clean()
    other = User.objects.create_user("foreign-owner")
    foreign_project = Project.objects.create(event=project.event, owner_user=other, name="其他")
    foreign_node = GeometryNode.objects.create(project=foreign_project, client_key="x", x_mm=1, y_mm=1, label="X")
    foreign = PhysicalMember(project=project, client_key="m2", start_geometry_node=n1, end_geometry_node=foreign_node, material=material, section=section, label="跨项目")
    with pytest.raises(ValidationError): foreign.full_clean()
    assert "solver_member_id" not in {field.name for field in PhysicalMember._meta.fields}


@pytest.mark.django_db
@pytest.mark.parametrize("support_type,axis,valid", [("PINNED", None, True), ("ROLLER", "X", True), ("ROLLER", "Y", True), ("PINNED", "X", False), ("ROLLER", None, False), ("ROLLER", "45", False)])
def test_support_enforces_v13_axis_policy(context, support_type, axis, valid):
    from modeling.models import Connection, GeometryNode, Support
    _, project, _, _ = context
    node = GeometryNode.objects.create(project=project, client_key="n", x_mm=0, y_mm=0, label="A")
    connection = Connection.objects.create(project=project, client_key="c", geometry_node=node)
    support = Support(project=project, target_connection=connection, support_type=support_type, restrained_axis=axis)
    if valid:
        support.full_clean()
    else:
        with pytest.raises(ValidationError): support.full_clean()


@pytest.mark.django_db
def test_connection_and_node_load_reject_cross_project_references(context):
    from accounts.models import User
    from modeling.models import Connection, GeometryNode, NodeLoad, PhysicalMember
    from projects.models import Project
    owner, project, material, section = context
    local = GeometryNode.objects.create(project=project, client_key="local", x_mm=0, y_mm=0, label="本地")
    other = User.objects.create_user("other-project-owner")
    foreign_project = Project.objects.create(event=project.event, owner_user=other, name="其他项目")
    foreign = GeometryNode.objects.create(project=foreign_project, client_key="foreign", x_mm=1, y_mm=0, label="外部")
    connection = Connection(project=project, client_key="foreign-connection", geometry_node=foreign)
    with pytest.raises(ValidationError): connection.full_clean()
    local_connection = Connection.objects.create(project=project, client_key="local-connection", geometry_node=local)
    foreign_connection = Connection.objects.create(project=foreign_project, client_key="other-connection", geometry_node=foreign)
    load = NodeLoad(project=project, client_key="foreign-load", target_connection=foreign_connection, fx_N=0, fy_N=-1, label="外部")
    with pytest.raises(ValidationError): load.full_clean()


@pytest.mark.django_db
def test_draft_save_increments_version_and_preserves_explicit_connection_only(context):
    from modeling.models import Connection, GeometryNode
    from modeling.services import save_physical_draft
    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["nodes"].extend([{"client_key": "n3", "x_mm": 500.0, "y_mm": -500.0, "label": "下"}, {"client_key": "n4", "x_mm": 500.0, "y_mm": 500.0, "label": "上"}])
    payload["physical_members"].append({"client_key": "m2", "start_node_client_key": "n3", "end_node_client_key": "n4", "material_id": material.id, "section_id": section.id, "label": "交叉杆", "is_active": True})
    result = save_physical_draft(actor=owner, project=project, payload=payload)
    assert result["draft_version"] == 1
    assert GeometryNode.objects.filter(project=project).count() == 4
    assert Connection.objects.filter(project=project).count() == 1


@pytest.mark.django_db
def test_draft_save_rejects_stale_and_rolls_back_invalid_complete_payload(context):
    from modeling.models import GeometryNode
    from modeling.services import DraftSaveError, save_physical_draft
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    with pytest.raises(DraftSaveError, match="STALE_DRAFT") as stale:
        save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section, version=0))
    assert stale.value.status_code == 409
    invalid = valid_payload(material, section, version=1)
    invalid["connections"].append({"client_key": "bad", "geometry_node_client_key": "n1", "participating_member_client_keys": ["missing"]})
    with pytest.raises(DraftSaveError, match="UNKNOWN_MEMBER"):
        save_physical_draft(actor=owner, project=project, payload=invalid)
    project.refresh_from_db()
    assert project.draft_version == 1
    assert GeometryNode.objects.filter(project=project).count() == 2


@pytest.mark.django_db
def test_draft_save_rejects_nonfinite_load_and_foreign_material(context):
    from accounts.models import User
    from materials.models import Material
    from modeling.services import DraftSaveError, save_physical_draft
    owner, project, material, section = context
    invalid = valid_payload(material, section)
    invalid["node_loads"][0]["fy_N"] = inf
    with pytest.raises(DraftSaveError, match="INVALID_NUMERIC_VALUE"):
        save_physical_draft(actor=owner, project=project, payload=invalid)
    other = User.objects.create_user("other-material-owner")
    foreign = Material.objects.create(owner_user=other, name="外部", E_MPa=1, density_g_per_mm3=0, source_type="MEASURED")
    invalid = valid_payload(material, section)
    invalid["physical_members"][0]["material_id"] = foreign.id
    with pytest.raises(DraftSaveError, match="FOREIGN_MATERIAL"):
        save_physical_draft(actor=owner, project=project, payload=invalid)


@pytest.mark.django_db
def test_invalid_support_aborts_whole_draft_save(context):
    from modeling.models import GeometryNode
    from modeling.services import DraftSaveError, save_physical_draft
    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["supports"][0]["restrained_axis"] = "X"
    with pytest.raises(DraftSaveError, match="INVALID_DRAFT"):
        save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    assert project.draft_version == 0
    assert GeometryNode.objects.filter(project=project).count() == 0
