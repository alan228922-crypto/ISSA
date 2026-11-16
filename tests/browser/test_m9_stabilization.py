"""M9 保存提示必须与真实提交结果一致，不改变所选分析的所有权。"""

import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.browser.test_m9_public_teaching_loop import public_page, draw_triangle, analyze
from tests.browser.test_m9_reflection_handoff import db_read

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def test_submitted_reflection_save_is_not_reported_as_unwritten_after_run_switch(public_page, tmp_path):
    """旧保存已落库、回包尚未显示时，切换提示不能声称它未写入。"""
    from learning.models import Reflection

    page, _, project = public_page
    draw_triangle(page)
    first = analyze(page)
    second = analyze(page)
    assert first != second
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(first))
    page.locator('[data-ux-summary-target="reflection"]').click()
    page.get_by_role('button', name='开始反思', exact=True).click()
    root = page.locator('#workspace-reflection')
    root.locator('[name="original_reasoning"]').fill('A：先观察荷载和支座。')

    held = []
    target = f'**/analyses/{first}/reflection/'
    page.route(target, lambda route: held.append(route) if route.request.method == 'POST' else route.continue_())
    with page.expect_request(lambda request: request.method == 'POST' and request.url.endswith(f'/analyses/{first}/reflection/')):
        root.get_by_role('button', name='保存草稿', exact=True).click()
    page.locator('#workspace-run-select').select_option(str(second))
    expect(root.get_by_role('button', name='开始反思', exact=True)).to_be_visible()
    expect(root).to_contain_text('不会带入')
    expect(root).not_to_contain_text('保存成功')
    page.screenshot(path=str(tmp_path / 'r3-save-pending-on-b.png'))

    # 只延迟真实 POST 的浏览器回包；服务器仍执行完整保存与授权流程。
    response = held[0].fetch()
    assert response.status == 201
    assert db_read(lambda: Reflection.objects.get(analysis_run_id=first).original_reasoning) == 'A：先观察荷载和支座。'
    with page.expect_response(lambda reply: reply.request.method == 'POST' and reply.url.endswith(f'/analyses/{first}/reflection/')):
        held[0].fulfill(response=response)
    expect(page.locator('#workspace-run-select')).to_have_value(str(second))
    page.screenshot(path=str(tmp_path / 'r3-save-persisted-on-a-viewing-b.png'))
    expect(root).not_to_contain_text('未写入')
    expect(root).to_contain_text('确认')

    root.get_by_role('button', name='开始反思', exact=True).click()
    root.locator('[name="original_reasoning"]').fill('B：这是本次选择的本地内容。')
    assert db_read(lambda: Reflection.objects.filter(analysis_run_id=second).count()) == 0
    page.locator('#workspace-run-select').select_option(str(first))
    expect(root.locator('[name="original_reasoning"]')).to_have_value('A：先观察荷载和支座。')
    assert db_read(lambda: Reflection.objects.get(analysis_run_id=first).analysis_run.project_id) == project.pk
