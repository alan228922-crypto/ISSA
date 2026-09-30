import pytest

from tests.application.test_physical_draft import context


@pytest.mark.django_db
def test_new_project_defaults_to_node_joint_v2_and_legacy_marker_stays_explicit(context):
    from projects.models import Project
    from projects.workspace import _draft

    owner, legacy, _, _ = context
    assert legacy.draft_schema_version == "physical-draft-v1"
    fresh = Project.objects.create(event=legacy.event, owner_user=owner, name="新桁架")
    assert fresh.draft_schema_version == "physical-draft-v2"
    assert _draft(fresh) == {"schema_version": "physical-draft-v2", "version": 0, "nodes": [], "physical_members": [], "member_joint_incidences": [], "supports": [], "node_loads": []}


def test_sparse_2000_nodes_1000_members_avoids_all_pairs(monkeypatch):
    from modeling import topology

    nodes = {}
    members = []
    for index in range(1000):
        x = index * 1000.0
        nodes[f"a{index}"] = (x, 0.0)
        nodes[f"b{index}"] = (x + 100.0, 0.0)
        members.append({"client_key": f"m{index}", "start_node_client_key": f"a{index}", "end_node_client_key": f"b{index}"})
    checks = 0
    original = topology._parameter

    def measured(*args):
        nonlocal checks
        checks += 1
        return original(*args)

    monkeypatch.setattr(topology, "_parameter", measured)
    assert topology.find_unrepresented_passes(nodes=nodes, members=members, incidences=set(), exemptions=set()) == []
    assert checks < 100_000


@pytest.mark.django_db
def test_blocked_legacy_workspace_is_read_only_and_exports_exact_source(context, client):
    from modeling.models import DraftMigrationAudit
    from projects.workspace import _draft

    owner, legacy, _, _ = context
    payload = _draft(legacy)
    DraftMigrationAudit.objects.create(
        project=legacy, status="BLOCKED", source_draft_version=0, source_hash="a" * 64,
        source_payload_json=payload, reason_code="AMBIGUOUS_CONNECTION_PARTICIPATION",
    )
    client.force_login(owner)
    workspace = client.get(f"/projects/{legacy.pk}/workspace/")
    assert workspace.status_code == 200
    assert workspace.context["bootstrap"]["read_only"] is True
    assert b"data-legacy-draft-export" in workspace.content
    response = client.get(f"/projects/{legacy.pk}/model/legacy-export/")
    assert response.status_code == 200
    assert response.json()["source_payload"] == payload
    assert response.json()["reason_code"] == "AMBIGUOUS_CONNECTION_PARTICIPATION"
