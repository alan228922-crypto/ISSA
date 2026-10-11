"""Bounded UX recovery: visible controls, real checks and unchanged modeling state."""
import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.application.test_analysis_acceptance import save_bt01_draft
from tests.browser.test_cad_core_drawing import open_core, move_world

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


def test_bridge_blank_guidance_consistently_starts_with_member(context, workspace_page):
    """RED-5/7: neither the shell nor property rerender may demand a first Node."""
    page, _ = open_core(context, workspace_page)
    for selector in ('[data-ux-next-task]', '[data-ux-panel-guidance]', '[data-ux-empty-state]'):
        assert '构件' in page.locator(selector).inner_text()
    properties = page.locator('#workspace-properties-panel').inner_text()
    assert '构件' in properties
    assert '第一个节点' not in properties
    assert '先放置' not in properties


def test_bridge_primary_cta_really_draws_member_from_blank_space(context, workspace_page):
    """RED-6: correct wording alone cannot hide activation of the wrong tool."""
    page, _ = open_core(context, workspace_page)
    page.locator('[data-ux-start-modeling]').click()
    expect(page.locator('[data-workspace-tool="MEMBER"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('[data-workspace-tool="NODE"]')).to_have_attribute('aria-pressed', 'false')
    move_world(page, 200, -100, click=True)
    move_world(page, 400, -100, click=True)
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)
    expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(2)


def test_bridge_independent_node_does_not_require_a_second_node(context, workspace_page):
    """Protect the alternate entry: existing standalone nodes are optional endpoints."""
    page, _ = open_core(context, workspace_page, [('standalone', 0, 0)])
    assert '构件' in page.locator('[data-ux-next-task]').inner_text()
    assert '第二个节点' not in page.locator('[data-ux-next-task]').inner_text()
    page.locator('[data-draft-object-key="standalone"]').click()
    assert '继续放置节点' not in page.locator('#workspace-properties-panel').inner_text()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 0, 0, click=True)
    move_world(page, 100, 0, click=True)
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)


def test_bridge_node_tool_retains_explicit_joint_explanation(context, workspace_page):
    """RED-8: primary Member guidance must not erase the explicit-joint exception."""
    page, _ = open_core(context, workspace_page)
    page.locator('[data-workspace-tool="NODE"]').click()
    instruction = page.locator('[data-modeling-instruction]').inner_text()
    assert '节点' in instruction and '交叉' in instruction
    assert '不会自动连接' in instruction
    move_world(page, 200, -100, click=True)
    expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(1)
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(0)


def test_bridge_empty_catalog_discloses_drawing_prerequisite(context, workspace_page):
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project
    owner, original, _, _ = context
    student = User.objects.create_user('empty-catalog-student')
    EventMembership.objects.create(user=student, event=original.event, membership_type=EventMembership.Type.PARTICIPANT)
    project = Project.objects.create(event=original.event, owner_user=student, name='First project')
    page = workspace_page(user=student, project=project)
    expect(page.locator('[data-ux-empty-state]')).to_contain_text('绘制前')
    expect(page.locator('[data-ux-empty-state]')).to_contain_text('材料与截面')
    page.locator('[data-ux-start-modeling]').click()
    expect(page.locator('[data-workspace-tool="MEMBER"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('[data-member-prerequisite]')).to_be_visible()
    expect(page.get_by_role('link', name='管理材料与截面', exact=True)).to_be_visible()
