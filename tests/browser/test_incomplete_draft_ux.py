from pathlib import Path

import pytest

from modeling.services import save_physical_draft
from tests.application.test_physical_draft import context, valid_payload


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_incomplete_inventory_rebinds_without_recreating_objects(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft["connections"][0]["geometry_node_client_key"] = None
    draft["connections"][0]["participating_member_client_keys"] = [None]
    draft["connections"].append({"client_key": "c2", "geometry_node_client_key": "n2", "participating_member_client_keys": ["m1"]})
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)

    entry = page.locator("[data-incomplete-inventory] summary")
    assert "未完成物件 3" in entry.inner_text()
    assert page.locator('[data-client-key="c1"][data-object-kind="Connection"]').count() == 0
    assert page.locator('[data-client-key="c2"][data-object-kind="Connection"]').count() == 1
    entry.click()
    connection = page.locator('[data-incomplete-object-kind="CONNECTION"][data-incomplete-object-key="c1"]')
    assert "连接" in connection.inner_text()
    assert "位置节点" in connection.inner_text()
    assert "参与构件" in connection.inner_text()
    assert "c1" not in connection.inner_text()
    connection.get_by_role("button", name="重新指定").click()
    page.locator("[data-property-connection-node]").select_option("n1")
    page.locator("[data-property-participant]").select_option("m1")
    assert "未完成物件 0" in entry.inner_text()
    assert page.locator('[data-client-key="c1"][data-object-kind="Connection"]').count() == 1
    assert "尚未完整" not in page.locator('[data-draft-object-key="c1"]').inner_text()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_inventory_rebinds_member_support_and_load_through_existing_controls(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft["physical_members"][0].update(start_node_client_key=None, material_id=None, section_id=None)
    draft["connections"][0].update(geometry_node_client_key=None, participating_member_client_keys=[None])
    draft["supports"][0]["target_connection_client_key"] = None
    draft["node_loads"][0]["target_connection_client_key"] = None
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    assert "未完成物件 4" in page.locator("[data-incomplete-inventory] summary").inner_text()
    page.locator("[data-incomplete-inventory] summary").click()
    page.locator('[data-incomplete-object-key="m1"] button').filter(has_text="重新指定").click()
    page.locator("[data-property-start-node]").select_option("n1")
    page.locator("[data-property-material]").select_option(str(material.id))
    page.locator("[data-property-section]").select_option(str(section.id))
    page.locator('[data-incomplete-object-key="c1"] button').filter(has_text="重新指定").click()
    page.locator("[data-property-connection-node]").select_option("n1")
    page.locator("[data-property-participant]").select_option("m1")
    page.locator('[data-incomplete-object-key="s1"] button').filter(has_text="重新指定").click()
    page.locator("[data-property-support-target]").select_option("c1")
    page.locator('[data-incomplete-object-key="l1"] button').filter(has_text="重新指定").click()
    page.locator("[data-property-load-target]").select_option("c1")
    assert "未完成物件 0" in page.locator("[data-incomplete-inventory] summary").inner_text()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_deleting_node_immediately_lists_all_dependent_incomplete_objects(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator('[data-draft-object-kind="GEOMETRY_NODE"][data-draft-object-key="n1"]').click()
    page.keyboard.press("Delete")
    assert "未完成物件 4" in page.locator("[data-incomplete-inventory] summary").inner_text()
    page.locator("[data-incomplete-inventory] summary").click()
    assert page.locator("[data-incomplete-object-kind]").count() == 4


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_anchored_partial_geometry_is_not_described_as_invisible(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft["physical_members"][0]["material_id"] = None
    draft["connections"][0]["participating_member_client_keys"] = [None]
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    assert page.locator('[data-client-key="m1"][data-object-kind="PhysicalMember"]').count() == 1
    assert page.locator('[data-client-key="c1"][data-object-kind="Connection"]').count() == 1
    page.locator("[data-incomplete-inventory] summary").click()
    assert "有真实位置的部分仍可能显示" in page.locator("[data-incomplete-inventory]").inner_text()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_incomplete_inventory_multi_delete_is_independent_and_persists(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft["connections"][0]["geometry_node_client_key"] = None
    draft["connections"][0]["participating_member_client_keys"] = [None]
    draft["connections"].append({"client_key": "c2", "geometry_node_client_key": "n2", "participating_member_client_keys": ["m1"]})
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator("[data-incomplete-inventory] summary").click()
    page.locator('[data-incomplete-object-key="c1"] input[type="checkbox"]').check()
    page.locator('[data-incomplete-object-key="s1"] input[type="checkbox"]').check()
    page.get_by_role("button", name="删除所选未完成物件").click()
    assert "未完成物件 1" in page.locator("[data-incomplete-inventory] summary").inner_text()
    assert page.locator('[data-draft-object-key="c2"]').count() == 1
    assert page.locator('[data-incomplete-object-key="l1"]').count() == 1
    page.locator('[data-incomplete-object-key="l1"] button[data-incomplete-delete]').click()
    assert "未完成物件 0" in page.locator("[data-incomplete-inventory] summary").inner_text()
    page.locator("#workspace-save").click()
    page.get_by_text("未保存修改：无").wait_for()
    page.reload()
    assert "未完成物件 0" in page.locator("[data-incomplete-inventory] summary").inner_text()
    page.locator('[data-ux-stage-target="check"]').click()
    page.locator("#workspace-model-check").click()
    page.wait_for_function("document.querySelector('#workspace-check-issues').textContent.trim().length > 0")
    assert page.locator("[data-incomplete-check-card]").count() == 0
    assert "未完成物件" not in page.locator("#workspace-check-issues").inner_text()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_delete_then_redraw_keeps_old_incomplete_connection_visible_until_explicit_delete(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft["supports"] = []
    draft["node_loads"] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator('[data-client-key="m1"] line').click(force=True)
    page.keyboard.press("Delete")
    assert "未完成物件 1" in page.locator("[data-incomplete-inventory] summary").inner_text()
    page.locator("#workspace-save").click()
    page.get_by_text("未保存修改：无").wait_for()
    page.reload()
    assert "未完成物件 1" in page.locator("[data-incomplete-inventory] summary").inner_text()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    page.locator('[data-client-key="n2"] circle').click(force=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
    assert "未完成物件 1" in page.locator("[data-incomplete-inventory] summary").inner_text()
    page.locator("[data-incomplete-inventory] summary").click()
    page.locator('[data-incomplete-object-key="c1"] [data-incomplete-delete]').click()
    assert "未完成物件 0" in page.locator("[data-incomplete-inventory] summary").inner_text()
    page.locator("#workspace-save").click()
    page.get_by_text("未保存修改：无").wait_for()
    page.locator('[data-ux-stage-target="check"]').click()
    page.locator("#workspace-model-check").click()
    page.wait_for_function("document.querySelector('#workspace-check-issues').textContent.trim().length > 0")
    assert page.locator("[data-incomplete-check-card]").count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_model_check_groups_audit_case_by_six_incomplete_objects(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft["nodes"].extend({"client_key": f"n{i}", "x_mm": (i - 2) * 150, "y_mm": 0, "label": ""} for i in range(3, 8))
    draft["connections"] = [
        {"client_key": f"connection-{i}", "geometry_node_client_key": None, "participating_member_client_keys": [None]}
        for i in range(1, 6)
    ] + [
        {"client_key": f"connection-{i}", "geometry_node_client_key": f"n{i - 3}", "participating_member_client_keys": ["m1"]}
        for i in range(6, 11)
    ]
    draft["supports"] = [{"client_key": "support-2", "target_connection_client_key": "connection-2", "support_type": "PINNED", "restrained_axis": None}]
    draft["node_loads"] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    captures = Path(__file__).resolve().parents[2] / ".superpowers/sdd/2026-09-29-incomplete-draft-ux/screenshots"
    captures.mkdir(parents=True, exist_ok=True)
    page.set_viewport_size({"width": 1440, "height": 900})
    assert "未完成物件 6" in page.locator("[data-incomplete-inventory] summary").inner_text()
    assert page.locator('[data-client-key="connection-1"][data-object-kind="Connection"]').count() == 0
    assert page.locator('[data-client-key="connection-6"][data-object-kind="Connection"]').count() == 1
    page.screenshot(path=str(captures / "audit-build.png"))
    page.locator("[data-incomplete-inventory] summary").click()
    page.screenshot(path=str(captures / "audit-inventory.png"))
    page.locator('[data-ux-stage-target="check"]').click()
    page.locator("#workspace-model-check").click()
    cards = page.locator("[data-incomplete-check-card]")
    cards.first.wait_for()
    assert cards.count() == 6
    assert "发现 6 个未完成物件" in page.locator("#workspace-check-issues").inner_text()
    assert "5 个连接" in page.locator("#workspace-check-issues").inner_text()
    assert "1 个支座" in page.locator("#workspace-check-issues").inner_text()
    first = cards.first.inner_text()
    assert "位置节点" in first and "参与构件" in first
    assert "connection-1" not in first
    assert "连接 1" in first
    assert "连接 5" in cards.nth(4).inner_text()
    page.screenshot(path=str(captures / "audit-check.png"))
    page.locator('[data-ux-stage-target="analyze"]').click()
    with page.expect_response(lambda response: response.url.endswith("/analyze/")) as response_info:
        page.locator("#workspace-analyze").click()
    assert response_info.value.status == 422
    page.get_by_text("模型暂时无法完成分析。请检查连接、支座和荷载，也可以返回建模。").wait_for()
