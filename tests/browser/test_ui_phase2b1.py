"""Real renderer/layout boundaries; existing CAD tests cover command semantics."""
import pytest
from tests.application.test_physical_draft import context
from tests.browser.test_cad_core_drawing import open_core
from tests.browser.test_m9_public_teaching_loop import public_page, draw_triangle, predict

pytestmark=[pytest.mark.browser,pytest.mark.django_db(transaction=True)]


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_preanalysis_layout_keeps_canvas_status_and_panels_separate(context,workspace_page,width,height):
    page,_=open_core(context,workspace_page,nodes=[('node-1',0,0),('node-2',400,0)],members=[('member-1','node-1','node-2')])
    page.set_viewport_size({'width':width,'height':height})
    page.locator('[data-cad-fit]').click()
    assert page.locator('[data-cad-shortcuts-open]').inner_text()=='?'
    before=page.locator('[data-node-body]').evaluate_all('(es)=>es.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')
    size=page.locator('[data-node-body]').first.bounding_box()['width']
    page.locator('[data-cad-zoom-in]').click()
    assert page.locator('[data-node-body]').first.bounding_box()['width']==pytest.approx(size,abs=.5)
    assert page.locator('[data-node-body]').evaluate_all('(es)=>es.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')==before
    for stage in ['build','check','prediction','analyze']:
        page.locator(f'[data-ux-stage-target={stage}]').click()
        page.locator('[data-cad-fit]').click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        canvas=page.locator('#workspace-canvas').bounding_box()
        status=page.locator('#workspace-status-bar').bounding_box()
        inspector=page.locator('#workspace-workflow-panel').bounding_box()
        assert canvas['width']>500 and canvas['height']>230,(stage,canvas)
        assert canvas['y']+canvas['height']<=status['y']+1
        assert canvas['x']+canvas['width']<=inspector['x']+1
        assert page.locator('#workspace-workflow-panel').evaluate('e=>getComputedStyle(e).overflowY')=='auto'
    page.locator('[data-ux-stage-target=build]').click()
    assert page.locator('[data-cad-transform-command]').is_visible()
    assert page.locator('[data-cad-copy] svg').count()==1
    page.locator('[data-cad-shortcuts-open]').click()
    dialog=page.locator('[data-cad-shortcuts-dialog]')
    assert dialog.is_visible()
    assert dialog.bounding_box()['height'] <= height-32
    page.keyboard.press('Escape')
    assert page.locator('[data-cad-shortcuts-open]').evaluate('e=>e===document.activeElement')


def test_prediction_authoring_and_real_analyze_keeps_saved_run_contract(public_page):
    from playwright.sync_api import expect
    page,_,_=public_page
    draw_triangle(page)
    predict(page)
    assert page.locator('[data-prediction-choice]:enabled').count()==0
    page.locator('[data-ux-stage-target=analyze]').click()
    assert '二维桁架' in page.locator('.ui-analysis-assumptions').text_content()
    with page.expect_response('**/analyze/') as response:
        page.locator('#workspace-analyze').click()
    payload=response.value.json()
    assert payload['ok'] and payload['status']=='SUCCESS'
    expect(page.locator('#workspace-root')).to_have_attribute('data-ux-stage','understanding')
    assert page.locator('[data-av01-root]').is_visible()
    assert not page.locator('.ui-command-dock').is_visible()
    assert not page.locator('.ux-precision').is_visible()
    assert page.locator('[data-orientation-style=axes]').count()==0
    assert page.locator('.workspace-layout').evaluate('e=>getComputedStyle(e).height')!='0px'


def test_direction_axes_keep_screen_size_and_world_geometry(context,workspace_page):
    page,_=open_core(context,workspace_page,nodes=[('node-1',0,0),('node-2',400,0)])
    world=page.locator('[data-node-body]').evaluate_all('(es)=>es.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')
    for width,height in [(1024,768),(1280,800),(1440,900)]:
        page.set_viewport_size({'width':width,'height':height})
        page.locator('[data-cad-fit]').click()
        for _ in range(2):
            axis=page.locator('[data-orientation-axis=x]')
            assert axis.count()==1
            length=lambda e:e.evaluate('e=>{const m=e.getScreenCTM(),a=e.getPointAtLength(0).matrixTransform(m),b=e.getPointAtLength(e.getTotalLength()).matrixTransform(m);return Math.hypot(b.x-a.x,b.y-a.y)}')
            assert length(axis)==pytest.approx(42,abs=.5)
            assert length(page.locator('[data-orientation-axis=y]'))==pytest.approx(42,abs=.5)
            canvas=page.locator('#workspace-canvas').bounding_box()
            origin=page.locator('[data-orientation-origin]').bounding_box()
            assert origin['x']-canvas['x']==pytest.approx(21.7,abs=1)
            assert canvas['y']+canvas['height']-origin['y']==pytest.approx(26.3,abs=1)
            assert page.locator('[data-node-body]').evaluate_all('(es)=>es.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')==world
            page.locator('[data-cad-zoom-in]').click()


def test_shared_primary_links_keep_readable_foreground(context,live_server,workspace_page):
    owner,project,_,_=context
    page=workspace_page(user=owner,project=project)
    page.goto(live_server.url+'/events/')
    links=page.locator('a.ui-primary')
    assert links.count()>0
    for link in links.all():
        assert link.evaluate('e=>getComputedStyle(e).color')=='rgb(255, 255, 255)'


def test_fit_keeps_screen_space_support_and_load_inside_canvas(context,workspace_page):
    from tests.browser.test_cad_core_drawing import move_world
    page,_=open_core(context,workspace_page,nodes=[('node-1',0,0),('node-2',1200,0),('node-3',500,600)],members=[('member-1','node-1','node-2'),('member-2','node-1','node-3'),('member-3','node-2','node-3')])
    page.locator('[data-workspace-tool=SUPPORT]').click();move_world(page,0,0,click=True)
    page.locator('[data-workspace-tool=LOAD]').click();move_world(page,500,600,click=True)
    page.locator('[data-property-fy]').fill('-120');page.locator('[data-property-fy]').press('Tab')
    page.locator('[data-workspace-tool=SELECT]').click()
    for width,height in [(1024,768),(1280,800),(1440,900)]:
        page.set_viewport_size({'width':width,'height':height});page.locator('[data-cad-fit]').click()
        bounds=page.locator('#workspace-canvas').bounding_box()
        for symbol in page.locator('[data-structural-symbol=support],[data-structural-symbol=load]').all():
            box=symbol.bounding_box()
            assert box['y']>=bounds['y']-1,(width,box,bounds)
            assert box['y']+box['height']<=bounds['y']+bounds['height']+1,(width,box,bounds)
        # The original 48→10 CSS-pixel transparent picking segment survives a shorter arrow.
        hit=page.locator('[data-object-kind=NodeLoad] [data-symbol-hit]')
        length=hit.evaluate('e=>{const m=e.getScreenCTM(),a=e.getPointAtLength(0).matrixTransform(m),b=e.getPointAtLength(e.getTotalLength()).matrixTransform(m);return Math.hypot(b.x-a.x,b.y-a.y)}')
        assert length==pytest.approx(38,abs=.1)
