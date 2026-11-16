"""Snapshot isolation through public controls, and lifecycle read/write boundaries."""
import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.browser.test_m9_public_teaching_loop import public_page, draw_triangle, predict, analyze, reflect
from tests.browser.test_m9_reflection_handoff import active_m9_run, m9_run, db_read, open_evidence
from tests.browser.test_cad_core_journey import save_reload

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def test_historical_run_a_survives_b_and_changed_draft(public_page):
    from learning.models import Reflection
    page, _, project = public_page
    draft = draw_triangle(page)
    predict(page)
    first = analyze(page)
    base = page.url.split('/projects/')[0] + f'/projects/{project.pk}'
    paths = ('data', 'comparison', 'explanation', 'report')
    frozen = {name: page.context.request.get(f'{base}/analyses/{first}/{name}/').json() for name in paths}
    reflect(page, 'A：先观察原来模型的位移位置。')
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-workspace-tool="SELECT"]').click()
    page.locator('[data-client-key="member-1"]').focus()
    page.keyboard.press('Enter')
    page.locator('[data-property-label]').fill('当前版本新描述')
    page.locator('[data-property-label]').press('Tab')
    load = draft['node_loads'][0]['client_key']
    page.locator(f'[data-draft-object-key="{load}"]').click()
    page.locator('[data-property-fy]').fill('-40')
    page.locator('[data-property-fy]').press('Tab')
    save_reload(page)
    page.get_by_role('link', name='管理材料与截面', exact=True).click()
    page.get_by_role('table').filter(has=page.get_by_role('columnheader', name='弹性模量 E / MPa', exact=True)).get_by_role('link', name='编辑', exact=True).click()
    page.get_by_label('弹性模量 E（MPa）').fill('3000')
    page.get_by_role('button', name='保存材料', exact=True).click()
    page.get_by_role('link', name=f'返回 {project.name} 工作区', exact=True).click()
    predict(page)
    second = analyze(page)
    assert second != first
    reflect(page, 'B：我改变荷载和材料后再观察。')
    page.locator('#workspace-run-select').select_option(str(first))
    expect(page.locator('#workspace-reflection [name="next_iteration_intent"]')).to_have_value('A：先观察原来模型的位移位置。')
    page.locator('[data-ux-stage-target="understanding"]').click()
    expect(page.locator('[data-result-context]')).to_contain_text('较早的模型版本')
    expect(page.locator('[data-result-conclusion]')).not_to_contain_text('当前版本新描述')
    page.get_by_role('tab', name='为什么', exact=True).click()
    expect(page.locator('[data-result-explanation]')).not_to_contain_text('当前版本新描述')
    expect(page.locator('[data-object-kind="PhysicalMember"][data-result-state]:not([data-result-state=""])')).to_have_count(0)
    for name in paths:
        current = page.context.request.get(f'{base}/analyses/{first}/{name}/').json()
        if name == 'report':
            # Current-draft provenance is deliberately live; snapshot/numerical
            # sections must not change when that staleness warning changes.
            for section, value in frozen[name]['report'].items():
                if section != 'provenance':
                    assert current['report'][section] == value, section
            provenance = current['report']['provenance']
            assert provenance['is_stale'] is True
            for key, value in frozen[name]['report']['provenance'].items():
                if key not in ('is_stale', 'current_draft_version'):
                    assert provenance[key] == value, key
        else:
            assert current == frozen[name], name
    assert db_read(lambda: Reflection.objects.get(analysis_run_id=second).next_iteration_intent) == 'B：我改变荷载和材料后再观察。'


def test_grace_is_history_only(active_m9_run, workspace_page):
    owner, project, run = active_m9_run
    project.event.status = 'FINISHED_GRACE'
    project.event.save()
    page = open_evidence(workspace_page, owner, project, run)
    expect(page.locator('[data-teaching-level="1"]')).to_be_visible()
    page.get_by_role('button', name='进入反思', exact=True).click()
    expect(page.locator('#workspace-reflection button')).to_have_count(0)
    base = page.url.split('/projects/')[0] + f'/projects/{project.pk}'
    for name in ('data', 'comparison', 'explanation', 'report'):
        assert page.context.request.get(f'{base}/analyses/{run.pk}/{name}/').status == 200
    csrf = next(c['value'] for c in page.context.cookies() if c['name'] == 'csrftoken')
    for path in ('model/save/', 'model/check/', 'analyze/', f'analyses/{run.pk}/reflection/'):
        payload = {'original_reasoning': 'No write'} if path.endswith('/reflection/') else {'expected_draft_version': 1}
        response = page.context.request.post(f'{base}/{path}', data=payload, headers={'X-CSRFToken': csrf})
        assert response.status == 403, (path, response.status)


def test_purged_residual_run_access_fails_closed(active_m9_run, workspace_page):
    owner, project, run = active_m9_run
    page = open_evidence(workspace_page, owner, project, run)
    from competitions.models import CompetitionEvent
    db_read(lambda: CompetitionEvent.objects.filter(pk=project.event_id).update(status='PURGED'))
    base = page.url.split('/projects/')[0] + f'/projects/{project.pk}'
    for path in ('workspace/', 'analyses/', *(f'analyses/{run.pk}/{name}/' for name in ('data', 'comparison', 'explanation', 'report', 'reflection'))):
        assert page.context.request.get(f'{base}/{path}').status in (403, 404), path
    csrf = next(c['value'] for c in page.context.cookies() if c['name'] == 'csrftoken')
    for path in ('model/save/', 'model/check/', 'analyze/', f'analyses/{run.pk}/reflection/'):
        payload = {'original_reasoning': 'No write'} if path.endswith('/reflection/') else {'expected_draft_version': 1}
        response = page.context.request.post(f'{base}/{path}', data=payload, headers={'X-CSRFToken': csrf})
        assert response.status == 403, (path, response.status)
    response = page.goto(f'{base}/workspace/')
    assert response.status in (403, 404)
