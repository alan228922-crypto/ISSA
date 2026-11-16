from datetime import timedelta
from django.utils import timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.browser.test_student_entry_flow import entry_page
from tests.endpoints.test_event_landing import make_event, add_membership

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def db_call(function):
    # Playwright sync API runs an event loop; keep real ORM work on a sync worker.
    from django.db import connection
    def run():
        try:
            return function()
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(run).result()


@pytest.fixture
def new_student(db):
    from accounts.models import User
    user = User.objects.create_user('m7-student')
    event = make_event(name='M7 验收赛事', code='M7-BROWSER')
    event.status = 'ACTIVE'
    event.starts_at = timezone.now() - timedelta(days=1)
    event.ends_at = timezone.now() + timedelta(days=1)
    event.save()
    add_membership(user=user, event=event, membership_type='PARTICIPANT')
    return user, event


def capture(page, name):
    folder = Path('.superpowers/sdd/2026-10-17-m7-project-creation-event-provisioning/screenshots')
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / f'{name}.png'), full_page=True)


def test_student_creates_project_from_event_and_completes_v2_journey(new_student, entry_page, live_server):
    from projects.models import Project
    from materials.models import Material, Section
    from analysis.models import AnalysisRun
    owner, event = new_student
    page = entry_page(user=owner)
    assert page.get_by_role('link', name='创建项目', exact=True).count() == 1
    page.get_by_role('link', name='创建项目', exact=True).click()
    page.get_by_label('项目名称').fill('我的 M7 桁架')
    page.get_by_role('button', name='创建项目', exact=True).click()
    assert page.locator('#workspace-canvas').is_visible()
    project = db_call(lambda: Project.objects.get(owner_user=owner, event=event))
    assert project.draft_schema_version == 'physical-draft-v2' and project.draft_version == 0
    assert db_call(lambda: (Material.objects.count(), Section.objects.count(), AnalysisRun.objects.count())) == (0,0,0)
    assert page.get_by_text('绘制前，请在右侧「管理材料与截面」准备并选择材料与截面。').is_visible()
    capture(page, 'new-empty-workspace')
    page.get_by_role('link', name='管理材料与截面').click()
    page.get_by_role('link', name='新建材料').click()
    for label, value in [('材料名称','木材'), ('弹性模量 E（MPa）','2000'), ('密度（g/mm³）','0.0007'), ('数据来源','MEASURED')]:
        page.get_by_label(label).fill(value)
    page.get_by_role('button', name='保存材料').click()
    page.get_by_role('link', name='新建矩形截面').click()
    for label, value in [('截面名称','矩形'),('宽度（mm）','2'),('高度（mm）','6'),('密度（g/mm³）','0.0007')]:
        page.get_by_label(label).fill(value)
    page.get_by_role('button', name='保存截面').click()
    page.get_by_role('link', name='返回 我的 M7 桁架 工作区').click()
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-workspace-tool="NODE"]').click()
    box = canvas.bounding_box()
    for x, y in [(box['width']*.25,box['height']*.7),(box['width']*.65,box['height']*.7),(box['width']*.45,box['height']*.3)]:
        canvas.click(position={'x':x, 'y':y})
    for a,b in [(1,2),(1,3),(2,3)]:
        page.locator('[data-workspace-tool="MEMBER"]').click()
        page.locator(f'[data-client-key="node-{a}"][data-object-kind="GeometryNode"]').click()
        page.locator(f'[data-client-key="node-{b}"][data-object-kind="GeometryNode"]').click()
        page.keyboard.press('Escape')
    for node in (1,2):
        page.locator('[data-workspace-tool="SUPPORT"]').click()
        page.locator(f'[data-client-key="node-{node}"][data-object-kind="GeometryNode"]').click()
    page.locator('[data-property-support-type]').select_option('ROLLER_Y')
    page.locator('[data-workspace-tool="LOAD"]').click()
    page.locator('[data-client-key="node-3"][data-object-kind="GeometryNode"]').click()
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('[data-ux-save-indicator]').textContent === '已保存'")
    page.reload()
    page.locator('[data-ux-stage-target="check"]').click()
    with page.expect_response('**/model/check/') as checked:
        page.locator('#workspace-model-check').click()
    assert checked.value.json()['ok'] is True
    page.locator('[data-ux-stage-target="prediction"]').click()
    page.get_by_role('button', name='开始预测', exact=True).click()
    page.wait_for_function("document.querySelector('[data-prediction-status]').textContent.includes('草稿')")
    # A draft Prediction remains optional: moving on does not forge completed evidence.
    page.locator('[data-ux-stage-target="analyze"]').click()
    page.locator('#workspace-analyze').click()
    page.wait_for_function("document.querySelector('#workspace-run-select').value !== ''")
    assert db_call(lambda: AnalysisRun.objects.get(project=project).status) == 'SUCCESS'
    capture(page, 'successful-results')
    # Direct duplicate POST remains safe although landing deliberately has no Create CTA.
    page.goto(live_server.url + '/events/')
    assert page.get_by_role('link', name='创建项目', exact=True).count() == 0
    assert page.get_by_role('link', name='继续建模', exact=True).count() == 1
    before = db_call(lambda: list(Project.objects.values()))
    csrf = next(cookie['value'] for cookie in page.context.cookies() if cookie['name'] == 'csrftoken')
    duplicate = page.request.post(live_server.url + f'/events/{event.pk}/projects/create/',
        form={'name':'不应覆盖原名称'}, headers={'X-CSRFToken':csrf})
    assert duplicate.status == 200
    assert db_call(lambda: list(Project.objects.values())) == before
    page.get_by_role('link', name='继续建模', exact=True).click()
    db_call(project.refresh_from_db)
    version = project.draft_version
    db_call(lambda: type(event).objects.filter(pk=event.pk).update(status='FINISHED_GRACE'))
    page.reload()
    assert page.locator('#workspace-save').is_disabled()
    # Existing contract: historical results require explicit run selection after reload.
    run_id = db_call(lambda: AnalysisRun.objects.get(project=project).pk)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run_id))
    page.locator('[data-ux-stage-target="understanding"]').click()
    for label in ('结论','为什么','技术数据','预测对比','结论'):
        page.get_by_role('tab', name=label, exact=True).click()
        for tab in ('结论','预测对比','为什么','技术数据'):
            assert page.get_by_role('tab', name=tab, exact=True).is_visible()
    page.locator('[data-ux-stage-target="summary"]').click()
    assert page.locator('#workspace-report-view').inner_text()
    page.locator('[data-ux-stage-target="understanding"]').click()
    assert page.get_by_role('tab', name='结论', exact=True).get_attribute('aria-selected') == 'true'
    capture(page, 'grace-history')
    db_call(project.refresh_from_db)
    assert project.draft_version == version
    assert db_call(AnalysisRun.objects.count) == 1


def test_legacy_multiple_projects_have_no_automatic_selection(new_student, entry_page, live_server):
    from projects.models import Project
    owner,event = new_student
    for name in ('历史方案甲','历史方案乙'):
        Project.objects.create(owner_user=owner,event=event,name=name,draft_schema_version='physical-draft-v1')
    page = entry_page(user=owner)
    assert page.get_by_role('link', name='创建项目', exact=True).count() == 0
    assert page.get_by_role('link', name='进入工作区', exact=True).count() == 2
    assert page.get_by_text('此赛事中已有多个项目，请选择要继续的项目。').is_visible()
    page.goto(live_server.url + f'/events/{event.pk}/projects/create/')
    page.get_by_label('项目名称').fill('不应新建')
    page.get_by_role('button', name='创建项目', exact=True).click()
    assert page.get_by_text('此赛事中已有多个项目，请返回赛事页选择现有项目。').is_visible()
    capture(page, 'safe-create-conflict')
    assert db_call(Project.objects.count) == 2
    for forbidden in ('PROJECT_MULTIPLE_EXISTING', 'physical-draft-v1', 'owner_user_id', 'Traceback'):
        assert forbidden not in page.locator('body').inner_text()
