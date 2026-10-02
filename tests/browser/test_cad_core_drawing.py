"""Core drawing contracts: real pointer actions plus independently derived module assertions."""
import pytest
from tests.application.test_physical_draft import context

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def open_core(context, workspace_page, nodes=(), members=()):
    from projects.models import Project
    from modeling.services import save_physical_draft
    owner, legacy, material, section = context
    project = Project.objects.create(event=legacy.event, owner_user=owner, name="Core drawing")
    if nodes or members:
        save_physical_draft(actor=owner, project=project, payload={
            "schema_version": "physical-draft-v2", "expected_draft_version": 0,
            "nodes": [{"client_key": k, "x_mm": x, "y_mm": y, "label": ""} for k, x, y in nodes],
            "physical_members": [{"client_key": k, "start_node_client_key": a, "end_node_client_key": b,
                "material_id": material.pk, "section_id": section.pk, "label": "", "is_active": True} for k, a, b in members],
            "member_joint_incidences": [], "supports": [], "node_loads": [],
        })
    page = workspace_page(user=owner, project=project)
    page.locator('[data-member-material]').select_option(str(material.pk))
    page.locator('[data-member-section]').select_option(str(section.pk))
    return page, project


def client_point(page, x, y):
    return page.evaluate("""([x,y]) => { const p=new DOMPoint(x,y).matrixTransform(document.querySelector('[data-world-layer]').getScreenCTM()); return {x:p.x,y:p.y}; }""", [x, y])


def move_world(page, x, y, click=False):
    p = client_point(page, x, y)
    page.mouse.move(p['x'], p['y'])
    if click:
        page.mouse.click(p['x'], p['y'])


def test_core_coordinate_roundtrip_and_invalid_matrix(context, workspace_page):
    page, _ = open_core(context, workspace_page)
    result = page.evaluate("""async()=>{try{
      const c=await import('/static/projects/workspace/coordinate-space.js');
      const space={svgToClient:{a:2,b:0,c:0,d:2,e:100,f:50},worldToSvg:{a:2,b:0,c:0,d:-2,e:10,f:90}};
      const local=c.clientPointToSvgLocal({x:140,y:110},space);
      const world=c.svgLocalToWorld(local,space);let invalid;
      try{c.clientPointToSvgLocal({x:0,y:0},{...space,svgToClient:{a:0,b:0,c:0,d:0,e:0,f:0}})}catch(e){invalid=e.code}
      return {local,world,roundtrip:c.worldToClient(world,space),invalid};
    }catch(e){return {missing:e.message}}}""")
    assert result.get('local') == {'x': 20, 'y': 30}, result
    assert result['world'] == {'x': 5, 'y': 30}
    assert result['roundtrip'] == {'x': 140, 'y': 110}
    assert result['invalid'] == 'INVALID_COORDINATE_SPACE'


def test_core_typed_snap_identity_priority_and_ortho(context, workspace_page):
    page, _ = open_core(context, workspace_page)
    result = page.evaluate("""async()=>{const {resolvePointerPoint:r}=await import('/static/projects/workspace/geometry.js');
      const identity={a:1,b:0,c:0,d:1,e:0,f:0};
      const base={worldPointer:{x:13.2,y:8.1},clientPointer:{x:13.2,y:8.1},coordinates:{svgToClient:identity,worldToSvg:identity},origin:{x:12.4,y:7.6},ortho:false,gridEnabled:true,explicitNumeric:false};
      const node={kind:'NODE',nodeClientKey:'n3',worldPoint:{x:13,y:8}};
      const int={kind:'INTERSECTION',memberClientKeys:['m1','m2'],worldPoint:{x:13.2,y:8.1}};
      try {let ambiguous;try{r({...base,candidates:[node,{...node,nodeClientKey:'other'}]})}catch(e){ambiguous=e.code}
        return {node:r({...base,candidates:[int,node]}),off:r({...base,ortho:true,candidates:[node,int]}),int:r({...base,candidates:[int]}),ambiguous};
      }catch(e){return {missing:e.message}}
    }""")
    assert result.get('node', {}).get('nodeClientKey') == 'n3', result
    assert result['off']['worldPoint'] == {'x': 13, 'y': 7.6}
    assert result['int']['memberClientKeys'] == ['m1', 'm2']
    assert result['ambiguous'] == 'AMBIGUOUS_NODE_IDENTITY'


def test_core_controller_routes_without_draft_effects(context, workspace_page):
    page, _ = open_core(context, workspace_page)
    result = page.evaluate("""async()=>{try{const {createInteractionController}=await import('/static/projects/workspace/interaction-controller.js');
      const c=createInteractionController({resolvePointer:()=>null,inspectEndpoint:()=>({passingMemberClientKeys:[],collocatedNodeClientKeys:[]})});
      const draft={nodes:[],physical_members:[]};const ctx={draft,readOnly:false,settings:{}};
      c.dispatch({type:'SELECT_TOOL',tool:'MEMBER'},ctx);
      const view=c.dispatch({type:'VIEW_CHANGED'},ctx);
      return {requests:view.effects.filter(e=>e.type.includes('COMMIT')||e.type==='REQUEST_NODE_CONFIRM').length,draft,phase:c.getState().phase};
    }catch(e){return {missing:e.message}}}""")
    assert result.get('requests') == 0, result
    assert result['draft'] == {'nodes': [], 'physical_members': []}
    assert result['phase'] == 'WAITING_FOR_START'


@pytest.mark.parametrize('width', [1024, 1440])
def test_core_offset_responsive_pointer_uses_one_adapter(context, workspace_page, width):
    page, _ = open_core(context, workspace_page, [('a', 0, 0), ('b', 100, 100)])
    page.set_viewport_size({'width': width, 'height': 900})
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('[data-cad-snap]').click()
    move_world(page, 12.4, 7.6)
    assert float(page.locator('[data-cad-x]').input_value()) == pytest.approx(12.4, abs=1e-5)
    assert float(page.locator('[data-cad-y]').input_value()) == pytest.approx(7.6, abs=1e-5)


def test_core_direct_node_click_cannot_bypass_ortho(context, workspace_page):
    page, _ = open_core(context, workspace_page, [('start', 0, 0), ('off', 100, 10)])
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 0, 0, click=True)
    page.locator('[data-cad-ortho]').click()
    move_world(page, 100, 10, click=True)
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    draft = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    member = draft['physical_members'][0]
    endpoint = next(n for n in draft['nodes'] if n['client_key'] == member['end_node_client_key'])
    assert endpoint['y_mm'] == 0
    assert member['end_node_client_key'] != 'off'


def test_core_singular_canvas_coordinate_cancels_without_commit(context, workspace_page):
    page, _ = open_core(context, workspace_page)
    page.locator('[data-workspace-tool="NODE"]').click()
    box = page.locator('#workspace-canvas').bounding_box()
    page.evaluate("document.querySelector('#workspace-canvas').getScreenCTM=()=>new DOMMatrix([0,0,0,0,0,0])")
    page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute('aria-pressed') == 'true'
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0
    assert '无' in page.locator('#workspace-save-status').inner_text()


@pytest.mark.parametrize('start_existing,end_existing,count', [(False,False,2),(True,False,1),(False,True,1),(True,True,0)])
def test_core_atomic_member_endpoint_combinations(context, workspace_page, start_existing, end_existing, count):
    page, _ = open_core(context, workspace_page, [('a',0,0),('b',100,0)])
    result = page.evaluate("""async ([se,ee])=>{
      const {createWorkspaceState,applyWorkspaceEditorAction,undoWorkspaceEdit,redoWorkspaceEdit}=await import('/static/projects/workspace/state.js');
      const s=createWorkspaceState(JSON.parse(document.querySelector('#workspace-bootstrap').textContent));
      const start=se?{kind:'EXISTING_NODE',nodeClientKey:'a'}:{kind:'PROVISIONAL_POINT',newNodeClientKey:'new-a',worldPoint:{x:0,y:50}};
      const end=ee?{kind:'EXISTING_NODE',nodeClientKey:'b'}:{kind:'PROVISIONAL_POINT',newNodeClientKey:'new-b',worldPoint:{x:100,y:50}};
      try{const n=applyWorkspaceEditorAction(s,{type:'CREATE_MEMBER_BETWEEN_POINTS',start,end,member:{client_key:'new-member',material_id:1,section_id:1,label:'',is_active:true}});
      return {added:n.draft.nodes.length-s.draft.nodes.length,history:n.history.past.length,member:n.draft.physical_members[0],undo:undoWorkspaceEdit(n).draft.nodes.length,redo:redoWorkspaceEdit(undoWorkspaceEdit(n)).draft};}catch(e){return {error:e.code}}
    }""", [start_existing,end_existing])
    assert result.get('added') == count, result
    assert result['history'] == 1
    assert result['member']['start_node_client_key'] == ('a' if start_existing else 'new-a')
    assert result['member']['end_node_client_key'] == ('b' if end_existing else 'new-b')
    assert result['undo'] == 2
    assert result['redo']['physical_members'][0] == result['member']


def test_core_atomic_member_incidence_and_crossing_guard(context, workspace_page):
    page, _ = open_core(context, workspace_page)
    result=page.evaluate("""async()=>{
      const {applyEditorActionV2:apply}=await import('/static/projects/workspace/editor-v2.js');
      const empty={schema_version:'physical-draft-v2',nodes:[],physical_members:[],member_joint_incidences:[],supports:[],node_loads:[]};
      const node=(key,x,y)=>({client_key:key,x_mm:x,y_mm:y,label:''});
      const member=(key,a,b)=>({client_key:key,start_node_client_key:a,end_node_client_key:b,material_id:1,section_id:1,is_active:true,label:''});
      const point=(key,x,y)=>({kind:'PROVISIONAL_POINT',newNodeClientKey:key,worldPoint:{x,y}});
      const action=(start,end)=>({type:'CREATE_MEMBER_BETWEEN_POINTS',start,end,member:{client_key:'new',material_id:1,section_id:1,is_active:true,label:''}});
      const crossing={...empty,nodes:[node('a',-100,0),node('b',100,0),node('c',0,-100),node('d',0,100)],physical_members:[member('h','a','b'),member('v','c','d')]};
      const run=(draft,a)=>{const before=JSON.stringify(draft);try{return {draft:apply(draft,a),unchanged:before===JSON.stringify(draft)}}catch(e){return {error:e.code,unchanged:before===JSON.stringify(draft)}}};
      return {crossStart:run(crossing,action(point('p',0,0),point('q',50,50))),crossEnd:run(crossing,action(point('p',50,50),point('q',0,0))),
        one:run({...crossing,physical_members:[crossing.physical_members[0]]},action(point('p',0,0),point('q',50,50))),
        through:run({...empty,nodes:[node('mid',50,0)]},action(point('p',0,0),point('q',100,0))),
        crossNoJoint:run(crossing,action(point('p',-50,-50),point('q',50,50))),
        collide:run(crossing,action(point('p',-100,0),point('q',50,50))),
        stale:run(crossing,action({kind:'EXISTING_NODE',nodeClientKey:'gone'},point('q',50,50))),
        zero:run(empty,action(point('p',0,0),point('q',0,0)))};
    }""")
    assert result['crossStart'].get('error') == 'EDITOR_UNJOINED_CROSSING_ENDPOINT', result
    assert result['crossEnd']['error'] == 'EDITOR_UNJOINED_CROSSING_ENDPOINT'
    assert result['one']['draft']['member_joint_incidences'] == [{'member_client_key':'h','node_client_key':'p'}]
    assert result['through']['draft']['member_joint_incidences'] == [{'member_client_key':'new','node_client_key':'mid'}]
    assert result['crossNoJoint']['draft']['member_joint_incidences'] == []
    assert result['collide']['error'] == 'EDITOR_EXPLICIT_NODE_REQUIRED'
    assert result['stale']['error'] == 'EDITOR_REFERENCE_NOT_FOUND'
    assert result['zero']['error'] == 'EDITOR_INVALID_TOPOLOGY'
    assert all(r['unchanged'] for r in result.values())


def test_core_blank_start_pending_cancel_and_atomic_commit(context, workspace_page):
    page, _ = open_core(context, workspace_page)
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 200, -100, click=True)
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0
    assert '无' in page.locator('#workspace-save-status').inner_text()
    page.keyboard.press('Escape')
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 200, -100, click=True)
    move_world(page, 500, -100, click=True)
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 2
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
    page.locator('[data-cad-undo]').click()
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0
    page.locator('[data-cad-redo]').click()
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 2


def test_core_node_endpoint_identity_and_no_chaining(context, workspace_page):
    page, _ = open_core(context, workspace_page, [('a',0,0),('b',100,0)])
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 0, 0, click=True)
    move_world(page, 100, 0, click=True)
    move_world(page, 50, 50, click=True)
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 2
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    draft=page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    assert draft['physical_members'][0]['start_node_client_key'] == 'a'
    assert draft['physical_members'][0]['end_node_client_key'] == 'b'


def test_core_crossing_requires_node_tool(context, workspace_page):
    page, _=open_core(context,workspace_page,[('a',-100,0),('b',100,0),('c',0,-100),('d',0,100)], [('h','a','b'),('v','c','d')])
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page,0,0,click=True)
    move_world(page,50,50,click=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==2
    assert page.locator('[data-object-kind="GeometryNode"]').count()==4
    page.locator('[data-workspace-tool="NODE"]').click()
    move_world(page,0,0,click=True)
    assert page.locator('[data-object-kind="GeometryNode"]').count()==5
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    draft=page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    assert len(draft['member_joint_incidences'])==2


def test_core_pending_start_invalidated_by_save_undo_and_tool_change(context, workspace_page):
    page,_=open_core(context,workspace_page,[('a',0,0),('b',100,100)])
    page.locator('[data-workspace-tool="NODE"]').click()
    move_world(page,50,50,click=True)
    assert '有' in page.locator('#workspace-save-status').inner_text()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page,0,0,click=True)
    with page.expect_response(lambda response: response.request.method=='POST' and '/model/' in response.url) as response:
        page.locator('#workspace-save').click()
    assert response.value.ok
    page.wait_for_function("document.querySelector('#workspace-draft-version').textContent.includes('v2')")
    move_world(page,100,100,click=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==0
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page,0,0,click=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==0


def test_core_grid_ortho_decimal_contract(context, workspace_page):
    page,_=open_core(context,workspace_page)
    result=page.evaluate("""async()=>{
      const {resolvePointerPoint:r}=await import('/static/projects/workspace/geometry.js');
      const {visibleGridLevels}=await import('/static/projects/workspace/grid.js');
      const run=(p,origin,ortho,gridEnabled,explicitNumeric=false,scale=1)=>r({worldPointer:p,clientPointer:p,candidates:[],coordinates:{svgToClient:{a:1,b:0,c:0,d:1,e:0,f:0},worldToSvg:{a:scale,b:0,c:0,d:scale,e:0,f:0}},origin,ortho,gridEnabled,explicitNumeric}).worldPoint;
      return {grid:run({x:12.6,y:8.4},null,false,true),h:run({x:13.2,y:7.8},{x:12.4,y:7.6},true,true),v:run({x:12.6,y:9.2},{x:12.4,y:7.6},true,true),free:run({x:13.2,y:7.8},{x:12.4,y:7.6},true,false),precise:run({x:12.4,y:7.6},{x:0,y:0},true,true,true),lod:[.05,1,20].map(scale=>({levels:visibleGridLevels(scale),point:run({x:12.6,y:8.4},null,false,true,false,scale)}))};
    }""")
    assert result['grid']=={'x':13,'y':8}
    assert result['h']=={'x':13,'y':7.6}
    assert result['v']=={'x':12.4,'y':9}
    assert result['free']=={'x':13.2,'y':7.6}
    assert result['precise']=={'x':12.4,'y':7.6}
    assert all(row['point']==result['grid'] for row in result['lod'])


def test_core_shift_and_fkeys_respect_input_focus_and_blur(context, workspace_page):
    page,_=open_core(context,workspace_page,[('a',0,0),('b',100,100)])
    page.locator('[data-workspace-tool="NODE"]').click()
    move_world(page,30,30)
    page.locator('#workspace-canvas').focus()
    page.keyboard.down('Shift')
    assert 'ORTHO: 开' in page.locator('#workspace-snap-indicator').inner_text()
    page.evaluate("window.dispatchEvent(new Event('blur'))")
    assert 'ORTHO: 关' in page.locator('#workspace-snap-indicator').inner_text()
    page.keyboard.up('Shift')
    page.keyboard.down('Shift')
    page.locator('[data-cad-x]').focus()
    assert 'ORTHO: 关' in page.locator('#workspace-snap-indicator').inner_text()
    page.keyboard.up('Shift')
    page.locator('#workspace-canvas').focus()
    for key,selector in [('F7','grid-visible'),('F8','ortho'),('F9','snap'),('F3','object-snap')]:
        button=page.locator(f'[data-cad-{selector}]')
        previous=button.get_attribute('aria-pressed')
        page.keyboard.press(key)
        assert button.get_attribute('aria-pressed') != previous
        field=page.locator('[data-cad-x]')
        field.focus()
        current=button.get_attribute('aria-pressed')
        field.press(key)
        field.press('Shift')
        assert button.get_attribute('aria-pressed')==current
        page.locator('#workspace-canvas').focus()


def test_core_dynamic_parser_rejects_blank_malformed_nonfinite(context,workspace_page):
    page,_=open_core(context,workspace_page)
    result=page.evaluate("""async()=>{try{
      const {parseDynamicPoint:p}=await import('/static/projects/workspace/cad-input.js');
      return {empty:p({mode:'XY',values:{x:' ',y:''}}),partial:p({mode:'XY',values:{x:'1',y:''}}),bad:p({mode:'XY',values:{x:'oops',y:'2'}}),infinite:p({mode:'XY',values:{x:'1e999',y:'2'}}),zero:p({mode:'POLAR',values:{length:'0',angle:'0'},origin:{x:0,y:0}}),relative:p({mode:'RELATIVE',values:{dx:'10.25',dy:'-3.75'},origin:{x:12.4,y:7.6}})};
    }catch(e){return {error:e.message}}}""")
    assert result.get('empty')=={'ok':False,'code':'EMPTY'},result
    assert result['partial']['code']=='INCOMPLETE'
    assert all(result[k]['code']=='MALFORMED' for k in ['bad','infinite','zero'])
    assert result['relative']['point']==pytest.approx({'x':22.65,'y':3.85},abs=1e-9)


def test_core_dynamic_xy_polar_relative_and_cancel(context,workspace_page):
    import math
    page,_=open_core(context,workspace_page,[('a',0,0),('b',200,100)])
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page,12.4,7.6)
    x=page.locator('[data-cad-x]');y=page.locator('[data-cad-y]')
    x.fill('12.4');y.fill('7.6');y.press('Enter')
    assert page.locator('[data-object-kind="GeometryNode"]').count()==2
    length=page.locator('[data-cad-dynamic-length]');angle=page.locator('[data-cad-dynamic-angle]')
    length.fill('100.5');angle.fill('30.25')
    box=page.locator('[data-cad-dynamic-overlay]').bounding_box()
    assert box['y']+box['height'] <= page.locator('#workspace-status-bar').bounding_box()['y']
    page.screenshot(path='.superpowers/sdd/2026-10-01-cad-core-drawing-v1/screenshots/dynamic-polar.png')
    move_world(page,150,50)
    assert angle.input_value()=='30.25'
    angle.press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==1
    page.keyboard.press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==1
    move_world(page,150,70)
    x.fill('150.25');y.fill('70.75');y.press('Enter')
    length.focus();length.press('Tab');angle.press('Tab')
    dx=page.locator('[data-cad-dynamic-dx]');dy=page.locator('[data-cad-dynamic-dy]')
    assert dx.evaluate('(el)=>el===document.activeElement')
    dx.fill('10.25');dy.fill('-3.75');dy.press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==2
    move_world(page,170,30,click=True)
    page.keyboard.press('Escape')
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    draft=page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    first,second=draft['physical_members']
    points={n['client_key']:n for n in draft['nodes']}
    end=points[first['end_node_client_key']]
    assert end['x_mm']==pytest.approx(12.4+100.5*math.cos(math.radians(30.25)),abs=1e-9)
    assert end['y_mm']==pytest.approx(7.6+100.5*math.sin(math.radians(30.25)),abs=1e-9)
    end2=points[second['end_node_client_key']]
    assert (end2['x_mm'],end2['y_mm'])==pytest.approx((160.5,67),abs=1e-9)


@pytest.mark.parametrize('width',[1024,1440])
def test_core_cursor_centered_zoom_at_offset_responsive_and_limits(context,workspace_page,width):
    page,_=open_core(context,workspace_page,[('a',0,0),('b',100,100)])
    page.set_viewport_size({'width':width,'height':900})
    target=client_point(page,40,60)
    page.mouse.move(target['x'],target['y'])
    for delta in [-100]*4+[100]*8:
        before=page.locator('[data-world-layer]').get_attribute('transform')
        page.mouse.wheel(0,delta)
        page.wait_for_function("before=>document.querySelector('[data-world-layer]').getAttribute('transform')!==before",arg=before)
        after=client_point(page,40,60)
        assert ((after['x']-target['x'])**2+(after['y']-target['y'])**2)**.5<=1
    result=page.evaluate("""async()=>{const {reduceView}=await import('/static/projects/workspace/canvas-interaction.js'); const v={a:1,b:0,c:0,d:-1,e:20,f:300};const low=reduceView(v,{type:'ZOOM',factor:1e-9,anchorSvgLocal:{x:400,y:200}});const high=reduceView(v,{type:'ZOOM',factor:1e9,anchorSvgLocal:{x:400,y:200}});return {low:low.a,high:high.a};}""")
    assert result=={'low':.05,'high':20}


def test_core_middle_pan_preserves_pending_member_and_updates_preview(context,workspace_page):
    page,_=open_core(context,workspace_page,[('a',0,0),('b',100,100)],[('m','a','b')])
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.evaluate("window.coreMember=document.querySelector('[data-object-kind=PhysicalMember]')")
    move_world(page,0,0,click=True)
    p=client_point(page,50,50)
    page.mouse.move(p['x'],p['y']);page.mouse.down(button='middle')
    page.mouse.move(p['x']+30,p['y']+20)
    expected=page.evaluate("p=>{const v=new DOMPoint(p.x,p.y).matrixTransform(document.querySelector('[data-world-layer]').getScreenCTM().inverse());return {x:Math.floor(v.x+.5),y:Math.floor(v.y+.5)}}",{'x':p['x']+30,'y':p['y']+20})
    preview=page.locator('[data-cad-member-preview]')
    assert float(preview.get_attribute('x2'))==pytest.approx(expected['x'])
    assert float(preview.get_attribute('y2'))==pytest.approx(expected['y'])
    page.mouse.up(button='middle')
    assert page.evaluate("window.coreMember===document.querySelector('[data-object-kind=PhysicalMember]')")
    assert '无' in page.locator('#workspace-save-status').inner_text()
    assert page.locator('[data-object-kind="GeometryNode"]').count()==2
    move_world(page,80,40,click=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==2


@pytest.mark.parametrize('cleanup',['pointercancel','lostpointercapture','blur'])
def test_core_pointercancel_blur_release_pan_without_commit(context,workspace_page,cleanup):
    page,_=open_core(context,workspace_page,[('a',0,0),('b',100,100)])
    page.locator('[data-workspace-tool="MEMBER"]').click();move_world(page,0,0,click=True)
    assert '请选择构件的终点' in page.locator('[data-modeling-instruction]').inner_text()
    p=client_point(page,50,50);page.mouse.move(p['x'],p['y']);page.mouse.down(button='middle')
    page.mouse.move(p['x']+15,p['y'])
    page.evaluate("event=>{const target=event==='blur'?window:document.querySelector('#workspace-canvas');target.dispatchEvent(new Event(event));}",cleanup)
    page.mouse.up(button='middle')
    before=page.locator('[data-world-layer]').get_attribute('transform')
    # A numeric field intentionally owns its click. Choose an unobstructed
    # Canvas point for the post-cancellation drawing assertion.
    move_world(page,70,70)
    p2=client_point(page,70,70)
    assert page.evaluate("p=>!!document.elementFromPoint(p.x,p.y)?.closest('#workspace-canvas')",p2),page.evaluate("p=>document.elementFromPoint(p.x,p.y)?.outerHTML",p2)
    assert page.locator('[data-world-layer]').get_attribute('transform')==before
    move_world(page,70,70,click=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==1,page.locator('[data-modeling-instruction]').inner_text()


def test_core_snap_index_lifecycle_and_local_query(context,workspace_page):
    page,_=open_core(context,workspace_page)
    result=page.evaluate("""async()=>{try{
      const {getSnapCandidateIndex:get,querySnapCandidates:query}=await import('/static/projects/workspace/snap-candidates.js');
      const draft={nodes:[],physical_members:[]};
      for(let c=0;c<100;c++){for(let n=0;n<10;n++)draft.nodes.push({client_key:`n${c}-${n}`,x_mm:c*1000+n,y_mm:n%2?10:0});for(let m=0;m<20;m++)draft.physical_members.push({client_key:`m${c}-${m}`,start_node_client_key:`n${c}-${m%10}`,end_node_client_key:`n${c}-${(m+3)%10}`});}
      draft.physical_members.push({client_key:'incomplete',start_node_client_key:null,end_node_client_key:'gone'});
      const idx=get(draft),identity={a:1,b:0,c:0,d:1,e:0,f:0},diagnostics={nodesVisited:0,segmentsVisited:0,pairsTested:0};
      const hits=query(idx,{clientPoint:{x:5,y:5},coordinates:{svgToClient:identity,worldToSvg:identity},diagnostics});
      const s=await import('/static/projects/workspace/state.js'),initial=s.createWorkspaceState(JSON.parse(document.querySelector('#workspace-bootstrap').textContent));
      const edit=s.applyWorkspaceEditorAction(initial,{type:'CREATE_NODE',node:{client_key:'new',x_mm:1,y_mm:2,label:''}}),undo=s.undoWorkspaceEdit(edit),save=s.applyWorkspaceSaveSuccess(edit,{draft_version:1});
      return {reuse:idx===get(draft),fresh:idx!==get({...draft,nodes:[...draft.nodes]}),lifecycle:[get(initial.draft)!==get(edit.draft),get(edit.draft)!==get(undo.draft),get(edit.draft)!==get(save.draft)],diagnostics,nodes:hits.filter(h=>h.kind==='NODE').length,intersections:hits.filter(h=>h.kind==='INTERSECTION').map(h=>h.memberClientKeys),incomplete:hits.some(h=>h.memberClientKeys?.includes('incomplete'))};
    }catch(e){return {missing:e.message}}}""")
    assert result.get('reuse') and result['fresh'],result
    assert result['diagnostics']['nodesVisited']<100
    assert result['diagnostics']['segmentsVisited']<200
    assert result['nodes']==10 and result['intersections']
    assert all(pair==sorted(pair) for pair in result['intersections'])
    assert result['incomplete'] is False
    assert all(result['lifecycle'])
    assert result['diagnostics']['pairsTested']==190


@pytest.mark.parametrize('width,height',[(500,500),(1000,1000),(2000,1000)])
def test_core_view_grid_marker_and_pointer_dom_cost(context,workspace_page,width,height):
    import json
    from pathlib import Path
    nodes=[(f'{side}{i}',x,height*i/49) for i in range(50) for side,x in [('a',0),('b',width)]]
    members=[(f'm{i}',f'a{i}',f'b{i}') for i in range(50)]
    page,_=open_core(context,workspace_page,nodes,members)
    page.locator('[data-workspace-tool="NODE"]').click()
    page.evaluate("window.coreMember=document.querySelector('[data-object-kind=PhysicalMember]')")
    move_world(page,0,0)
    marker=page.locator('[data-cad-snap-marker] circle')
    size=marker.bounding_box()['width']
    page.locator('[data-cad-zoom-in]').click()
    move_world(page,0,0)
    assert abs(marker.bounding_box()['width']-size)<=1
    p=client_point(page,width*.5,height*.5);page.mouse.move(p['x'],p['y']);page.mouse.down(button='middle');page.mouse.move(p['x']+20,p['y']);page.mouse.up(button='middle')
    assert page.evaluate("window.coreMember===document.querySelector('[data-object-kind=PhysicalMember]')")
    assert page.locator('pattern[data-grid-level]').count()==3
    assert page.locator('[data-canvas-grid] line').count()==0
    page.evaluate("""()=>{window.coreTimings={pointer:[],pan:[],zoom:[]};const svg=document.querySelector('#workspace-canvas');for(const type of ['pointermove','wheel']){svg.addEventListener(type,e=>{window.coreStamp=performance.now()},true);svg.addEventListener(type,e=>{window.coreTimings[type==='wheel'?'zoom':e.buttons&4?'pan':'pointer'].push(performance.now()-window.coreStamp)});}}""")
    for i in range(25):
        move_world(page,width*(.4+i*.001),height*.5)
    p=client_point(page,width*.5,height*.5);page.mouse.move(p['x'],p['y']);page.mouse.down(button='middle')
    for i in range(25):
        page.mouse.move(p['x']+i,p['y']+i*.2)
    page.mouse.up(button='middle')
    for i in range(12):
        before=page.locator('[data-world-layer]').get_attribute('transform')
        page.mouse.wheel(0,-100 if i%2 else 100)
        page.wait_for_function("before=>document.querySelector('[data-world-layer]').getAttribute('transform')!==before",arg=before)
    samples=page.evaluate('window.coreTimings')
    metrics={}
    for kind,values in samples.items():
        values=sorted(values[3:])
        assert values, samples
        metrics[kind]={'p50_ms':values[len(values)//2],'p95_ms':values[min(len(values)-1,int(len(values)*.95))],'samples':len(values)}
    metrics.update({'range_mm':[width,height],'nodes':100,'members':50})
    Path(f'.superpowers/sdd/2026-10-01-cad-core-drawing-v1/screenshots/performance-{width}x{height}.json').write_text(json.dumps(metrics,indent=2))


def test_core_dynamic_numeric_topology_preview_requires_confirmation(context,workspace_page):
    page,_=open_core(context,workspace_page,[('a',0,0),('mid',50,0),('b',100,100)])
    page.locator('[data-workspace-tool="MEMBER"]').click()
    p=client_point(page,0,0)
    assert page.evaluate("p=>!!document.elementFromPoint(p.x,p.y)?.closest('#workspace-canvas')",p),page.evaluate("p=>({p,hit:document.elementFromPoint(p.x,p.y)?.outerHTML,rect:document.querySelector('#workspace-canvas').getBoundingClientRect().toJSON()})",p)
    move_world(page,0,0,click=True)
    assert '终点' in page.locator('[data-modeling-instruction]').inner_text()
    move_world(page,90,10)
    length=page.locator('[data-cad-dynamic-length]');angle=page.locator('[data-cad-dynamic-angle]')
    assert length.is_visible(), page.evaluate("({tool:document.querySelector('#workspace-root').dataset.uxTool,overlay:document.querySelector('[data-cad-dynamic-overlay]').outerHTML,instruction:document.querySelector('[data-modeling-instruction]').textContent})")
    length.fill('100');angle.fill('0');angle.press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==0
    length.fill('101');length.fill('100');angle.press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==0
    angle.press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==1


def test_core_far_grid_coverage_and_int_marker_stability(context,workspace_page):
    page,_=open_core(context,workspace_page,[('a',-100,0),('b',100,0),('c',0,-100),('d',0,100)],[('h','a','b'),('v','c','d')])
    page.locator('[data-workspace-tool="NODE"]').click();move_world(page,0,0)
    marker=page.locator('[data-cad-snap-marker][data-snap-type="INT"] path')
    size=marker.bounding_box()['width']
    for selector in ['zoom-in','zoom-out','zoom-out']:
        page.locator(f'[data-cad-{selector}]').click();move_world(page,0,0)
        assert abs(marker.bounding_box()['width']-size)<=1
    result=page.evaluate("""async()=>{
      const {renderWorkspaceView}=await import('/static/projects/workspace/renderer.js');
      const {readCoordinateSpace,visibleSvgViewport,svgLocalToWorld}=await import('/static/projects/workspace/coordinate-space.js');
      const svg=document.querySelector('#workspace-canvas'),draft=JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft;
      const viewTransform={a:1,b:0,c:0,d:-1,e:-20000,f:300};
      const coordinates=readCoordinateSpace(svg,viewTransform);
      renderWorkspaceView(svg,draft,{viewTransform,cad:{}},coordinates);
      const viewport=visibleSvgViewport(svg,coordinates),world=svgLocalToWorld({x:viewport.left,y:viewport.top},coordinates),rect=svg.querySelector('[data-grid-fill]');
      return {x:Number(rect.getAttribute('x')),width:Number(rect.getAttribute('width')),worldX:world.x,patterns:svg.querySelectorAll('pattern[data-grid-level]').length,lines:svg.querySelectorAll('[data-canvas-grid] line').length};
    }""")
    assert result['x']>10000
    assert result['x']<=result['worldX']<=result['x']+result['width']
    assert result['patterns']==3 and result['lines']==0
