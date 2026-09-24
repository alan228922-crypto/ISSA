import pytest
from django.urls import reverse

from tests.application.test_physical_draft import context


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_rectangle_preview_updates_without_saving(context, live_server, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.goto(live_server.url + reverse("materials:section_create", kwargs={"project_id": project.id}))
    page.get_by_label("截面名称").fill("预览矩形")
    page.get_by_label("宽度（mm）").fill("2")
    page.get_by_label("高度（mm）").fill("6")
    page.get_by_label("密度（g/mm³）").fill("0.0007")
    page.wait_for_function("document.querySelector('[data-section-properties]')?.textContent.includes('36')")
    assert page.locator("[data-section-preview-svg] rect").count() == 1
    assert "2 mm" in page.locator("[data-section-preview-svg]").text_content()
    assert "6 mm" in page.locator("[data-section-preview-svg]").text_content()
    assert "12" in page.locator("[data-section-properties]").text_content()
    assert "4" in page.locator("[data-section-properties]").text_content()
    page.get_by_label("宽度（mm）").fill("0")
    assert page.locator("[data-section-properties]").text_content().strip() == ""
    assert page.url.endswith(reverse("materials:section_create", kwargs={"project_id": project.id}))


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_composite_presets_preview_and_free_section_is_selectable(context, live_server, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.goto(live_server.url + reverse("materials:composite_section_create", kwargs={"project_id": project.id}))
    for preset, count in (("h", 3), ("t", 2), ("box", 4)):
        page.locator(f'[data-section-preset="{preset}"]').click()
        page.wait_for_timeout(700)
        assert "已更新" in page.locator("[data-section-preview-status]").text_content(), (preset, page.locator("[data-section-preview-status]").text_content())
        assert page.locator("[data-section-preview-svg] rect").count() == count
    page.get_by_label("截面名称").fill("自由双条截面")
    page.locator('[data-section-preset="t"]').click()
    rows = page.locator("[data-component-row]")
    rows.nth(0).get_by_label("宽度（mm）").fill("20")
    rows.nth(0).get_by_label("高度（mm）").fill("4")
    rows.nth(0).get_by_label("中心 Y（mm）").fill("4")
    rows.nth(1).get_by_label("宽度（mm）").fill("4")
    rows.nth(1).get_by_label("高度（mm）").fill("4")
    rows.nth(1).get_by_label("中心 Y（mm）").fill("0")
    page.wait_for_function("document.querySelector('[data-section-preview-status]').textContent.includes('已更新')")
    page.get_by_role("button", name="保存截面").click()
    assert page.get_by_text("自由双条截面").is_visible()
    page.get_by_role("link", name="编辑").last.click()
    assert page.locator("[data-component-row]").count() == 2
    assert page.locator("[data-component-row]").nth(0).get_by_label("宽度（mm）").input_value() == "20.0"
    page.locator("[data-component-row]").nth(0).get_by_label("宽度（mm）").fill("22")
    page.get_by_role("button", name="保存截面").click()
    page.get_by_role("link", name=f"返回 {project.name} 工作区").click()
    option = page.locator("[data-member-section]").locator("option", has_text="自由双条截面")
    assert option.count() == 1
    page.locator("[data-member-section]").select_option(option.get_attribute("value"))
    page.locator('[data-workspace-tool="NODE"]').click()
    command = page.locator("[data-cad-command-input]")
    for coordinates in ("100,100", "400,100"):
        command.fill(coordinates)
        command.press("Enter")
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"]').click(force=True)
    page.locator('[data-client-key="node-2"]').click(force=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
    page.locator("#workspace-save").click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
    page.locator('[data-client-key="member-1"] line').click(force=True)
    assert "自由双条截面" in page.locator("[data-property-section]").text_content()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_composite_overlap_preview_and_save_do_not_persist(context, live_server, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.goto(live_server.url + reverse("materials:composite_section_create", kwargs={"project_id": project.id}))
    page.get_by_label("截面名称").fill("无效重叠截面")
    page.locator('[data-section-preset="t"]').click()
    page.wait_for_function("document.querySelector('[data-section-preview-status]').textContent.includes('已更新')")
    page.locator("[data-component-row]").nth(1).get_by_label("中心 Y（mm）").fill("40")
    page.wait_for_function("document.querySelector('[data-section-preview-status]').textContent.includes('重叠')")
    assert page.locator("[data-section-properties]").text_content().strip() == ""
    page.get_by_role("button", name="保存截面").click()
    assert page.get_by_role("alert").is_visible()
    assert "重叠" in page.get_by_role("alert").text_content() or "重叠" in page.locator("main").text_content()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_composite_rows_can_be_added_removed_and_fit_desktop_width(context, live_server, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.goto(live_server.url + reverse("materials:composite_section_create", kwargs={"project_id": project.id}))
    page.get_by_role("button", name="新增矩形组件").click()
    assert page.locator("[data-component-row]:visible").count() == 2
    page.locator("[data-component-row]").first.get_by_role("button", name="移除组件").click()
    assert page.locator("[data-component-row]:visible").count() == 1
    row = page.locator("[data-component-row]:visible")
    for label, value in (("宽度（mm）", "2"), ("高度（mm）", "6"), ("中心 X（mm）", "0"), ("中心 Y（mm）", "0"), ("旋转角度（°）", "0"), ("密度（g/mm³）", "0.0007")):
        row.get_by_label(label).fill(value)
    page.wait_for_function("document.querySelector('[data-section-preview-status]').textContent.includes('已更新')")
    for width in (1024, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), width
    page.get_by_label("截面名称").fill("删列后截面")
    page.get_by_role("button", name="保存截面").click()
    assert page.get_by_text("删列后截面").is_visible()
