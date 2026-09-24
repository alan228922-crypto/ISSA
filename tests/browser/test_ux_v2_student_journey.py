import pytest

from tests.endpoints.test_event_landing import add_membership, make_event


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
