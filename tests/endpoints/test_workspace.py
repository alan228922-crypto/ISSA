import json
import re

import pytest
from django.urls import reverse

from modeling.services import save_physical_draft
from tests.application.test_physical_draft import context, valid_payload


def _bootstrap(response):
    match = re.search(
        rb'<script id="workspace-bootstrap" type="application/json">(.*?)</script>',
        response.content,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


@pytest.mark.django_db
def test_owner_gets_bootstrap_and_manager_gets_read_only(context, client):
    from accounts.models import User
    from competitions.models import EventMembership

    owner, project, material, section = context
    save_physical_draft(
        actor=owner,
        project=project,
        payload=valid_payload(material, section),
    )
    workspace_url = reverse("projects:workspace", kwargs={"project_id": project.id})

    client.force_login(owner)
    owner_response = client.get(workspace_url)

    assert owner_response.status_code == 200
    assert any(template.name == "projects/workspace.html" for template in owner_response.templates)
    owner_html = owner_response.content.decode()
    assert '<a href="/events/" class="product-home">赛事与项目</a>' in owner_html
    assert '<form method="post" action="/accounts/logout/"' in owner_html
    owner_bootstrap = _bootstrap(owner_response)
    assert owner_bootstrap["schema_version"] == "workspace-bootstrap-v1"
    assert owner_bootstrap["project"] == {
        "id": project.id,
        "name": project.name,
        "analysis_type": "TRUSS_2D",
    }
    assert owner_bootstrap["draft"]["schema_version"] == "physical-draft-v1"
    assert owner_bootstrap["draft"]["version"] == 1
    assert owner_bootstrap["draft"]["nodes"] == [
        {"client_key": "n1", "x_mm": 0.0, "y_mm": 0.0, "label": "左"},
        {"client_key": "n2", "x_mm": 1000.0, "y_mm": 0.0, "label": "右"},
    ]
    assert owner_bootstrap["read_only"] is False
    assert owner_bootstrap["access"] == {
        "current_user": {"id": owner.id, "username": owner.username, "role": "USER"},
        "owner": {"id": owner.id, "username": owner.username},
        "event": {"id": project.event.id, "name": project.event.name},
        "editable": True,
        "read_only_reason": "",
    }
    assert owner_bootstrap["materials"] == [{
        "id": material.id,
        "name": material.name,
        "E_MPa": float(material.E_MPa),
        "density_g_per_mm3": float(material.density_g_per_mm3),
    }]
    assert owner_bootstrap["sections"] == [{
        "id": section.id,
        "name": section.name,
        "section_type": "RECTANGLE",
        "A_mm2": section.properties_json["A_mm2"],
        "Ix_mm4": section.properties_json["Ix_mm4"],
        "Iy_mm4": section.properties_json["Iy_mm4"],
    }]
    assert set(owner_bootstrap["urls"]) == {
        "save",
        "check",
        "prediction_current",
        "prediction_create",
            "prediction_complete_template",
            "analyze",
            "analysis_runs",
            "result_template",
            "report_template",
            "reasoning_template",
            "comparison_template",
        "explanation_template",
        "reflection_template",
        "reflection_complete_template",
        "materials",
    }
    assert owner_bootstrap["urls"] == {
        "save": f"/projects/{project.id}/model/save/", "check": f"/projects/{project.id}/model/check/",
            "prediction_current": f"/projects/{project.id}/predictions/current/", "prediction_create": f"/projects/{project.id}/predictions/",
            "prediction_complete_template": f"/projects/{project.id}/predictions/{{prediction_id}}/complete/", "analyze": f"/projects/{project.id}/analyze/",
            "analysis_runs": f"/projects/{project.id}/analyses/", "result_template": f"/projects/{project.id}/analyses/{{run_id}}/data/", "report_template": f"/projects/{project.id}/analyses/{{run_id}}/report/", "reasoning_template": f"/projects/{project.id}/analyses/{{run_id}}/reasoning/", "comparison_template": f"/projects/{project.id}/analyses/{{run_id}}/comparison/",
        "explanation_template": f"/projects/{project.id}/analyses/{{run_id}}/explanation/", "reflection_template": f"/projects/{project.id}/analyses/{{run_id}}/reflection/",
        "reflection_complete_template": f"/projects/{project.id}/analyses/{{run_id}}/reflection/complete/",
        "materials": f"/projects/{project.id}/materials/",
    }
    assert owner_bootstrap["draft"]["physical_members"] == [{"client_key": "m1", "start_node_client_key": "n1", "end_node_client_key": "n2", "material_id": material.id, "section_id": section.id, "label": "杆件", "is_active": True}]
    assert owner_bootstrap["draft"]["connections"] == [{"client_key": "c1", "geometry_node_client_key": "n1", "participating_member_client_keys": ["m1"]}]
    assert owner_bootstrap["draft"]["supports"] == [{"client_key": "s1", "target_connection_client_key": "c1", "support_type": "PINNED", "restrained_axis": None}]
    assert owner_bootstrap["draft"]["node_loads"] == [{"client_key": "l1", "target_connection_client_key": "c1", "fx_N": 0.0, "fy_N": -100.0, "label": "荷载"}]

    manager = User.objects.create_user("workspace-manager", role=User.Role.MANAGER)
    EventMembership.objects.create(
        user=manager,
        event=project.event,
        membership_type=EventMembership.Type.MANAGER,
    )
    client.force_login(manager)
    manager_response = client.get(workspace_url)

    assert manager_response.status_code == 200
    manager_bootstrap = _bootstrap(manager_response)
    assert manager_bootstrap["read_only"] is True
    assert manager_bootstrap["access"]["editable"] is False
    assert manager_bootstrap["access"]["read_only_reason"] == "你正在以只读身份查看此项目。"

    developer = User.objects.create_user("workspace-developer", role=User.Role.DEVELOPER)
    client.force_login(developer)
    developer_response = client.get(workspace_url)

    assert developer_response.status_code == 200
    assert _bootstrap(developer_response)["read_only"] is True

    project.analysis_type = "FRAME_2D"
    project.save(update_fields=["analysis_type"])
    client.force_login(owner)
    assert client.get(workspace_url).status_code == 404
