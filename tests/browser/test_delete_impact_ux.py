"""Explicit deletion intent: preview purity, bounded topology and public journeys."""
import pytest
from pathlib import Path
from playwright.sync_api import expect
from tests.application.test_physical_draft import context
from tests.browser.test_cad_core_drawing import open_core, move_world
from tests.browser.test_cad_core_journey import save_reload, member
from tests.browser.test_model_check_recovery import read_draft
from tests.browser.test_bridge_public_journey import check

EVIDENCE = Path(__file__).resolve().parents[2] / '.superpowers/sdd/貼上的文字.txt/screenshots'

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def test_topology_query_and_placement_regression(context, workspace_page):
    page, _ = open_core(context, workspace_page)
    result = page.evaluate("""async()=>{
      const {applyEditorAction}=await import('/static/projects/workspace/editor.js');
      const draft={schema_version:'physical-draft-v2',version:0,
        nodes:[['a',0],['mid',50],['b',100],['free',120]].map(([client_key,x_mm])=>({client_key,x_mm,y_mm:0,label:''})),
        physical_members:[{client_key:'m',start_node_client_key:'a',end_node_client_key:'b',material_id:1,section_id:1,is_active:false,label:''}],
        member_joint_incidences:[{member_client_key:'m',node_client_key:'mid'}],supports:[],node_loads:[]};
      const before=JSON.stringify(draft);let participation;
      try {const {memberParticipationByNode}=await import('/static/projects/workspace/draft-topology.js');
        participation=[...memberParticipationByNode(draft)].map(([k,v])=>[k,[...v]]).sort();
      }catch(e){participation={missing:e.message}}
      const targets=['a','mid','free'].map(nodeClientKey=>{try{
        const next=applyEditorAction(draft,{type:'CREATE_SUPPORT_AT_NODE',nodeClientKey,support:{client_key:'s',support_type:'PINNED',restrained_axis:null}});
        return next.supports[0].target_node_client_key;
      }catch(e){return e.code}});
      const loads=['b','mid','free'].map(nodeClientKey=>{try{
        const next=applyEditorAction(draft,{type:'CREATE_NODE_LOAD_AT_NODE',nodeClientKey,nodeLoad:{client_key:'l',fx_N:0,fy_N:-20,label:''}});
        return next.node_loads[0].target_node_client_key;
      }catch(e){return e.code}});
      return {participation,targets,loads,unchanged:before===JSON.stringify(draft)};
    }""")
    assert result['targets'] == ['a', 'mid', 'NODE_NOT_ON_MEMBER']
    assert result['loads'] == ['b', 'mid', 'NODE_NOT_ON_MEMBER']
    assert result['unchanged'] is True
    assert result['participation'] == [['a', ['m']], ['b', ['m']], ['mid', ['m']]]


@pytest.mark.parametrize('case,direct,second,final', [
    ('another-member', ['PHYSICAL_MEMBER:ab', 'SUPPORT:sa'], [], ['GEOMETRY_NODE:a', 'PHYSICAL_MEMBER:ab', 'SUPPORT:sa']),
    ('last-member', ['PHYSICAL_MEMBER:ab', 'SUPPORT:sa'], ['SUPPORT:sb', 'NODE_LOAD:lb'], ['GEOMETRY_NODE:a', 'PHYSICAL_MEMBER:ab', 'SUPPORT:sa', 'SUPPORT:sb', 'NODE_LOAD:lb']),
    ('incidence', ['PHYSICAL_MEMBER:ab', 'SUPPORT:sa'], ['SUPPORT:sb', 'SUPPORT:sc', 'NODE_LOAD:lb', 'NODE_LOAD:lc'], ['GEOMETRY_NODE:a', 'PHYSICAL_MEMBER:ab', 'SUPPORT:sa', 'SUPPORT:sb', 'SUPPORT:sc', 'NODE_LOAD:lb', 'NODE_LOAD:lc']),
    ('already-incomplete', ['PHYSICAL_MEMBER:ab', 'SUPPORT:sa'], ['SUPPORT:sb', 'NODE_LOAD:lb'], ['GEOMETRY_NODE:a', 'PHYSICAL_MEMBER:ab', 'SUPPORT:sa', 'SUPPORT:sb', 'NODE_LOAD:lb']),
    ('member-only', [], ['SUPPORT:sa', 'SUPPORT:sb', 'NODE_LOAD:lb'], ['PHYSICAL_MEMBER:ab', 'SUPPORT:sa', 'SUPPORT:sb', 'NODE_LOAD:lb']),
])
def test_preview_bounded_closure_purity_and_unrelated_protection(context, workspace_page, case, direct, second, final):
    page, _ = open_core(context, workspace_page)
    result = page.evaluate("""async(scenario)=>{
      const draft={schema_version:'physical-draft-v2',version:0,
        nodes:[['a',0],['b',100],['c',scenario==='incidence'?50:200],['free',300]].map(([client_key,x_mm])=>({client_key,x_mm,y_mm:0,label:''})),
        physical_members:[{client_key:'ab',start_node_client_key:'a',end_node_client_key:'b',material_id:scenario==='already-incomplete'?null:1,section_id:1,label:'',is_active:true}],
        member_joint_incidences:scenario==='incidence'?[{member_client_key:'ab',node_client_key:'c'}]:[],
        supports:[['sa','a'],['sb','b'],['sc','c'],['old',null],['unattached','free']].map(([client_key,target_node_client_key])=>({client_key,target_node_client_key,support_type:'PINNED',restrained_axis:null})),
        node_loads:[['lb','b'],['lc','c'],['old-load',null]].map(([client_key,target_node_client_key])=>({client_key,target_node_client_key,fx_N:0,fy_N:-20,label:''}))};
      if(scenario==='another-member')draft.physical_members.push({client_key:'bc',start_node_client_key:'b',end_node_client_key:'c',material_id:1,section_id:1,label:'',is_active:true});
      const selected=scenario==='member-only'?[{kind:'PHYSICAL_MEMBER',clientKey:'ab'}]:[{kind:'GEOMETRY_NODE',clientKey:'a'},{kind:'GEOMETRY_NODE',clientKey:'a'}];
      const before=JSON.stringify(draft);
      try{const {previewDeleteImpact}=await import('/static/projects/workspace/delete-impact.js');
        const p=previewDeleteImpact(draft,selected), ids=xs=>xs.map(x=>x.kind+':'+x.clientKey);
        const {applyEditorAction}=await import('/static/projects/workspace/editor.js');
        const deleted=applyEditorAction(draft,{type:'DELETE_OBJECTS',targets:p.finalDeleteSet});
        return {direct:ids(p.directAffected),second:ids(p.newlyUnattached),final:ids(p.finalDeleteSet),
          selected:ids(p.selected),unchanged:before===JSON.stringify(draft),
          preserved:deleted.supports.filter(s=>['old','unattached'].includes(s.client_key)).map(s=>s.client_key),
          oldLoad:deleted.node_loads.some(l=>l.client_key==='old-load')};
      }catch(e){return {missing:e.message}}
    }""", case)
    assert result.get('direct') == direct, result
    assert result['second'] == second
    assert result['final'] == final
    assert result['unchanged'] is True
    assert result['preserved'] == ['old', 'unattached']
    assert result['oldLoad'] is True


def open_model(context, workspace_page, line=False):
    page, project = open_core(context, workspace_page,
        [('a',0,0),('b',1000,0),('c',500,500)],
        [('base','a','b')] if line else [('base','a','b'),('left','a','c'),('right','b','c')])
    page.locator('[data-workspace-tool="SUPPORT"]').click();move_world(page,0,0,click=True)
    page.locator('[data-support-choice="ROLLER_Y"]').click();move_world(page,1000,0,click=True)
    page.locator('[data-workspace-tool="LOAD"]').click();move_world(page,1000 if line else 500,0 if line else 500,click=True)
    page.locator('[data-property-fy]').fill('-20');page.locator('[data-property-fy]').press('Tab')
    original=save_reload(page)
    return page,project,original


def delete_nodes(page, keys=('a',)):
    coords={'a':(0,0),'b':(1000,0),'c':(500,500)}
    page.locator('[data-workspace-tool="SELECT"]').click();page.keyboard.press('Escape')
    for i,key in enumerate(keys):
        if i:page.keyboard.down('Shift')
        move_world(page,*coords[key],click=True)
        if i:page.keyboard.up('Shift')
    assert page.locator('[data-object-kind][data-selected="true"]').count()==len(keys)
    page.locator('#workspace-canvas').focus();page.keyboard.press('Delete')


def dialog(page):
    result=page.get_by_role('dialog',name='删除会影响其他物件')
    expect(result).to_be_visible(timeout=1500)
    return result


@pytest.mark.parametrize('action',['保留并重新指定','一起删除相关物件','取消','Escape'])
def test_three_actions_preserve_keep_cancel_and_one_history(context,workspace_page,action):
    page,project,original=open_model(context,workspace_page)
    delete_nodes(page)
    modal=dialog(page)
    expect(modal.get_by_role('button',name='取消',exact=True)).to_be_focused()
    assert read_draft(project)==original
    assert not page.locator('[data-cad-undo]').is_enabled()
    if action=='Escape':page.keyboard.press('Escape')
    else:modal.get_by_role('button',name=action,exact=True).click()
    expect(modal).not_to_be_visible()
    if action in ['取消','Escape']:
        expect(page.locator('#workspace-save-status')).to_contain_text('无')
        assert not page.locator('[data-cad-undo]').is_enabled()
        assert page.locator('[data-object-kind="GeometryNode"][data-client-key="a"][data-selected="true"]').count()==1
        assert read_draft(project)==original
        return
    expect(page.locator('#workspace-save-status')).to_contain_text('有')
    assert page.locator('[data-cad-undo]').is_enabled()
    if action=='保留并重新指定':
        assert page.locator('[data-draft-object-key="base"]').count()==1
        assert page.locator('[data-draft-object-key="support-1"]').count()==1
    else:
        for key in ['a','base','left','support-1']:assert page.locator(f'[data-draft-object-key="{key}"]').count()==0
        for key in ['b','c','right','support-2','load-1']:assert page.locator(f'[data-draft-object-key="{key}"]').count()==1
    page.locator('[data-cad-undo]').click()
    assert not page.locator('[data-cad-undo]').is_enabled()  # exactly one history entry
    expect(page.locator('#workspace-save-status')).to_contain_text('无')
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==3
    assert page.locator('[data-object-kind="Support"]').count()==2
    page.locator('[data-cad-redo]').click()
    saved=save_reload(page)
    if action=='保留并重新指定':
        assert next(m for m in saved['physical_members'] if m['client_key']=='base')['start_node_client_key'] is None
        assert next(s for s in saved['supports'] if s['client_key']=='support-1')['target_node_client_key'] is None
        assert any(i['code']=='MISSING_SUPPORT_NODE' for i in check(page)['issues'])
    else:
        assert {m['client_key'] for m in saved['physical_members']}=={'right'}
        assert saved['supports'][0]['client_key']=='support-2'


@pytest.mark.parametrize('width',[1024,1280,1440])
def test_second_level_summary_keyboard_responsive_and_undo(context,workspace_page,width):
    page,project,original=open_model(context,workspace_page,line=True)
    page.set_viewport_size({'width':width,'height':900})
    page.locator('[data-cad-fit]').click()
    delete_nodes(page)
    modal=dialog(page)
    expect(modal.locator('[data-delete-impact-related-summary]')).to_have_text('1 个构件 · 2 个支座 · 1 个荷载')
    modal.locator('summary').click()
    expect(modal).to_contain_text('一起删除相关构件后额外受影响')
    expect(modal.locator('[data-delete-impact-total-summary]')).to_contain_text('1 个节点 · 1 个构件 · 2 个支座 · 1 个荷载')
    page.keyboard.press('Delete');page.keyboard.press('Backspace');page.keyboard.press('Shift')
    assert page.locator('[data-object-kind="GeometryNode"]').count()==3
    assert not page.locator('[data-cad-undo]').is_enabled()
    reached=set()
    for _ in range(8):
        reached.add(page.evaluate('document.activeElement.textContent'))
        page.keyboard.press('Tab')
    assert {'保留并重新指定','一起删除相关物件','取消'} <= reached
    box=modal.bounding_box()
    assert 0<=box['x'] and box['x']+box['width']<=width
    assert 0<=box['y'] and box['y']+box['height']<=900
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    for button in modal.get_by_role('button').all():
        assert button.is_visible()
        bounds=button.bounding_box(); assert bounds['y']+bounds['height']<=900
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(EVIDENCE/f'delete-impact-{width}.png'),full_page=True)
    modal.get_by_role('button',name='一起删除相关物件',exact=True).click()
    for kind in ['PhysicalMember','Support','NodeLoad']:assert page.locator(f'[data-object-kind="{kind}"]').count()==0
    page.locator('[data-cad-undo]').click()
    assert not page.locator('[data-cad-undo]').is_enabled()
    assert page.locator('[data-object-kind="Support"]').count()==2
    page.locator('[data-cad-redo]').click()
    saved=save_reload(page)
    assert saved['physical_members']==saved['supports']==saved['node_loads']==[]
    assert {n['client_key'] for n in saved['nodes']}=={'b','c'}
    assert not any(i['code'].startswith('UNATTACHED_') for i in check(page)['issues'])


def draw_triangle(page, points):
    a,b,c=points
    for start,end in [(a,b),(a,c),(b,c)]:member(page,start,end)
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    page.locator('[data-support-choice="PINNED"]').click();move_world(page,*a,click=True)
    page.locator('[data-support-choice="ROLLER_Y"]').click();move_world(page,*b,click=True)
    page.locator('[data-workspace-tool="LOAD"]').click();move_world(page,*c,click=True)
    page.locator('[data-property-fy]').fill('-20');page.locator('[data-property-fy]').press('Tab')


def test_second_build_public_journey_removes_old_draft_and_restores_once(context,workspace_page):
    page,project=open_core(context,workspace_page)
    points=[(200,-100),(600,-100),(400,0)]
    draw_triangle(page,points)
    first=save_reload(page)
    assert [len(first[k]) for k in ['nodes','physical_members','supports','node_loads']]==[3,3,2,1]
    assert check(page)['ok'] is True
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-workspace-tool="SELECT"]').click()
    for i,point in enumerate(points):
        if i:page.keyboard.down('Shift')
        move_world(page,*point,click=True)
        if i:page.keyboard.up('Shift')
    assert page.locator('[data-object-kind][data-selected="true"]').count()==3
    page.locator('#workspace-canvas').focus();page.keyboard.press('Delete')
    modal=dialog(page)
    expect(modal.locator('[data-delete-impact-related-summary]')).to_have_text('3 个构件 · 2 个支座 · 1 个荷载')
    modal.locator('summary').click()
    expect(modal).to_contain_text('构件 1')
    modal.get_by_role('button',name='一起删除相关物件',exact=True).click()
    assert page.locator('[data-draft-object-key]').count()==0
    page.locator('[data-cad-undo]').click()
    assert page.locator('[data-draft-object-key]').count()==9
    assert not page.locator('[data-cad-undo]').is_enabled()
    expect(page.locator('#workspace-save-status')).to_contain_text('无')
    assert read_draft(project)==first
    page.locator('[data-cad-redo]').click()
    assert page.locator('[data-draft-object-key]').count()==0
    for _ in range(3):page.locator('[data-cad-zoom-out]').click()
    draw_triangle(page,[(250,-250),(650,-250),(450,-100)])
    second=save_reload(page)
    assert [len(second[k]) for k in ['nodes','physical_members','supports','node_loads']]==[3,3,2,1]
    assert all(m['start_node_client_key'] and m['end_node_client_key'] for m in second['physical_members'])
    assert check(page)['ok'] is True
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(EVIDENCE/'second-build-check-pass.png'),full_page=True)


def test_keep_partial_redesign_recovery_to_valid_model(context,workspace_page):
    page,project,_=open_model(context,workspace_page)
    delete_nodes(page)
    dialog(page).get_by_role('button',name='保留并重新指定',exact=True).click()
    incomplete=save_reload(page)
    assert len(incomplete['physical_members'])==3 and len(incomplete['supports'])==2
    result=check(page)
    assert {i['code'] for i in result['issues']} >= {'MISSING_MEMBER_START_NODE','MISSING_SUPPORT_NODE'}
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('.ux-precision summary').click()
    page.locator('[data-cad-command-input]').fill('0,0');page.locator('[data-cad-command-input]').press('Enter')
    assert page.locator('[data-object-kind="GeometryNode"]').count()==3
    node_key=page.locator('[data-object-kind="GeometryNode"]').evaluate_all('(xs)=>xs.map(x=>x.dataset.clientKey).find(k=>!["b","c"].includes(k))')
    page.locator('[data-incomplete-inventory] summary').click()
    for key in ['base','left']:
        page.locator(f'[data-incomplete-object-key="{key}"]').get_by_role('button',name='重新指定',exact=True).click()
        page.locator('[data-property-start-node]').select_option(node_key)
    page.locator('[data-incomplete-object-key="support-1"]').get_by_role('button',name='重新指定',exact=True).click()
    page.locator('[data-property-support-target]').select_option(node_key)
    restored=save_reload(page)
    assert len(restored['physical_members'])==3 and len(restored['supports'])==2
    assert check(page)['ok'] is True


@pytest.mark.parametrize('crossing',[False,True])
def test_whole_visible_model_delete_bypasses_impact_dialog(context,workspace_page,crossing):
    page,project,_=open_model(context,workspace_page)
    page.locator('[data-workspace-tool="SELECT"]').click();page.locator('[data-cad-zoom-out]').click()
    bounds=page.locator('[data-object-kind]').evaluate_all('(xs)=>{const rs=xs.map(x=>x.getBoundingClientRect());return {l:Math.min(...rs.map(r=>r.left))-12,r:Math.max(...rs.map(r=>r.right))+12,t:Math.min(...rs.map(r=>r.top))-12,b:Math.max(...rs.map(r=>r.bottom))+12}}')
    page.mouse.click(bounds['r'] if crossing else bounds['l'],bounds['t'])
    page.mouse.click(bounds['l'] if crossing else bounds['r'],bounds['b'])
    assert page.locator('[data-object-kind][data-selected="true"]').count()==9
    page.locator('[data-property-delete]').click()
    expect(page.locator('[data-delete-impact-dialog]')).not_to_be_visible()
    assert page.locator('[data-draft-object-key]').count()==0
    saved=save_reload(page)
    assert all(saved[k]==[] for k in ['nodes','physical_members','supports','node_loads'])


def test_unrelated_null_and_unattached_survive_ui_delete(context,workspace_page):
    page,project,_=open_model(context,workspace_page,line=True)
    page.locator('[data-workspace-tool="SUPPORT"]').click();move_world(page,1000,0,click=True)
    page.locator('[data-property-support-target]').select_option('')
    page.locator('[data-workspace-tool="LOAD"]').click();move_world(page,1000,0,click=True)
    page.locator('[data-property-load-target]').select_option('c')
    save_reload(page)
    delete_nodes(page)
    modal=dialog(page)
    expect(modal.locator('[data-delete-impact-related-summary]')).to_have_text('1 个构件 · 2 个支座 · 1 个荷载')
    modal.get_by_role('button',name='一起删除相关物件',exact=True).click()
    saved=save_reload(page)
    assert [(s['client_key'],s['target_node_client_key']) for s in saved['supports']]==[('support-3',None)]
    assert [(s['client_key'],s['target_node_client_key']) for s in saved['node_loads']]==[('load-2','c')]


def test_delayed_save_invalidates_preview_without_private_state_changes(context,workspace_page):
    page,project,_=open_model(context,workspace_page)
    page.locator('[data-draft-object-key="load-1"]').click()
    page.locator('[data-property-fy]').fill('-30');page.locator('[data-property-fy]').press('Tab')
    pending=[]
    page.route('**/model/save/',lambda route:pending.append(route))  # delay transport, real Save backend
    with page.expect_request('**/model/save/'):
        page.locator('#workspace-save').click()
    delete_nodes(page)
    modal=dialog(page)
    with page.expect_response('**/model/save/') as response:pending[0].continue_()
    assert response.value.ok
    expect(page.locator('#workspace-save-status')).to_contain_text('无')
    modal.get_by_role('button',name='一起删除相关物件',exact=True).click()
    expect(modal).not_to_be_visible()
    expect(page.locator('#workspace-error')).to_contain_text('模型已发生变化，请重新执行删除。')
    assert page.locator('[data-draft-object-key]').count()==9
    saved=read_draft(project)
    assert len(saved['nodes'])==3 and len(saved['physical_members'])==3
    assert saved['node_loads'][0]['fy_N']==-30


def test_member_only_keep_reports_preserved_unattached_objects(context,workspace_page):
    page,project,_=open_model(context,workspace_page,line=True)
    page.locator('[data-draft-object-key="base"]').click()
    page.locator('[data-property-delete]').click()
    modal=dialog(page)
    expect(modal.locator('[data-delete-impact-related-summary]')).to_have_text('2 个支座 · 1 个荷载')
    modal.get_by_role('button',name='保留并重新指定',exact=True).click()
    expect(page.locator('[data-delete-feedback]')).to_contain_text('相关物件已保留')
    saved=save_reload(page)
    assert saved['physical_members']==[]
    assert len(saved['supports'])==2 and len(saved['node_loads'])==1
    assert {'UNATTACHED_SUPPORT_NODE','UNATTACHED_LOAD_NODE'} <= {i['code'] for i in check(page)['issues']}


@pytest.mark.parametrize('held',['Space','Shift'])
def test_held_key_release_inside_dialog_cleans_up_without_workspace_command(context,workspace_page,held):
    page,project,_=open_model(context,workspace_page)
    # Complete a real drawing command so Space-tap would normally repeat NODE.
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('.ux-precision summary').click()
    page.locator('[data-cad-command-input]').fill('1200,500');page.locator('[data-cad-command-input]').press('Enter')
    page.locator('[data-workspace-tool="SELECT"]').click()
    page.locator('[data-draft-object-key="a"]').click()
    if held=='Shift':page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('#workspace-canvas').focus()
    page.keyboard.down(held);page.keyboard.press('Delete')
    modal=dialog(page)
    page.keyboard.up(held)
    modal.get_by_role('button',name='取消',exact=True).click()
    if held=='Shift':
        expect(page.locator('#workspace-snap-indicator')).to_contain_text('ORTHO: 关')
        expect(page.locator('[data-workspace-tool="MEMBER"]')).to_have_attribute('aria-pressed','true')
        page.locator('[data-workspace-tool="SELECT"]').click()
    else:expect(page.locator('[data-workspace-tool="SELECT"]')).to_have_attribute('aria-pressed','true')
    # No synthetic controller access: inspect the visible world transform during
    # a normal left drag. A leaked held-Space makes this pan instead of selecting.
    move_world(page,100,300)
    before=page.locator('[data-world-layer]').get_attribute('transform')
    page.mouse.down();move_world(page,200,350);page.mouse.up()
    assert page.locator('[data-world-layer]').get_attribute('transform')==before
    assert page.locator('[data-draft-object-key="a"]').count()==1
