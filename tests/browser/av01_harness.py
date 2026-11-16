"""Test-only isolated carrier. Real SVG comes only from production renderer modules."""
from copy import deepcopy
import json
from pathlib import Path

import pytest


@pytest.fixture
def av01_page(live_server):
    from playwright.sync_api import sync_playwright
    runtime = sync_playwright().start()
    browser = runtime.chromium.launch()
    page = browser.new_page(viewport={'width': 1280, 'height': 800}, has_touch=True)
    # This intercepted test document is not a production URL or a permission bypass.
    html = '''<!doctype html><meta charset="utf-8"><title>AV-01 独立组件测试</title>
    <link rel="stylesheet" href="/static/projects/workspace/analysis-visualization.css">
    <style>body{margin:0;padding:12px;font-family:system-ui;background:#f7f9fc}h1{font-size:16px;margin:0 0 8px}.carrier{max-width:1400px;margin:auto}</style>
    <main class="carrier"><h1 data-case-origin>受控保存事实 · 独立 Renderer 验证（未接入正式 Results）</h1><div data-mount></div></main>'''
    page.route('**/__av01_component__', lambda route: route.fulfill(status=200, content_type='text/html', body=html))
    page.route('**/favicon.ico', lambda route: route.fulfill(status=204, body=''))
    page.goto(live_server.url + '/__av01_component__')
    yield page
    browser.close()
    runtime.stop()


def projection_fixture():
    """Controlled phase1 DTO, not claimed to be a newly solved model."""
    return {
        'schema_version':'analysis-visualization-v1','status':'READY',
        'provenance':{'project_id':1,'analysis_run_id':11,'model_revision_id':7,'source_draft_version':2,
          'physical_snapshot_schema_version':'physical-snapshot-v2','input_schema_version':'truss2d-input-v1',
          'result_schema_version':'truss2d-result-v1','model_hash':'a'*64,'input_hash':'b'*64,'readonly':True},
        'capabilities':{k:{'status':'READY','reason':None} for k in ['geometry','loads','reactions','axial_forces','deformation']},
        'label_source':{'nodes':[{'id':'n1','label':'左支座','x_mm':0,'y_mm':0},{'id':'n2','label':'右节点','x_mm':1000,'y_mm':0}],
          'physical_members':[{'id':'m1','label':'主杆','start_node_id':'n1','end_node_id':'n2'}],
          'connections':[],'supports':[{'id':'s1'},{'id':'s2'}],
          'node_loads':[{'id':'l1','label':'外力'}],'analysis_member_mapping':{'m1':['m1:1']}},
        'nodes':[{'analysis_node_id':'node:n1','source_ref':{'kind':'NODE','identity':'n1','endpoint':None},'x_mm':0,'y_mm':0,'displacement':{'ux_mm':0,'uy_mm':0},'support_ids':['s1'],'load_ids':[]},
          {'analysis_node_id':'node:n2','source_ref':{'kind':'NODE','identity':'n2','endpoint':None},'x_mm':1000,'y_mm':0,'displacement':{'ux_mm':1,'uy_mm':0},'support_ids':['s2'],'load_ids':['l1']}],
        'segments':[{'analysis_segment_id':'m1:1','start_analysis_node_id':'node:n1','end_analysis_node_id':'node:n2','physical_member_id':'m1','axial_force_N':100}],
        'supports':[{'support_id':'s1','analysis_node_id':'node:n1','support_type':'PINNED','restrained_axis':None},{'support_id':'s2','analysis_node_id':'node:n2','support_type':'ROLLER','restrained_axis':'Y'}],
        'loads':[{'load_id':'l1','analysis_node_id':'node:n2','fx_N':100,'fy_N':0}],
        'reactions':[{'analysis_node_id':'node:n1','rx_N':84,'ry_N':-326,'support_ids':['s1']},{'analysis_node_id':'node:n2','rx_N':0,'ry_N':0,'support_ids':['s2']}],
    }


def expected_context(projection):
    p=projection['provenance']
    return {dest:p[src] for dest,src in [('projectId','project_id'),('runId','analysis_run_id'),('revisionId','model_revision_id'),('sourceDraftVersion','source_draft_version'),('modelHash','model_hash'),('inputHash','input_hash'),('inputSchemaVersion','input_schema_version'),('resultSchemaVersion','result_schema_version')]}


def teaching_fixture(projection, maximum=1):
    p=projection['provenance']
    return {'available':True,'projectId':p['project_id'],'runId':p['analysis_run_id'],'sourceDraftVersion':p['source_draft_version'],
      'members':[{'key':row['id'],'actualState':'TENSION','segments':[{'analysis_member_id':s['analysis_segment_id'],'axial_force_N':s['axial_force_N'],'teaching_state':'TENSION'} for s in projection['segments'] if s['physical_member_id']==row['id']]} for row in projection['label_source']['physical_members']],
      'displacement':{'available':True,'maximumMm':maximum,'candidates':[{'id':projection['nodes'][-1]['analysis_node_id']}]}}


def load_modules(page):
    result=page.evaluate('''async()=>{try{window.av01=await import('/static/projects/workspace/analysis-visualization.js');window.av01Renderer=await import('/static/projects/workspace/analysis-visualization-renderer.js');return {ready:true}}catch(e){return {ready:false,message:String(e)}}}''')
    assert result['ready'], 'production AV-01 renderer unavailable: '+result.get('message','')


def mount(page, projection=None, teaching=None, context=None):
    projection=projection if projection is not None else projection_fixture()
    load_modules(page)
    page.evaluate('''({projection,teaching,context})=>{
      window.inputFacts=structuredClone(projection);window.beforeFacts=JSON.stringify(window.inputFacts);
      window.component?.destroy();document.querySelector('[data-mount]').replaceChildren();
      window.component=av01.createAnalysisVisualization({root:document.querySelector('[data-mount]')});
      component.setSelection({runId:projection.provenance.analysis_run_id,epoch:1,metadata:{runNumber:1}});
      component.useProjection({kind:'READY',runId:projection.provenance.analysis_run_id,epoch:1,expectedContext:context,projection:window.inputFacts});
      if(teaching)component.useTeachingView(teaching,1);
    }''',{'projection':projection,'teaching':teaching,'context':context if context is not None else expected_context(projection)})
    page.locator('[data-av01-canvas]').wait_for()
    return projection


def screenshot(page, name):
    target=Path('.superpowers/sdd/2026-10-27-av01-analysis-visualization/screenshots');target.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(target/(name+'.png')),full_page=True)


def follow_saved_member_link(page, link):
    """Use the public M9 link; prove it focuses saved evidence, never Draft."""
    from playwright.sync_api import expect
    expect(page.locator('[data-av01-root]')).to_have_attribute('data-av01-availability','READY')
    draft=page.locator('#workspace-canvas')
    before=draft.locator('[data-selected=true]').evaluate_all('(els)=>els.map(el=>el.dataset.clientKey).sort()')
    dirty=page.locator('#workspace-save-status').text_content()
    label=link.inner_text()
    link.click()
    canvas=page.locator('[data-av01-canvas]');expect(canvas).to_be_visible();expect(canvas).to_be_focused()
    inspector=page.locator('[data-av01-evidence]');expect(inspector).to_be_visible()
    selected=page.locator('[data-av01-object-list] [aria-pressed=true]')
    expect(selected).to_have_attribute('data-object-kind','ANALYSIS_SEGMENT')
    member=inspector.locator(':scope > [data-av01-field=member] [data-av01-value]').inner_text()
    assert label==member or label.startswith(member+'：')
    expect(draft).not_to_be_visible()
    assert draft.locator('[data-selected=true]').evaluate_all('(els)=>els.map(el=>el.dataset.clientKey).sort()')==before
    assert page.locator('#workspace-save-status').text_content()==dirty
    return inspector
