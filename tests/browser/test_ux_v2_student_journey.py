import pytest

from modeling.services import save_physical_draft
from tests.endpoints.test_event_landing import add_membership, make_event
from tests.application.test_physical_draft import context, valid_payload
from tests.application.test_analysis_acceptance import save_bt01_draft


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_new_student_sees_purpose_stage_and_can_draw_first_member(live_server):
    """Break caught: a newcomer lands in a tool dashboard without a starting action."""
    playwright = pytest.importorskip("playwright.sync_api")
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project
    from materials.models import Material
    from materials.services import create_section

    student = User.objects.create_user("ux-v2-first-student", password="StudyPass123!")
    event = make_event(name="新生结构赛", code="UX-V2-ENTRY")
    add_membership(user=student, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    Project.objects.create(event=event, owner_user=student, name="我的第一座桥")
    material = Material.objects.create(owner_user=student, name="木材", E_MPa=10000, density_g_per_mm3=0.0005, source_type="MEASURED")
    section = create_section(owner=student, name="方杆", definition={"schema_version": "section-definition-v1", "type": "rectangle", "width_mm": 10, "height_mm": 10, "density_g_per_mm3": 0.0005})
    runtime = playwright.sync_playwright().start()
    browser = runtime.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    try:
        page.goto(live_server.url + "/accounts/login/")
        assert page.get_by_text("建立结构 → 预测 → 分析 → 理解 → 总结").is_visible()
        page.locator('input[name="username"]').fill(student.username)
        page.locator('input[name="password"]').fill("StudyPass123!")
        page.get_by_role("button", name="登录").click()
        assert page.get_by_text("从第一根构件开始").is_visible()
        page.get_by_role("link", name="进入工作区").click()
        assert page.locator("[data-ux-stage-nav]").get_by_role("button", name="建模").is_visible()
        assert "构件" in page.locator("[data-ux-next-task]").inner_text()
        page.locator('[data-member-material]').select_option(str(material.pk))
        page.locator('[data-member-section]').select_option(str(section.pk))
        page.get_by_role("button", name="开始建模").click()
        assert page.locator('[data-workspace-tool="MEMBER"]').get_attribute("aria-pressed") == "true"
        canvas = page.locator("#workspace-canvas")
        canvas.click(position={"x": 200, "y": 200})
        canvas.click(position={"x": 400, "y": 200})
        assert page.locator('[data-object-kind="GeometryNode"]').count() == 2
        assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
        assert page.get_by_text("下一步：为结构添加支座").is_visible()
        page.set_viewport_size({"width": 1024, "height": 768})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("#workspace-canvas").bounding_box()["width"] > 500
    finally:
        browser.close()
        runtime.stop()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_build_guidance_context_save_and_check(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    assert page.locator(".ux-precision").get_attribute("open") is None
    tools = page.locator("[data-workspace-tool]")
    assert tools.count() == 5
    assert all(button.locator("[data-tool-icon]").count() == 1 for button in tools.all())
    page.locator('[data-workspace-tool="NODE"]').click()
    assert "交叉不会自动连接" in page.locator("[data-modeling-instruction]").inner_text()
    page.locator("#workspace-canvas").click(position={"x": 200, "y": 200})
    assert page.get_by_text("已放置节点").is_visible()
    assert page.locator("[data-ux-save-indicator]").inner_text() == "有未保存修改"
    page.locator('[data-client-key="node-1"]').click()
    page.set_viewport_size({"width": 1024, "height": 768})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.get_by_text("这是什么").is_visible()
    assert page.get_by_text("可以做什么").is_visible()
    assert page.get_by_text("下一步", exact=True).is_visible()
    page.keyboard.press("Escape")
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute("aria-pressed") == "true"
    page.locator("#workspace-save").click()
    page.wait_for_function("document.querySelector('[data-ux-save-indicator]').textContent === '已保存'")
    page.locator('[data-ux-stage-target="check"]').click()
    assert page.locator("#workspace-canvas").is_visible()
    assert page.get_by_role("button", name="检查模型").is_visible()
    page.locator("#workspace-model-check").click()
    page.wait_for_function("document.querySelector('#workspace-check-issues').textContent.trim().length > 0")
    assert page.locator("#workspace-check-issues").inner_text().strip()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_node_joint_does_not_reuse_stale_selection_on_blank_canvas(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas.click(position={"x": 200, "y": 200})
    canvas.click(position={"x": 400, "y": 200})
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"]').click()
    page.locator('[data-client-key="node-2"]').click()
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
    assert page.locator('[data-object-kind="Connection"]').count() == 2
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas.click(position={"x": 500, "y": 350})
    assert page.locator('[data-object-kind="Connection"]').count() == 2


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_support_and_load_tools_use_automatic_endpoint_joints(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas.click(position={"x": 200, "y": 200})
    canvas.click(position={"x": 400, "y": 200})
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"]').click()
    page.locator('[data-client-key="node-2"]').click()
    assert page.locator('[data-object-kind="Connection"]').count() == 2
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    page.locator('[data-object-kind="Connection"] rect').first.click(force=True)
    assert page.locator('[data-object-kind="Support"]').get_attribute('data-selected') == 'true'
    assert page.locator('[data-property-support-type]').is_visible()
    page.locator('[data-workspace-tool="LOAD"]').click()
    page.locator('[data-object-kind="Connection"] rect').last.click(force=True)
    assert page.locator('[data-object-kind="NodeLoad"]').get_attribute('data-selected') == 'true'
    assert page.locator('[data-property-fy]').is_visible()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_created_support_and_load_show_controls_and_persist(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.set_viewport_size({"width": 1024, "height": 768})
    connection = page.locator('[data-client-key="c1"] rect')

    page.locator('[data-workspace-tool="SUPPORT"]').click()
    connection.click(force=True)
    support = page.locator('[data-object-kind="Support"]')
    assert support.count() == 1 and support.get_attribute('data-selected') == 'true'
    assert support.locator('path').is_visible()
    assert support.locator('path').bounding_box()['width'] >= 20
    assert page.locator('[data-property-support-type]').is_visible()
    page.locator('[data-property-support-type]').select_option('ROLLER_Y')

    page.locator('[data-workspace-tool="LOAD"]').click()
    connection.click(force=True)
    load = page.locator('[data-object-kind="NodeLoad"]')
    assert load.count() == 1 and load.get_attribute('data-selected') == 'true'
    assert load.locator('[data-load-stem]').count() == 1
    assert load.locator('[data-load-stem]').bounding_box()['height'] >= 20
    assert page.locator('[data-property-fx]').is_visible()
    page.locator('[data-property-fx]').fill('75')
    page.locator('[data-property-fy]').fill('0')
    page.locator('[data-property-fy]').press('Tab')
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent === '未保存修改：无'")
    page.reload()

    page.locator('[data-object-kind="Support"] path').click(force=True)
    assert page.locator('[data-property-support-type]').input_value() == 'ROLLER_Y'
    page.locator('[data-draft-object-kind="NODE_LOAD"]').click()
    assert page.locator('[data-property-fx]').input_value() == '75'
    assert page.locator('[data-property-fy]').input_value() == '0'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_connection_marker_is_visible_for_support_and_load_tools_at_1024(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.set_viewport_size({"width": 1024, "height": 768})
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    marker = page.locator('[data-client-key="c1"] rect')
    assert marker.bounding_box()['width'] >= 12


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_support_and_negative_vertical_load_symbols_have_correct_screen_direction(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    positions = page.evaluate("""() => {
      const connection = document.querySelector('[data-client-key="c1"] rect').getBoundingClientRect();
      const support = document.querySelector('[data-client-key="s1"] path').getBoundingClientRect();
      const line = document.querySelector('[data-client-key="l1"] line');
      const matrix = line.getScreenCTM();
      const start = new DOMPoint(Number(line.getAttribute('x1')), Number(line.getAttribute('y1'))).matrixTransform(matrix);
      const end = new DOMPoint(Number(line.getAttribute('x2')), Number(line.getAttribute('y2'))).matrixTransform(matrix);
      return { connectionBottom: connection.bottom, supportTop: support.top, loadStartY: start.y, loadEndY: end.y };
    }""")
    assert positions['supportTop'] > positions['connectionBottom']
    assert positions['loadStartY'] < positions['loadEndY']


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_zero_vector_load_symbol_remains_visible_beyond_connection_marker(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['node_loads'][0]['fx_N'] = 0
    draft['node_loads'][0]['fy_N'] = 0
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.set_viewport_size({"width": 1024, "height": 768})
    circle = page.locator('[data-client-key="l1"] [data-structural-symbol="load"]').bounding_box()
    marker = page.locator('[data-client-key="c1"] rect').bounding_box()
    assert circle['width'] >= marker['width'] + 16


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_canvas_does_not_edit_after_leaving_build_stage(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('[data-ux-stage-target="check"]').click()
    page.locator('#workspace-canvas').click(position={"x": 280, "y": 230})
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute('aria-pressed') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_saving_draft_clears_previous_summary_selection(context, workspace_page):
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run.id))
    page.wait_for_function("document.querySelector('#workspace-report').dataset.runSelected === 'true'")
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('#workspace-canvas').click(position={"x": 500, "y": 360})
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent === '未保存修改：无'")
    page.wait_for_function("document.querySelector('#workspace-run-select').value === ''")
    assert page.locator('#workspace-report').get_attribute('data-run-selected') == 'false'
    assert not page.locator('#workspace-report-view').is_visible()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_repeat_save_without_changes_preserves_analysis(context, workspace_page):
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run.id))
    page.wait_for_function("document.querySelector('#workspace-report').dataset.runSelected === 'true'")
    save_requests = []
    page.on('request', lambda request: save_requests.append(request.url) if '/model/save/' in request.url else None)
    page.locator('#workspace-save').click()
    assert save_requests == []
    assert page.locator('#workspace-draft-version').inner_text() == '当前草稿 v1'
    assert page.locator('#workspace-run-select').input_value() == str(run.id)
    assert page.locator('#workspace-report').get_attribute('data-run-selected') == 'true'
    page.reload()
    assert page.locator('#workspace-draft-version').inner_text() == '当前草稿 v1'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_save_failure_is_visible_and_retry_preserves_draft(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator("#workspace-canvas").click(position={"x": 240, "y": 210})
    assert page.locator("[data-ux-save-indicator]").inner_text() == "有未保存修改"
    page.route("**/model/save/", lambda route: route.abort())
    page.locator("#workspace-save").click()
    page.wait_for_function("document.querySelector('[data-ux-save-indicator]').textContent === '保存失败'")
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
    page.unroute("**/model/save/")
    page.locator("#workspace-save").click()
    page.wait_for_function("document.querySelector('[data-ux-save-indicator]').textContent === '已保存'")
    page.reload()
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_analysis_opens_conclusions_then_evidence_tabs(context, workspace_page):
    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="prediction"]').click()
    assert page.get_by_text("先记录你的判断，也可以直接分析。").is_visible()
    page.locator('[data-prediction-skip]').click()
    page.locator('[data-ux-stage-target="analyze"]').click()
    assert page.get_by_text("将分析已保存的草稿 v1。").is_visible()
    page.locator('#workspace-analyze').click()
    page.wait_for_function("document.querySelector('#workspace-root').dataset.uxStage === 'understanding'")
    page.set_viewport_size({"width": 1280, "height": 800})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not page.locator('.workspace-member-properties').is_visible()
    assert page.get_by_role('tab', name='结论').get_attribute('aria-selected') == 'true'
    page.get_by_role('tab', name='结论').focus()
    page.keyboard.press('End')
    assert page.get_by_role('tab', name='技术数据').get_attribute('aria-selected') == 'true'
    page.keyboard.press('Home')
    assert page.get_by_role('tab', name='结论').get_attribute('aria-selected') == 'true'
    assert page.locator('[data-result-conclusion]').get_by_text('最大位移', exact=False).is_visible()
    page.locator('[data-result-conclusion] [data-teaching-member="m1"]').click()
    assert page.locator('[data-client-key="m1"]').get_attribute('data-selected') == 'true'
    page.get_by_role('tab', name='预测对比').click()
    assert page.get_by_text('这次没有保存预测，因此暂时无法比较。').is_visible()
    page.get_by_role('tab', name='为什么').click()
    assert page.locator('[data-result-explanation]').is_visible()
    assert '轴力' in page.locator('[data-result-explanation]').inner_text()
    page.locator('[data-client-key="m1"] line').click(force=True)
    assert page.locator('[data-result-explanation] [data-teaching-member="m1"][data-teaching-focused="true"]').count() >= 1
    page.get_by_role('tab', name='技术数据').click()
    assert page.locator('#workspace-engineering-details').is_visible()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_analysis_failure_explains_recovery_without_raw_error(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="analyze"]').click()
    page.locator('#workspace-analyze').click()
    page.wait_for_function("document.querySelector('[data-ux-analyze-status]').textContent.includes('模型暂时无法完成分析')")
    assert page.get_by_text('请检查连接、支座和荷载，也可以返回建模。', exact=False).is_visible()
    page.locator('[data-ux-back-to-build]').click()
    assert page.locator('#workspace-root').get_attribute('data-ux-stage') == 'build'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_summary_run_binding_reasoning_and_optional_reflection(context, workspace_page):
    from analysis.orchestration import analyze_project
    from competitions.models import CompetitionEvent

    owner, project, material, section = context
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    save_bt01_draft(owner, project, material, section, fx_N=100)
    first = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    save_bt01_draft(owner, project, material, section, fx_N=125)
    second = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(first.id))
    page.wait_for_function("document.querySelector('#workspace-report-view').textContent.includes('计算依据')")
    assert '第 1 次分析' in page.locator(f'#workspace-run-select option[value="{first.id}"]').inner_text()
    assert '8.333' in page.locator('#workspace-report-view').inner_text()
    for width, height in ((1024, 768), (1280, 800), (1440, 900)):
        page.set_viewport_size({"width": width, "height": height})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.get_by_role('tab', name='计算依据').get_attribute('aria-selected') == 'true'
    page.get_by_role('tab', name='计算依据').focus()
    page.keyboard.press('ArrowRight')
    assert page.get_by_role('tab', name='我的设计说明').get_attribute('aria-selected') == 'true'
    assert page.get_by_role('tab', name='我的设计说明').evaluate('(element) => document.activeElement === element')
    assert page.locator('#workspace-report-view details').count() >= 1
    page.get_by_role('tab', name='我的设计说明').click()
    assert page.get_by_text('由你自己填写，平台不会替你生成设计理由。').is_visible()
    assert page.locator('#workspace-report-reasoning textarea').count() == 7
    page.locator('#workspace-report-reasoning [name="final_conclusion"]').fill('第一次分析的判断')
    page.get_by_role('button', name='保存设计说明').click()
    page.wait_for_function("document.querySelector('#workspace-report-reasoning form p').textContent.includes('已保存')")
    page.get_by_role('tab', name='反思（可选）').click()
    page.get_by_role('button', name='开始反思').click()
    page.locator('#workspace-reflection [name="original_reasoning"]').fill('第一次反思')
    with page.expect_response("**/reflection/") as saved_reflection:
        page.get_by_role('button', name='保存草稿').click()
    assert saved_reflection.value.ok
    page.locator('#workspace-run-select').select_option(str(second.id))
    page.wait_for_function("document.querySelector('#workspace-report-reasoning [name=final_conclusion]')?.value === ''")
    page.locator('#workspace-run-select').select_option(str(first.id))
    page.wait_for_function("document.querySelector('#workspace-report-reasoning [name=final_conclusion]')?.value.includes('第一次')")
    assert '第一次反思' in page.locator('#workspace-reflection [name="original_reasoning"]').input_value()
