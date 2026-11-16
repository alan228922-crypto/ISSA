"""Phase2 Task5 only: layers/readable facts. Object Evidence/Hover remains Task6."""
from copy import deepcopy

import pytest
from tests.browser.av01_harness import av01_page,projection_fixture,teaching_fixture,expected_context,mount,screenshot

pytestmark=pytest.mark.browser


def layer(page,name):
    target=page.locator(f'input[data-av01-layer="{name}"]')
    assert target.count()==1, f'Task5 native layer control {name} missing'
    return target


def reset_selection(page,p,teaching,epoch):
    page.evaluate('''({p,teaching,context,epoch})=>{component.setSelection({runId:p.provenance.analysis_run_id,epoch,metadata:{runNumber:1}});
      component.useProjection({kind:'READY',runId:p.provenance.analysis_run_id,epoch,projection:p,expectedContext:context});component.useTeachingView(teaching,epoch)}''',{'p':p,'teaching':teaching,'context':expected_context(p),'epoch':epoch})


def test_layer_defaults_toggles_and_reset_are_transient(av01_page):
    p=projection_fixture();t=teaching_fixture(p);mount(av01_page,p,t)
    assert av01_page.get_by_role('checkbox').count()==4
    for key,value in [('loads',True),('reactions',True),('forceStates',True),('deformation',False)]:assert layer(av01_page,key).is_checked()==value
    layer(av01_page,'reactions').uncheck();assert not av01_page.locator('[data-av01-reaction]').count()
    assert layer(av01_page,'loads').is_checked() and layer(av01_page,'forceStates').is_checked()
    layer(av01_page,'deformation').check();assert av01_page.locator('[data-av01-ghost]').count()==1
    reset_selection(av01_page,p,t,2)
    assert layer(av01_page,'reactions').is_checked() and not layer(av01_page,'deformation').is_checked()
    assert not av01_page.locator('[data-av01-deformed-segment]').count()
    layer(av01_page,'loads').uncheck();mount(av01_page,p,t)
    assert layer(av01_page,'loads').is_checked()
    assert av01_page.evaluate('()=>localStorage.length')==0
    assert av01_page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')
    assert not av01_page.get_by_role('checkbox',name='原始结构',exact=True).count()


@pytest.mark.parametrize('name',['loads','reactions','forceStates','deformation'])
def test_unavailable_layer_is_disabled_with_a_safe_reason(av01_page,name):
    p=projection_fixture();t=teaching_fixture(p)
    if name=='forceStates':t['members']=[]
    else:
        p['capabilities'][name]={'status':'UNAVAILABLE','reason':'PRIVATE_REASON_NOT_FOR_STUDENT'}
        if name=='loads':p['loads']=[]
        elif name=='reactions':p['reactions']=[]
        elif name=='deformation':p['nodes'][1]['displacement']=None
    mount(av01_page,p,t);control=layer(av01_page,name)
    assert control.is_disabled() and not control.is_checked()
    assert '暂不可用' in av01_page.locator(f'[data-av01-layer-reason="{name}"]').inner_text()
    assert 'PRIVATE_REASON_NOT_FOR_STUDENT' not in av01_page.locator('[data-mount]').inner_text()
    assert av01_page.locator('[data-av01-original-segment]').count()==1


def test_zero_load_ready_is_an_empty_layer_not_unavailable(av01_page):
    p=projection_fixture();p['loads']=[];p['label_source']['node_loads']=[];p['nodes'][1]['load_ids']=[]
    mount(av01_page,p,teaching_fixture(p))
    assert layer(av01_page,'loads').is_enabled() and layer(av01_page,'loads').is_checked()
    assert av01_page.locator('[data-av01-load]').count()==0
    av01_page.locator('[data-av01-legend-details] summary').click()
    assert '未保存外部荷载' in av01_page.locator('[data-av01-legend]').inner_text()


def test_keyboard_tab_space_uses_native_controls_and_keeps_focus(av01_page):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));layer(av01_page,'loads')
    av01_page.get_by_role('button',name='适合视窗',exact=True).focus()
    for name in ['loads','reactions','forceStates','deformation']:
        av01_page.keyboard.press('Tab');control=layer(av01_page,name)
        assert control.evaluate('(el)=>el===document.activeElement')
        before=control.is_checked();av01_page.keyboard.press('Space');assert control.is_checked()!=before
        assert control.evaluate('(el)=>el===document.activeElement')
        assert control.evaluate('(el)=>getComputedStyle(el).outlineStyle')!='none'
        av01_page.keyboard.press('Space');assert control.is_checked()==before


def test_force_layer_never_classifies_raw_axial_force_when_m9_is_absent(av01_page):
    p=projection_fixture();mount(av01_page,p)
    assert layer(av01_page,'forceStates').is_disabled()
    assert layer(av01_page,'deformation').is_disabled()
    assert av01_page.locator('[data-av01-original-segment]').get_attribute('stroke')=='#475569'
    assert layer(av01_page,'reactions').is_enabled()
    assert av01_page.locator('[data-av01-reaction]').count()==2


def test_mixed_member_keeps_distinct_saved_segment_states(av01_page):
    p=projection_fixture();p['nodes'].insert(1,{'analysis_node_id':'node:mid','source_ref':{'kind':'NODE','identity':'mid','endpoint':None},'x_mm':400,'y_mm':0,'displacement':{'ux_mm':.2,'uy_mm':0},'support_ids':[],'load_ids':[]})
    p['label_source']['nodes'].append({'id':'mid','label':'中间节点','x_mm':400,'y_mm':0})
    p['segments']=[dict(p['segments'][0],end_analysis_node_id='node:mid'),dict(p['segments'][0],analysis_segment_id='m1:2',start_analysis_node_id='node:mid',axial_force_N=-50)]
    p['label_source']['analysis_member_mapping']['m1']=['m1:1','m1:2'];t=teaching_fixture(p);t['members'][0]['actualState']='MIXED';t['members'][0]['segments'][1]['teaching_state']='COMPRESSION'
    mount(av01_page,p,t);assert layer(av01_page,'forceStates').is_enabled()
    lines=av01_page.locator('[data-av01-original-segment]')
    assert [x.get_attribute('stroke') for x in lines.all()]==['#b91c1c','#1d4ed8']
    assert lines.nth(1).get_attribute('stroke-dasharray')=='10 5'
    layer(av01_page,'forceStates').uncheck();assert all(x.get_attribute('stroke')=='#475569' for x in lines.all())
    layer(av01_page,'deformation').check();assert av01_page.locator('[data-av01-ghost]').count()==1
    layer(av01_page,'forceStates').check()
    assert [x.get_attribute('stroke') for x in av01_page.locator('[data-av01-deformed-segment]').all()]==['#b91c1c','#1d4ed8']
    assert av01_page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


def test_mismatched_segment_evidence_does_not_color_the_structure(av01_page):
    p=projection_fixture();t=teaching_fixture(p);t['members'][0]['segments'][0]['axial_force_N']=999
    mount(av01_page,p,t)
    assert layer(av01_page,'forceStates').is_disabled()
    assert av01_page.locator('[data-av01-original-segment]').get_attribute('stroke')=='#475569'


def test_load_rows_stay_separate_and_force_anchors_stay_undeformed(av01_page):
    p=projection_fixture();p['loads'].append({'load_id':'l2','analysis_node_id':'node:n2','fx_N':-50,'fy_N':10});p['label_source']['node_loads'].append({'id':'l2','label':'第二笔外力'});p['nodes'][1]['load_ids'].append('l2')
    mount(av01_page,p,teaching_fixture(p));assert layer(av01_page,'loads').is_enabled()
    assert av01_page.locator('[data-av01-load]').count()==3
    before=av01_page.locator('[data-av01-original-segment]').get_attribute('x2')
    layer(av01_page,'deformation').check()
    assert av01_page.locator('[data-av01-original-segment]').get_attribute('x2')==before  # toggling does not auto-Fit.
    assert av01_page.locator('[data-av01-deformed-segment]').get_attribute('x2')!=before
    fx=av01_page.locator('[data-av01-load][data-load-id=l1][data-component=Fx] line')
    assert fx.get_attribute('x2')==before
    layer(av01_page,'reactions').uncheck();assert av01_page.locator('[data-av01-load]').count()==3
    layer(av01_page,'loads').uncheck();assert av01_page.locator('[data-av01-load]').count()==0
    av01_page.get_by_role('button',name='适合视窗',exact=True).click()
    assert av01_page.locator('[data-av01-original-segment]').get_attribute('x2')!=before


def test_layers_pan_zoom_never_write_or_change_saved_facts(av01_page):
    writes=[];av01_page.on('request',lambda req:writes.append(req.method) if req.method not in ['GET','HEAD'] else None)
    av01_page.evaluate("()=>{Storage.prototype.setItem=()=>{throw new Error('unexpected persistence')}}")
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));layer(av01_page,'deformation').check()
    alpha=av01_page.locator('[data-av01-scale]').get_attribute('data-alpha')
    av01_page.get_by_role('button',name='放大',exact=True).click();av01_page.get_by_role('button',name='缩小',exact=True).click()
    rect=av01_page.locator('[data-av01-canvas]').bounding_box();x=rect['x']+rect['width']/2;y=rect['y']+rect['height']/2
    av01_page.mouse.move(x,y);av01_page.mouse.down();av01_page.mouse.move(x+20,y+14);av01_page.mouse.up()
    assert av01_page.locator('[data-av01-scale]').get_attribute('data-alpha')==alpha
    assert not writes and av01_page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')
    assert not av01_page.locator('[data-cad-node-grip],input[type=text]').count()
    av01_page.locator('[data-av01-values] summary').click()
    assert '显示倍率原值' in av01_page.locator('[data-av01-exact-scale]').inner_text()


def test_all_supplied_maximum_candidates_are_preserved_without_a_winner(av01_page):
    p=projection_fixture();p['nodes'][1]['displacement']['ux_mm']=0;t=teaching_fixture(p,0);t['displacement']['candidates']=[{'id':'node:n1'},{'id':'node:n2'}]
    mount(av01_page,p,t);layer(av01_page,'deformation').check()
    assert av01_page.locator('[data-av01-maximum]').count()==2
    av01_page.locator('[data-av01-legend-details] summary').click()
    assert '最大位移候选' in av01_page.locator('[data-av01-legend]').inner_text()
    assert '均为 0 mm' in av01_page.locator('[data-av01-scale]').text_content()


def test_two_instances_do_not_share_layers_or_svg_resources(av01_page):
    p=projection_fixture();t=teaching_fixture(p);mount(av01_page,p,t);layer(av01_page,'loads')
    av01_page.evaluate('''({p,t,context})=>{const second=document.createElement('div');second.dataset.secondMount='';document.querySelector('main').append(second);
      window.secondComponent=av01.createAnalysisVisualization({root:second});secondComponent.setSelection({runId:p.provenance.analysis_run_id,epoch:1});secondComponent.useProjection({kind:'READY',runId:p.provenance.analysis_run_id,epoch:1,projection:p,expectedContext:context});secondComponent.useTeachingView(t,1)}''',{'p':p,'t':t,'context':expected_context(p)})
    av01_page.locator('[data-mount] [data-av01-layer=loads]').uncheck()
    assert av01_page.locator('[data-second-mount] [data-av01-layer=loads]').is_checked()
    ids=av01_page.locator('[id]').evaluate_all('(els)=>els.map(e=>e.id)');assert len(ids)==len(set(ids))


def test_hidden_component_update_does_not_steal_other_tab_focus(av01_page):
    p=projection_fixture();t=teaching_fixture(p);mount(av01_page,p,t);layer(av01_page,'loads')
    av01_page.evaluate("()=>{const b=document.createElement('button');b.textContent='另一个标签页（测试载体）';b.id='other-tab';document.body.append(b);b.focus();document.querySelector('[data-mount]').hidden=true}")
    reset_selection(av01_page,p,t,2)
    assert av01_page.locator('#other-tab').evaluate('(el)=>el===document.activeElement')
    av01_page.locator('[data-mount]').evaluate('(el)=>el.hidden=false')
    av01_page.wait_for_function("()=>document.querySelectorAll('[data-av01-original-segment]').length===1")
    assert av01_page.locator('#other-tab').evaluate('(el)=>el===document.activeElement')


def test_stale_component_delivery_cannot_override_a_new_local_run_epoch(av01_page):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));layer(av01_page,'loads')
    newer=deepcopy(p);newer['provenance']['analysis_run_id']=12;newer['reactions'][0]['rx_N']=-21
    reset_selection(av01_page,newer,teaching_fixture(newer),2)
    av01_page.evaluate('''({p,context})=>component.useProjection({kind:'READY',runId:p.provenance.analysis_run_id,epoch:1,projection:p,expectedContext:context})''',{'p':p,'context':expected_context(p)})
    assert av01_page.locator('[data-av01-reaction][data-component=Rx]').get_attribute('data-value')=='-21'


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_layer_controls_and_combined_renderer_three_sizes(av01_page,width,height):
    av01_page.set_viewport_size({'width':width,'height':height});p=projection_fixture();p['nodes'][1]['displacement']['uy_mm']=-.5;t=teaching_fixture(p,1.118033988749895)
    mount(av01_page,p,t);layer(av01_page,'deformation').check();av01_page.get_by_role('button',name='适合视窗',exact=True).click()
    assert av01_page.locator('[data-av01-ghost]').count()==1
    assert av01_page.get_by_role('checkbox').count()==4
    assert av01_page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth')
    svg=av01_page.locator('[data-av01-canvas]').bounding_box();assert svg['y']+svg['height']<=height
    screenshot(av01_page,f'task5-combined-{width}x{height}')


def test_load_numeric_fallback_preserves_each_exact_row_and_zero(av01_page):
    p=projection_fixture();p['loads'][0]['fx_N']=1e-12
    p['loads'].append({'load_id':'l2','analysis_node_id':'node:n2','fx_N':0,'fy_N':-3.141592653589793})
    p['label_source']['node_loads'].append({'id':'l2','label':'第二笔荷载'})
    mount(av01_page,p,teaching_fixture(p));av01_page.locator('[data-av01-values] summary').click()
    rows=av01_page.locator('[data-av01-load-row]')
    assert rows.count()==2
    assert rows.nth(0).locator('td').all_text_contents()==['1e-12','0']
    assert rows.nth(1).locator('td').all_text_contents()==['0','-3.141592653589793']
    assert '第二笔荷载' in rows.nth(1).inner_text()


def test_supplied_maximum_marker_tracks_primary_shape_even_when_deformation_is_off(av01_page):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p))
    marker=av01_page.locator('[data-av01-maximum]');assert marker.count()==1
    original=av01_page.locator('[data-av01-original-segment]')
    assert marker.get_attribute('cx')==original.get_attribute('x2')
    assert marker.get_attribute('cy')==original.get_attribute('y2')
    av01_page.locator('[data-av01-legend-details] summary').click()
    assert '最大位移候选' in av01_page.locator('[data-av01-legend]').inner_text()
    layer(av01_page,'deformation').check()
    assert marker.get_attribute('cx')==av01_page.locator('[data-av01-deformed-segment]').get_attribute('x2')
    layer(av01_page,'deformation').uncheck()
    assert marker.get_attribute('cx')==original.get_attribute('x2')


def test_crowded_force_labels_do_not_hide_under_scale_or_shape_notices(av01_page):
    p=projection_fixture()
    for index in range(15):
        key=f'additional-load-{index}'
        p['loads'].append({'load_id':key,'analysis_node_id':'node:n2','fx_N':20+index,'fy_N':0})
        p['label_source']['node_loads'].append({'id':key,'label':f'独立荷载 {index+1}'})
    mount(av01_page,p,teaching_fixture(p));layer(av01_page,'deformation').check()
    overlaps=av01_page.locator('[data-av01-canvas]').evaluate('''svg=>{
      const rect=svg.querySelector('[data-av01-scale] rect').getBBox();
      const title=svg.querySelector('[data-av01-shape-legend]').getBBox();
      const intersects=(a,b)=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;
      return [...svg.querySelectorAll('[data-av01-load-label],[data-av01-reaction-label]')].filter(el=>{
        const box=el.getBBox();return intersects(box,rect)||intersects(box,title);
      }).map(el=>el.textContent);
    }''')
    assert not overlaps
    assert av01_page.locator('[data-av01-overflow]').is_visible()
    av01_page.locator('[data-av01-values] summary').click()
    assert av01_page.locator('[data-av01-load-row]').count()==16


def test_clear_removes_old_run_candidate_names_from_the_legend(av01_page):
    p=projection_fixture();p['label_source']['nodes'][1]['label']='旧分析专属候选名称'
    mount(av01_page,p,teaching_fixture(p));layer(av01_page,'deformation').check()
    av01_page.locator('[data-av01-legend-details] summary').click()
    assert '旧分析专属候选名称' in av01_page.locator('[data-av01-legend]').inner_text()
    av01_page.evaluate('()=>component.setSelection({runId:12,epoch:2})')
    assert '旧分析专属候选名称' not in av01_page.locator('[data-av01-legend]').text_content()
    assert not av01_page.locator('[data-av01-maximum]').count()


@pytest.mark.parametrize('finish',['move','cancel'])
def test_selection_reset_cancels_old_pan_capture_and_pending_frame(av01_page,finish):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p))
    rect=av01_page.locator('[data-av01-canvas]').bounding_box();x=rect['x']+rect['width']/2;y=rect['y']+rect['height']/2
    av01_page.mouse.move(x,y);av01_page.mouse.down()
    newer=deepcopy(p);newer['provenance']['analysis_run_id']=12
    for node in newer['nodes']:node['x_mm']=node['x_mm']*2+5000
    reset_selection(av01_page,newer,teaching_fixture(newer),2)
    before=av01_page.locator('[data-av01-original-segment]').get_attribute('x1')
    if finish=='move':av01_page.mouse.move(x+35,y+20)
    else:av01_page.locator('[data-av01-canvas]').dispatch_event('pointercancel',{'pointerId':1})
    av01_page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    av01_page.mouse.up()
    assert av01_page.locator('[data-av01-original-segment]').get_attribute('x1')==before

# Phase3 Task6: changing selected-object source or skipping hover cleanup must fail these.
from copy import deepcopy as clone_evidence
from playwright.sync_api import expect as evidence_expect


def object_button(page,kind,identity):
    match=page.locator(f'[data-av01-object-list] button[data-object-kind="{kind}"]')
    # Identity is used only as an internal selector, never as an expected student label.
    found=match.evaluate_all('(els,id)=>els.filter(el=>el.dataset.objectId===id).length',identity)
    assert found==1, f'Object Evidence list entry missing for {kind}'
    return page.locator(f'[data-av01-object-list] button[data-object-kind="{kind}"]').nth(match.evaluate_all('(els,id)=>els.findIndex(el=>el.dataset.objectId===id)',identity))


def choose_evidence(page,kind,identity):
    button=object_button(page,kind,identity)
    listing=page.locator('[data-av01-object-list]')
    if listing.evaluate('(el)=>el.tagName==="DETAILS"&&!el.open'):listing.locator('summary').click()
    button.click()
    return page.locator('[data-av01-evidence]')


def evidence_value(panel,key):
    return panel.locator(f'[data-av01-field="{key}"] [data-av01-value]').first.inner_text()


def hit_object(page,kind,identity):
    targets=page.locator(f'[data-av01-target][data-object-kind="{kind}"]')
    index=targets.evaluate_all('(els,id)=>els.findIndex(el=>el.dataset.objectId===id)',identity)
    assert index>=0, f'Readonly target missing for {kind}'
    return targets.nth(index)


def clock_hover(page,kind,identity):
    target=hit_object(page,kind,identity)
    page.locator('[data-av01-canvas]').scroll_into_view_if_needed()
    page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    from datetime import datetime, timezone, timedelta
    start=datetime(2026,11,13,tzinfo=timezone.utc)
    page.clock.install(time=start)
    page.clock.pause_at(start+timedelta(seconds=1))
    # The support group includes a display leader; its bounding-box center
    # can be empty space. Hover the actual public symbol, not that empty box.
    symbol=target.locator('polygon,rect').first if kind=='SUPPORT' else target
    box=symbol.bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
    assert page.evaluate('''({x,y,kind,id})=>{const t=document.elementFromPoint(x,y)?.closest('[data-av01-target]');return t?.dataset.objectKind===kind&&t?.dataset.objectId===id}''',{'x':x,'y':y,'kind':kind,'id':identity})
    page.mouse.move(x,y)
    return target


@pytest.mark.parametrize('kind,identity,expected',[('ANALYSIS_NODE','node:n2',{'X':'1000 mm','Y':'0 mm','ux':'1 mm','uy':'0 mm','magnitude':'1 mm'}),('SUPPORT','s1',{'Rx':'+84 N','Ry':'-326 N','type':'铰支座','restrictions':'X、Y'}),('ANALYSIS_SEGMENT','m1:1',{'N':'+100 N','state':'受拉'})])
def test_selected_object_evidence_is_snapshot_bound(av01_page,kind,identity,expected):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));layer(av01_page,'deformation').check()
    panel=choose_evidence(av01_page,kind,identity)
    for key,value in expected.items():assert evidence_value(panel,key)==value
    panel.locator('[data-av01-exact] summary').click()
    assert '完整保存值' in panel.inner_text()
    assert av01_page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


def test_support_evidence_retains_node_aggregate_without_force_sharing(av01_page):
    p=projection_fixture();p['supports'].append(dict(p['supports'][0],support_id='s3'));p['label_source']['supports'].append({'id':'s3','label':'第二支座'})
    p['nodes'][0]['support_ids'].append('s3');p['reactions'][0]['support_ids'].append('s3')
    mount(av01_page,p,teaching_fixture(p));panel=choose_evidence(av01_page,'SUPPORT','s3')
    assert evidence_value(panel,'Rx')=='+84 N' and evidence_value(panel,'Ry')=='-326 N'
    assert '节点合计' in panel.inner_text() and '第二支座' in panel.inner_text()
    assert av01_page.locator('[data-av01-reaction][data-component=Rx]').count()==1


def mixed_evidence_fixture():
    p=projection_fixture();p['nodes'].insert(1,{'analysis_node_id':'node:mid','source_ref':{'kind':'NODE','identity':'mid','endpoint':None},'x_mm':400,'y_mm':0,'displacement':{'ux_mm':.2,'uy_mm':0},'support_ids':[],'load_ids':[]})
    p['label_source']['nodes'].append({'id':'mid','label':'中间节点'})
    p['segments']=[dict(p['segments'][0],end_analysis_node_id='node:mid'),dict(p['segments'][0],analysis_segment_id='m1:2',start_analysis_node_id='node:mid',axial_force_N=-50)]
    p['label_source']['analysis_member_mapping']['m1']=['m1:1','m1:2'];t=teaching_fixture(p);t['members'][0]['actualState']='MIXED';t['members'][0]['segments'][1]['teaching_state']='COMPRESSION';t['members'][0]['comparisonStatus']='NOT_COMPARABLE'
    return p,t


def test_mixed_segment_evidence_preserves_every_sibling_and_existing_comparison(av01_page):
    p,t=mixed_evidence_fixture();mount(av01_page,p,t);panel=choose_evidence(av01_page,'ANALYSIS_SEGMENT','m1:2')
    assert evidence_value(panel,'N')=='-50 N' and evidence_value(panel,'state')=='受压'
    assert '不同' in panel.inner_text() and '不能用单一类别直接对照' in panel.inner_text()
    rows=panel.locator('[data-av01-sibling]');assert rows.count()==2
    assert '+100 N' in rows.nth(0).inner_text() and '-50 N' in rows.nth(1).inner_text()
    assert '平均' not in panel.inner_text()


@pytest.mark.parametrize('legacy',[False,True])
def test_no_internal_identity_in_visible_or_accessible_copy(av01_page,legacy):
    import json
    p=projection_fixture()
    if legacy:
        p=json.loads(json.dumps(p).replace('node:n1','free:m1:START').replace('node:n2','free:m1:END'))
        p['provenance']['physical_snapshot_schema_version']='physical-snapshot-v1'
    p=json.loads(json.dumps(p).replace('m1','member:private:9d624a77-aaaa-bbbb-cccc-123456789000'))
    t=teaching_fixture(p);mount(av01_page,p,t)
    node_id=p['nodes'][0]['analysis_node_id'];panel=choose_evidence(av01_page,'ANALYSIS_NODE',node_id);panel.locator('[data-av01-exact] summary').click()
    text=av01_page.locator('[data-mount]').inner_text()
    accessible=av01_page.locator('[aria-label],[title]').evaluate_all('(els)=>els.map(el=>[el.getAttribute("aria-label"),el.getAttribute("title")].join(" ")).join(" ")')
    for raw in ['member:private','9d624a77-aaaa-bbbb-cccc-123456789000','node:n1','free:','a'*64,'b'*64]:assert raw not in text+accessible
    assert av01_page.locator('[data-av01-object-list] button').count()==5


def test_keyboard_touch_and_canvas_share_one_object_evidence_selection(av01_page):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));panel=choose_evidence(av01_page,'ANALYSIS_NODE','node:n2');expected=panel.inner_text()
    choose_evidence(av01_page,'SUPPORT','s1')
    button=object_button(av01_page,'ANALYSIS_NODE','node:n2');button.focus();av01_page.keyboard.press('Enter');assert panel.inner_text()==expected
    choose_evidence(av01_page,'SUPPORT','s1');hit_object(av01_page,'ANALYSIS_NODE','node:n2').tap()
    assert panel.inner_text()==expected and button.get_attribute('aria-pressed')=='true'
    assert av01_page.locator('[data-av01-selected]').count()>0
    assert not av01_page.locator('[data-cad-node-grip],input[type=text]').count()


def test_evidence_names_and_all_ties_survive_order_and_no_prediction(av01_page):
    p=projection_fixture();p['nodes'][1]['displacement']['ux_mm']=0;t=teaching_fixture(p,0);t['displacement']['candidates']=[{'id':'node:n1'},{'id':'node:n2'}]
    mount(av01_page,p,t);before=object_button(av01_page,'ANALYSIS_NODE','node:n2').inner_text()
    assert av01_page.locator('[data-av01-object-list] button[data-av01-maximum-candidate]').count()==2
    p['nodes'].reverse();p['supports'].reverse();mount(av01_page,p,t)
    assert object_button(av01_page,'ANALYSIS_NODE','node:n2').inner_text()==before
    assert av01_page.locator('[data-av01-maximum]').count()==2


@pytest.mark.parametrize('kind,identity',[('ANALYSIS_NODE','node:n1'),('SUPPORT','s1'),('ANALYSIS_SEGMENT','m1:1')])
def test_hover_preview_reuses_object_evidence(av01_page,kind,identity):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));panel=choose_evidence(av01_page,kind,identity);expected=panel.inner_text()
    other_kind,other_id=('SUPPORT','s2') if kind!='SUPPORT' else ('ANALYSIS_NODE','node:n2')
    panel=choose_evidence(av01_page,other_kind,other_id);original=panel.inner_text()
    # Hover another existing object must not alter the selected Inspector.
    selected_before=av01_page.locator('[data-av01-object-list] [aria-pressed=true]').inner_text()
    clock_hover(av01_page,kind,identity);av01_page.clock.run_for(399)
    tooltip=av01_page.locator('[data-av01-hover]');assert not tooltip.is_visible()
    av01_page.clock.run_for(1);assert tooltip.is_visible()
    rows=tooltip.locator('[data-av01-preview-field]');assert 2<=rows.count()<=4
    for row in rows.all():
        value=row.locator('[data-av01-value]').inner_text();assert value in expected
    assert panel.inner_text()==original and av01_page.locator('[data-av01-object-list] [aria-pressed=true]').inner_text()==selected_before


def test_stable_hover_does_not_rebuild_evidence_or_redraw_canvas(av01_page):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));target=clock_hover(av01_page,'ANALYSIS_SEGMENT','m1:1')
    av01_page.evaluate('()=>{window.originalSegment=document.querySelector("[data-av01-original-segment]");window.clones=0;const old=structuredClone;window.structuredClone=(...args)=>{clones++;return old(...args)}}')
    requests=[];av01_page.on('request',lambda r:requests.append(r.url))
    av01_page.clock.run_for(300);box=target.bounding_box();av01_page.mouse.move(box['x']+box['width']/2+2,box['y']+box['height']/2)
    av01_page.clock.run_for(399);assert not av01_page.locator('[data-av01-hover]').is_visible()
    av01_page.clock.run_for(1);assert av01_page.locator('[data-av01-hover]').is_visible()
    assert av01_page.evaluate('()=>originalSegment===document.querySelector("[data-av01-original-segment]")&&clones===0')
    assert requests==[]


def test_hover_preview_does_not_intercept_canvas_actions(av01_page):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));clock_hover(av01_page,'ANALYSIS_SEGMENT','m1:1');av01_page.clock.run_for(400)
    tooltip=av01_page.locator('[data-av01-hover]');assert tooltip.is_visible()
    assert tooltip.evaluate('(el)=>[el,...el.querySelectorAll("*")].every(x=>getComputedStyle(x).pointerEvents==="none")')
    assert not tooltip.locator('button,input,[tabindex]').count()
    svg=av01_page.locator('[data-av01-canvas]').bounding_box();box=tooltip.bounding_box()
    assert box['x']>=svg['x'] and box['x']+box['width']<=svg['x']+svg['width']+1
    assert box['y']>=svg['y'] and box['y']+box['height']<=min(av01_page.viewport_size['height'],svg['y']+svg['height'])+1
    hit_object(av01_page,'ANALYSIS_SEGMENT','m1:1').click()
    assert '+100 N' in av01_page.locator('[data-av01-evidence]').inner_text() and not tooltip.is_visible()
    assert av01_page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


@pytest.mark.parametrize('cause',['leave','target-change','pointerdown','wheel','fit','pointercancel','hidden','removed','destroy'])
def test_hover_preview_cancel_and_dismiss(av01_page,cause):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));target=clock_hover(av01_page,'ANALYSIS_SEGMENT','m1:1');av01_page.clock.run_for(400)
    assert av01_page.locator('[data-av01-hover]').is_visible()
    if cause=='leave':av01_page.mouse.move(1,1)
    elif cause=='target-change':
        other=hit_object(av01_page,'ANALYSIS_NODE','node:n1').bounding_box();av01_page.mouse.move(other['x']+other['width']/2,other['y']+other['height']/2)
    elif cause=='pointerdown':av01_page.mouse.down();av01_page.mouse.up()
    elif cause=='wheel':av01_page.mouse.wheel(0,-80)
    elif cause=='fit':av01_page.get_by_role('button',name='适合视窗',exact=True).click()
    elif cause=='pointercancel':av01_page.locator('[data-av01-canvas]').dispatch_event('pointercancel',{'pointerId':1})
    elif cause=='hidden':av01_page.evaluate('()=>component.setVisible(false)')
    elif cause=='removed':target.evaluate('(el)=>el.remove()')
    elif cause=='destroy':av01_page.evaluate('()=>component.destroy()')
    av01_page.evaluate('()=>Promise.resolve()')
    assert not av01_page.locator('[data-av01-hover]').is_visible()
    if cause!='target-change':
        av01_page.clock.run_for(1000);assert not av01_page.locator('[data-av01-hover]').is_visible()


def test_hover_escape_dismisses_until_target_leave_without_consuming_escape(av01_page):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));target=clock_hover(av01_page,'ANALYSIS_SEGMENT','m1:1');av01_page.clock.run_for(400)
    av01_page.locator('[data-av01-canvas]').focus();av01_page.keyboard.press('Escape');assert not av01_page.locator('[data-av01-hover]').is_visible()
    target.dispatch_event('pointermove',{'clientX':500,'clientY':300,'pointerType':'mouse'});av01_page.clock.run_for(1000)
    assert not av01_page.locator('[data-av01-hover]').is_visible()
    av01_page.mouse.move(1,1);box=target.bounding_box();av01_page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);av01_page.clock.run_for(400)
    assert av01_page.locator('[data-av01-hover]').is_visible()


@pytest.mark.parametrize('epoch,run',[ (2,12),(2,11),(3,11)])
def test_hover_preview_cannot_survive_run_epoch_change(av01_page,epoch,run):
    p=projection_fixture();mount(av01_page,p,teaching_fixture(p));clock_hover(av01_page,'ANALYSIS_SEGMENT','m1:1');av01_page.clock.run_for(200)
    newer=clone_evidence(p);newer['provenance']['analysis_run_id']=run
    reset_selection(av01_page,newer,teaching_fixture(newer),epoch);av01_page.clock.run_for(1000)
    assert not av01_page.locator('[data-av01-hover]').is_visible()
    assert av01_page.locator('[data-av01-object-list] [aria-pressed=true]').count()==0


@pytest.mark.parametrize('value,shown',[(0,'0 N'),(1e-12,'+1e-12 N'),(None,'暂不可用')])
def test_hover_preview_uses_safe_availability_and_labels(av01_page,value,shown):
    p=projection_fixture();p['reactions'][0]['rx_N']=value;mount(av01_page,p,teaching_fixture(p));panel=choose_evidence(av01_page,'SUPPORT','s1')
    assert evidence_value(panel,'Rx')==shown
    clock_hover(av01_page,'SUPPORT','s1');av01_page.clock.run_for(400)
    assert shown in av01_page.locator('[data-av01-hover]').inner_text()


@pytest.mark.parametrize('support_type,axis',[('PINNED',None),('ROLLER','Y'),('ROLLER','X')])
def test_support_glyph_matches_saved_restraints(av01_page,support_type,axis):
    p=projection_fixture();p['supports'][0].update(support_type=support_type,restrained_axis=axis)
    mount(av01_page,p,teaching_fixture(p))
    glyph=hit_object(av01_page,'SUPPORT','s1')
    rollers=glyph.locator('[data-av01-support-roller]')
    assert rollers.count()==(0 if support_type=='PINNED' else 2)
    assert glyph.locator('[data-av01-support-ground]').count()==1
    if support_type=='ROLLER':
        points=rollers.evaluate_all('(els)=>els.map(el=>{const p=new DOMPoint(Number(el.getAttribute("cx")),Number(el.getAttribute("cy"))).matrixTransform(el.getScreenCTM());return {x:p.x,y:p.y}})')
        node=av01_page.locator('[data-av01-original-layer] circle').first
        anchor=node.evaluate('(el)=>{const p=new DOMPoint(Number(el.getAttribute("cx")),Number(el.getAttribute("cy"))).matrixTransform(el.getScreenCTM());return {x:p.x,y:p.y}}')
        if axis=='Y':
            assert all(point['y']>anchor['y'] for point in points)
            assert abs(points[0]['y']-points[1]['y'])<1 and abs(points[0]['x']-points[1]['x'])>5
        else:
            assert all(point['x']>anchor['x'] for point in points)
            assert abs(points[0]['x']-points[1]['x'])<1 and abs(points[0]['y']-points[1]['y'])>5
