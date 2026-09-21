import pytest
from django.test import Client

from tests.endpoints.test_event_landing import add_membership, make_event


@pytest.fixture
def entry_page(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    resources = {}

    def open_events(*, user):
        client = Client()
        client.force_login(user)
        if not resources:
            runtime = playwright.sync_playwright().start()
            try:
                browser = runtime.chromium.launch()
            except Exception as exc:
                runtime.stop()
                pytest.skip(f"Playwright Chromium unavailable: {exc}")
            resources.update(runtime=runtime, browser=browser, context=browser.new_context())
            resources["page"] = resources["context"].new_page()
        resources["context"].add_cookies(
            [{"name": "sessionid", "value": client.session.session_key, "url": live_server.url}]
        )
        resources["page"].goto(live_server.url + "/events/")
        return resources["page"]

    yield open_events
    if resources:
        resources["context"].close()
        resources["browser"].close()
        resources["runtime"].stop()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_participant_navigates_from_events_to_authorized_workspace(entry_page):
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project

    participant = User.objects.create_user("browser-entry-owner")
    event = make_event(name="浏览器赛事", code="BROWSER-ENTRY")
    add_membership(user=participant, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    Project.objects.create(event=event, owner_user=participant, name="浏览器桁架")

    page = entry_page(user=participant)

    assert page.get_by_text("浏览器赛事").is_visible()
    assert page.get_by_text("浏览器桁架").is_visible()
    page.get_by_role("link", name="进入工作区").click()
    assert page.locator("#workspace-bootstrap").count() == 1


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_participant_without_project_sees_meaningful_empty_state(entry_page):
    from accounts.models import User
    from competitions.models import EventMembership

    participant = User.objects.create_user("browser-entry-empty")
    event = make_event(name="空浏览器赛事", code="BROWSER-EMPTY")
    add_membership(user=participant, event=event, membership_type=EventMembership.Type.PARTICIPANT)

    page = entry_page(user=participant)

    assert page.get_by_text("空浏览器赛事").is_visible()
    assert page.get_by_text("目前没有可进入的项目。").is_visible()
    assert page.get_by_role("link", name="进入工作区").count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_participant_configures_empty_project_and_saves_first_member(entry_page):
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project

    participant = User.objects.create_user("blank-journey-owner")
    event = make_event(name="空白建模赛事", code="BLANK-JOURNEY")
    add_membership(user=participant, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    Project.objects.create(event=event, owner_user=participant, name="空白桁架")
    page = entry_page(user=participant)

    assert page.get_by_text("当前账号：blank-journey-owner").is_visible()
    page.get_by_role("link", name="进入工作区").click()
    assert page.get_by_text("可编辑（项目所有者）").is_visible()
    page.get_by_role("link", name="管理材料与截面").click()
    page.get_by_role("link", name="新建材料").click()
    page.get_by_label("材料名称").fill("旅程竹材")
    page.get_by_label("弹性模量 E（MPa）").fill("2000")
    page.get_by_label("密度（g/mm³）").fill("0.0007")
    page.get_by_label("数据来源").fill("MEASURED")
    page.get_by_role("button", name="保存材料").click()
    page.get_by_role("link", name="新建矩形截面").click()
    page.get_by_label("截面名称").fill("1×6 mm")
    page.get_by_label("宽度（mm）").fill("1")
    page.get_by_label("高度（mm）").fill("6")
    page.get_by_label("密度（g/mm³）").fill("0.0007")
    page.get_by_role("button", name="保存截面").click()
    page.get_by_role("link", name="返回 空白桁架 工作区").click()

    canvas = page.locator("#workspace-canvas")
    box = canvas.bounding_box()
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas.click(position={"x": box["width"] * 0.35, "y": box["height"] * 0.5})
    canvas.click(position={"x": box["width"] * 0.65, "y": box["height"] * 0.5})
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"]').click()
    page.locator('[data-client-key="node-2"]').click()
    page.get_by_role("button", name="保存", exact=True).click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    assert page.locator('[data-client-key="member-1"]').count() == 1
