"""Real login and public controls: no injected state, transport or result fixture."""
import secrets
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.application.test_physical_draft import context
from tests.browser.test_cad_core_drawing import move_world
from tests.browser.test_cad_core_journey import member, save_reload
from tests.browser.test_bridge_public_journey import check
from tests.browser.test_m9_reflection_handoff import db_read

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]
EVIDENCE = Path('.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots')


@pytest.fixture
def public_page(context, live_server):
    owner, project, material, section = context
    password = secrets.token_urlsafe(24)
    owner.set_password(password)
    owner.save()
    # This is an active teaching journey, not the event-expiry permission test.
    # Keep its fixture window valid when the calendar passes the original date.
    from datetime import timedelta
    from django.utils import timezone
    project.event.starts_at = timezone.now() - timedelta(days=1)
    project.event.ends_at = timezone.now() + timedelta(days=1)
    project.event.status = 'ACTIVE'
    project.event.save()
    project.draft_schema_version = 'physical-draft-v2'
    project.save()
    assert project.analysis_runs.count() == 0
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        browser_context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = browser_context.new_page()
        page.goto(live_server.url + '/accounts/login/')
        page.locator('input[name="username"]').fill(owner.username)
        page.locator('input[name="password"]').fill(password)
        page.get_by_role('button', name='登录', exact=True).click()
        page.get_by_role('link', name='继续建模', exact=True).click()
        expect(page.get_by_text('可编辑（项目所有者）')).to_be_visible()
        page.locator('[data-member-material]').select_option(str(material.pk))
        page.locator('[data-member-section]').select_option(str(section.pk))
        yield page, owner, project
        browser.close()


def draw_triangle(page):
    # Use the existing public toggle: floating numeric fields can overlap a
    # pointer endpoint, so this pointer-only journey does not enable them.
    page.locator('[data-cad-dynamic-input]').click()
    member(page, (200, -100), (600, -100))
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)
    member(page, (200, -100), (400, 0))
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(2)
    member(page, (400, 0), (600, -100))
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(3)
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    move_world(page, 200, -100, click=True)
    page.locator('[data-support-choice="ROLLER_Y"]').click()
    move_world(page, 600, -100, click=True)
    page.locator('[data-workspace-tool="LOAD"]').click()
    move_world(page, 400, 0, click=True)
    page.locator('[data-property-fy]').fill('-20')
    page.locator('[data-property-fy]').press('Tab')
    saved = save_reload(page)
    assert saved['schema_version'] == 'physical-draft-v2'
    assert len(saved['physical_members']) == 3 and len(saved['supports']) == 2
    assert check(page)['ok'] is True
    return saved


def predict(page):
    page.locator('[data-ux-stage-target="prediction"]').click()
    page.get_by_role('button', name='开始预测', exact=True).click()
    expect(page.locator('[data-prediction-status]')).to_contain_text('草稿')
    for row in page.locator('[data-prediction-members] p').all():
        row.get_by_role('button', name='受拉', exact=True).click()
    page.locator('[data-client-key="node-3"]').focus()
    page.keyboard.press('Enter')
    page.get_by_role('button', name='用当前画布选择设置最大位移位置', exact=True).click()
    for key in ('node-1', 'member-1', 'node-2'):
        page.locator(f'[data-client-key="{key}"]').focus()
        page.keyboard.press('Enter')
        page.get_by_role('button', name='将当前画布选择加入路径', exact=True).click()
    with page.expect_response('**/complete/') as response:
        page.get_by_role('button', name='完成预测', exact=True).click()
    assert response.value.status == 200
    expect(page.locator('[data-prediction-status]')).to_contain_text('已完成')


def analyze(page):
    page.locator('[data-ux-stage-target="analyze"]').click()
    with page.expect_response('**/analyze/') as response:
        page.locator('#workspace-analyze').click()
    body = response.value.json()
    assert response.value.status == 200 and body['status'] == 'SUCCESS'
    expect(page.locator('[data-result-conclusion]')).to_be_visible()
    return body['analysis_run_id']


def reflect(page, text):
    page.get_by_role('tab', name='为什么', exact=True).click()
    writes = []
    page.on('request', lambda request: writes.append(request.url) if request.method == 'POST' else None)
    page.get_by_role('button', name='进入反思', exact=True).click()
    page.get_by_role('button', name='开始反思', exact=True).click()
    assert writes == []
    root = page.locator('#workspace-reflection')
    root.locator('[name="original_reasoning"]').fill('我先从荷载和支座判断三角形受力。')
    with page.expect_response('**/reflection/') as partial:
        root.get_by_role('button', name='保存草稿', exact=True).click()
    assert partial.value.status == 201
    root.locator('[name="unexpected_results"]').fill('斜杆与我的受拉预测不同，我想对照轴力依据。')
    root.locator('[name="next_iteration_intent"]').fill(text)
    with page.expect_response('**/reflection/') as saved:
        root.get_by_role('button', name='保存草稿', exact=True).click()
    assert saved.value.status == 200
    with page.expect_response('**/reflection/complete/') as completed:
        root.get_by_role('button', name='完成反思', exact=True).click()
    assert completed.value.status == 200
    expect(root.locator('textarea:not(:disabled)')).to_have_count(0)


def test_public_v2_prediction_to_self_authored_reflection(public_page):
    from analysis.models import AnalysisRun
    from learning.models import Reflection

    page, owner, project = public_page
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    draw_triangle(page)
    predict(page)
    run_id = analyze(page)
    run = db_read(lambda: AnalysisRun.objects.get(pk=run_id))
    assert run.status == 'SUCCESS' and run.prediction_id is not None
    assert db_read(lambda: run.prediction.status) == 'COMPLETED'
    base = page.url.split('/projects/')[0] + f'/projects/{project.pk}/analyses/{run_id}'
    comparison = page.context.request.get(base + '/comparison/').json()['comparison']
    explanation = page.context.request.get(base + '/explanation/').json()['explanation']
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for width in (1024, 1280, 1440):
        page.set_viewport_size({'width': width, 'height': 900})
        for name in ('结论', '预测对比', '为什么'):
            page.get_by_role('tab', name=name, exact=True).click()
            expect(page.get_by_role('tab', name='技术数据', exact=True)).to_be_visible()
            page.screenshot(path=str(EVIDENCE / f'm9-{width}-{name}.png'))
    page.get_by_role('tab', name='预测对比', exact=True).click()
    expect(page.locator('[data-comparison-evidence-member]')).to_have_count(3)
    expect(page.locator('[data-result-comparison]')).to_contain_text('构件 M1：和预测一致')
    expect(page.locator('[data-result-comparison]')).to_contain_text('构件 M2：和预测不同')
    maximum = comparison['maximum_displacement']
    expect(page.locator('[data-maximum-candidate]')).to_have_count(len(maximum['candidate_analysis_node_ids']))
    expect(page.locator('[data-result-comparison]')).to_contain_text('学生传力假设')
    page.get_by_role('tab', name='为什么', exact=True).click()
    for level in ('1', '2'):
        expect(page.locator(f'[data-teaching-level="{level}"]')).to_be_visible()
    expect(page.locator('[data-teaching-level="3"]')).not_to_be_visible()
    page.get_by_text('查看具体数值与来源', exact=True).click()
    expect(page.locator('[data-teaching-level="3"]')).to_be_visible()
    for block in explanation['blocks']:
        for segment in block.get('facts', {}).get('segments', []):
            expect(page.locator('[data-teaching-level="3"]')).to_contain_text(f"{segment['axial_force_N']} N")
    page.screenshot(path=str(EVIDENCE / 'm9-level3.png'))
    for width in (1024, 1280, 1440):
        page.set_viewport_size({'width': width, 'height': 900})
        for level, name in (('2', 'evidence'), ('3', 'level3')):
            page.locator(f'[data-teaching-level="{level}"]').scroll_into_view_if_needed()
            page.screenshot(path=str(EVIDENCE / f'm9-{width}-{name}.png'))
    text = '下一次我想改变荷载，再观察节点位移位置。'
    reflect(page, text)
    page.screenshot(path=str(EVIDENCE / 'm9-reflection.png'))
    for width in (1024, 1280, 1440):
        page.set_viewport_size({'width': width, 'height': 900})
        page.locator('#workspace-reflection').scroll_into_view_if_needed()
        page.screenshot(path=str(EVIDENCE / f'm9-{width}-reflection.png'))
    reflection = db_read(lambda: Reflection.objects.get(analysis_run_id=run_id))
    assert reflection.status == 'COMPLETED' and reflection.analysis_run_id == run_id
    assert reflection.next_iteration_intent == text
    page.reload()
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run_id))
    page.locator('[data-ux-summary-target="reflection"]').click()
    expect(page.locator('#workspace-reflection [name="next_iteration_intent"]')).to_have_value(text)
    expect(page.locator('#workspace-reflection textarea:not(:disabled)')).to_have_count(0)
    assert errors == []


def test_public_v2_no_prediction_keeps_explain_and_reflection_legal(public_page):
    from analysis.models import AnalysisRun
    page, _, _ = public_page
    draw_triangle(page)
    run_id = analyze(page)
    assert db_read(lambda: AnalysisRun.objects.get(pk=run_id).prediction_id) is None
    page.get_by_role('tab', name='预测对比', exact=True).click()
    expect(page.locator('[data-result-comparison]')).to_contain_text('没有保存预测')
    expect(page.locator('[data-comparison-evidence-member]')).to_have_count(0)
    page.get_by_role('tab', name='为什么', exact=True).click()
    expect(page.locator('[data-teaching-level="1"]')).to_contain_text('构件 M1')
    reflect(page, '没有预测也可以写下我自己的下一次观察。')
