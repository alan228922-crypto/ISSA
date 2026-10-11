"""Existing Model Check codes become navigation, never a second validator."""
import pytest
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import expect

from modeling.services import save_physical_draft
from projects.models import Project
from projects.workspace import _draft
from tests.application.test_physical_draft import context

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def triangle(material, section):
    return {
        'schema_version': 'physical-draft-v2', 'expected_draft_version': 0,
        'nodes': [{'client_key': k, 'x_mm': x, 'y_mm': y, 'label': label}
                  for k, x, y, label in [('a', 0, 0, '左'), ('b', 1000, 0, '右'), ('c', 500, 500, '顶')]],
        'physical_members': [{'client_key': k, 'start_node_client_key': a, 'end_node_client_key': b,
            'material_id': material.pk, 'section_id': section.pk, 'label': label, 'is_active': True}
            for k, a, b, label in [('base', 'a', 'b', '底杆'), ('left', 'a', 'c', '左杆'), ('right', 'b', 'c', '右杆')]],
        'member_joint_incidences': [],
        'supports': [
            {'client_key': 'pin', 'target_node_client_key': 'a', 'support_type': 'PINNED', 'restrained_axis': None},
            {'client_key': 'roller', 'target_node_client_key': 'b', 'support_type': 'ROLLER', 'restrained_axis': 'Y'}],
        'node_loads': [{'client_key': 'load', 'target_node_client_key': 'c', 'fx_N': 0, 'fy_N': -20, 'label': '顶荷载'}],
    }


def open_check(context, workspace_page, change=lambda draft: None):
    owner, original, material, section = context
    project = Project.objects.create(event=original.event, owner_user=owner, name='Recovery')
    draft = triangle(material, section)
    change(draft)
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="check"]').click()
    with page.expect_response('**/check/') as response:
        page.locator('#workspace-model-check').click()
    return page, project, response.value.json()


def assert_navigation_only(page, project, before):
    expect(page.locator('[data-ux-current-stage]')).to_have_text('当前：建模')
    expect(page.locator('[data-ux-save-indicator]')).to_have_text('已保存')
    expect(page.locator('[data-cad-undo]')).to_be_disabled()
    assert read_draft(project) == before


def read_draft(project):
    def read():
        project.refresh_from_db()
        return _draft(project)
    with ThreadPoolExecutor() as pool:
        return pool.submit(read).result()


def test_recovery_no_support_returns_to_support_tool_without_edit(context, workspace_page):
    page, project, result = open_check(context, workspace_page, lambda d: d.update(supports=[]))
    assert 'NO_SUPPORT' in {i['code'] for i in result['issues']}
    before = read_draft(project)
    expect(page.locator('#workspace-check-issues')).to_contain_text('缺少支座')
    page.get_by_role('button', name='回建模添加支座', exact=True).click()
    expect(page.locator('[data-workspace-tool="SUPPORT"]')).to_have_attribute('aria-pressed', 'true')
    assert_navigation_only(page, project, before)


@pytest.mark.parametrize('singular', [False, True])
def test_recovery_restraint_and_singular_have_distinct_cautious_guidance(context, workspace_page, singular):
    def change(draft):
        if singular:
            draft['nodes'][2]['y_mm'] = 0
            draft['physical_members'] = draft['physical_members'][1:]
        else:
            draft['supports'] = draft['supports'][:1]
    page, project, result = open_check(context, workspace_page, change)
    code = 'SINGULAR_GLOBAL_STIFFNESS' if singular else 'INSUFFICIENT_RESTRAINT'
    assert code in {i['code'] for i in result['issues']}
    before = read_draft(project)
    expect(page.locator('#workspace-check-issues')).to_contain_text('结构可能不稳定' if singular else '支座约束不足')
    if singular:
        expect(page.locator('#workspace-check-issues')).to_contain_text('可能')
    page.get_by_role('button', name='回建模检查支座与连接' if singular else '回建模检查支座', exact=True).click()
    expect(page.locator('[data-workspace-tool="SELECT"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('[data-check-recovery-guidance]')).to_contain_text('支座')
    assert_navigation_only(page, project, before)


@pytest.mark.parametrize('field,selector,word', [
    ('start_node_client_key', '[data-property-start-node]', '起点'),
    ('end_node_client_key', '[data-property-end-node]', '终点'),
    ('target_node_client_key', '[data-property-load-target]', '作用节点'),
])
def test_recovery_incomplete_object_focuses_actual_missing_field(context, workspace_page, field, selector, word):
    def change(draft):
        record = draft['node_loads'][0] if field == 'target_node_client_key' else draft['physical_members'][0]
        record[field] = None
    page, project, result = open_check(context, workspace_page, change)
    assert result['ok'] is False
    before = read_draft(project)
    card = page.locator('[data-incomplete-check-card]').filter(has_text='顶荷载' if field == 'target_node_client_key' else '底杆')
    expect(card).to_contain_text('荷载尚未指定作用节点' if field == 'target_node_client_key' else f'缺少：{word}')
    card.get_by_role('button', name='重新指定', exact=True).click()
    expect(page.locator('[data-incomplete-inventory]')).to_have_attribute('open', '')
    expect(page.locator(selector)).to_be_focused()
    expect(page.locator(selector)).to_be_in_viewport()
    assert_navigation_only(page, project, before)
    page.locator(selector).select_option('c' if field == 'target_node_client_key' else 'a' if field.startswith('start') else 'b')
    with page.expect_response('**/model/save/'):
        page.locator('#workspace-save').click()
    expect(page.locator('[data-ux-save-indicator]')).to_have_text('已保存')
    page.locator('[data-ux-stage-target="check"]').click()
    with page.expect_response('**/check/') as checked:
        page.locator('#workspace-model-check').click()
    assert checked.value.json()['ok'] is True
    expect(page.locator('#workspace-check-issues')).to_contain_text('模型检查通过')


@pytest.mark.parametrize('code', ['FUTURE_INTERNAL_CODE', 'constructor', '__proto__'])
def test_recovery_unknown_code_has_generic_fallback_not_internal_code(context, workspace_page, code):
    page, _, _ = open_check(context, workspace_page)
    page.route('**/check/', lambda route: route.fulfill(json={'ok': False, 'issues': [{'code': code, 'severity': 'ERROR', 'physical_object': {'kind': 'PHYSICAL_MEMBER', 'client_key': 'base'}}]}))
    with page.expect_response('**/check/'):
        page.locator('#workspace-model-check').click()
    expect(page.locator('#workspace-check-issues')).to_contain_text('发现一个需要检查的地方')
    expect(page.locator('#workspace-check-issues')).not_to_contain_text(code)
    expect(page.locator('[data-incomplete-check-card]')).to_have_count(0)


def test_recovery_legacy_missing_participant_focuses_missing_slot(context, workspace_page):
    from tests.application.test_physical_draft import valid_payload
    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload['connections'][0]['participating_member_client_keys'] = ['m1', None]
    save_physical_draft(actor=owner, project=project, payload=payload)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="check"]').click()
    with page.expect_response('**/model/check/'):
        page.locator('#workspace-model-check').click()
    page.locator('[data-incomplete-check-card]').get_by_role('button', name='重新指定').click()
    expect(page.locator('[data-property-participant="1"]')).to_be_focused()


def test_recovery_stable_unjoined_crossing_is_not_an_error(context, workspace_page):
    def change(draft):
        draft['nodes'] = [{'client_key': k, 'x_mm': x, 'y_mm': y, 'label': ''} for k, x, y in
                          [('a', 0, 0), ('b', 1000, 0), ('c', 1000, 1000), ('d', 0, 1000)]]
        member = draft['physical_members'][0]
        draft['physical_members'] = [{**member, 'client_key': f'm{i}', 'start_node_client_key': a, 'end_node_client_key': b}
                                    for i, (a, b) in enumerate([('a','b'), ('b','c'), ('c','d'), ('d','a'), ('a','c'), ('b','d')])]
    page, project, result = open_check(context, workspace_page, change)
    assert result['ok'] is True and result['issues'] == []
    expect(page.locator('#workspace-check-issues')).to_contain_text('模型检查通过')
    saved = read_draft(project)
    assert len(saved['nodes']) == 4
    assert saved['member_joint_incidences'] == []
