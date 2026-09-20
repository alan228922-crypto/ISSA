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
