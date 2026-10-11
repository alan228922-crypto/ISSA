"""Bounded UX recovery: visible controls, real checks and unchanged modeling state."""
import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.application.test_analysis_acceptance import save_bt01_draft

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]
TAB_NAMES = ("结论", "预测对比", "为什么", "技术数据")


@pytest.fixture
def analyzed_bridge(context, workspace_page):
    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="analyze"]').click()
    with page.expect_response('**/analyze/') as response:
        page.locator('#workspace-analyze').click()
    assert response.value.json()['ok'] is True
    expect(page.locator('[data-ux-current-stage]')).to_have_text('当前：理解')
    return page


def assert_result_tabs_visible(page):
    for name in TAB_NAMES:
        expect(page.get_by_role('tab', name=name, exact=True)).to_be_visible()


def test_bridge_result_initial_conclusion_is_available(analyzed_bridge):
    """RED-1 regression: Analyze must open the conclusions before evidence."""
    assert_result_tabs_visible(analyzed_bridge)
    expect(analyzed_bridge.get_by_role('tab', name='结论', exact=True)).to_have_attribute('aria-selected', 'true')


@pytest.mark.parametrize('name', TAB_NAMES[1:])
def test_bridge_result_switch_never_hides_any_tab(analyzed_bridge, name):
    """RED-2: panel CSS must not match and hide its conclusion trigger."""
    page = analyzed_bridge
    page.get_by_role('tab', name=name, exact=True).click()
    assert_result_tabs_visible(page)
    expect(page.get_by_role('tab', name=name, exact=True)).to_have_attribute('aria-selected', 'true')
    panel = {'预测对比': '[data-result-comparison]', '为什么': '[data-result-explanation]', '技术数据': '#workspace-engineering-details'}[name]
    expect(page.locator(panel)).to_be_visible()


def test_bridge_result_returns_from_technical_to_conclusion(analyzed_bridge):
    """RED-3: the mouse must be able to return, not just programmatic key handlers."""
    page = analyzed_bridge
    page.get_by_role('tab', name='技术数据', exact=True).click()
    expect(page.get_by_role('tab', name='结论', exact=True)).to_be_visible()
    page.get_by_role('tab', name='结论', exact=True).click()
    expect(page.locator('section[data-result-conclusion]')).to_be_visible()
    for selector in ('[data-result-comparison]', '[data-result-explanation]', '#workspace-engineering-details'):
        expect(page.locator(selector)).to_be_hidden()


def test_bridge_result_stage_reentry_defaults_to_conclusion(analyzed_bridge):
    """RED-4: returning to Understanding must not strand the student on evidence."""
    page = analyzed_bridge
    page.get_by_role('tab', name='为什么', exact=True).click()
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-ux-stage-target="understanding"]').click()
    expect(page.get_by_role('tab', name='结论', exact=True)).to_have_attribute('aria-selected', 'true')
    assert_result_tabs_visible(page)
    expect(page.locator('section[data-result-conclusion]')).to_be_visible()


def test_bridge_result_keyboard_navigation_stays_available(analyzed_bridge):
    """Protect existing arrow, Home and End navigation and selected tab focus."""
    page = analyzed_bridge
    page.get_by_role('tab', name='结论', exact=True).focus()
    for key, name in [('ArrowRight', '预测对比'), ('End', '技术数据'), ('Home', '结论'), ('ArrowLeft', '技术数据')]:
        page.keyboard.press(key)
        expect(page.get_by_role('tab', name=name, exact=True)).to_have_attribute('aria-selected', 'true')
        assert_result_tabs_visible(page)
