"""Known legacy connection checks retain safe, specific recovery guidance."""
import pytest
from playwright.sync_api import expect

from modeling.services import save_physical_draft
from tests.application.test_physical_draft import context, valid_payload
from tests.browser.test_model_check_recovery import assert_navigation_only, read_draft

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


@pytest.mark.parametrize('untrusted_message', [False, True])
def test_public_off_member_check_has_safe_specific_recovery(context, workspace_page, untrusted_message):
    """Break: a known geometry issue falls back to generic copy or trusts raw text."""
    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload['nodes'].append(dict(client_key='private-off-node', x_mm=500, y_mm=1, label=''))
    payload['connections'].append(dict(client_key='private-off-connection',
        geometry_node_client_key='private-off-node', participating_member_client_keys=['m1']))
    save_physical_draft(actor=owner, project=project, payload=payload)
    page = workspace_page(user=owner, project=project)
    before = read_draft(project)
    if untrusted_message:
        def inject_untrusted_message(route):
            response = route.fetch()
            body = response.json()
            body['issues'][0]['human_message'] = 'RAW_SERVER_MESSAGE client key DB ID schema raw payload internal reference'
            body['issues'][0]['entity_refs'] = ['PRIVATE_INTERNAL_REFERENCE']
            route.fulfill(response=response, json=body)
        page.route('**/model/check/', inject_untrusted_message)
    page.locator('[data-ux-stage-target="check"]').click()
    with page.expect_response('**/model/check/') as checked:
        page.locator('#workspace-model-check').click()
    result = checked.value.json()
    assert result['ok'] is False
    assert [issue['code'] for issue in result['issues']] == ['CONNECTION_OFF_MEMBER']
    card = page.locator('#workspace-check-issues .ux-check-issue')
    expect(card).to_have_count(1)
    expect(card).to_contain_text('连接点偏离构件')
    expect(card).to_contain_text('连接点不位于指定杆件上')
    expect(card).to_contain_text('请检查连接点位置和参与杆件')
    visible = card.inner_text()
    for private in ['CONNECTION_OFF_MEMBER', 'private-off-', 'm1', 'RAW_SERVER_MESSAGE',
                    'client key', 'DB ID', 'schema', 'raw payload', 'internal reference',
                    'PRIVATE_INTERNAL_REFERENCE', '技术信息']:
        assert private not in visible
    card.get_by_role('button', name='回建模检查连接', exact=True).click()
    expect(page.locator('[data-workspace-tool="SELECT"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('[data-check-recovery-guidance]')).to_contain_text('请检查连接点位置和参与杆件')
    assert_navigation_only(page, project, before)
