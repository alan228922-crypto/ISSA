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
    resources = {}

    def open_workspace(*, user, project):
        client = Client()
        client.force_login(user)
        session_key = client.session.session_key
        if not resources:
            runtime = playwright.sync_playwright().start()
            try:
                browser = runtime.chromium.launch()
            except Exception as exc:
                runtime.stop()
                pytest.skip(f"Playwright Chromium unavailable: {exc}")
            resources.update(
                runtime=runtime,
                browser=browser,
                context=browser.new_context(),
            )
            resources["page"] = resources["context"].new_page()
        resources["context"].add_cookies([{"name": "sessionid", "value": session_key, "url": live_server.url}])
        resources["page"].goto(live_server.url + reverse("projects:workspace", kwargs={"project_id": project.id}))
        return resources["page"]

    yield open_workspace
    if resources:
        resources["context"].close()
        resources["browser"].close()
        resources["runtime"].stop()
