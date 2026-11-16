from datetime import timedelta
from django.utils import timezone
import pytest

from tests.endpoints.test_event_landing import add_membership, make_event


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_poc_v1_full_student_journey_uses_public_controls(live_server, monkeypatch):
    playwright = pytest.importorskip("playwright.sync_api")
    from accounts.models import User
    from competitions.models import CompetitionEvent, EventMembership
    from projects.models import Project
    from learning import services as learning_services
    original_authorize = learning_services._authorize_reflection_author
    def traced_authorize(project, actor):
        try:
            return original_authorize(project, actor)
        except Exception as exc:
            print('M7_REFLECTION_AUTH_TRACE', getattr(exc, 'code', str(exc)),
                'actor', actor.pk, actor.role, actor.is_active, 'owner', project.owner_user_id,
                'event', CompetitionEvent.objects.filter(pk=project.event_id).values('id', 'status').first(),
                'memberships', list(EventMembership.objects.filter(user=actor, event_id=project.event_id).values()),
                'audits', list(project.draft_migration_audits.values('status')))
            raise
    monkeypatch.setattr(learning_services, '_authorize_reflection_author', traced_authorize)

    student = User.objects.create_user("poc-v1-student", password="JourneyPass123!")
    event = make_event(name="POC V1 验收赛事", code="POC-V1-JOURNEY")
    event.starts_at = timezone.now() - timedelta(days=1)
    event.ends_at = timezone.now() + timedelta(days=1)
    event.save()
    CompetitionEvent.objects.filter(pk=event.id).update(status=CompetitionEvent.Status.ACTIVE)
    add_membership(user=student, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    Project.objects.create(event=event, owner_user=student, name="学生空白桁架", draft_schema_version="physical-draft-v1")

    runtime = playwright.sync_playwright().start()
    browser = runtime.chromium.launch()
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    def trace_response(response):
        if '/reflection/' in response.url and response.status >= 400:
            print('M7_REFLECTION_HTTP_TRACE', response.request.method, response.status, response.url, response.text())
    page.on('response', trace_response)
    page.on('requestfailed', lambda request: print('M7_REFLECTION_REQUEST_FAILED', request.method, request.url, request.failure)
        if '/reflection/' in request.url else None)
    try:
        page.goto(live_server.url + "/accounts/login/")
        page.locator('input[name="username"]').fill("poc-v1-student")
        page.locator('input[name="password"]').fill("JourneyPass123!")
        page.get_by_role("button", name="登录").click()
        assert page.get_by_text("POC V1 验收赛事").is_visible()
        page.get_by_role("link", name="继续建模").click()
        assert page.get_by_text("可编辑（项目所有者）").is_visible()

        page.get_by_role("link", name="管理材料与截面").click()
        page.get_by_role("link", name="新建材料").click()
        page.get_by_label("材料名称").fill("验收竹材")
        page.get_by_label("弹性模量 E（MPa）").fill("2000")
        page.get_by_label("密度（g/mm³）").fill("0.0007")
        page.get_by_label("数据来源").fill("MEASURED")
        page.get_by_role("button", name="保存材料").click()
        page.get_by_role("link", name="新建矩形截面").click()
        page.get_by_label("截面名称").fill("1×6 mm 验收截面")
        page.get_by_label("宽度（mm）").fill("1")
        page.get_by_label("高度（mm）").fill("6")
        page.get_by_label("密度（g/mm³）").fill("0.0007")
        page.get_by_role("button", name="保存截面").click()
        page.get_by_role("link", name="返回 学生空白桁架 工作区").click()

        page.locator(".ux-precision summary").click()
        page.locator("[data-cad-snap]").click()
        page.locator("[data-cad-ortho]").click()
        page.locator("[data-cad-ortho]").click()
        page.locator('[data-workspace-tool="NODE"]').click()
        command = page.locator("[data-cad-command-input]")
        for coordinate in ("0,0", "1000,0", "500,500"):
            command.fill(coordinate)
            command.press("Enter")
        command.fill("待取消")
        command.press("Escape")
        page.locator("[data-cad-fit]").click()

        def choose_tool(name):
            page.locator(f'[data-workspace-tool="{name}"]').click()

        choose_tool("MEMBER")
        for start, end in (("node-1", "node-2"), ("connection-1", "node-3"), ("connection-2", "connection-3")):
            page.locator(f'[data-client-key="{start}"]').click(force=True)
            page.locator(f'[data-client-key="{end}"]').click(force=True)
        assert page.locator('[data-object-kind="PhysicalMember"]').count() == 3

        assert page.locator('[data-object-kind="Connection"]').count() == 3

        choose_tool("SUPPORT")
        page.locator('[data-client-key="connection-1"] rect').click(force=True)
        page.locator('[data-client-key="connection-2"] rect').click(force=True)
        page.locator('[data-client-key="support-2"]').focus()
        page.keyboard.press("Enter")
        page.locator("[data-property-support-type]").select_option("ROLLER_Y")
        choose_tool("LOAD")
        page.locator('[data-client-key="connection-3"] rect').click(force=True)
        assert page.locator('[data-object-kind="NodeLoad"]').count() == 1

        page.locator("#workspace-save").click()
        page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
        page.reload()
        assert page.locator('[data-object-kind="PhysicalMember"]').count() == 3
        page.locator('[data-ux-stage-target="check"]').click()
        with page.expect_response("**/model/check/") as check_response:
            page.locator("#workspace-model-check").click()
        page.wait_for_function("document.querySelector('#workspace-check-issues').textContent.length > 0")
        assert check_response.value.json()["ok"] is True
        assert "模型检查通过" in page.locator("#workspace-check-issues").text_content()

        page.locator('[data-ux-stage-target="prediction"]').click()
        page.get_by_role("button", name="开始预测").click()
        page.wait_for_function("document.querySelector('[data-prediction-status]').textContent.includes('草稿')")
        for row in page.locator("[data-prediction-members] p").all():
            row.get_by_role("button", name="受拉").click()
        page.locator('[data-client-key="connection-3"]').focus()
        page.keyboard.press("Enter")
        page.get_by_role("button", name="用当前画布选择设置最大位移位置").click()
        for key in ("connection-1", "member-1", "connection-2"):
            page.locator(f'[data-client-key="{key}"]').focus()
            page.keyboard.press("Enter")
            page.get_by_role("button", name="将当前画布选择加入路径").click()
        page.get_by_role("button", name="完成预测").click()
        page.wait_for_function("document.querySelector('[data-prediction-status]').textContent.includes('已完成')")

        page.locator('[data-ux-stage-target="analyze"]').click()
        with page.expect_response('**/analyze/') as first_analysis:
            page.locator("#workspace-analyze").click()
        assert first_analysis.value.ok and first_analysis.value.json()['status'] == 'SUCCESS'
        first_run = str(first_analysis.value.json()['analysis_run_id'])
        page.wait_for_function("id => document.querySelector('#workspace-run-select').value === id", arg=first_run)
        page.wait_for_function("document.querySelector('[data-result-compare]')")
        page.locator("[data-result-compare]").click()
        page.wait_for_function("document.querySelector('[data-result-comparison]').textContent.length > 0")
        from tests.browser.av01_harness import follow_saved_member_link
        comparison_member = page.locator('[data-result-comparison] [data-teaching-member]').first
        playwright.expect(comparison_member).to_be_visible()
        first_member_key = comparison_member.get_attribute('data-teaching-member')
        follow_saved_member_link(page, comparison_member)
        page.locator("[data-result-explain]").click()
        page.wait_for_function("document.querySelector('[data-result-explanation]').textContent.length > 0")
        explanation_member = page.locator(f'[data-result-explanation] [data-teaching-member="{first_member_key}"]').first
        playwright.expect(explanation_member).to_be_visible()
        follow_saved_member_link(page, explanation_member)
        page.locator('[data-ux-stage-target="summary"]').click()
        assert "计算依据" in page.locator("#workspace-report-view").text_content()

        page.get_by_role("tab", name="我的设计说明").click()
        reasoning = page.locator('#workspace-report-reasoning [name="final_conclusion"]')
        reasoning.fill("第一次分析：三角形传力路径完整。")
        with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith(f'/analyses/{first_run}/reasoning/')) as saved_reasoning:
            page.get_by_role("button", name="保存设计说明").click()
        assert saved_reasoning.value.ok and saved_reasoning.value.json()['analysis_run_id'] == int(first_run)
        page.wait_for_function("document.querySelector('#workspace-report-reasoning form p').textContent.includes('已保存')")
        page.get_by_role("tab", name="反思（可选）").click()
        page.get_by_role("button", name="开始反思").click()
        page.locator('#workspace-reflection [name="original_reasoning"]').fill("我先判断三角形整体受力。")
        page.locator('#workspace-reflection [name="unexpected_results"]').fill("位移位置值得继续观察。")
        page.locator('#workspace-reflection [name="next_iteration_intent"]').fill("下一版调整荷载后比较。")
        with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith(f'/analyses/{first_run}/reflection/')) as saved_reflection:
            page.get_by_role("button", name="保存草稿").click()
        assert saved_reflection.value.ok and saved_reflection.value.json()['analysis_run_id'] == int(first_run)
        page.wait_for_function("!document.querySelector('#workspace-reflection [name=original_reasoning]').disabled")
        page.wait_for_function("document.querySelector('#workspace-reflection textarea').value.includes('三角形')")

        page.locator('[data-ux-stage-target="analyze"]').click()
        with page.expect_response('**/analyze/') as second_analysis:
            page.locator("#workspace-analyze").click()
        assert second_analysis.value.ok and second_analysis.value.json()['status'] == 'SUCCESS'
        second_run = str(second_analysis.value.json()['analysis_run_id'])
        assert second_run != first_run
        page.wait_for_function("document.querySelector('#workspace-root').dataset.uxStage === 'understanding'")
        page.wait_for_function("id => document.querySelector('#workspace-run-select').value === id", arg=second_run)
        page.locator('[data-ux-stage-target="summary"]').click()
        page.get_by_role("tab", name="我的设计说明").click()
        page.locator('#workspace-report-reasoning [name="final_conclusion"]').fill("第二次分析：保留同一模型作为历史对照。")
        with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith(f'/analyses/{second_run}/reasoning/')) as saved_reasoning:
            page.get_by_role("button", name="保存设计说明").click()
        assert saved_reasoning.value.ok and saved_reasoning.value.json()['analysis_run_id'] == int(second_run)
        page.wait_for_function("document.querySelector('#workspace-report-reasoning form p').textContent.includes('已保存')")
        page.get_by_role("tab", name="反思（可选）").click()
        page.get_by_role("button", name="开始反思").click()
        page.locator('#workspace-reflection [name="original_reasoning"]').fill("第二次运行用于验证历史隔离。")
        with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith(f'/analyses/{second_run}/reflection/')) as saved_reflection:
            page.get_by_role("button", name="保存草稿").click()
        assert saved_reflection.value.ok and saved_reflection.value.json()['analysis_run_id'] == int(second_run)
        page.wait_for_function("!document.querySelector('#workspace-reflection [name=original_reasoning]').disabled")

        page.reload()
        page.locator('[data-ux-stage-target="summary"]').click()
        page.locator("#workspace-run-select").select_option(first_run)
        page.wait_for_function("document.querySelector('#workspace-report-reasoning [name=final_conclusion]')?.value.includes('第一次')")
        assert "第一次" in page.locator('#workspace-report-reasoning [name="final_conclusion"]').input_value()
        assert "三角形" in page.locator('#workspace-reflection [name="original_reasoning"]').input_value()
        page.locator("#workspace-run-select").select_option(second_run)
        page.wait_for_function("document.querySelector('#workspace-report-reasoning [name=final_conclusion]')?.value.includes('第二次')")
        assert "第二次" in page.locator('#workspace-report-reasoning [name="final_conclusion"]').input_value()
        assert "历史隔离" in page.locator('#workspace-reflection [name="original_reasoning"]').input_value()
    finally:
        context.close()
        browser.close()
        runtime.stop()
