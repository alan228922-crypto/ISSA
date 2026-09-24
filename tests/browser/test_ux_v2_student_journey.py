import pytest

from tests.endpoints.test_event_landing import add_membership, make_event
from tests.application.test_physical_draft import context


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_new_student_sees_purpose_stage_and_can_place_first_node(live_server):
    """Break caught: a newcomer lands in a tool dashboard without a starting action."""
    playwright = pytest.importorskip("playwright.sync_api")
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project

    student = User.objects.create_user("ux-v2-first-student", password="StudyPass123!")
    event = make_event(name="新生结构赛", code="UX-V2-ENTRY")
    add_membership(user=student, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    Project.objects.create(event=event, owner_user=student, name="我的第一座桥")
    runtime = playwright.sync_playwright().start()
    browser = runtime.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    try:
        page.goto(live_server.url + "/accounts/login/")
        assert page.get_by_text("建立结构 → 预测 → 分析 → 理解 → 总结").is_visible()
        page.locator('input[name="username"]').fill(student.username)
        page.locator('input[name="password"]').fill("StudyPass123!")
        page.get_by_role("button", name="登录").click()
        assert page.get_by_text("从第一个节点开始").is_visible()
        page.get_by_role("link", name="进入工作区").click()
        assert page.locator("[data-ux-stage-nav]").get_by_role("button", name="建模").is_visible()
        assert page.get_by_text("下一步：放置第一个节点").is_visible()
        page.get_by_role("button", name="开始建模").click()
        assert page.locator('[data-workspace-tool="NODE"]').get_attribute("aria-pressed") == "true"
        canvas = page.locator("#workspace-canvas")
        canvas.click(position={"x": 200, "y": 200})
        assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
        assert page.get_by_text("下一步：添加第二个节点，再用构件连接").is_visible()
        page.set_viewport_size({"width": 1024, "height": 768})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("#workspace-canvas").bounding_box()["width"] > 500
    finally:
        browser.close()
        runtime.stop()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_build_guidance_context_save_and_check(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    assert page.locator(".ux-precision").get_attribute("open") is None
    tools = page.locator("[data-workspace-tool]")
    assert tools.count() == 6
    assert all(button.locator("[data-tool-icon]").count() == 1 for button in tools.all())
    page.locator('[data-workspace-tool="NODE"]').click()
    assert page.get_by_text("在画布点一下放置节点").is_visible()
    page.locator("#workspace-canvas").click(position={"x": 200, "y": 200})
    assert page.get_by_text("已放置节点").is_visible()
    assert page.locator("[data-ux-save-indicator]").inner_text() == "有未保存修改"
    page.locator('[data-client-key="node-1"]').click()
    page.set_viewport_size({"width": 1024, "height": 768})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.get_by_text("这是什么").is_visible()
    assert page.get_by_text("可以做什么").is_visible()
    assert page.get_by_text("下一步", exact=True).is_visible()
    page.keyboard.press("Escape")
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute("aria-pressed") == "true"
    page.locator("#workspace-save").click()
    page.wait_for_function("document.querySelector('[data-ux-save-indicator]').textContent === '已保存'")
    page.locator('[data-ux-stage-target="check"]').click()
    assert page.locator("#workspace-canvas").is_visible()
    assert page.get_by_role("button", name="检查模型").is_visible()
    page.locator("#workspace-model-check").click()
    page.wait_for_function("document.querySelector('#workspace-check-issues').textContent.trim().length > 0")
    assert page.locator("#workspace-check-issues").inner_text().strip()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_save_failure_is_visible_and_retry_preserves_draft(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator("#workspace-canvas").click(position={"x": 240, "y": 210})
    assert page.locator("[data-ux-save-indicator]").inner_text() == "有未保存修改"
    page.route("**/model/save/", lambda route: route.abort())
    page.locator("#workspace-save").click()
    page.wait_for_function("document.querySelector('[data-ux-save-indicator]').textContent === '保存失败'")
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
    page.unroute("**/model/save/")
    page.locator("#workspace-save").click()
    page.wait_for_function("document.querySelector('[data-ux-save-indicator]').textContent === '已保存'")
    page.reload()
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
