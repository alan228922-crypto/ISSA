import pytest

from tests.endpoints.test_event_landing import add_membership, make_event


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_poc_v1_full_student_journey_uses_public_controls(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    from accounts.models import User
    from competitions.models import CompetitionEvent, EventMembership
    from projects.models import Project

    student = User.objects.create_user("poc-v1-student", password="JourneyPass123!")
    event = make_event(name="POC V1 验收赛事", code="POC-V1-JOURNEY")
    CompetitionEvent.objects.filter(pk=event.id).update(status=CompetitionEvent.Status.ACTIVE)
    add_membership(user=student, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    Project.objects.create(event=event, owner_user=student, name="学生空白桁架")

    runtime = playwright.sync_playwright().start()
    browser = runtime.chromium.launch()
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        page.goto(live_server.url + "/accounts/login/")
        page.locator('input[name="username"]').fill("poc-v1-student")
        page.locator('input[name="password"]').fill("JourneyPass123!")
        page.get_by_role("button", name="登录").click()
        assert page.get_by_text("POC V1 验收赛事").is_visible()
        page.get_by_role("link", name="进入工作区").click()
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
        for start, end in (("node-1", "node-2"), ("node-1", "node-3"), ("node-2", "node-3")):
            page.locator(f'[data-client-key="{start}"]').click()
            page.locator(f'[data-client-key="{end}"]').click()
        assert page.locator('[data-object-kind="PhysicalMember"]').count() == 3

        choose_tool("CONNECTION")
        for key in ("node-1", "node-2", "node-3"):
            page.locator(f'[data-client-key="{key}"] circle').click(force=True)
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
        page.locator("#workspace-model-check").click()
        page.wait_for_function("document.querySelector('#workspace-check-issues').textContent.length > 0")
        assert "模型检查通过" in page.locator("#workspace-check-issues").text_content()

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

        page.locator("#workspace-analyze").click()
        page.wait_for_function("document.querySelector('#workspace-run-select').value !== ''")
        first_run = page.locator("#workspace-run-select").input_value()
        page.wait_for_function("document.querySelector('[data-result-compare]')")
        page.locator("[data-result-compare]").click()
        page.wait_for_function("document.querySelector('[data-result-comparison]').textContent.length > 0")
        first_member_key = page.locator('[data-object-kind="PhysicalMember"]').first.get_attribute("data-client-key")
        page.locator(f'[data-client-key="{first_member_key}"] line').click(force=True)
        page.wait_for_function("key => document.activeElement?.dataset.teachingMember === key", arg=first_member_key)
        assert page.locator(f'[data-result-comparison] [data-teaching-member="{first_member_key}"][data-teaching-focused="true"]').count() == 1
        page.locator("[data-result-explain]").click()
        page.wait_for_function("document.querySelector('[data-result-explanation]').textContent.length > 0")
        page.locator(f'[data-client-key="{first_member_key}"] line').click(force=True)
        page.wait_for_function("key => document.activeElement?.dataset.teachingMember === key", arg=first_member_key)
        assert page.locator(f'[data-result-explanation] [data-teaching-member="{first_member_key}"][data-teaching-focused="true"]').count() == 1
        page.locator("[data-result-report]").click()
        assert f"分析 #{first_run}" in page.locator("#workspace-report-view").text_content()

        reasoning = page.locator('#workspace-report-reasoning [name="final_conclusion"]')
        reasoning.fill("第一次分析：三角形传力路径完整。")
        page.get_by_role("button", name="保存设计说明").click()
        page.wait_for_function("document.querySelector('#workspace-report-reasoning form p').textContent.includes('已保存')")
        page.get_by_role("button", name="开始反思").click()
        page.locator('#workspace-reflection [name="original_reasoning"]').fill("我先判断三角形整体受力。")
        page.locator('#workspace-reflection [name="unexpected_results"]').fill("位移位置值得继续观察。")
        page.locator('#workspace-reflection [name="next_iteration_intent"]').fill("下一版调整荷载后比较。")
        page.get_by_role("button", name="保存草稿").click()
        page.wait_for_function("document.querySelector('#workspace-reflection textarea').value.includes('三角形')")

        page.locator("#workspace-analyze").click()
        page.wait_for_function("previous => document.querySelector('#workspace-run-select').value !== previous", arg=first_run)
        second_run = page.locator("#workspace-run-select").input_value()
        page.wait_for_function("runId => document.querySelector('#workspace-results').textContent.includes(`#${runId}`)", arg=int(second_run))
        page.locator('#workspace-report-reasoning [name="final_conclusion"]').fill("第二次分析：保留同一模型作为历史对照。")
        page.get_by_role("button", name="保存设计说明").click()
        page.get_by_role("button", name="开始反思").click()
        page.locator('#workspace-reflection [name="original_reasoning"]').fill("第二次运行用于验证历史隔离。")
        page.get_by_role("button", name="保存草稿").click()

        page.reload()
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
