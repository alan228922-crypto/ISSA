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
