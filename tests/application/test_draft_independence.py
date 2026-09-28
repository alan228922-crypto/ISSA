"""Current editable drafts may contain unresolved links; frozen analyses may not."""

import pytest

from tests.application.test_physical_draft import context, valid_payload


@pytest.mark.django_db
def test_node_delete_keeps_member_and_connection_as_incomplete_draft(context):
    from modeling.models import Connection, GeometryNode, PhysicalMember
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    GeometryNode.objects.get(project=project, client_key="n1").delete()

    member = PhysicalMember.objects.get(project=project, client_key="m1")
    connection = Connection.objects.get(project=project, client_key="c1")
    assert member.start_geometry_node_id is None
    assert member.end_geometry_node.client_key == "n2"
    assert connection.geometry_node_id is None
    assert project.supports.count() == 1
    assert project.node_loads.count() == 1

    from analysis.orchestration import check_project
    project.refresh_from_db()
    codes = {issue["code"] for issue in check_project(project=project, actor=owner, expected_draft_version=project.draft_version)["issues"]}
    assert {"MISSING_MEMBER_START_NODE", "MISSING_CONNECTION_NODE", "MISSING_SUPPORT_NODE", "MISSING_LOAD_NODE"} <= codes


@pytest.mark.django_db
def test_member_delete_keeps_nodes_and_explicit_participation_gap(context):
    from modeling.models import Connection, GeometryNode, PhysicalMember
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    PhysicalMember.objects.get(project=project, client_key="m1").delete()

    connection = Connection.objects.get(project=project, client_key="c1")
    assert GeometryNode.objects.filter(project=project).count() == 2
    assert list(connection.participation_slots.order_by("position").values_list("member_id", flat=True)) == [None]


@pytest.mark.django_db
def test_connection_delete_keeps_support_and_load_unresolved(context):
    from modeling.models import Connection, NodeLoad, PhysicalMember, Support
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    Connection.objects.get(project=project, client_key="c1").delete()

    assert PhysicalMember.objects.filter(project=project).count() == 1
    assert Support.objects.get(project=project, client_key="s1").target_connection_id is None
    assert NodeLoad.objects.get(project=project, client_key="l1").target_connection_id is None


@pytest.mark.django_db
def test_material_and_section_delete_preserve_member_and_strip(context):
    from materials.models import Strip
    from modeling.models import PhysicalMember
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    strip = Strip.objects.create(owner_user=owner, material=material, name="竹条", width_mm=1, thickness_mm=2)
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    material.delete()
    section.delete()

    member = PhysicalMember.objects.get(project=project, client_key="m1")
    strip.refresh_from_db()
    assert member.material_id is None
    assert member.section_id is None
    assert strip.material_id is None


@pytest.mark.django_db
def test_incomplete_draft_round_trips_and_rebinds_all_nullable_references(context):
    from modeling.models import Connection, PhysicalMember
    from modeling.services import save_physical_draft
    from projects.workspace import _draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["physical_members"][0].update(start_node_client_key=None, material_id=None, section_id=None)
    payload["connections"][0].update(geometry_node_client_key=None, participating_member_client_keys=[None, "m1"])
    payload["supports"][0]["target_connection_client_key"] = None
    payload["node_loads"][0]["target_connection_client_key"] = None
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    draft = _draft(project)
    assert draft["physical_members"][0]["start_node_client_key"] is None
    assert draft["physical_members"][0]["material_id"] is None
    assert draft["connections"][0]["participating_member_client_keys"] == [None, "m1"]
    assert draft["supports"][0]["target_connection_client_key"] is None
    assert draft["node_loads"][0]["target_connection_client_key"] is None
    assert list(Connection.objects.get(project=project).participation_slots.values_list("member_id", flat=True)) == [None, PhysicalMember.objects.get(project=project).id]

    rebound = valid_payload(material, section, version=project.draft_version)
    save_physical_draft(actor=owner, project=project, payload=rebound)
    project.refresh_from_db()
    assert _draft(project)["physical_members"][0]["start_node_client_key"] == "n1"
    assert _draft(project)["connections"][0]["participating_member_client_keys"] == ["m1"]


@pytest.mark.django_db
def test_model_check_reports_incomplete_refs_without_snapshot_or_solver(context, monkeypatch):
    from analysis.orchestration import check_project
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["physical_members"][0].update(start_node_client_key=None, end_node_client_key=None, material_id=None, section_id=None)
    payload["connections"][0]["participating_member_client_keys"] = [None]
    payload["supports"][0]["target_connection_client_key"] = None
    payload["node_loads"][0]["target_connection_client_key"] = None
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()

    def forbidden(*args, **kwargs):
        raise AssertionError("strict snapshot/solver must not run for incomplete draft")

    monkeypatch.setattr("modeling.snapshot.build_physical_snapshot", forbidden)
    monkeypatch.setattr("analysis.orchestration.Truss2DSolver", forbidden)
    result = check_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    assert not result["ok"]
    assert {issue["code"] for issue in result["issues"]} == {
        "MISSING_MEMBER_START_NODE", "MISSING_MEMBER_END_NODE", "MISSING_MEMBER_MATERIAL",
        "MISSING_MEMBER_SECTION", "MISSING_CONNECTION_PARTICIPANT", "MISSING_SUPPORT_NODE", "MISSING_LOAD_NODE",
    }
    assert all(issue["human_message"] and issue["physical_object"] for issue in result["issues"])


@pytest.mark.django_db
def test_analyze_rejects_incomplete_before_revision_run_and_solver(context, monkeypatch):
    from analysis.models import AnalysisRun, ModelRevision
    from analysis.orchestration import AnalysisError, analyze_project
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["physical_members"][0]["material_id"] = None
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    monkeypatch.setattr("analysis.orchestration.get_or_create_revision", lambda **kwargs: (_ for _ in ()).throw(AssertionError("revision created")))
    with pytest.raises(AnalysisError, match="INCOMPLETE_DRAFT"):
        analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    assert ModelRevision.objects.filter(project=project).count() == 0
    assert AnalysisRun.objects.filter(project=project).count() == 0


@pytest.mark.django_db
def test_direct_revision_service_rejects_participation_gap_before_snapshot(context):
    from analysis.models import ModelRevision
    from analysis.services import get_or_create_revision
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["connections"][0]["participating_member_client_keys"] = [None]
    save_physical_draft(actor=owner, project=project, payload=payload)
    with pytest.raises(ValueError, match="INCOMPLETE_DRAFT"):
        get_or_create_revision(project=project, actor=owner)
    assert not ModelRevision.objects.filter(project=project).exists()


@pytest.mark.django_db
def test_check_uses_current_locked_version_after_shared_resource_deletion(context):
    from analysis.orchestration import AnalysisError, check_project
    from materials.services import delete_resource
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    project.refresh_from_db()
    stale_project = project
    delete_resource(actor=owner, resource=material)
    with pytest.raises(AnalysisError, match="STALE_DRAFT"):
        check_project(project=stale_project, actor=owner, expected_draft_version=1)


@pytest.mark.django_db
def test_shared_material_delete_updates_each_affected_project_once_and_audits(context):
    from materials.models import Material, ResourceDeletionAudit, Strip
    from materials.services import delete_resource
    from modeling.models import PhysicalMember
    from modeling.services import save_physical_draft
    from projects.models import Project

    owner, project, material, section = context
    second = Project.objects.create(event=project.event, owner_user=owner, name="第二项目")
    for current in (project, second):
        payload = valid_payload(material, section)
        if current == project:
            payload["physical_members"].append({**payload["physical_members"][0], "client_key": "m2"})
        save_physical_draft(actor=owner, project=current, payload=payload)
    strip = Strip.objects.create(owner_user=owner, material=material, name="条材", width_mm=1, thickness_mm=2)
    receipt = delete_resource(actor=owner, resource=material)

    assert not Material.objects.filter(pk=material.pk).exists()
    assert set(receipt.affected_project_ids) == {project.pk, second.pk}
    assert receipt.object_counts_json == {"members": 3, "strips": 1}
    assert ResourceDeletionAudit.objects.get(pk=receipt.pk).actor_id == owner.pk
    for current in (project, second):
        current.refresh_from_db()
        assert current.draft_version == 2
        assert all(member.material_id is None for member in PhysicalMember.objects.filter(project=current))
    strip.refresh_from_db()
    assert strip.material_id is None


@pytest.mark.django_db
def test_shared_section_delete_preserves_historical_snapshot(context):
    from analysis.services import get_or_create_revision
    from materials.models import Section
    from materials.services import delete_resource
    from modeling.models import PhysicalMember
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    revision, _ = get_or_create_revision(project=project, actor=owner)
    frozen = revision.physical_snapshot_json
    receipt = delete_resource(actor=owner, resource=section)

    assert not Section.objects.filter(pk=section.pk).exists()
    assert receipt.object_counts_json == {"members": 1, "strips": 0}
    assert PhysicalMember.objects.get(project=project).section_id is None
    revision.refresh_from_db()
    assert revision.physical_snapshot_json == frozen


@pytest.mark.django_db
def test_resource_delete_denies_unrelated_actor_without_mutation(context):
    from accounts.models import User
    from materials.services import SectionServiceError, delete_resource
    from modeling.models import PhysicalMember
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    other = User.objects.create_user("other-resource-actor")
    with pytest.raises(SectionServiceError, match="FORBIDDEN"):
        delete_resource(actor=other, resource=material)
    assert PhysicalMember.objects.get(project=project).material_id == material.pk
    project.refresh_from_db()
    assert project.draft_version == 1


@pytest.mark.django_db
@pytest.mark.parametrize("bad_participant", [["m1"], {"client_key": "m1"}, 42])
def test_malformed_participant_reference_rejected_without_partial_save(context, bad_participant):
    from modeling.models import GeometryNode
    from modeling.services import DraftSaveError, save_physical_draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["connections"][0]["participating_member_client_keys"] = [bad_participant]
    with pytest.raises(DraftSaveError, match="INVALID_DRAFT"):
        save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    assert project.draft_version == 0
    assert GeometryNode.objects.filter(project=project).count() == 0
