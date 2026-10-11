"""One continuous public-control journey; fixture supplies only a blank project/catalog."""
from pathlib import Path
import os
import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.browser.test_cad_core_drawing import open_core, move_world
from tests.browser.test_cad_core_journey import member, save_reload
from tests.browser.test_modeling_ux_bridge import assert_result_tabs_visible

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def check(page):
    page.locator('[data-ux-stage-target="check"]').click()
    with page.expect_response('**/model/check/') as response:
        page.locator('#workspace-model-check').click()
    return response.value.json()


def test_bridge_new_project_drawing_recovery_to_all_result_tabs(context, workspace_page):
    page, _ = open_core(context, workspace_page)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.locator('[data-ux-start-modeling]').click()
    expect(page.locator('[data-workspace-tool="MEMBER"]')).to_have_attribute('aria-pressed', 'true')
    move_world(page, 200, -100, click=True)
    move_world(page, 600, -100, click=True)
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)
    saved = save_reload(page)
    assert len(saved['nodes']) == 2 and len(saved['physical_members']) == 1
    assert 'NO_SUPPORT' in {i['code'] for i in check(page)['issues']}
    page.get_by_role('button', name='回建模添加支座', exact=True).click()
    expect(page.locator('[data-workspace-tool="SUPPORT"]')).to_have_attribute('aria-pressed', 'true')
    move_world(page, 200, -100, click=True)
    page.locator('[data-support-choice="ROLLER_Y"]').click()
    move_world(page, 600, -100, click=True)
    member(page, (200, -100), (400, 0))
    member(page, (400, 0), (600, -100))
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(3)
    page.locator('[data-workspace-tool="LOAD"]').click()
    move_world(page, 400, 0, click=True)
    expect(page.locator('[data-object-kind="NodeLoad"]')).to_have_count(1)
    page.locator('[data-property-fy]').fill('-20')
    page.locator('[data-property-fy]').press('Tab')
    complete = save_reload(page)
    assert check(page)['ok'] is True

    # Deliberately incomplete through existing public property controls, not injected state.
    page.locator('[data-ux-stage-target="build"]').click()
    load_key = complete['node_loads'][0]['client_key']
    first = complete['physical_members'][0]
    page.locator(f'[data-draft-object-key="{load_key}"]').click()
    page.locator('[data-property-load-target]').select_option('')
    page.locator(f'[data-draft-object-key="{first["client_key"]}"]').click()
    page.locator('[data-property-end-node]').select_option('')
    save_reload(page)
    page.locator('[data-ux-stage-target="analyze"]').click()
    with page.expect_response('**/analyze/') as blocked:
        page.locator('#workspace-analyze').click()
    assert blocked.value.json()['error']['code'] == 'INCOMPLETE_DRAFT'
    assert check(page)['ok'] is False
    expect(page.locator('[data-incomplete-check-card]')).to_have_count(2)
    page.locator('[data-incomplete-check-card]').filter(has_text='缺少：终点').get_by_role('button', name='重新指定').click()
    expect(page.locator('[data-property-end-node]')).to_be_focused()
    page.locator('[data-property-end-node]').select_option(first['end_node_client_key'])
    page.locator('[data-ux-stage-target="check"]').click()
    page.locator('[data-incomplete-check-card]').filter(has_text='荷载尚未指定作用节点').get_by_role('button', name='重新指定').click()
    expect(page.locator('[data-property-load-target]')).to_be_focused()
    page.locator('[data-property-load-target]').select_option(complete['node_loads'][0]['target_node_client_key'])
    save_reload(page)
    assert check(page)['ok'] is True
    page.locator('[data-ux-stage-target="analyze"]').click()
    with page.expect_response('**/analyze/') as analyzed:
        page.locator('#workspace-analyze').click()
    assert analyzed.value.json()['ok'] is True
    expect(page.locator('[data-ux-current-stage]')).to_have_text('当前：理解')
    expect(page.get_by_role('tab', name='结论', exact=True)).to_have_attribute('aria-selected', 'true')
    for name in ('预测对比', '为什么', '技术数据', '结论'):
        page.get_by_role('tab', name=name, exact=True).click()
        assert_result_tabs_visible(page)
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-ux-stage-target="understanding"]').click()
    expect(page.get_by_role('tab', name='结论', exact=True)).to_have_attribute('aria-selected', 'true')
    assert_result_tabs_visible(page)
    assert not errors, errors
    output = Path(os.environ.get('BRIDGE_SCREENSHOTS', str(Path('/private/tmp') / 'bridge-result-evidence')))
    output.mkdir(parents=True, exist_ok=True)
    for width in (1024, 1280, 1440):
        page.set_viewport_size({'width': width, 'height': 900})
        for name in ('预测对比', '为什么', '技术数据', '结论'):
            page.get_by_role('tab', name=name, exact=True).click()
            assert_result_tabs_visible(page)
        for name in ('结论', '预测对比', '为什么', '技术数据'):
            expect(page.get_by_role('tab', name=name, exact=True)).to_be_in_viewport()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(output / f'bridge-{width}-results.png'))


@pytest.mark.parametrize('width', [1024, 1280, 1440])
def test_bridge_responsive_visible_controls_and_recovery(context, workspace_page, width, tmp_path):
    page, _ = open_core(context, workspace_page)
    page.set_viewport_size({'width': width, 'height': 900})
    output = Path(os.environ.get('BRIDGE_SCREENSHOTS', str(tmp_path)))
    output.mkdir(parents=True, exist_ok=True)
    expect(page.locator('[data-ux-start-modeling]')).to_be_in_viewport()
    assert '构件' in page.locator('[data-ux-next-task]').inner_text()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(output / f'bridge-{width}-build.png'))
    page.locator('[data-ux-start-modeling]').click()
    move_world(page, 200, -100, click=True)
    move_world(page, 400, -100, click=True)
    save_reload(page)
    check(page)
    recovery = page.get_by_role('button', name='回建模添加支座', exact=True)
    expect(recovery).to_be_in_viewport()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(output / f'bridge-{width}-check.png'))
    recovery.click()
    expect(page.locator('[data-check-recovery-guidance]')).to_be_visible()
