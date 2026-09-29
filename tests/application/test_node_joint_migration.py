"""Read-only proposal, auditable conversion, and unchanged numerical behavior."""

import pytest

from tests.application.test_analysis_acceptance import save_bt01_draft
from tests.application.test_physical_draft import context, valid_payload


@pytest.mark.django_db
def test_complete_v1_conversion_preserves_normalized_graph_and_numbers(context):
    from idealization.truss2d import idealize
    from modeling.node_joint_migration import build_migration_proposal, compare_legacy_v2, convert_project
    from modeling.snapshot import build_physical_snapshot
    from modeling.models import Connection, MemberJointIncidence

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    old = build_physical_snapshot(project)
    proposal = build_migration_proposal(project)
    assert proposal.source_version == 1
    audit = convert_project(project_id=project.pk, expected_draft_version=1, actor=owner)
    project.refresh_from_db()
    assert project.draft_schema_version == "physical-draft-v2"
    assert project.draft_version == 2
    assert audit.status == "CONVERTED"
    assert not Connection.objects.filter(project=project).exists()
    new = build_physical_snapshot(project)
    assert compare_legacy_v2(v1_snapshot=old, v2_snapshot=new, mapping=proposal.node_mapping).equivalent
    assert idealize(new).model.schema_version == "truss2d-input-v1"
    assert MemberJointIncidence.objects.filter(project=project).count() == 0


@pytest.mark.django_db
def test_legacy_free_endpoints_same_coordinate_remain_distinct(context):
    from modeling.node_joint_migration import build_migration_proposal
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["physical_members"].append({**payload["physical_members"][0], "client_key": "m2"})
    save_physical_draft(actor=owner, project=project, payload=payload)
    proposal = build_migration_proposal(project)
    assert proposal.node_mapping["free:m1:END"] != proposal.node_mapping["free:m2:END"]
    by_key = {row["client_key"]: row for row in proposal.draft_v2["nodes"]}
    first = by_key[proposal.node_mapping["free:m1:END"]]
    second = by_key[proposal.node_mapping["free:m2:END"]]
    assert (first["x_mm"], first["y_mm"]) == (second["x_mm"], second["y_mm"])


@pytest.mark.django_db
def test_ambiguous_null_participant_blocks_only_its_project(context):
    from modeling.models import Connection, DraftMigrationAudit
    from modeling.node_joint_migration import convert_project
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["connections"][0]["participating_member_client_keys"] = [None]
    save_physical_draft(actor=owner, project=project, payload=payload)
    audit = convert_project(project_id=project.pk, expected_draft_version=1, actor=owner)
    project.refresh_from_db()
    assert audit.status == "BLOCKED"
    assert audit.reason_code == "AMBIGUOUS_CONNECTION_PARTICIPATION"
    assert project.draft_schema_version == "physical-draft-v1"
    assert Connection.objects.filter(project=project).exists()
    assert DraftMigrationAudit.objects.filter(project=project).count() == 1


@pytest.mark.django_db
def test_legacy_nonparticipating_pass_is_audited_not_connected(context):
    from modeling.models import MemberJointIncidence
    from modeling.node_joint_migration import build_migration_proposal, convert_project
    from modeling.services import save_physical_draft
    from projects.workspace import _draft

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    project.refresh_from_db()
    payload = {**_draft(project), "expected_draft_version": 1}
    payload["nodes"].append({"client_key": "legacy-visual", "x_mm": 500.0, "y_mm": 0.0, "label": "未连接"})
    save_physical_draft(actor=owner, project=project, payload=payload)
    project.refresh_from_db()
    proposal = build_migration_proposal(project)
    assert ("m1", "geometry:legacy-visual") in proposal.exceptions
    audit = convert_project(project_id=project.pk, expected_draft_version=2, actor=owner)
    assert audit.status == "CONVERTED"
    assert audit.legacy_exceptions_json["nonparticipating_passes"]
    project.refresh_from_db()
    assert project.draft_schema_version == "physical-draft-v2"
    assert not MemberJointIncidence.objects.filter(project=project, node__client_key="geometry:legacy-visual").exists()


@pytest.mark.django_db
def test_stale_v1_tab_cannot_overwrite_converted_project(context):
    from modeling.services import DraftSaveError, save_physical_draft
    from modeling.node_joint_migration import convert_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    old = valid_payload(material, section, version=1)
    assert convert_project(project_id=project.pk, expected_draft_version=1, actor=owner).status == "CONVERTED"
    with pytest.raises(DraftSaveError, match="UNSUPPORTED_DRAFT_SCHEMA"):
        save_physical_draft(actor=owner, project=project, payload=old)
    project.refresh_from_db()
    assert project.draft_version == 2


@pytest.mark.django_db
def test_equivalence_mismatch_rolls_back_conversion(context, monkeypatch):
    from modeling.models import Connection, DraftMigrationAudit
    from modeling.node_joint_migration import EquivalenceReport, convert_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    monkeypatch.setattr("modeling.node_joint_migration.compare_legacy_v2", lambda **_kwargs: EquivalenceReport(False, ("FORCED_NUMERIC_MISMATCH",)))
    audit = convert_project(project_id=project.pk, expected_draft_version=1, actor=owner)
    project.refresh_from_db()
    assert audit.status == "BLOCKED"
    assert "EQUIVALENCE_MISMATCH" in audit.reason_code
    assert project.draft_schema_version == "physical-draft-v1"
    assert project.draft_version == 1
    assert Connection.objects.filter(project=project).count() == 2
    assert DraftMigrationAudit.objects.filter(project=project, status="CONVERTED").count() == 0


@pytest.mark.django_db
def test_rollback_refuses_after_v2_edits(context):
    from modeling.node_joint_migration import MigrationBlocked, convert_project, restore_v1_from_audit
    from modeling.services import save_physical_draft
    from projects.workspace import _draft

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    assert convert_project(project_id=project.pk, expected_draft_version=1, actor=owner).status == "CONVERTED"
    project.refresh_from_db()
    draft = _draft(project)
    save_physical_draft(actor=owner, project=project, payload={**draft, "expected_draft_version": 2})
    with pytest.raises(MigrationBlocked, match="NEWER_DRAFT_REQUIRES_OWNER_DISPOSITION"):
        restore_v1_from_audit(project_id=project.pk, expected_draft_version=3, actor=owner)
    project.refresh_from_db()
    assert project.draft_schema_version == "physical-draft-v2"
    assert project.draft_version == 3
