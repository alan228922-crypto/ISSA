"""Task 8: genuine public Runs and explicitly supplied-fact visual cases, never mixed."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import time

import pytest
from playwright.sync_api import expect
from tests.browser.av01_harness import av01_page, projection_fixture, teaching_fixture, mount
from tests.browser.test_m9_public_teaching_loop import public_page, draw_triangle, analyze
from tests.browser.test_m9_reflection_handoff import active_m9_run, db_read
from tests.browser.test_m9_run_context import m9_run
from tests.application.test_physical_draft import context
from tests.browser.test_av01_run_integration import select_public, ready_plot
from tests.browser.test_av01_layers_evidence import choose_evidence, clock_hover
from tests.endpoints.test_analysis_visualization import frozen_artifacts

pytestmark=pytest.mark.browser
SIZES=[(1024,768),(1280,800),(1440,900)]
E=Path('.superpowers/sdd/2026-10-27-av01-analysis-visualization')


def capture(page,case,origin,**extra):
    target=E/'screenshots';target.mkdir(parents=True,exist_ok=True)
    width,height=page.viewport_size.values();name=f'matrix-{case}-{width}x{height}'
    page.locator('[data-av01-canvas]').scroll_into_view_if_needed() if page.locator('[data-av01-canvas]').count() else None
    page.screenshot(path=str(target/(name+'.png')))
    page.screenshot(path=str(target/(name+'-overview.png')),full_page=True)
    record={'case':case,'origin':origin,'viewport':page.viewport_size,'url':page.url,'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),**extra}
    (target/(name+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2))


def supplied_case(case):
    p=projection_fixture()
    if case=='B':
        p['nodes']=[];p['segments']=[];source=p['label_source'];source['nodes']=[];source['physical_members']=[];source['analysis_member_mapping']={}
        for i in range(42):
            key=f'node-{i+1}';p['nodes'].append({'analysis_node_id':'node:'+key,'source_ref':{'kind':'NODE','identity':key,'endpoint':None},'x_mm':(i//2)*100,'y_mm':(i%2)*100,'displacement':{'ux_mm':i*.01,'uy_mm':-i*.005},'support_ids':[],'load_ids':[]});source['nodes'].append({'id':key,'label':''})
        pairs=[(i,i+2) for i in range(40)]+[(i,i+1) for i in range(0,42,2)]+[(i,i+3) for i in range(0,38,2)]
        for i,(a,b) in enumerate(pairs):
            key=f'member-{i+1}';segment=key+':1';p['segments'].append({'analysis_segment_id':segment,'physical_member_id':key,'start_analysis_node_id':p['nodes'][a]['analysis_node_id'],'end_analysis_node_id':p['nodes'][b]['analysis_node_id'],'axial_force_N':10+i});source['physical_members'].append({'id':key,'start_node_id':f'node-{a+1}','end_node_id':f'node-{b+1}'});source['analysis_member_mapping'][key]=[segment]
        for i,index in enumerate([0,40]):
            node=p['nodes'][index];p['supports'][i]['analysis_node_id']=node['analysis_node_id'];node['support_ids']=[p['supports'][i]['support_id']];p['reactions'][i]['analysis_node_id']=node['analysis_node_id']
        p['loads'][0]['analysis_node_id']=p['nodes'][21]['analysis_node_id'];p['nodes'][21]['load_ids']=['l1']
    elif case=='C':
        p['supports'].append({'support_id':'s3','analysis_node_id':'node:n1','support_type':'ROLLER','restrained_axis':'Y'});p['label_source']['supports'].append({'id':'s3'});p['nodes'][0]['support_ids'].append('s3');p['reactions'][0]['support_ids'].append('s3')
    elif case=='D':
        for i,(fx,fy) in enumerate([(100,0),(50,0),(0,-100)],2):
            key=f'load-{i}';p['loads'].append({'load_id':key,'analysis_node_id':'node:n1','fx_N':fx,'fy_N':fy});p['label_source']['node_loads'].append({'id':key,'label':''});p['nodes'][0]['load_ids'].append(key)
        p['reactions'][0].update(rx_N=-100,ry_N=-60)
    elif case=='E':p['nodes'][1]['displacement']={'ux_mm':1e-12,'uy_mm':0};p['reactions'][0]['rx_N']=1.42109e-14
    elif case=='F':p['nodes'][1]['displacement']={'ux_mm':5000,'uy_mm':0}
    elif case=='G':
        p['nodes'].insert(1,{'analysis_node_id':'node:mid','source_ref':{'kind':'NODE','identity':'mid','endpoint':None},'x_mm':400,'y_mm':0,'displacement':{'ux_mm':.2,'uy_mm':-.3},'support_ids':[],'load_ids':[]});p['label_source']['nodes'].append({'id':'mid','label':'中间节点'})
        p['segments']=[dict(p['segments'][0],end_analysis_node_id='node:mid'),dict(p['segments'][0],analysis_segment_id='m1:2',start_analysis_node_id='node:mid',axial_force_N=-50)];p['label_source']['analysis_member_mapping']['m1']=['m1:1','m1:2']
    t=teaching_fixture(p,maximum=1e-12 if case=='E' else 5000 if case=='F' else 1)
    if case=='G':t['members'][0]['actualState']='MIXED';t['members'][0]['segments'][1]['teaching_state']='COMPRESSION'
    return p,t


COLLISION_JS='''()=>{
const svg=document.querySelector('[data-av01-canvas]'),frame=svg.getBoundingClientRect();
const rect=el=>{const r=el.getBoundingClientRect();return {x:r.left-frame.left,y:r.top-frame.top,w:r.width,h:r.height}};
const overlap=(a,b)=>a.x<b.x+b.w+2&&a.x+a.w+2>b.x&&a.y<b.y+b.h+2&&a.y+a.h+2>b.y;
const hits=[];
const labels=[...svg.querySelectorAll('[data-av01-reaction-label],[data-av01-load-label]')];
for(let i=0;i<labels.length;i++)for(let j=i+1;j<labels.length;j++)if(overlap(rect(labels[i]),rect(labels[j])))hits.push('label-label');
const objects=[...svg.querySelectorAll('[data-av01-target][data-object-kind="SUPPORT"],[data-av01-reaction],[data-av01-load]')];
for(const label of labels)for(const object of objects)if(overlap(rect(label),rect(object)))hits.push('label-symbol');
const segments=[...svg.querySelectorAll('[data-av01-original-segment],[data-av01-deformed-segment]')];
for(const label of labels){const r=rect(label);for(const line of segments){const a=line.getBoundingClientRect();const start=new DOMPoint(+line.getAttribute('x1'),+line.getAttribute('y1')).matrixTransform(line.getScreenCTM()),end=new DOMPoint(+line.getAttribute('x2'),+line.getAttribute('y2')).matrixTransform(line.getScreenCTM());let x=start.x-frame.left,y=start.y-frame.top,dx=end.x-start.x,dy=end.y-start.y,lo=0,hi=1,intersects=true;for(const [p,q] of [[-dx,x-r.x],[dx,r.x+r.w-x],[-dy,y-r.y],[dy,r.y+r.h-y]]){if(p===0){if(q<0){intersects=false;break}}else{const u=q/p;if(p<0)lo=Math.max(lo,u);else hi=Math.min(hi,u);if(lo>hi){intersects=false;break}}}if(intersects)hits.push('label-member')}}
return hits;
}'''


def inspect(page):
    expect(page.locator('[data-av01-canvas]')).to_be_visible()
    assert page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth')
    assert not page.locator('[data-av01-root] [data-cad-node-grip],[data-av01-root] input[type=text]').count()
    texts=page.locator('[data-av01-root]').inner_text()
    assert 'node:n1' not in texts and 'm1:1' not in texts and 'a'*64 not in texts
    assert page.locator('[data-av01-original-segment]').count()>0
    assert page.locator('[data-av01-scale]').is_visible()
    assert page.evaluate(COLLISION_JS)==[]
    force_count=page.locator('[data-av01-reaction],[data-av01-load]').count()
    label_count=page.locator('[data-av01-reaction-label],[data-av01-load-label]').count()
    assert label_count>=min(force_count,2)
    if label_count<force_count:
        expect(page.locator('[data-av01-overflow]')).to_be_visible()


@pytest.mark.parametrize('width,height',SIZES)
@pytest.mark.parametrize('case',list('BCDEFG'))
def test_supplied_fact_visual_matrix(av01_page,case,width,height):
    page=av01_page;page.set_viewport_size({'width':width,'height':height});p,t=supplied_case(case);mount(page,p,t)
    page.locator('[data-case-origin]').evaluate('(el,text)=>el.textContent=text',f'案例 {case} · 受控保存事实，非自然 Solver 输出')
    page.locator('[data-av01-layer=deformation]').check();page.get_by_role('button',name='适合视窗',exact=True).click()
    choose_evidence(page,'ANALYSIS_SEGMENT',p['segments'][0]['analysis_segment_id'])
    capture(page,case,'controlled saved-fact component; not public Solver result',nodes=len(p['nodes']),segments=len(p['segments']))
    inspect(page)
    assert page.locator('[data-av01-deformed-segment]').count()==len(p['segments'])
    assert page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')
    if case=='C':assert page.locator('[data-av01-reaction]').count()==2
    if case=='D':assert page.locator('[data-av01-load]').count()==4
    if case=='E':assert '放大上限' in page.locator('[data-av01-scale]').text_content()
    if case=='F':assert page.locator('[data-av01-scale]').get_attribute('data-alpha')=='1'
    if case=='G':assert page.locator('[data-av01-sibling]').count()==2
    before=page.locator('[data-av01-original-segment]').first.get_attribute('x1');started=time.perf_counter()
    page.get_by_role('button',name='放大',exact=True).click();page.get_by_role('button',name='缩小',exact=True).click()
    box=page.locator('[data-av01-canvas]').bounding_box();x=box['x']+box['width']*.4;y=box['y']+box['height']*.4
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+25,y+15);page.mouse.up()
    assert page.locator('[data-av01-original-segment]').first.get_attribute('x1')!=before
    page.get_by_role('button',name='适合视窗',exact=True).click();inspect(page)
    capture(page,case,'controlled saved-fact component; not public Solver result',nodes=len(p['nodes']),segments=len(p['segments']),zoom_pan_fit_seconds=round(time.perf_counter()-started,3))


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('width,height',SIZES)
def test_genuine_public_triangle_visual_matrix(public_page,width,height):
    page,_,_=public_page;page.set_viewport_size({'width':width,'height':height});draw_triangle(page);run=analyze(page);ready_plot(page)
    page.locator('[data-av01-layer=deformation]').check();page.get_by_role('button',name='适合视窗',exact=True).click()
    choose_evidence(page,'ANALYSIS_SEGMENT','member-1:1');capture(page,'A','genuine public UI Save/Reload/Check/Analyze',run=run);inspect(page)
    from analysis.models import AnalysisRun
    saved=db_read(lambda:AnalysisRun.objects.get(pk=run));before=db_read(lambda:frozen_artifacts(saved))
    writes=[];page.on('request',lambda req:writes.append(req.method) if req.method not in ['GET','HEAD'] else None)
    clock_hover(page,'ANALYSIS_SEGMENT','member-1:1');page.clock.run_for(400)
    tooltip=page.locator('[data-av01-hover]');expect(tooltip).to_be_visible()
    box=tooltip.bounding_box();assert box['x']>=0 and box['y']>=0
    assert box['x']+box['width']<=width and box['y']+box['height']<=height
    capture(page,'A-hover','genuine public UI Saved Run; real pointer hover',run=run)
    assert not writes and db_read(lambda:frozen_artifacts(saved))==before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('width,height',SIZES)
def test_historical_visual_matrix(active_m9_run,workspace_page,width,height):
    owner,project,run=active_m9_run;before=frozen_artifacts(run);page=workspace_page(user=owner,project=project);page.set_viewport_size({'width':width,'height':height})
    page.locator('[data-draft-object-kind="PHYSICAL_MEMBER"]').first.click();page.locator('[data-property-label]').fill('仅当前草稿，不能进入历史结果');page.locator('[data-property-label]').press('Tab')
    select_public(page,run.pk);ready_plot(page);page.locator('[data-av01-layer=deformation]').check();page.get_by_role('button',name='适合视窗',exact=True).click()
    choose_evidence(page,'ANALYSIS_SEGMENT',run.solver_input_json['members'][0]['id']);capture(page,'H','genuine saved Run with changed unsaved current Draft',run=run.pk);inspect(page)
    assert '仅当前草稿' not in page.locator('[data-av01-root]').inner_text();assert db_read(lambda:frozen_artifacts(run))==before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('width,height',SIZES)
@pytest.mark.parametrize('role',['MANAGER','DEVELOPER','GRACE'])
def test_visualization_keyboard_and_role_matrix(active_m9_run,workspace_page,width,height,role):
    from accounts.models import User
    from competitions.models import EventMembership
    owner,project,run=active_m9_run
    if role=='GRACE':project.event.status='FINISHED_GRACE';project.event.save();viewer=owner
    else:
        viewer=User.objects.create_user('matrix-'+role.lower(),role=role)
        if role=='MANAGER':EventMembership.objects.create(user=viewer,event=project.event,membership_type=EventMembership.Type.MANAGER)
    page=workspace_page(user=viewer,project=project);page.set_viewport_size({'width':width,'height':height});select_public(page,run.pk);ready_plot(page)
    page.locator('[data-av01-layer=deformation]').check();page.get_by_role('button',name='适合视窗',exact=True).click()
    details=page.locator('[data-av01-object-list]');details.locator('summary').click() if not details.get_attribute('open') else None
    button=details.locator('button').first;button.focus();page.keyboard.press('Enter');expect(button).to_be_focused();expect(button).to_have_attribute('aria-pressed','true')
    capture(page,'J' if role=='GRACE' else 'I-'+role,'genuine saved Run; readonly role',role=role,run=run.pk);inspect(page)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('width,height',SIZES)
def test_purged_visual_matrix(active_m9_run,workspace_page,width,height):
    from competitions.models import CompetitionEvent
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project);page.set_viewport_size({'width':width,'height':height});select_public(page,run.pk);ready_plot(page)
    db_read(lambda:CompetitionEvent.objects.filter(pk=project.event_id).update(status='PURGED'))
    response=page.goto(page.url);assert response.status in [403,404]
    assert not page.locator('[data-av01-original-segment]').count();capture(page,'K','real PURGED server access rejection',http_status=response.status,run=run.pk)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('width,height',SIZES)
def test_hidden_then_visible_canvas_refits_without_fact_change(active_m9_run,workspace_page,width,height):
    owner,project,run=active_m9_run;before=frozen_artifacts(run);page=workspace_page(user=owner,project=project);page.set_viewport_size({'width':width,'height':height});select_public(page,run.pk);ready_plot(page)
    page.get_by_role('tab',name='技术数据',exact=True).click();page.set_viewport_size({'width':width-80,'height':height-40});page.get_by_role('tab',name='结论',exact=True).click();ready_plot(page)
    page.set_viewport_size({'width':width,'height':height});page.get_by_role('button',name='适合视窗',exact=True).click()
    assert db_read(lambda:frozen_artifacts(run))==before


@pytest.mark.parametrize('width,height',SIZES)
def test_support_records_do_not_overlap_their_symbols(av01_page,width,height):
    page=av01_page;page.set_viewport_size({'width':width,'height':height});p,t=supplied_case('C');mount(page,p,t)
    boxes=page.locator('[data-av01-target][data-object-kind=SUPPORT] polygon').evaluate_all('(els)=>els.map(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})')
    for i,a in enumerate(boxes):
        for b in boxes[i+1:]:assert not (min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x'])>1 and min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])>1)
    assert page.locator('[data-av01-reaction]').count()==2
    assert page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


@pytest.mark.parametrize('width,height',SIZES)
def test_saved_load_vectors_remain_visually_separate(av01_page,width,height):
    page=av01_page;page.set_viewport_size({'width':width,'height':height});p,t=supplied_case('D');mount(page,p,t)
    conflicts=page.evaluate('''()=>{const lines=[...document.querySelectorAll('[data-av01-reaction] > line:first-child,[data-av01-load] > line:first-child')].map(el=>['x1','y1','x2','y2'].map(k=>Number(el.getAttribute(k))));let overlaps=0;for(let i=0;i<lines.length;i++)for(let j=i+1;j<lines.length;j++){const [x,y,a,b]=lines[i],[u,v,c,d]=lines[j];if(Math.abs(y-b)<.1&&Math.abs(v-d)<.1&&Math.abs(y-v)<4&&Math.min(Math.max(x,a),Math.max(u,c))-Math.max(Math.min(x,a),Math.min(u,c))>4)overlaps++;if(Math.abs(x-a)<.1&&Math.abs(u-c)<.1&&Math.abs(x-u)<4&&Math.min(Math.max(y,b),Math.max(v,d))-Math.max(Math.min(y,b),Math.min(v,d))>4)overlaps++}return overlaps}''')
    assert conflicts==0
    assert page.locator('[data-av01-load]').count()==4
    assert page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


@pytest.mark.parametrize('width,height',SIZES)
def test_display_guidance_is_progressively_disclosed_without_losing_facts(av01_page,width,height):
    page=av01_page;page.set_viewport_size({'width':width,'height':height});p,t=supplied_case('E');mount(page,p,t)
    details=page.locator('[data-av01-legend-details]');expect(details).to_have_count(1)
    assert details.get_attribute('open') is None
    assert page.locator('[data-av01-object-list]').get_attribute('open') is None
    assert page.locator('[data-av01-values]').get_attribute('open') is None
    expect(page.locator('[data-av01-display-summary]')).to_contain_text('力 N')
    details.locator('summary').click();expect(page.locator('[data-av01-legend]')).to_be_visible()
    choose_evidence(page,'SUPPORT','s1');expect(page.locator('[data-av01-evidence]')).to_contain_text('极小非零值')
    page.locator('[data-av01-evidence] [data-av01-exact] summary').click()
    exact=page.locator('[data-av01-evidence] [data-av01-exact] [data-av01-field=Rx] [data-av01-value]').inner_text()
    assert float(exact.split()[0])==p['reactions'][0]['rx_N']
    assert page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


@pytest.mark.parametrize('width,height',SIZES)
def test_support_display_leader_does_not_steal_node_selection(av01_page,width,height):
    page=av01_page;page.set_viewport_size({'width':width,'height':height})
    p,t=supplied_case('C');mount(page,p,t)
    svg=page.locator('[data-av01-canvas]');svg.scroll_into_view_if_needed()
    line=page.locator('[data-av01-original-segment]').first
    point=line.evaluate("el=>{const p=new DOMPoint(+el.getAttribute('x1'),+el.getAttribute('y1')).matrixTransform(el.getScreenCTM());return {x:p.x,y:p.y}}")
    page.mouse.click(point['x'],point['y'])
    selected=page.locator('[data-av01-object-list] [aria-pressed=true]')
    expect(selected).to_have_attribute('data-object-kind','ANALYSIS_NODE')
    expect(selected).to_have_attribute('data-object-id','node:n1')
    symbol=page.locator('[data-av01-target][data-object-kind=SUPPORT] polygon').first
    symbol.click()
    expect(selected).to_have_attribute('data-object-kind','SUPPORT')
    expect(selected).to_have_attribute('data-object-id','s1')
    capture(page,'C-hit','controlled saved-fact component; actual node and support pointer selection',selected_kind='SUPPORT')
    assert page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


@pytest.mark.parametrize('width,height',SIZES)
@pytest.mark.parametrize('fraction',[.65,1.0],ids=['shaft','head'])
def test_visible_reaction_pointer_selects_node_over_member(av01_page,width,height,fraction):
    page=av01_page;page.set_viewport_size({'width':width,'height':height})
    p=projection_fixture();mount(page,p,teaching_fixture(p))
    svg=page.locator('[data-av01-canvas]');svg.scroll_into_view_if_needed()
    shaft=page.locator('[data-av01-reaction][data-component=Rx] > line').first
    point=shaft.evaluate('''(el,f)=>{const x=+el.getAttribute('x1'),y=+el.getAttribute('y1'),p=new DOMPoint(x+f*(+el.getAttribute('x2')-x),y+f*(+el.getAttribute('y2')-y)).matrixTransform(el.getScreenCTM());return {x:p.x,y:p.y}}''',fraction)
    page.mouse.click(point['x'],point['y'])
    selected=page.locator('[data-av01-object-list] [aria-pressed=true]')
    capture(page,'Rx-hit-'+('shaft' if fraction<1 else 'head'),'controlled saved-fact component; real visible reaction pointer hit',selected_kind=selected.get_attribute('data-object-kind'))
    expect(selected).to_have_attribute('data-object-kind','ANALYSIS_NODE')
    expect(selected).to_have_attribute('data-object-id','node:n1')
    # The rest of the member remains directly selectable, not only via the list.
    line=page.locator('[data-av01-original-segment]').first
    middle=line.evaluate("el=>{const p=new DOMPoint((+el.getAttribute('x1')+ +el.getAttribute('x2'))/2,(+el.getAttribute('y1')+ +el.getAttribute('y2'))/2).matrixTransform(el.getScreenCTM());return {x:p.x,y:p.y}}")
    page.mouse.click(middle['x'],middle['y'])
    expect(selected).to_have_attribute('data-object-kind','ANALYSIS_SEGMENT')
    expect(selected).to_have_attribute('data-object-id','m1:1')
    assert page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')
