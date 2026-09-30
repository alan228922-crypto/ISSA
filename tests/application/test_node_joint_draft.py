"""V2 editable topology contracts; no Solver or historical artifact is involved."""

import pytest

from tests.application.test_physical_draft import context


def v2_payload(material, section, *, version=0):
    return {
        "schema_version": "physical-draft-v2",
        "expected_draft_version": version,
        "nodes": [
            {"client_key": "n1", "x_mm": 0.0, "y_mm": 0.0, "label": "左"},
            {"client_key": "n2", "x_mm": 1000.0, "y_mm": 0.0, "label": "右"},
        ],
        "physical_members": [{
            "client_key": "m1", "start_node_client_key": "n1", "end_node_client_key": "n2",
            "material_id": material.id, "section_id": section.id, "label": "主杆", "is_active": True,
        }],
        "member_joint_incidences": [],
        "supports": [{"client_key": "s1", "target_node_client_key": "n1", "support_type": "PINNED", "restrained_axis": None}],
        "node_loads": [{"client_key": "l1", "target_node_client_key": "n2", "fx_N": 0.0, "fy_N": -100.0, "label": "向下"}],
    }


def v2_project(project):
    project.draft_schema_version = "physical-draft-v2"
    project.save(update_fields=["draft_schema_version"])
    return project


@pytest.mark.django_db
def test_v2_round_trip_and_direct_node_targets(context):
    from modeling.models import MemberJointIncidence, NodeLoad, Support
    from modeling.services import save_physical_draft
    from projects.workspace import _draft

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["nodes"].append({"client_key": "n3", "x_mm": 500.0, "y_mm": 0.0, "label": "中"})
    payload["member_joint_incidences"] = [{"member_client_key": "m1", "node_client_key": "n3"}]
    result = save_physical_draft(actor=owner, project=project, payload=payload)
    assert result["draft_version"] == 1
    assert MemberJointIncidence.objects.filter(project=project, member__client_key="m1", node__client_key="n3").exists()
    assert Support.objects.get(project=project, client_key="s1").target_node.client_key == "n1"
    assert NodeLoad.objects.get(project=project, client_key="l1").target_node.client_key == "n2"
    draft = _draft(project)
    assert draft["schema_version"] == "physical-draft-v2"
    assert draft["member_joint_incidences"] == [{"member_client_key": "m1", "node_client_key": "n3"}]
    assert "connections" not in draft
    assert draft["supports"][0]["target_node_client_key"] == "n1"
    assert draft["node_loads"][0]["target_node_client_key"] == "n2"
    save_physical_draft(actor=owner, project=project, payload={**draft, "expected_draft_version": 1})
    assert MemberJointIncidence.objects.filter(project=project).count() == 1


@pytest.mark.django_db
def test_v2_save_rejects_member_through_node_without_incidence(context):
    from modeling.services import DraftSaveError, save_physical_draft

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["nodes"].append({"client_key": "n3", "x_mm": 500.0, "y_mm": 0.0, "label": "中"})
    with pytest.raises(DraftSaveError, match="MEMBER_PASSES_THROUGH_NODE_WITHOUT_INCIDENCE"):
        save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    assert project.draft_version == 0
    assert project.geometry_nodes.count() == 0


@pytest.mark.django_db
def test_v2_missing_endpoint_remains_savable(context):
    from modeling.completeness import draft_completeness_issues
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["physical_members"][0]["end_node_client_key"] = None
    save_physical_draft(actor=owner, project=project, payload=payload)
    assert {issue["code"] for issue in draft_completeness_issues(project)} == {"MISSING_MEMBER_END_NODE", "UNATTACHED_LOAD_NODE"}


@pytest.mark.django_db
def test_v2_delete_node_preserves_dependents(context):
    from modeling.models import GeometryNode, MemberJointIncidence, NodeLoad, PhysicalMember, Support
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["nodes"].insert(0, {"client_key": "n0", "x_mm": -1000.0, "y_mm": 0.0, "label": "延伸"})
    payload["physical_members"].append({
        "client_key": "m2", "start_node_client_key": "n0", "end_node_client_key": "n2",
        "material_id": material.id, "section_id": section.id, "label": "通杆", "is_active": True,
    })
    payload["member_joint_incidences"].append({"member_client_key": "m2", "node_client_key": "n1"})
    save_physical_draft(actor=owner, project=project, payload=payload)
    GeometryNode.objects.get(project=project, client_key="n1").delete()
    assert PhysicalMember.objects.get(project=project, client_key="m1").start_geometry_node_id is None
    assert PhysicalMember.objects.get(project=project, client_key="m2").start_geometry_node.client_key == "n0"
    assert not MemberJointIncidence.objects.filter(project=project, node__client_key="n1").exists()
    assert Support.objects.get(project=project, client_key="s1").target_node_id is None
    assert NodeLoad.objects.get(project=project, client_key="l1").target_node.client_key == "n2"


@pytest.mark.django_db
def test_v2_rejects_new_same_coordinate_identity_but_keeps_audited_legacy_pair(context):
    from modeling.models import DraftMigrationAudit
    from modeling.services import DraftSaveError, save_physical_draft

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["nodes"].append({"client_key": "legacy-free", "x_mm": 0.0, "y_mm": 0.0, "label": "旧自由端"})
    with pytest.raises(DraftSaveError, match="DUPLICATE_NODE_COORDINATE"):
        save_physical_draft(actor=owner, project=project, payload=payload)
    DraftMigrationAudit.objects.create(
        project=project, status="CONVERTED", source_draft_version=0, source_hash="a" * 64,
        source_payload_json={}, node_mapping_json={},
        legacy_exceptions_json={
            "same_coordinate_pairs": [["n1", "legacy-free", 0.0, 0.0]],
            "nonparticipating_passes": [["m1", "legacy-free", 0.0, 0.0, 0.0, 0.0, 1000.0, 0.0]],
        },
        reason_code="",
    )
    save_physical_draft(actor=owner, project=project, payload=payload)
    assert project.geometry_nodes.filter(x_mm=0.0, y_mm=0.0).count() == 2
    from modeling.completeness import draft_completeness_issues
    assert "DUPLICATE_NODE_COORDINATE" not in {issue["code"] for issue in draft_completeness_issues(project)}


@pytest.mark.django_db
def test_v1_payload_cannot_write_v2_project(context):
    from modeling.models import Connection
    from modeling.services import DraftSaveError, save_physical_draft
    from tests.application.test_physical_draft import valid_payload

    owner, project, material, section = context
    v2_project(project)
    with pytest.raises(DraftSaveError, match="UNSUPPORTED_DRAFT_SCHEMA"):
        save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    assert Connection.objects.filter(project=project).count() == 0
    project.refresh_from_db()
    assert project.draft_version == 0


def test_topology_candidate_filter_matches_bruteforce_on_small_models():
    from modeling.topology import find_unrepresented_passes

    nodes = {"a": (0.0, 0.0), "b": (10.0, 0.0), "mid": (5.0, 0.0), "off": (5.0, 1.0), "x": (5.0, 5.0)}
    members = [{"client_key": "horizontal", "start_node_client_key": "a", "end_node_client_key": "b"}]
    assert find_unrepresented_passes(nodes=nodes, members=members, incidences=set(), exemptions=set()) == [("horizontal", "mid")]


@pytest.mark.django_db
def test_v2_and_v1_target_authorities_do_not_mix(context):
    from django.core.exceptions import ValidationError

    from modeling.models import Connection, GeometryNode, NodeLoad, Support

    _, project, _, _ = context
    node = GeometryNode.objects.create(project=project, client_key="n", x_mm=0, y_mm=0)
    connection = Connection.objects.create(project=project, client_key="c", geometry_node=node)
    with pytest.raises(ValidationError):
        Support(project=project, client_key="s", target_node=node, support_type="PINNED").full_clean()
    with pytest.raises(ValidationError):
        NodeLoad(project=project, client_key="l", target_node=node, fx_N=1, fy_N=0).full_clean()
    v2_project(project)
    with pytest.raises(ValidationError):
        Connection(project=project, client_key="c2", geometry_node=node).full_clean()
    with pytest.raises(ValidationError):
        Support(project=project, client_key="s2", target_connection=connection, support_type="PINNED").full_clean()
    with pytest.raises(ValidationError):
        NodeLoad(project=project, client_key="l2", target_connection=connection, fx_N=1, fy_N=0).full_clean()
