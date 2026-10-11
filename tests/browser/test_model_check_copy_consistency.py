"""Grouped missing fields and their student explanation must describe the same member."""
from pathlib import Path
import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.browser.test_model_check_recovery import open_check, read_draft, assert_navigation_only

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]
EVIDENCE = Path('/private/tmp/isaa-copy-consistency-evidence')


def missing_endpoints(*fields):
    def change(draft):
        for field in fields:
            draft['physical_members'][0][field] = None
    return change


@pytest.mark.parametrize('fields,codes,summary,detail,absent', [
    (['start_node_client_key'], ['MISSING_MEMBER_START_NODE'], '缺少：起点', '构件尚未指定起点', '终点'),
    (['end_node_client_key'], ['MISSING_MEMBER_END_NODE'], '缺少：终点', '构件尚未指定终点', '起点'),
    (['start_node_client_key', 'end_node_client_key'], ['MISSING_MEMBER_START_NODE', 'MISSING_MEMBER_END_NODE'],
     '缺少：起点、终点', '尚未指定起点和终点', None),
])
def test_copy_matches_actual_endpoint_combination(context, workspace_page, fields, codes, summary, detail, absent):
    """Break caught: a complete grouped summary paired with only the first issue's meaning."""
    page, _, result = open_check(context, workspace_page, missing_endpoints(*fields))
    actual = [issue['code'] for issue in result['issues'] if issue.get('physical_object') == {'kind': 'PHYSICAL_MEMBER', 'client_key': 'base'}]
    assert actual == codes
    card = page.locator('[data-incomplete-check-card]').filter(has_text='构件 底杆')
    expect(card).to_have_count(1)
    expect(card.locator('p').nth(0)).to_have_text(summary)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(EVIDENCE / f'member-{len(fields)}-{fields[0]}.png'), full_page=True)
    explanation = card.locator('p').nth(1)
    print('ACTUAL_ISSUE_CODES', actual, 'STUDENT_CARD', card.inner_text())
    expect(explanation).to_contain_text(detail)
    if absent:
        expect(explanation).not_to_contain_text(absent)
    else:
        expect(explanation).to_contain_text('重新指定两个端点')
        expect(explanation).not_to_contain_text('构件缺少起点。')
    for internal in codes + ['base', 'physical-draft', 'incidence']:
        expect(card).not_to_contain_text(internal)


def test_copy_both_endpoint_recovery_keeps_focus_inventory_and_save_recheck(context, workspace_page):
    """RED-4 regression: copy composition must not alter the original recovery target/action."""
    page, project, _ = open_check(context, workspace_page, missing_endpoints('start_node_client_key', 'end_node_client_key'))
    before = read_draft(project)
    page.locator('[data-incomplete-check-card]').filter(has_text='构件 底杆').get_by_role('button', name='重新指定').click()
    expect(page.locator('[data-incomplete-inventory]')).to_have_attribute('open', '')
    expect(page.locator('[data-property-start-node]')).to_be_focused()
    expect(page.locator('[data-property-identity]')).to_contain_text('底杆')
    assert_navigation_only(page, project, before)
    page.locator('[data-property-start-node]').select_option('a')
    page.locator('[data-property-end-node]').select_option('b')
    with page.expect_response('**/model/save/'):
        page.locator('#workspace-save').click()
    expect(page.locator('[data-ux-save-indicator]')).to_have_text('已保存')
    page.locator('[data-ux-stage-target="check"]').click()
    with page.expect_response('**/model/check/') as response:
        page.locator('#workspace-model-check').click()
    assert response.value.json()['ok'] is True
    expect(page.locator('#workspace-check-issues')).to_contain_text('模型检查通过')


def test_copy_member_multiple_fields_not_only_first_material_issue(context, workspace_page):
    """Preserve material/section recovery while preventing the same first-only copy defect."""
    def change(draft):
        draft['physical_members'][0].update(material_id=None, section_id=None)
    page, _, _ = open_check(context, workspace_page, change)
    card = page.locator('[data-incomplete-check-card]').filter(has_text='构件 底杆')
    expect(card.locator('p').nth(0)).to_have_text('缺少：材料、截面')
    expect(card.locator('p').nth(1)).to_contain_text('材料、截面')
    card.get_by_role('button', name='重新指定').click()
    expect(page.locator('[data-property-material]')).to_be_focused()
