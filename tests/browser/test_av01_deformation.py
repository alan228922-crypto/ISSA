"""Task4 display math/ghost using the real isolated renderer, no Solver recomputation."""
from copy import deepcopy
import math

import pytest
from tests.browser.av01_harness import av01_page,projection_fixture,teaching_fixture,expected_context,mount,load_modules,screenshot

pytestmark=pytest.mark.browser


def direct_render(page,p=None,maximum=1,alpha=None,transform=None):
    p=p or projection_fixture();teaching=teaching_fixture(p,maximum);mount(page,p,teaching)
    return page.evaluate('''({projection,teaching,context,alpha,transform})=>{
      window.directView=av01.buildAnalysisVisualizationView({projection,teachingView:teaching,expectedContext:context});
      const svg=document.querySelector('[data-av01-canvas]');svg.remove();component.destroy();document.querySelector('[data-mount]').append(svg);
      window.directOptions={layers:{loads:false,reactions:false,forceStates:false,deformation:true,original:false},alpha:alpha??directView.deformation?.alpha,viewTransform:transform};
      window.directResult=av01Renderer.renderAnalysisVisualization(svg,directView,directOptions);return directResult;
    }''',{'projection':p,'teaching':teaching,'context':expected_context(p),'alpha':alpha,'transform':transform})


@pytest.mark.parametrize('ux,uy,x,y',[(.5,0,11,20),(0,-.25,10,19.5),(.5,-.25,11,19.5)])
def test_deformation_uses_saved_segment_endpoints(av01_page,ux,uy,x,y):
    p=projection_fixture();p['nodes'][0].update(x_mm=10,y_mm=20,displacement={'ux_mm':ux,'uy_mm':uy});p['nodes'][1].update(x_mm=1010,y_mm=20)
    transform={'scale':10,'originX':0,'originY':50,'panX':100,'panY':40}
    direct_render(av01_page,p,alpha=2,transform=transform)
    value=av01_page.evaluate('(nodes)=>av01Renderer.displacedAnalysisNodes(nodes,2)',p['nodes'])
    assert value[0]['x_mm']==x and value[0]['y_mm']==y
    glyph=av01_page.locator('[data-av01-displaced-node][data-analysis-node="node:n1"]')
    assert float(glyph.get_attribute('cx'))==pytest.approx(x*10+100)
    assert float(glyph.get_attribute('cy'))==pytest.approx((50-y)*10+40)
    assert av01_page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


def test_intermediate_joint_remains_piecewise_straight(av01_page):
    p=projection_fixture();p['nodes'].insert(1,{'analysis_node_id':'node:mid','x_mm':400,'y_mm':0,'displacement':{'ux_mm':.2,'uy_mm':-.2},'support_ids':[],'load_ids':[]})
    p['label_source']['nodes'].append({'id':'mid','label':'中间节点','x_mm':400,'y_mm':0})
    p['segments']=[dict(p['segments'][0],end_analysis_node_id='node:mid'),dict(p['segments'][0],analysis_segment_id='m1:2',start_analysis_node_id='node:mid')]
    p['label_source']['analysis_member_mapping']['m1']=['m1:1','m1:2']
    direct_render(av01_page,p,alpha=2,transform={'scale':.5,'originX':0,'originY':20,'panX':50,'panY':80})
    lines=av01_page.locator('[data-av01-deformed-segment]');assert lines.count()==2
    assert av01_page.locator('[data-av01-displaced-node]').count()==3
    assert float(lines.nth(0).get_attribute('x2'))==pytest.approx(400.4*.5+50)
    assert lines.nth(0).get_attribute('x2')==lines.nth(1).get_attribute('x1')
    assert lines.nth(0).get_attribute('y2')==lines.nth(1).get_attribute('y1')
    assert not av01_page.locator('path[d*="C"],path[d*="Q"]').count()


@pytest.mark.parametrize('maximum,expected',[(1,50),(100,1),(1e-12,10000),(0,1)])
def test_deformation_scale_cases(av01_page,maximum,expected):
    load_modules(av01_page);nodes=projection_fixture()['nodes'];nodes[1]['displacement']['ux_mm']=maximum
    result=av01_page.evaluate('({nodes,maximumMm})=>av01.deformationDisplayScale({nodes,maximumMm})',{'nodes':nodes,'maximumMm':maximum})
    assert result['available'] and result['alpha']==expected
    calibration=av01_page.evaluate('()=>av01.VISUAL_CALIBRATION')
    assert calibration['minAlpha']==1 and calibration['maxAlpha']==10000
    assert calibration['minAlpha']<=result['alpha']<=calibration['maxAlpha']


@pytest.mark.parametrize('defect',['missing_max','bool_max','nan_max','inf_max','negative_max','zero_D','missing_uy','bool_ux','zero_max_nonzero_u','positive_max_allzero'])
def test_missing_or_contradictory_scale_facts_are_unavailable(av01_page,defect):
    load_modules(av01_page);nodes=projection_fixture()['nodes'];maximum=1
    if defect=='missing_max':maximum=None
    elif defect=='bool_max':maximum=True
    elif defect=='nan_max':maximum=float('nan')
    elif defect=='inf_max':maximum=float('inf')
    elif defect=='negative_max':maximum=-1
    elif defect=='zero_D':nodes[1]['x_mm']=0
    elif defect=='missing_uy':nodes[0]['displacement'].pop('uy_mm')
    elif defect=='bool_ux':nodes[0]['displacement']['ux_mm']=False
    elif defect=='zero_max_nonzero_u':maximum=0
    elif defect=='positive_max_allzero':nodes[1]['displacement']['ux_mm']=0
    result=av01_page.evaluate('({nodes,maximumMm})=>av01.deformationDisplayScale({nodes,maximumMm})',{'nodes':nodes,'maximumMm':maximum})
    assert not result['available'] and result['alpha'] is None


@pytest.mark.parametrize('alpha',[1,2,1.0000000000000002])
def test_ghost_and_scale_notice_are_always_present_when_on(av01_page,alpha):
    direct_render(av01_page,alpha=alpha)
    assert av01_page.locator('[data-av01-ghost]').count()==1  # original:false cannot hide it.
    assert av01_page.locator('[data-av01-deformed-segment]').count()==1
    notice=av01_page.locator('[data-av01-scale]');assert notice.is_visible()
    assert float(notice.get_attribute('data-alpha'))==alpha
    text=notice.text_content()
    if alpha==1:assert '倍率 ×1' in text
    else:
        assert '已放大' in text and '实际分析位移' in text
        if alpha<1.0001:assert '1.0000000000000002' in text


def test_tiny_nonzero_deformation_is_not_called_zero(av01_page):
    p=projection_fixture();p['nodes'][1]['displacement']['ux_mm']=1e-12;direct_render(av01_page,p,maximum=1e-12)
    text=av01_page.locator('[data-av01-scale]').text_content()
    assert '显示放大上限' in text and '均为 0' not in text
    assert float(av01_page.locator('[data-av01-scale]').get_attribute('data-alpha'))==10000


def test_zero_displacement_is_explicit_and_keeps_ghost(av01_page):
    p=projection_fixture();p['nodes'][1]['displacement']['ux_mm']=0;direct_render(av01_page,p,maximum=0)
    assert '本次节点位移均为 0 mm' in av01_page.locator('[data-av01-scale]').text_content()
    assert av01_page.locator('[data-av01-ghost]').count()==1


def test_missing_matching_m9_maximum_never_uses_a_frontend_node_max(av01_page):
    p=projection_fixture();mount(av01_page,p)
    value=av01_page.evaluate('({projection,context})=>{const v=av01.buildAnalysisVisualizationView({projection,expectedContext:context});return {available:v.available,deformation:v.deformation}}',{'projection':p,'context':expected_context(p)})
    assert value['available'] and not value['deformation']['available']
    teaching=teaching_fixture(p);teaching['runId']=999
    value=av01_page.evaluate('({projection,context,teaching})=>av01.buildAnalysisVisualizationView({projection,expectedContext:context,teachingView:teaching}).deformation',{'projection':p,'context':expected_context(p),'teaching':teaching})
    assert not value['available']


def test_huge_display_arithmetic_cannot_emit_invalid_svg(av01_page):
    p=projection_fixture();p['nodes'][0].update(x_mm=1e308,displacement={'ux_mm':1e308,'uy_mm':0})
    direct_render(av01_page,p,maximum=1e308,alpha=10000)
    assert not av01_page.locator('[data-av01-deformed-segment]').count()
    text=av01_page.locator('[data-av01-canvas]').inner_html();assert 'Infinity' not in text and 'NaN' not in text
    assert '暂不可用' in av01_page.locator('[data-av01-scale]').text_content()


def test_pan_zoom_display_does_not_change_amplification_or_saved_values(av01_page):
    direct_render(av01_page)
    before=av01_page.locator('[data-av01-scale]').get_attribute('data-alpha')
    av01_page.evaluate('()=>{const t=directResult.transform;directOptions.viewTransform={...t,scale:t.scale*1.5,panX:t.panX+17,panY:t.panY-9};directResult=av01Renderer.renderAnalysisVisualization(document.querySelector("[data-av01-canvas]"),directView,directOptions)}')
    assert av01_page.locator('[data-av01-scale]').get_attribute('data-alpha')==before
    assert av01_page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_preliminary_deformation_fit_and_notice_three_sizes(av01_page,width,height):
    av01_page.set_viewport_size({'width':width,'height':height});direct_render(av01_page)
    assert av01_page.locator('[data-av01-scale]').is_visible()
    assert av01_page.locator('[data-av01-ghost]').count()==1
    assert av01_page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth')
    bounds=av01_page.locator('[data-av01-canvas]').bounding_box();assert bounds and bounds['width']>0
    for line in av01_page.locator('[data-av01-original-segment],[data-av01-deformed-segment]').all():
        for key,limit in [('x1',bounds['width']),('x2',bounds['width']),('y1',bounds['height']),('y2',bounds['height'])]:assert 0<=float(line.get_attribute(key))<=limit
    screenshot(av01_page,f'task4-deformation-{width}x{height}')


def test_collinear_original_ghost_remains_visually_distinguishable(av01_page):
    import base64
    direct_render(av01_page)
    samples=av01_page.evaluate('''()=>{const line=document.querySelector('[data-av01-original-segment]'),rect=document.querySelector('[data-av01-canvas]').getBoundingClientRect();
      const start=Number(line.getAttribute('x1')),end=Number(line.getAttribute('x2')),y=Number(line.getAttribute('y1'));
      return Array.from({length:20},(_,i)=>{const p=new DOMPoint(start+(end-start)*(.2+i*.02),y).matrixTransform(line.getScreenCTM());return {x:p.x-rect.left,y:p.y-rect.top}})}''')
    png=base64.b64encode(av01_page.locator('[data-av01-canvas]').screenshot()).decode()
    visible=av01_page.evaluate('''async({png,samples})=>{const bitmap=await createImageBitmap(await(await fetch('data:image/png;base64,'+png)).blob());
      const canvas=new OffscreenCanvas(bitmap.width,bitmap.height),ctx=canvas.getContext('2d');ctx.drawImage(bitmap,0,0);
      return samples.some(p=>[-2,2].some(d=>{const pixel=ctx.getImageData(Math.round(p.x),Math.floor(p.y)+d,1,1).data;
        return pixel[0]>140&&pixel[0]<230&&pixel[2]-pixel[0]>=12}))}''',{'png':png,'samples':samples})
    assert visible, 'Original dashed ghost is fully covered by the collinear primary shape'
