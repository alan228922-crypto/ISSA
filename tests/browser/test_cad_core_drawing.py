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
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page,0,0,click=True)
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    move_world(page,100,100,click=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==0
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page,0,0,click=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==0
