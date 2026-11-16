from datetime import timedelta
from django.utils import timezone
import pytest
from pathlib import Path

from tests.browser.test_student_entry_flow import entry_page
from tests.browser.test_m7_project_creation import db_call
from tests.endpoints.test_event_landing import make_event, add_membership

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


@pytest.fixture
def manager_context(db):
    from accounts.models import User
    manager = User.objects.create_user('m8-manager', role='MANAGER')
    event = make_event(name='M8 管理赛事', code='M8-BROWSER')
    event.status = 'ACTIVE'
    event.starts_at = timezone.now() - timedelta(days=1)
    event.ends_at = timezone.now() + timedelta(days=1)
    event.save()
    add_membership(user=manager, event=event, membership_type='MANAGER')
    return manager, event


def test_manager_opens_public_management_entry(manager_context, entry_page):
    manager, event = manager_context
    page = entry_page(user=manager)
    assert page.get_by_role('link', name='赛事管理', exact=True).count() == 1
    page.get_by_role('link', name='赛事管理', exact=True).click()
    page.get_by_role('link', name='参赛队伍', exact=True).click()
    page.get_by_role('link', name='新增队伍', exact=True).click()
    page.get_by_label('队伍编号').fill('4')
    page.get_by_label('队长学号（初始凭证）').fill('browser-synthetic-credential')
    page.get_by_role('button', name='预览', exact=True).click()
    assert 'browser-synthetic-credential' not in page.content()
    assert page.get_by_role('button', name='确认新增', exact=True).is_visible()


def capture(page, name):
    folder = Path('.superpowers/sdd/2026-10-18-m8-event-participant-management/screenshots')
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / f'{name}.png'), full_page=True)


def build_and_analyze_public_model(page):
    from playwright.sync_api import expect
    page.get_by_role('link', name='管理材料与截面').click()
    page.get_by_role('link', name='新建材料').click()
    for label, value in [('材料名称', 'M8木材'), ('弹性模量 E（MPa）', '2000'),
                         ('密度（g/mm³）', '0.0007'), ('数据来源', 'MEASURED')]:
        page.get_by_label(label).fill(value)
    page.get_by_role('button', name='保存材料').click()
    page.get_by_role('link', name='新建矩形截面').click()
    for label, value in [('截面名称', 'M8矩形'), ('宽度（mm）', '2'), ('高度（mm）', '6'), ('密度（g/mm³）', '0.0007')]:
        page.get_by_label(label).fill(value)
    page.get_by_role('button', name='保存截面').click()
    page.get_by_role('link', name='返回 M8学生桁架 工作区').click()
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-workspace-tool="NODE"]').click()
    box = canvas.bounding_box()
    for x, y in [(box['width']*.25,box['height']*.7),(box['width']*.65,box['height']*.7),(box['width']*.45,box['height']*.3)]:
        canvas.click(position={'x': x, 'y': y})
    for a, b in [(1, 2), (1, 3), (2, 3)]:
        page.locator('[data-workspace-tool="MEMBER"]').click()
        page.locator(f'[data-client-key="node-{a}"][data-object-kind="GeometryNode"]').click()
        page.locator(f'[data-client-key="node-{b}"][data-object-kind="GeometryNode"]').click()
        page.keyboard.press('Escape')
    for node in (1, 2):
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
    page.locator('[data-ux-stage-target="analyze"]').click()
    page.locator('#workspace-analyze').click()
    expect(page.locator('[data-ux-analyze-status]')).to_have_text('分析已完成。')


def test_manager_student_m7_journey_and_preserved_history(manager_context, entry_page, live_server):
    from playwright.sync_api import expect
    from accounts.models import User
    from projects.models import Project
    from analysis.models import AnalysisRun
    from competitions.models import EventMembership, BulkImportBatch
    manager, event = manager_context
    page = entry_page(user=manager)
    page.get_by_role('link', name='赛事管理', exact=True).click()
    page.get_by_role('link', name='参赛队伍', exact=True).click()
    page.get_by_role('link', name='新增队伍', exact=True).click()
    page.get_by_label('队伍编号').fill('4')
    initial = 'SYNTHETIC-M8-STUDENT-INITIAL'
    page.get_by_label('队长学号（初始凭证）').fill(initial)
    page.get_by_role('button', name='预览', exact=True).click()
    assert initial not in page.content() and 'password_hash' not in page.content()
    ref = page.locator('input[name="preview_ref"]').input_value()
    capture(page, 'manager-confirm-new')
    page.get_by_role('button', name='确认新增', exact=True).click()
    assert page.get_by_text('参赛资格：有效', exact=True).is_visible()
    capture(page, 'manager-created-roster')
    page.reload()
    username = f'{event.competition_date:%Y%m%d}04'
    user = db_call(lambda: User.objects.get(username=username))
    member_id = db_call(lambda: EventMembership.objects.get(user=user, event=event).pk)
    assert db_call(Project.objects.count) == 0
    csrf = next(cookie['value'] for cookie in page.context.cookies() if cookie['name'] == 'csrftoken')
    replay = page.request.post(live_server.url + f'/competitions/{event.pk}/participants/confirm/',
                               form={'operation': 'CREATE_USER', 'preview_ref': ref}, headers={'X-CSRFToken': csrf})
    assert replay.status == 200 and db_call(BulkImportBatch.objects.count) == 1
    student_context = page.context.browser.new_context()
    student = student_context.new_page()
    try:
        student.goto(live_server.url + '/accounts/login/')
        student.locator('input[name="username"]').fill(username)
        student.locator('input[name="password"]').fill(initial)
        student.get_by_role('button', name='登录', exact=True).click()
        assert student.get_by_role('heading', name='修改密码', exact=True).is_visible()
        student.locator('input[name="old_password"]').fill(initial)
        student.locator('input[name="new_password1"]').fill('M8-Changed-Synthetic-93!')
        student.locator('input[name="new_password2"]').fill('M8-Changed-Synthetic-93!')
        student.get_by_role('button', name='确认修改', exact=True).click()
        student.get_by_role('link', name='创建项目', exact=True).click()
        student.get_by_label('项目名称').fill('M8学生桁架')
        student.get_by_role('button', name='创建项目', exact=True).click()
        project = db_call(lambda: Project.objects.get(owner_user=user, event=event))
        assert project.draft_schema_version == 'physical-draft-v2' and project.draft_version == 0
        capture(student, 'student-new-empty-project')
        build_and_analyze_public_model(student)
        run = db_call(lambda: AnalysisRun.objects.get(project=project))
        assert run.status == 'SUCCESS'
        capture(student, 'student-real-analysis')
        before = db_call(lambda: (Project.objects.filter(pk=project.pk).values().get(),
                                  AnalysisRun.objects.filter(pk=run.pk).values().get()))
        page.goto(live_server.url + f'/competitions/{event.pk}/participants/')
        page.get_by_label('确认仅停用此赛事的参赛资格，保留项目和历史').check()
        page.get_by_role('button', name='预览停用', exact=True).click()
        assert page.get_by_text('仅停用此赛事参赛资格，下一次请求不能进入本赛事项目。账号、项目和历史全部保留。').is_visible()
        capture(page, 'manager-confirm-deactivation')
        page.get_by_role('button', name='确认停用', exact=True).click()
        response = student.goto(live_server.url + f'/projects/{project.pk}/workspace/')
        assert response.status == 404
        assert db_call(lambda: (Project.objects.filter(pk=project.pk).values().get(),
                                AnalysisRun.objects.filter(pk=run.pk).values().get())) == before
        page.get_by_label('已核实这是同一支队伍').check()
        page.get_by_role('button', name='预览恢复', exact=True).click()
        page.get_by_role('button', name='确认恢复', exact=True).click()
        assert db_call(lambda: EventMembership.objects.get(user=user, event=event).pk) == member_id
        student.goto(live_server.url + '/events/')
        student.get_by_role('link', name='继续建模', exact=True).click()
        assert student.locator('#workspace-canvas').is_visible()
        assert db_call(AnalysisRun.objects.count) == 1
        student.locator('[data-ux-stage-target="summary"]').click()
        with student.expect_response(f'**/analyses/{run.pk}/data/') as restored:
            student.locator('#workspace-run-select').select_option(str(run.pk))
        assert restored.value.status == 200 and restored.value.json()['ok'] is True
        student.locator('[data-ux-stage-target="understanding"]').click()
        expect(student.get_by_role('tab', name='结论', exact=True)).to_be_visible()
        capture(student, 'student-history-after-select')
        capture(student, 'student-history-restored')
    finally:
        student_context.close()


@pytest.mark.parametrize('role', ['MANAGER', 'DEVELOPER'])
def test_existing_join_noop_and_lifecycle_readonly_in_browser(manager_context, entry_page, live_server, role):
    from accounts.models import User
    from competitions.models import CompetitionEvent, EventMembership
    manager, event = manager_context
    manager.role = role
    manager.save()
    target = User.objects.create_user('verified-existing', password='unchanged-synthetic')
    before = target.password
    page = entry_page(user=manager)
    base = live_server.url + f'/competitions/{event.pk}'
    for _ in range(2):
        page.goto(base + '/participants/')
        page.get_by_role('link', name='加入既有账号', exact=True).click()
        page.get_by_label('既有账号').fill(target.username)
        page.get_by_label('已核实这是同一支队伍').check()
        page.get_by_role('button', name='预览', exact=True).click()
        page.get_by_role('button', name='确认加入', exact=True).click()
    assert page.get_by_text('参赛资格已处于请求状态，未重复变更。', exact=False).is_visible()
    assert db_call(lambda: EventMembership.objects.filter(user=target, event=event).count()) == 1
    assert db_call(lambda: User.objects.get(pk=target.pk).password) == before
    other = db_call(lambda: make_event(name='未指派赛事', code='OTHER-M8'))
    response = page.goto(live_server.url + f'/competitions/{other.pk}/participants/')
    assert response.status == (200 if role == 'DEVELOPER' else 403)
    db_call(lambda: CompetitionEvent.objects.filter(pk=event.pk).update(status='FINISHED_GRACE'))
    page.goto(base + '/participants/')
    assert page.get_by_text('只读历史：不能新增、恢复或停用参赛资格。', exact=True).is_visible()
    assert page.get_by_role('link', name='新增队伍', exact=True).count() == 0
    capture(page, f'{role.lower()}-grace-readonly')
    db_call(lambda: CompetitionEvent.objects.filter(pk=event.pk).update(status='PURGED'))
    assert page.goto(base + '/participants/').status == 403


def test_draft_csv_real_upload_and_active_forged_request_denied(manager_context, entry_page, live_server):
    from competitions.models import CompetitionEvent, BulkImportBatch
    manager, event = manager_context
    event.status = 'DRAFT'
    event.save()
    page = entry_page(user=manager)
    base = live_server.url + f'/competitions/{event.pk}'
    page.goto(base + '/participants/')
    page.get_by_role('link', name='CSV 批量开户', exact=True).click()
    secret = 'SYNTHETIC-CSV-CREDENTIAL'
    page.get_by_label('CSV 文件').set_input_files({'name': 'teams.csv', 'mimeType': 'text/csv',
                                                   'buffer': f'team_number,captain_student_id\n1,{secret}\n'.encode()})
    page.get_by_role('button', name='预览批量开户', exact=True).click()
    assert secret not in page.content() and 'name="token"' not in page.content()
    ref = page.locator('input[name="preview_ref"]').input_value()
    capture(page, 'draft-csv-safe-preview')
    page.get_by_role('button', name='确认创建', exact=True).click()
    assert page.get_by_text('参赛资格：有效', exact=True).is_visible()
    assert db_call(BulkImportBatch.objects.count) == 1
    db_call(lambda: CompetitionEvent.objects.filter(pk=event.pk).update(status='ACTIVE'))
    csrf = next(cookie['value'] for cookie in page.context.cookies() if cookie['name'] == 'csrftoken')
    response = page.request.post(base + '/accounts/confirm/', form={'preview_ref': ref}, headers={'X-CSRFToken': csrf})
    assert response.status == 403
    assert 'PROVISIONING_STATUS_POLICY_GAP' not in response.text()
    assert db_call(BulkImportBatch.objects.count) == 1
