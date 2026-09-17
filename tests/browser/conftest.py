import pytest
from django.test import Client
from django.urls import reverse


def pytest_configure(config):
    config.addinivalue_line("markers", "browser: requires Playwright Chromium")
    requested = tuple(map(str, config.invocation_params.args))
    if config.option.markexpr == "not browser" and any(path.startswith("tests/browser") for path in requested):
        config.option.markexpr = "browser"


@pytest.fixture
def workspace_page(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        try:
            browser = runtime.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Playwright Chromium unavailable: {exc}")
        context = browser.new_context()
        page = context.new_page()

        def open_workspace(*, user, project):
            client = Client()
            client.force_login(user)
            session_key = client.session.session_key
            context.add_cookies([{"name": "sessionid", "value": session_key, "url": live_server.url}])
            page.goto(live_server.url + reverse("projects:workspace", kwargs={"project_id": project.id}))
            return page

        yield open_workspace
        context.close()
        browser.close()
