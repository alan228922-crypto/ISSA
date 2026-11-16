"""Learning presentation through existing real Run selection and authoring endpoints."""
import pytest
from playwright.sync_api import expect
from tests.application.test_physical_draft import context
from tests.endpoints.test_m9_run_contract import m9_run
from tests.browser.test_m9_reflection_handoff import active_m9_run,two_active_runs,db_read
from tests.browser.test_av01_run_integration import select_public,ready_plot
from tests.endpoints.test_analysis_visualization import frozen_artifacts
from tests.browser.av01_harness import av01_page

pytestmark=[pytest.mark.browser,pytest.mark.django_db(transaction=True)]

@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_learning_surfaces_share_layout_run_context_and_focus(active_m9_run,workspace_page,width,height):
    owner,project,run=active_m9_run
    page=workspace_page(user=owner,project=project);page.set_viewport_size({'width':width,'height':height})
    select_public(page,run.pk);ready_plot(page)
    page.get_by_role('tab',name='为什么',exact=True).click()
    expect(page.locator('[data-learning-step]')).to_have_count(3)
    expect(page.locator('[data-learning-visible-context]')).to_be_visible()
    for tab in ['为什么','预测对比']:
        page.get_by_role('tab',name=tab,exact=True).click()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        expect(page.locator('[data-result-panel]:visible [data-teaching-context]').first).to_contain_text('第 1 次分析')
    page.locator('[data-ux-stage-target=summary]').click()
    expect(page.locator('[data-learning-run-context]')).to_contain_text('第 1 次分析')
    for tab in ['report','reasoning','reflection','history']:
        page.locator(f'[data-ux-summary-target={tab}]').click()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not page.locator('#workspace-status-bar').is_visible()
    assert page.locator('[data-history-run]').count()==1
    page.locator('[data-ux-summary-target=reasoning]').click()
    assert page.locator('#workspace-report-reasoning fieldset').count()==3
    assert page.locator('#workspace-report-reasoning textarea').count()==7
    page.locator('#workspace-report-reasoning textarea').first.focus()
    assert page.evaluate('getComputedStyle(document.activeElement).outlineStyle')!='none'


def test_history_cards_delegate_to_the_existing_native_run_selection(two_active_runs,workspace_page):
    owner,project,first,second=two_active_runs
    page=workspace_page(user=owner,project=project);select_public(page,first.pk);ready_plot(page)
    page.locator('[data-ux-stage-target=summary]').click();page.locator('[data-ux-summary-target=history]').click()
    page.locator(f'[data-history-run="{second.pk}"]').click()
    expect(page.locator('#workspace-run-select')).to_have_value(str(second.pk))
    expect(page.locator('[data-learning-run-context]')).to_contain_text('第 2 次分析')
    expect(page.locator('#workspace-report')).to_have_attribute('data-learning-selection','ready')
    expect(page.locator(f'[data-history-run="{second.pk}"]')).to_have_attribute('aria-pressed','true')


def test_all_reasoning_and_reflection_fields_keep_real_save_and_completion(active_m9_run,workspace_page):
    owner,project,run=active_m9_run;before=frozen_artifacts(run)
    page=workspace_page(user=owner,project=project);select_public(page,run.pk);ready_plot(page)
    page.locator('[data-ux-stage-target=summary]').click();page.locator('[data-ux-summary-target=reasoning]').click()
    fields=page.locator('#workspace-report-reasoning textarea')
    expect(fields).to_have_count(7)
    for index,field in enumerate(fields.all()):field.fill(f'学生自己的第{index+1}项说明')
    with page.expect_response('**/reasoning/') as response:page.get_by_role('button',name='保存设计说明',exact=True).click()
    assert response.value.ok and response.value.json()['analysis_run_id']==run.pk
    page.locator('[data-ux-summary-target=reflection]').click();page.get_by_role('button',name='开始反思',exact=True).click()
    for index,field in enumerate(page.locator('#workspace-reflection textarea').all()):field.fill(f'学生自己的第{index+1}项反思')
    with page.expect_response('**/reflection/') as response:page.get_by_role('button',name='保存草稿',exact=True).click()
    assert response.value.ok
    with page.expect_response('**/reflection/complete/') as response:page.get_by_role('button',name='完成反思',exact=True).click()
    assert response.value.ok
    expect(page.locator('#workspace-reflection')).to_contain_text('已完成，不能修改')
    assert page.locator('#workspace-reflection textarea:disabled').count()==3
    assert db_read(lambda:frozen_artifacts(run))==before

@pytest.mark.parametrize('value,shown',[(1.2e-12,'1.2e-12'),(0,'0')])
def test_report_summary_preserves_tiny_nonzero(av01_page,value,shown):
    page=av01_page
    page.evaluate("""async value=>{const {renderReport}=await import('/static/projects/workspace/report.js');renderReport(document.querySelector('[data-mount]'),{report:{results_summary:{maximum_displacement:{maximum_displacement:{maximum_displacement_mm:value}}}}})}""",value)
    assert f'最大位移 {shown} mm' in page.locator('[data-mount]').inner_text()


def test_history_names_saved_draft_without_claiming_unsaved_model(active_m9_run,workspace_page):
    owner,project,run=active_m9_run
    page=workspace_page(user=owner,project=project);select_public(page,run.pk);ready_plot(page)
    page.locator('[data-ux-stage-target=summary]').click();page.locator('[data-ux-summary-target=history]').click()
    card=page.locator(f'[data-history-run="{run.pk}"]')
    expect(card).to_contain_text('与当前已保存草稿一致')
    expect(card).not_to_contain_text('当前模型版本')
