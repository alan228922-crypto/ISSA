"""Actual saved-run shell checks; numerical edge carriers are explicitly component-only."""
import pytest
from playwright.sync_api import expect
from tests.application.test_physical_draft import context
from tests.endpoints.test_analysis_visualization import saved_context, frozen_artifacts
from tests.browser.test_av01_run_integration import select_public, ready_plot
from tests.browser.test_m9_reflection_handoff import db_read
from tests.browser.av01_harness import av01_page, mount, projection_fixture, teaching_fixture

pytestmark=[pytest.mark.browser,pytest.mark.django_db(transaction=True)]

@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_saved_results_canvas_and_evidence_rail_fit_viewport(saved_context,workspace_page,width,height):
    owner,project,run,_,_=saved_context
    before=frozen_artifacts(run)
    page=workspace_page(user=owner,project=project);page.set_viewport_size({'width':width,'height':height})
    select_public(page,run.pk);ready_plot(page)
    assert page.locator('[data-av01-fit] svg use').count()==1
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    canvas=page.locator('[data-av01-canvas]').bounding_box();rail=page.locator('.av01-sidebar').bounding_box()
    assert canvas['width']>width-420,(width,canvas)
    assert canvas['height']>=250 and canvas['y']+canvas['height']<=height-5,(height,canvas)
    assert canvas['x']+canvas['width']<=rail['x']+1
    assert page.locator('.av01-sidebar').evaluate('e=>getComputedStyle(e).overflowY')=='auto'
    assert page.locator('[data-av01-axis=x]').count()==1
    assert page.locator('[data-av01-original-layer] circle').first.get_attribute('r')=='4'
    page.locator('[data-av01-object-list]').evaluate('e=>e.open=true')
    page.locator('[data-av01-object-list] button').first.click()
    expect(page.locator('[data-av01-evidence]')).to_contain_text('mm')
    page.locator('[data-av01-exact] summary').click()
    assert db_read(lambda:frozen_artifacts(run))==before
    page.locator('[data-ux-stage-target=build]').click()
    assert page.locator('[data-cad-shortcuts-open]').inner_text()=='?'
    assert page.locator('#workspace-canvas [data-orientation-axis=x]').count()==1

@pytest.mark.parametrize('value,shown',[(1.2e-12,'1.2e-12'),(0,'0')])
def test_level_one_displacement_does_not_turn_tiny_nonzero_into_zero(av01_page,value,shown):
    page=av01_page
    page.evaluate("""async value=>{const {renderLevelOne}=await import('/static/projects/workspace/results.js');renderLevelOne(document.querySelector('[data-mount]'),{members:[],maximum:{maximum_displacement_mm:value,displayCandidateLabels:['节点 1']}})}""",value)
    assert page.locator('[data-student-rounded-value]').inner_text()==shown+' mm'


def test_component_sidebar_preserves_partial_and_exact_evidence(av01_page):
    p=projection_fixture();p['status']='PARTIAL';p['reactions'][0]['rx_N']=1.2e-12
    p['capabilities']['deformation']={'status':'UNAVAILABLE','reason':'MISSING_DISPLACEMENTS'}
    mount(av01_page,p,teaching_fixture(p));page=av01_page
    assert page.locator('.av01-sidebar [data-av01-layer]').count()==4
    expect(page.locator('[data-av01-layer=deformation]')).to_be_disabled()
    assert page.locator('[data-av01-reaction][data-component=Rx]').count()==1
    page.locator('[data-av01-object-list]').evaluate('e=>e.open=true')
    page.locator('[data-av01-object-list] button[data-object-kind=SUPPORT]').first.click()
    expect(page.locator('[data-av01-evidence]')).to_contain_text('1.2e-12')
    page.locator('[data-av01-exact] summary').click()
    assert float(page.locator('[data-av01-exact] [data-av01-field=Rx] strong').inner_text().split()[0])==1.2e-12
    assert page.evaluate('JSON.stringify(inputFacts)===beforeFacts')


@pytest.mark.parametrize('width,height',[(800,768),(1024,600)])
def test_short_or_narrow_results_leave_evidence_in_document_flow(saved_context,workspace_page,width,height):
    owner,project,run,_,_=saved_context
    page=workspace_page(user=owner,project=project);page.set_viewport_size({'width':width,'height':height})
    select_public(page,run.pk);ready_plot(page)
    # Numeric projection may become READY before late teaching adds its overview.
    # Measure all three boxes in one frame, never across two async render epochs.
    panel,rail,canvas=page.evaluate("['#workspace-workflow-panel','.av01-sidebar','[data-av01-canvas]'].map(s=>document.querySelector(s).getBoundingClientRect().toJSON())")
    assert rail['y']>=canvas['y']+canvas['height']-1
    assert rail['y']+rail['height']<=panel['y']+panel['height']+1,(panel,rail)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('[data-av01-values] summary').click()
    assert page.locator('[data-av01-reaction-row]').first.is_visible()


def test_empty_results_do_not_present_current_draft_as_saved_result(context,workspace_page):
    owner,project,_,_=context
    page=workspace_page(user=owner,project=project)
    page.locator('[data-ux-stage-target=understanding]').click()
    expect(page.locator('.ui-results-empty')).to_be_visible()
    expect(page.locator('.ui-results-empty')).to_contain_text('选择已保存分析')
    assert not page.locator('#workspace-canvas').is_visible()
    assert page.locator('[data-av01-canvas]').count()==0
