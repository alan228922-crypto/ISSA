from pathlib import Path

import pytest

from modeling.services import save_physical_draft
from tests.application.test_analysis_acceptance import save_bt01_draft
from tests.application.test_physical_draft import context, valid_payload


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_sketch_visual_acceptance_and_fixed_dom_cost(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    captures = Path(__file__).resolve().parents[2] / '.superpowers/sdd/2026-09-28-structural-sketch-visual-language/screenshots'
    captures.mkdir(parents=True, exist_ok=True)
    for width, height in [(1024, 768), (1280, 800), (1440, 900)]:
        page.set_viewport_size({'width': width, 'height': height})
        for name, scale in [('near', 0.8), ('mid', 0.55), ('far', 0.28)]:
            result = page.evaluate("""async (scale) => {
              const {renderWorkspace}=await import('/static/projects/workspace/renderer.js');
              const svg=document.querySelector('#workspace-canvas');
              const nodes=[[0,0],[300,0],[600,0],[900,0],[150,220],[450,220],[750,220],[1100,0]].map(([x,y],i)=>({client_key:`n${i}`,x_mm:x,y_mm:y,label:''}));
              const segments=[[0,1],[1,2],[2,3],[0,4],[4,1],[1,5],[5,2],[2,6],[6,3],[3,7],[4,5],[5,6]].map(([a,b],i)=>({client_key:`m${i}`,start_node_client_key:`n${a}`,end_node_client_key:`n${b}`,material_id:1,section_id:1,label:'',is_active:true}));
              const connections=[0,1,2,3,4,5,6,7].map(i=>({client_key:`c${i}`,geometry_node_client_key:`n${i}`,participating_member_client_keys:segments.filter(m=>[m.start_node_client_key,m.end_node_client_key].includes(`n${i}`)).map(m=>m.client_key)}));
              const draft={nodes,physical_members:segments,connections,supports:[{client_key:'pin',target_connection_client_key:'c0',support_type:'PINNED',restrained_axis:null},{client_key:'rollerY',target_connection_client_key:'c3',support_type:'ROLLER',restrained_axis:'Y'},{client_key:'rollerX',target_connection_client_key:'c7',support_type:'ROLLER',restrained_axis:'X'}],node_loads:[{client_key:'down',target_connection_client_key:'c4',fx_N:0,fy_N:-20,label:''},{client_key:'up',target_connection_client_key:'c5',fx_N:0,fy_N:15,label:''},{client_key:'right',target_connection_client_key:'c1',fx_N:30,fy_N:0,label:''},{client_key:'left',target_connection_client_key:'c2',fx_N:-25,fy_N:0,label:''},{client_key:'both',target_connection_client_key:'c6',fx_N:40,fy_N:-50,label:''}]};
              const view={a:scale,b:0,c:0,d:-scale,e:90,f:350};
              renderWorkspace(svg,draft,{viewTransform:view,selectedObject:{kind:'Support',clientKey:'rollerY'}});
              const emptyState=document.querySelector('[data-ux-empty-state]'); if (emptyState) emptyState.hidden=true;
              const kinds=['GeometryNode','PhysicalMember','Connection','Support','NodeLoad'];
              const counts=Object.fromEntries(kinds.map(kind=>[kind,svg.querySelectorAll(`[data-object-kind="${kind}"]`).length]));
              const tips=[...svg.querySelectorAll('[data-load-arrowhead]')].map(head=>head.getAttribute('points').split(' ')[0]);
              const stable=svg.querySelector('[data-render-layer="members"]');
              svg.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,clientX:420,clientY:420,pointerId:1}));
              return {counts,tips,labels:svg.querySelectorAll('[data-load-label]').length,defs:svg.querySelectorAll('#workspace-support-hatch').length,patterns:svg.querySelectorAll('[data-grid-level]').length,selected:getComputedStyle(svg.querySelector('[data-client-key="rollerY"] [data-selection-outline]')).display,decorations:[...svg.querySelectorAll('[data-support-part]')].every(el=>getComputedStyle(el).pointerEvents==='none'),memberLayerStable:stable===svg.querySelector('[data-render-layer="members"]')};
            }""", scale)
            assert result['counts'] == {'GeometryNode': 8, 'PhysicalMember': 12, 'Connection': 8, 'Support': 3, 'NodeLoad': 5}
            assert result['defs'] == 1 and result['patterns'] == 3
            assert result['selected'] != 'none' and result['decorations'] is True
            assert result['memberLayerStable'] is True
            assert len(result['tips']) == 6
            if name == 'far':
                assert result['labels'] == 0
            else:
                assert result['labels'] == 6
            page.screenshot(path=str(captures / f'structural-sketch-{width}x{height}-{name}.png'))


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_sketch_many_symbols_and_crossing_do_not_add_topology(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {renderWorkspace}=await import('/static/projects/workspace/renderer.js');
      const svg=document.querySelector('#workspace-canvas');
      const nodes=[{client_key:'a',x_mm:-100,y_mm:-100},{client_key:'b',x_mm:100,y_mm:100},{client_key:'c',x_mm:-100,y_mm:100},{client_key:'d',x_mm:100,y_mm:-100}];
      const members=[['a','b'],['c','d']].map(([a,b],i)=>({client_key:`cross${i}`,start_node_client_key:a,end_node_client_key:b}));
      members.push({client_key:'incomplete',start_node_client_key:'a',end_node_client_key:null});
      for(let i=0;i<150;i++) nodes.push({client_key:`extra${i}`,x_mm:300+i*60,y_mm:0});
      const connections=nodes.slice(4).map((node,i)=>({client_key:`conn${i}`,geometry_node_client_key:node.client_key,participating_member_client_keys:[null]}));
      const supports=connections.map((connection,i)=>({client_key:`support${i}`,target_connection_client_key:connection.client_key,support_type:i%2?'ROLLER':'PINNED',restrained_axis:i%2?'Y':null}));
      const node_loads=connections.map((connection,i)=>({client_key:`load${i}`,target_connection_client_key:connection.client_key,fx_N:0,fy_N:-10}));
      renderWorkspace(svg,{nodes,physical_members:members,connections,supports,node_loads},{viewTransform:{a:1,b:0,c:0,d:-1,e:400,f:300}});
      return {nodes:svg.querySelectorAll('[data-object-kind="GeometryNode"]').length,members:svg.querySelectorAll('[data-object-kind="PhysicalMember"]').length,connections:svg.querySelectorAll('[data-object-kind="Connection"]').length,supports:svg.querySelectorAll('[data-object-kind="Support"]').length,loads:svg.querySelectorAll('[data-object-kind="NodeLoad"]').length,defs:svg.querySelectorAll('#workspace-support-hatch').length,markers:svg.querySelectorAll('#workspace-load-arrow').length,gridLines:svg.querySelectorAll('[data-canvas-grid] line').length,crossingAtOrigin:svg.querySelectorAll('[data-object-kind="Connection"] circle[cx="0"][cy="0"]').length};
    }""")
    assert result == {'nodes': 154, 'members': 2, 'connections': 150, 'supports': 150, 'loads': 150, 'defs': 1, 'markers': 1, 'gridLines': 0, 'crossingAtOrigin': 0}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_result_stays_above_interaction_outlines_and_empty_symbols_focus(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {renderWorkspace}=await import('/static/projects/workspace/renderer.js');
      const svg=document.querySelector('#workspace-canvas');
      const draft={nodes:[{client_key:'n1',x_mm:0,y_mm:0},{client_key:'n2',x_mm:100,y_mm:0}],physical_members:[{client_key:'m1',start_node_client_key:'n1',end_node_client_key:'n2'}],connections:[{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:['m1']}],supports:[],node_loads:[{client_key:'l1',target_connection_client_key:'c1',fx_N:0,fy_N:0}]};
      renderWorkspace(svg,draft,{selectedObjects:[{kind:'PhysicalMember',clientKey:'m1'},{kind:'Connection',clientKey:'c1'},{kind:'NodeLoad',clientKey:'l1'}],resultOverlay:{m1:{state:'TENSION',color:'#b91c1c',dash:'7 3',label:'受拉'}}});
      const member=svg.querySelector('[data-client-key="m1"]'); member.dataset.hovered='true';
      const children=[...member.children]; const body=member.querySelector('[data-member-body]');
      const feedback=key=>{const group=svg.querySelector(`[data-client-key="${key}"]`);return {hover:Boolean(group.querySelector('[data-hover-outline]')),selection:group.querySelector('[data-selection-outline]')&&getComputedStyle(group.querySelector('[data-selection-outline]')).display!=='none'};};
      return {bodyAboveHover:children.indexOf(body)>children.indexOf(member.querySelector('[data-hover-outline]')),bodyAboveSelection:children.indexOf(body)>children.indexOf(member.querySelector('[data-selection-outline]')),hoverDash:member.querySelector('[data-hover-outline]').getAttribute('stroke-dasharray'),selectionDash:member.querySelector('[data-selection-outline]').getAttribute('stroke-dasharray'),bodyColor:body.getAttribute('stroke'),connection:feedback('c1'),zeroLoad:feedback('l1')};
    }""")
    assert result == {'bodyAboveHover': True, 'bodyAboveSelection': True, 'hoverDash': '7 3', 'selectionDash': '7 3', 'bodyColor': '#b91c1c', 'connection': {'hover': True, 'selection': True}, 'zeroLoad': {'hover': True, 'selection': True}}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_support_and_load_with_connection_missing_geometry_remain_repairable(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['connections'][0]['geometry_node_client_key'] = None
    draft['connections'].append({'client_key': 'c2', 'geometry_node_client_key': 'n2', 'participating_member_client_keys': ['m1']})
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    assert page.locator('[data-client-key="s1"][data-object-kind="Support"]').count() == 0
    assert page.locator('[data-client-key="l1"][data-object-kind="NodeLoad"]').count() == 0
    page.locator('[data-draft-object-kind="SUPPORT"][data-draft-object-key="s1"]').click()
    assert page.locator('[data-property-support-target]').is_visible()
    page.locator('[data-property-support-target]').select_option('c2')
    assert page.locator('[data-client-key="s1"][data-object-kind="Support"]').count() == 1
    page.locator('[data-draft-object-kind="NODE_LOAD"][data-draft-object-key="l1"]').click()
    assert page.locator('[data-property-load-target]').is_visible()
    page.locator('[data-property-load-target]').select_option('c2')
    assert page.locator('[data-client-key="l1"][data-object-kind="NodeLoad"]').count() == 1


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_symbol_seam_keeps_world_anchors_and_single_shared_defs(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""() => {
      const svg = document.querySelector('#workspace-canvas');
      const kinds = ['GeometryNode', 'PhysicalMember', 'Connection', 'Support', 'NodeLoad'];
      return {
        tagged: kinds.map(kind => svg.querySelector(`[data-object-kind="${kind}"] [data-structural-symbol]`) !== null),
        defs: svg.querySelectorAll(':scope > defs').length,
        member: (() => { const line = svg.querySelector('[data-object-kind="PhysicalMember"] line'); return [line?.getAttribute('x1'), line?.getAttribute('y1'), line?.getAttribute('x2'), line?.getAttribute('y2')]; })(),
        wrappers: kinds.map(kind => Boolean(svg.querySelector(`[data-object-kind="${kind}"][data-client-key]`))),
      };
    }""")
    assert result == {'tagged': [True] * 5, 'defs': 1, 'member': ['0', '0', '1000', '0'], 'wrappers': [True] * 5}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_node_member_connection_textbook_symbols(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""() => {
      const svg=document.querySelector('#workspace-canvas');
      const node=svg.querySelector('[data-client-key="n1"] [data-structural-symbol="node"]');
      const member=svg.querySelector('[data-client-key="m1"] [data-member-body]');
      const ring=svg.querySelector('[data-client-key="c1"] [data-connection-ring]');
      const memberScale=Math.abs(svg.querySelector('[data-client-key="m1"]').getScreenCTM().a);
      return {nodeFill:node?.getAttribute('fill'),nodeStroke:node?.getAttribute('stroke'),nodeWidth:node?.getBoundingClientRect().width,
        memberWidth:member ? Number(member.getAttribute('stroke-width'))*memberScale : null,
        memberEnds:member && [member.getAttribute('x1'),member.getAttribute('y1'),member.getAttribute('x2'),member.getAttribute('y2')],
        ring:Boolean(ring),connectionCount:svg.querySelectorAll('[data-object-kind="Connection"]').length};
    }""")
    assert result['nodeFill'] == 'white'
    assert result['nodeStroke'] in ('#1f2937', '#111827', '#111111', '#171717')
    assert 12 <= result['nodeWidth'] <= 18
    assert 2 <= result['memberWidth'] <= 5
    assert result['memberEnds'] == ['0', '0', '1000', '0']
    assert result['ring'] is True and result['connectionCount'] == 1


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_node_member_connection_crossing_is_not_joint_and_incomplete_is_listed(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['nodes'] += [
        {'client_key': 'n3', 'x_mm': 0, 'y_mm': 1000, 'label': ''},
        {'client_key': 'n4', 'x_mm': 1000, 'y_mm': -1000, 'label': ''},
    ]
    draft['physical_members'].append({'client_key': 'm2', 'start_node_client_key': 'n3', 'end_node_client_key': 'n4', 'material_id': material.id, 'section_id': section.id, 'label': '', 'is_active': True})
    draft['physical_members'].append({'client_key': 'm3', 'start_node_client_key': 'n1', 'end_node_client_key': None, 'material_id': material.id, 'section_id': section.id, 'label': '', 'is_active': True})
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    assert page.locator('[data-client-key="c1"] [data-connection-ring]').count() == 1
    assert page.locator('[data-object-kind="Connection"]').count() == 1
    assert page.locator('[data-client-key="m3"][data-object-kind="PhysicalMember"]').count() == 0
    assert '尚未完整' in page.locator('[data-draft-object-kind="PHYSICAL_MEMBER"][data-draft-object-key="m3"]').inner_text()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_node_member_connection_selection_keeps_result_body(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const {renderWorkspace}=await import('/static/projects/workspace/renderer.js');
      const svg=document.querySelector('#workspace-canvas');
      const draft=JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft;
      renderWorkspace(svg,draft,{selectedObject:{kind:'PhysicalMember',clientKey:'m1'},resultOverlay:{m1:{state:'TENSION',color:'#b91c1c',dash:'7 3',label:'受拉'}}});
      const group=svg.querySelector('[data-client-key="m1"]');
      const body=group.querySelector('[data-member-body]');
      return {stroke:body.getAttribute('stroke'),dash:body.getAttribute('stroke-dasharray'),selected:Boolean(group.querySelector('[data-selection-outline]')),hit:Boolean(group.querySelector('[data-symbol-hit]'))};
    }""")
    assert result == {'stroke': '#b91c1c', 'dash': '7 3', 'selected': True, 'hit': True}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_node_member_connection_node_remains_top_hit_at_joint(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    top_kind = page.evaluate("""() => {
      const circle=document.querySelector('[data-client-key="n1"] [data-node-body]');
      const box=circle.getBoundingClientRect();
      return document.elementFromPoint(box.x+box.width/2,box.y+box.height/2)?.closest('[data-object-kind]')?.getAttribute('data-object-kind');
    }""")
    assert top_kind == 'GeometryNode'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_node_member_connection_ring_is_hit_outside_node(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    top_kind = page.evaluate("""() => {
      const ring=document.querySelector('[data-client-key="c1"] [data-connection-ring]');
      const box=ring.getBoundingClientRect();
      return document.elementFromPoint(box.right-1,box.y+box.height/2)?.closest('[data-object-kind]')?.getAttribute('data-object-kind');
    }""")
    assert top_kind == 'Connection'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_support_symbol_pinned_rollers_share_hatch_and_ignore_decoration(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {renderWorkspace}=await import('/static/projects/workspace/renderer.js');
      const svg=document.querySelector('#workspace-canvas');
      const draft={nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:''},{client_key:'n2',x_mm:100,y_mm:0,label:''},{client_key:'n3',x_mm:200,y_mm:0,label:''}],physical_members:[],connections:[{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:[null]},{client_key:'c2',geometry_node_client_key:'n2',participating_member_client_keys:[null]},{client_key:'c3',geometry_node_client_key:'n3',participating_member_client_keys:[null]}],supports:[{client_key:'s1',target_connection_client_key:'c1',support_type:'PINNED',restrained_axis:null},{client_key:'s2',target_connection_client_key:'c2',support_type:'ROLLER',restrained_axis:'Y'},{client_key:'s3',target_connection_client_key:'c3',support_type:'ROLLER',restrained_axis:'X'}],node_loads:[]};
      renderWorkspace(svg,draft,{viewTransform:{a:1,b:0,c:0,d:-1,e:0,f:0}});
      const support=key=>svg.querySelector(`[data-client-key="${key}"]`);
      const part=(key,name)=>support(key)?.querySelectorAll(`[data-support-part="${name}"]`).length;
      const wall=support('s3')?.querySelector('[data-support-part="base"]');
      const wheel=support('s2')?.querySelector('[data-support-part="wheel"]');
      return {pinned:[part('s1','triangle'),part('s1','base'),part('s1','hatch')],rollerY:[part('s2','triangle'),part('s2','wheel'),part('s2','base')],rollerX:[part('s3','wheel'),part('s3','base')],wallVertical:wall ? wall.getBoundingClientRect().height>wall.getBoundingClientRect().width : false,hatchDefs:svg.querySelectorAll('#workspace-support-hatch').length,wheelPointer:wheel && getComputedStyle(wheel).pointerEvents,trianglePointer:support('s1')?.querySelector('[data-support-part="triangle"]') && getComputedStyle(support('s1').querySelector('[data-support-part="triangle"]')).pointerEvents};
    }""")
    assert result == {'pinned': [1, 1, 1], 'rollerY': [1, 2, 1], 'rollerX': [2, 1], 'wallVertical': True, 'hatchDefs': 1, 'wheelPointer': 'none', 'trianglePointer': 'none'}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_support_symbol_roller_wheel_click_does_not_create_node(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['supports'][0].update(support_type='ROLLER', restrained_axis='Y')
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    before = page.locator('[data-object-kind="GeometryNode"]').count()
    page.locator('[data-workspace-tool="NODE"]').click()
    wheel = page.locator('[data-client-key="s1"] [data-support-part="wheel"]').first
    box = wheel.bounding_box()
    page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    assert page.locator('[data-object-kind="GeometryNode"]').count() == before


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_load_symbol_components_point_to_true_anchor_with_magnitude_labels(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {renderWorkspace}=await import('/static/projects/workspace/renderer.js');
      const svg=document.querySelector('#workspace-canvas');
      const points=[[0,0],[100,0],[200,0],[300,0],[400,0]];
      const draft={nodes:points.map(([x,y],i)=>({client_key:`n${i}`,x_mm:x,y_mm:y,label:''})),physical_members:[],connections:points.map((_,i)=>({client_key:`c${i}`,geometry_node_client_key:`n${i}`,participating_member_client_keys:[null]})),supports:[],node_loads:[{client_key:'down',target_connection_client_key:'c0',fx_N:0,fy_N:-20,label:''},{client_key:'up',target_connection_client_key:'c1',fx_N:0,fy_N:15,label:''},{client_key:'right',target_connection_client_key:'c2',fx_N:30,fy_N:0,label:''},{client_key:'left',target_connection_client_key:'c3',fx_N:-25,fy_N:0,label:''},{client_key:'both',target_connection_client_key:'c4',fx_N:40,fy_N:-50,label:''}]};
      renderWorkspace(svg,draft,{viewTransform:{a:1,b:0,c:0,d:-1,e:0,f:0}});
      const inspect=key=>{const group=svg.querySelector(`[data-client-key="${key}"]`);return [...group.querySelectorAll('[data-load-component]')].map(part=>({axis:part.getAttribute('data-load-component'),start:[Number(part.querySelector('[data-load-stem]').getAttribute('x1')),Number(part.querySelector('[data-load-stem]').getAttribute('y1'))],tip:[Number(part.querySelector('[data-load-stem]').getAttribute('x2')),Number(part.querySelector('[data-load-stem]').getAttribute('y2'))],head:part.querySelector('[data-load-arrowhead]').getAttribute('points').split(' ')[0],label:part.querySelector('[data-load-label]').textContent,red:part.querySelector('[data-load-stem]').getAttribute('stroke')}));};
      return {down:inspect('down'),up:inspect('up'),right:inspect('right'),left:inspect('left'),both:inspect('both')};
    }""")
    assert result['down'][0]['axis'] == 'Fy' and result['down'][0]['start'][1] > result['down'][0]['tip'][1]
    assert result['up'][0]['start'][1] < result['up'][0]['tip'][1]
    assert result['right'][0]['start'][0] < result['right'][0]['tip'][0]
    assert result['left'][0]['start'][0] > result['left'][0]['tip'][0]
    assert result['down'][0]['tip'] == [0, 0] and result['down'][0]['head'] == '0,0'
    assert result['both'][0]['tip'] == [400, 0] and result['both'][1]['tip'] == [400, 0]
    assert {part['axis'] for part in result['both']} == {'Fx', 'Fy'}
    assert [part['label'] for part in result['both']] == ['40 N', '50 N']
    assert result['down'][0]['label'] == '20 N' and result['left'][0]['label'] == '25 N'
    assert all(part['red'] == '#b91c1c' for parts in result.values() for part in parts)


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_load_symbol_preview_is_transient_and_property_edit_updates_canvas(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="LOAD"]').click()
    page.locator('[data-client-key="n1"] [data-node-body]').hover(force=True)
    assert page.locator('[data-cad-load-preview]').count() == 1
    assert page.locator('[data-object-kind="NodeLoad"]').count() == 1
    page.locator('#workspace-canvas').dispatch_event('pointerleave')
    assert page.locator('[data-cad-load-preview]').count() == 0
    page.locator('[data-draft-object-kind="NODE_LOAD"][data-draft-object-key="l1"]').click()
    page.locator('[data-property-fy]').fill('-20')
    page.locator('[data-property-fy]').dispatch_event('change')
    assert page.locator('[data-client-key="l1"] [data-load-label]').text_content() == '20 N'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_palette_selection_support_cards_map_to_existing_axes(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['connections'].append({'client_key': 'c2', 'geometry_node_client_key': 'n2', 'participating_member_client_keys': ['m1']})
    draft['supports'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    choices = page.locator('[data-support-choice]')
    assert choices.count() == 3
    assert '铰支座' in choices.nth(0).inner_text()
    assert '限制竖向移动' in choices.nth(1).inner_text()
    assert '限制水平移动' in choices.nth(2).inner_text()
    choices.nth(1).click()
    page.locator('[data-client-key="n1"] [data-node-body]').click(force=True)
    assert page.locator('[data-property-support-type]').input_value() == 'ROLLER_Y'
    choices.nth(2).click()
    page.locator('[data-client-key="n2"] [data-node-body]').click(force=True)
    assert page.locator('[data-property-support-type]').input_value() == 'ROLLER_X'
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    supports = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft.supports")
    assert [(item['support_type'], item['restrained_axis']) for item in supports] == [('ROLLER', 'Y'), ('ROLLER', 'X')]


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_structural_palette_selection_load_copy_and_independent_visual_states(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="LOAD"]').click()
    assert '集中力' in page.locator('[data-load-palette]').inner_text()
    page.locator('[data-draft-object-kind="NODE_LOAD"][data-draft-object-key="l1"]').click()
    assert '水平力' in page.locator('[data-property-fx]').locator('..').inner_text()
    assert '竖向力' in page.locator('[data-property-fy]').locator('..').inner_text()
    page.locator('[data-draft-object-kind="SUPPORT"][data-draft-object-key="s1"]').click()
    assert page.locator('[data-client-key="s1"] [data-selection-outline]').evaluate('(element) => getComputedStyle(element).display') != 'none'
    result = page.evaluate("""async () => {
      const {renderWorkspace}=await import('/static/projects/workspace/renderer.js');
      const svg=document.querySelector('#workspace-canvas');
      const draft=JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft;
      renderWorkspace(svg,draft,{selectedObject:{kind:'PhysicalMember',clientKey:'m1'},resultOverlay:{m1:{state:'TENSION',color:'#b91c1c',dash:'7 3',label:'受拉'}}});
      const member=svg.querySelector('[data-client-key="m1"]');
      const node=svg.querySelector('[data-client-key="n1"]');
      const body=member.querySelector('[data-member-body]');
      const hit=member.querySelector('[data-symbol-hit]');
      const nodeHit=node.querySelector('[data-symbol-hit]').getBoundingClientRect();
      return {bodyStroke:body.getAttribute('stroke'),bodyDash:body.getAttribute('stroke-dasharray'),selection:getComputedStyle(member.querySelector('[data-selection-outline]')).display,hitPointer:getComputedStyle(hit).pointerEvents,hitWidth:Number(hit.getAttribute('stroke-width'))*Math.abs(hit.getScreenCTM().a),nodeHitWidth:nodeHit.width,bodyPointer:getComputedStyle(body).pointerEvents};
    }""")
    assert result['bodyStroke'] == '#b91c1c' and result['bodyDash'] == '7 3'
    assert result['selection'] != 'none' and result['hitPointer'] == 'stroke'
    assert 15 <= result['hitWidth'] <= 24 and 20 <= result['nodeHitWidth'] <= 28
    assert result['bodyPointer'] == 'none'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_editor_independent_delete_preserves_gaps_and_undo_restores_identity(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const {applyEditorAction} = await import('/static/projects/workspace/editor.js');
      const {applyWorkspaceEditorAction, undoWorkspaceEdit} = await import('/static/projects/workspace/state.js');
      const draft={schema_version:'physical-draft-v1',version:1,nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:''},{client_key:'n2',x_mm:100,y_mm:0,label:''}],physical_members:[{client_key:'m1',start_node_client_key:'n1',end_node_client_key:'n2',material_id:1,section_id:1,label:'',is_active:true}],connections:[{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:['m1']}],supports:[{client_key:'s1',target_connection_client_key:'c1',support_type:'PINNED',restrained_axis:null}],node_loads:[{client_key:'l1',target_connection_client_key:'c1',fx_N:0,fy_N:-1,label:''}]};
      const deletedNode=applyEditorAction(draft,{type:'DELETE_OBJECT',target:{kind:'GEOMETRY_NODE',clientKey:'n1'}});
      const deletedMember=applyEditorAction(draft,{type:'DELETE_OBJECT',target:{kind:'PHYSICAL_MEMBER',clientKey:'m1'}});
      const deletedConnection=applyEditorAction(draft,{type:'DELETE_OBJECT',target:{kind:'CONNECTION',clientKey:'c1'}});
      const rebound=applyEditorAction(deletedNode,{type:'UPDATE_OBJECT',target:{kind:'PHYSICAL_MEMBER',clientKey:'m1'},changes:{start_node_client_key:'n2'}});
      const movedIncomplete=applyEditorAction(deletedNode,{type:'UPDATE_OBJECT',target:{kind:'GEOMETRY_NODE',clientKey:'n2'},changes:{x_mm:120}});
      const state={draft,draftVersion:1,readOnly:false};
      const undone=undoWorkspaceEdit(applyWorkspaceEditorAction(state,{type:'DELETE_OBJECT',target:{kind:'GEOMETRY_NODE',clientKey:'n1'}}));
      return {node:{members:deletedNode.physical_members.length,start:deletedNode.physical_members[0].start_node_client_key,connectionNode:deletedNode.connections[0].geometry_node_client_key},member:{nodes:deletedMember.nodes.length,slots:deletedMember.connections[0].participating_member_client_keys},connection:{members:deletedConnection.physical_members.length,support:deletedConnection.supports[0].target_connection_client_key,load:deletedConnection.node_loads[0].target_connection_client_key},rebound:rebound.physical_members[0].start_node_client_key,movedIncomplete:movedIncomplete.nodes.find(node=>node.client_key==='n2').x_mm,undo:JSON.stringify(undone.draft)===JSON.stringify(draft),original:JSON.stringify(draft).includes('"start_node_client_key":"n1"')};
    }""")
    assert result == {
        'node': {'members': 1, 'start': None, 'connectionNode': None},
        'member': {'nodes': 2, 'slots': [None]},
        'connection': {'members': 1, 'support': None, 'load': None},
        'rebound': 'n2', 'movedIncomplete': 120, 'undo': True, 'original': True,
    }


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_editor_can_create_incomplete_objects_without_inventing_references(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {applyEditorAction}=await import('/static/projects/workspace/editor.js');
      const base={schema_version:'physical-draft-v1',version:0,nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:''}],physical_members:[],connections:[],supports:[],node_loads:[]};
      const member=applyEditorAction(base,{type:'CREATE_MEMBER',member:{client_key:'m1',start_node_client_key:'n1',end_node_client_key:null,material_id:null,section_id:null,label:'',is_active:true}});
      const connection=applyEditorAction(member,{type:'CREATE_CONNECTION',connection:{client_key:'c1',geometry_node_client_key:null,participating_member_client_keys:[null]}});
      const support=applyEditorAction(connection,{type:'CREATE_SUPPORT',support:{client_key:'s1',target_connection_client_key:null,support_type:'PINNED',restrained_axis:null}});
      const load=applyEditorAction(support,{type:'CREATE_NODE_LOAD',nodeLoad:{client_key:'l1',target_connection_client_key:null,fx_N:0,fy_N:-1,label:''}});
      return {member:load.physical_members[0],connection:load.connections[0],support:load.supports[0],load:load.node_loads[0],baseUnchanged:base.physical_members.length===0};
    }""")
    assert result['member']['end_node_client_key'] is None
    assert result['connection']['participating_member_client_keys'] == [None]
    assert result['support']['target_connection_client_key'] is None
    assert result['load']['target_connection_client_key'] is None
    assert result['baseUnchanged'] is True


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_incomplete_objects_are_selectable_and_rebindable_from_properties(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['physical_members'][0].update(start_node_client_key=None, material_id=None, section_id=None)
    draft['connections'][0].update(geometry_node_client_key=None, participating_member_client_keys=[None])
    draft['supports'][0]['target_connection_client_key'] = None
    draft['node_loads'][0]['target_connection_client_key'] = None
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)

    page.locator('[data-draft-object-kind="PHYSICAL_MEMBER"][data-draft-object-key="m1"]').click()
    assert page.locator('[data-property-start-node]').input_value() == ''
    assert page.locator('[data-property-material]').input_value() == ''
    page.locator('[data-property-start-node]').select_option('n1')
    page.locator('[data-property-material]').select_option(str(material.id))
    page.locator('[data-property-section]').select_option(str(section.id))

    page.locator('[data-draft-object-kind="CONNECTION"][data-draft-object-key="c1"]').click()
    page.locator('[data-property-connection-node]').select_option('n1')
    page.locator('[data-property-participant="0"]').select_option('m1')
    page.locator('[data-draft-object-kind="SUPPORT"][data-draft-object-key="s1"]').click()
    page.locator('[data-property-support-target]').select_option('c1')
    page.locator('[data-draft-object-kind="NODE_LOAD"][data-draft-object-key="l1"]').click()
    page.locator('[data-property-load-target]').select_option('c1')
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    saved = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    assert saved['physical_members'][0]['start_node_client_key'] == 'n1'
    assert saved['physical_members'][0]['material_id'] == material.id
    assert saved['connections'][0]['participating_member_client_keys'] == ['m1']
    assert saved['supports'][0]['target_connection_client_key'] == 'c1'
    assert saved['node_loads'][0]['target_connection_client_key'] == 'c1'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_rebinding_multiple_participation_slots_keeps_earlier_choice(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['physical_members'].append({**draft['physical_members'][0], 'client_key': 'm2'})
    draft['connections'][0]['participating_member_client_keys'] = [None, None]
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-draft-object-kind="CONNECTION"][data-draft-object-key="c1"]').click()
    page.locator('[data-property-participant="0"]').select_option('m1')
    page.locator('[data-property-participant="1"]').select_option('m1')
    assert page.locator('[data-property-participant="1"]').input_value() == ''
    assert '已在此连接中参与' in page.locator('#workspace-error').inner_text()
    page.locator('[data-property-participant="1"]').select_option('m2')
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    saved = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    assert saved['connections'][0]['participating_member_client_keys'] == ['m1', 'm2']


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_property_delete_confirms_impact_then_keeps_dependent_draft(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-draft-object-kind="GEOMETRY_NODE"][data-draft-object-key="n1"]').click()
    messages = []
    page.on('dialog', lambda dialog: (messages.append(dialog.message), dialog.accept()))
    page.locator('[data-property-delete]').click()
    assert messages and '4 个其他对象' in messages[0] and '不会被删除' in messages[0]
    assert page.locator('[data-draft-object-kind="PHYSICAL_MEMBER"][data-draft-object-key="m1"]').count() == 1
    assert '未指定' in page.locator('[data-draft-object-kind="SUPPORT"][data-draft-object-key="s1"]').inner_text()
    assert '未指定' in page.locator('[data-draft-object-kind="NODE_LOAD"][data-draft-object-key="l1"]').inner_text()
    assert page.locator('[data-delete-feedback]').count() == 1
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    saved = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    assert saved['physical_members'][0]['start_node_client_key'] is None
    assert saved['connections'][0]['geometry_node_client_key'] is None


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_member_endpoints_become_truss_joints_without_connection_tool(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    page.locator('[data-member-material]').select_option(str(material.id))
    page.locator('[data-member-section]').select_option(str(section.id))
    page.locator('.ux-precision summary').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    command = page.locator('[data-cad-command-input]')
    for point in ('0,0', '1000,0'):
        command.fill(point)
        command.press('Enter')
    page.locator('[data-cad-fit]').click()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"] circle').click(force=True)
    page.locator('[data-client-key="node-2"] circle').click(force=True)
    assert page.locator('[data-object-kind="Connection"]').count() == 2
    assert page.locator('[data-workspace-tool="CONNECTION"]').count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_placing_node_at_crossing_creates_pin_joint_only_on_request(context, workspace_page):
    owner, project, material, section = context
    crossing = valid_payload(material, section)
    crossing['nodes'] = [
        {'client_key': 'n1', 'x_mm': 0, 'y_mm': 0, 'label': ''},
        {'client_key': 'n2', 'x_mm': 1000, 'y_mm': 1000, 'label': ''},
        {'client_key': 'n3', 'x_mm': 0, 'y_mm': 1000, 'label': ''},
        {'client_key': 'n4', 'x_mm': 1000, 'y_mm': 0, 'label': ''},
    ]
    crossing['physical_members'] = [
        {'client_key': 'm1', 'start_node_client_key': 'n1', 'end_node_client_key': 'n2', 'material_id': material.id, 'section_id': section.id, 'label': '', 'is_active': True},
        {'client_key': 'm2', 'start_node_client_key': 'n3', 'end_node_client_key': 'n4', 'material_id': material.id, 'section_id': section.id, 'label': '', 'is_active': True},
    ]
    crossing['connections'] = []
    crossing['supports'] = []
    crossing['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=crossing)
    page = workspace_page(user=owner, project=project)
    assert page.locator('[data-object-kind="Connection"]').count() == 0
    page.locator('[data-workspace-tool="NODE"]').click()
    point = page.evaluate("""() => {
      const svg = document.querySelector('[data-world-layer]');
      const p = new DOMPoint(500, 500).matrixTransform(svg.getScreenCTM());
      return {x:p.x,y:p.y};
    }""")
    page.mouse.click(point['x'], point['y'])
    joint = page.evaluate("""() => {
      const marker = document.querySelector('[data-object-kind="Connection"]');
      return {count:document.querySelectorAll('[data-object-kind="Connection"]').length,
        participants:marker?.getAttribute('aria-label')};
    }""")
    assert joint['count'] == 1
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    saved = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    assert len(saved['connections']) == 1
    assert saved['connections'][0]['participating_member_client_keys'] == ['m1', 'm2']
    node = next(item for item in saved['nodes'] if item['client_key'] == saved['connections'][0]['geometry_node_client_key'])
    assert (node['x_mm'], node['y_mm']) == (500, 500)


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_node_tool_can_activate_joint_on_legacy_unconnected_endpoint(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['connections'] = []
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    assert page.locator('[data-object-kind="Connection"]').count() == 1


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_support_and_load_can_target_visible_node(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['connections'] = []
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    assert page.locator('[data-object-kind="Support"]').count() == 1
    page.locator('[data-workspace-tool="LOAD"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    assert page.locator('[data-object-kind="NodeLoad"]').count() == 1
    assert page.locator('[data-object-kind="Connection"]').count() == 1
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    saved = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    assert saved['supports'][0]['target_connection_client_key'] == saved['node_loads'][0]['target_connection_client_key'] == saved['connections'][0]['client_key']


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_node_target_rejects_isolated_and_ambiguous_connections(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const {applyEditorAction} = await import('/static/projects/workspace/editor.js');
      const draft={nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:''},{client_key:'n2',x_mm:100,y_mm:0,label:''}],physical_members:[{client_key:'m1',start_node_client_key:'n1',end_node_client_key:'n2',material_id:1,section_id:1,label:'',is_active:true}],connections:[],supports:[],node_loads:[]};
      const support={client_key:'s1',support_type:'PINNED',restrained_axis:null};
      const added=applyEditorAction(draft,{type:'CREATE_SUPPORT_AT_NODE',nodeClientKey:'n1',support});
      const fail=(source,key)=>{try{applyEditorAction(source,{type:'CREATE_SUPPORT_AT_NODE',nodeClientKey:key,support})}catch(error){return error.code}};
      const isolated={...draft,physical_members:[]};
      const ambiguous={...draft,connections:[{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:['m1']},{client_key:'c2',geometry_node_client_key:'n1',participating_member_client_keys:['m1']}]};
      return {created:added.connections.length,target:added.supports[0].target_connection_client_key,isolated:fail(isolated,'n1'),ambiguous:fail(ambiguous,'n1'),unchanged:draft.connections.length};
    }""")
    assert result == {'created': 1, 'target': 'connection-1', 'isolated': 'NODE_NOT_ON_MEMBER', 'ambiguous': 'MULTIPLE_JOINTS_AT_NODE', 'unchanged': 0}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_window_and_crossing_selection(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {objectsInMarquee} = await import('/static/projects/workspace/selection-geometry.js');
      const objects=[{kind:'PHYSICAL_MEMBER',clientKey:'m1',hit:{type:'SEGMENT',start:{x:0,y:50},end:{x:100,y:50}}},{kind:'GEOMETRY_NODE',clientKey:'n1',hit:{type:'POINT',point:{x:50,y:50}}}];
      const rect={left:40,right:60,top:40,bottom:60};
      return {crossing:objectsInMarquee(rect,objects,'CROSSING'),window:objectsInMarquee(rect,objects,'WINDOW')};
    }""")
    assert result == {'crossing':[{'kind':'PHYSICAL_MEMBER','clientKey':'m1'},{'kind':'GEOMETRY_NODE','clientKey':'n1'}], 'window':[{'kind':'GEOMETRY_NODE','clientKey':'n1'}]}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_marquee_drag_selects_without_creating_node(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    canvas = page.locator('#workspace-canvas')
    box = canvas.bounding_box()
    page.locator('[data-workspace-tool="NODE"]').click()
    before = page.locator('[data-object-kind="GeometryNode"]').count()
    page.mouse.move(box['x']+box['width']*.2, box['y']+box['height']*.2)
    page.mouse.down()
    page.mouse.move(box['x']+box['width']*.7, box['y']+box['height']*.7, steps=5)
    page.mouse.up()
    assert page.locator('[data-object-kind="GeometryNode"]').count() == before


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_batch_delete_preserves_unselected_joints_as_incomplete(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {applyEditorAction} = await import('/static/projects/workspace/editor.js');
      const nodes=['n1','n2','n3'].map((client_key,i)=>({client_key,x_mm:i*100,y_mm:0,label:''}));
      const member=(client_key,start,end)=>({client_key,start_node_client_key:start,end_node_client_key:end,material_id:1,section_id:1,label:'',is_active:true});
      const draft={nodes,physical_members:[member('m1','n1','n2'),member('m2','n2','n3')],connections:[{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:['m1']},{client_key:'c2',geometry_node_client_key:'n2',participating_member_client_keys:['m1','m2']},{client_key:'c3',geometry_node_client_key:'n3',participating_member_client_keys:['m2']}],supports:[],node_loads:[]};
      const single=applyEditorAction(draft,{type:'DELETE_OBJECTS',targets:[{kind:'PHYSICAL_MEMBER',clientKey:'m1'}]});
      const next=applyEditorAction(draft,{type:'DELETE_OBJECTS',targets:[{kind:'PHYSICAL_MEMBER',clientKey:'m1'},{kind:'PHYSICAL_MEMBER',clientKey:'m2'},{kind:'CONNECTION',clientKey:'c1'},{kind:'CONNECTION',clientKey:'c2'},{kind:'CONNECTION',clientKey:'c3'}]});
      const loaded={...draft,supports:[{client_key:'s1',target_connection_client_key:'c1',support_type:'PINNED',restrained_axis:null}]};
      const loadedAfter=applyEditorAction(loaded,{type:'DELETE_OBJECTS',targets:[{kind:'PHYSICAL_MEMBER',clientKey:'m1'}]});
      return {members:next.physical_members.length,joints:next.connections.length,nodes:next.nodes.length,singleJoint:single.connections[0].participating_member_client_keys,loadedSupport:loadedAfter.supports[0].target_connection_client_key,original:draft.physical_members.length};
    }""")
    assert result == {'members':0,'joints':0,'nodes':3,'singleJoint':[None],'loadedSupport':'c1','original':2}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_delete_keeps_unselected_connection_as_incomplete(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-client-key="m1"] line').click(force=True)
    page.on('dialog', lambda dialog: dialog.accept())
    page.keyboard.press('Delete')
    assert page.locator('[data-client-key="m1"]').count() == 0
    assert page.locator('[data-client-key="c1"]').count() == 1
    assert '需要重新指定' in page.locator('[data-delete-feedback]').inner_text()
    assert page.locator('#workspace-save-status').inner_text() == '未保存修改：有'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_delete_key_ignores_editable_input_and_deletes_selected_node(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas = page.locator('#workspace-canvas')
    canvas.click(position={'x': 200, 'y': 200})
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
    page.locator('.ux-precision summary').click()
    command = page.locator('[data-cad-command-input]')
    command.fill('123')
    command.press('Backspace')
    assert command.input_value() == '12'
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
    page.locator('[data-workspace-tool="SELECT"]').click()
    page.locator('[data-object-kind="GeometryNode"]').click(force=True)
    page.keyboard.press('Delete')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_marquee_direction_selects_crossing_but_not_window(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    line = page.locator('[data-client-key="m1"] line')
    box = line.bounding_box()
    center_x = box['x'] + box['width'] / 2
    center_y = box['y'] + box['height'] / 2
    page.mouse.move(center_x - 25, center_y - 20)
    page.mouse.down()
    page.mouse.move(center_x + 25, center_y + 20, steps=5)
    page.mouse.up()
    assert page.locator('[data-client-key="m1"]').get_attribute('data-selected') == 'false'
    page.mouse.move(center_x + 25, center_y - 20)
    page.mouse.down()
    page.mouse.move(center_x - 25, center_y + 20, steps=5)
    page.mouse.up()
    assert page.locator('[data-client-key="m1"]').get_attribute('data-selected') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_two_click_marquee_previews_without_holding_and_keeps_direction(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    canvas = page.locator('#workspace-canvas')
    box = page.locator('[data-client-key="m1"] line').bounding_box()
    center_x = box['x'] + box['width'] / 2
    center_y = box['y'] + box['height'] / 2
    original_view = canvas.locator('[data-world-layer]').get_attribute('transform')

    page.mouse.click(center_x - 25, center_y - 20)
    page.mouse.move(center_x + 25, center_y + 20, steps=5)
    assert canvas.locator('[data-selection-marquee]').count() == 1
    assert canvas.locator('[data-world-layer]').get_attribute('transform') == original_view
    page.mouse.click(center_x + 25, center_y + 20)
    assert canvas.locator('[data-selection-marquee]').count() == 0
    assert page.locator('[data-client-key="m1"]').get_attribute('data-selected') == 'false'

    page.mouse.click(center_x + 25, center_y - 20)
    page.mouse.move(center_x - 25, center_y + 20, steps=5)
    assert canvas.locator('[data-selection-marquee]').count() == 1
    page.mouse.click(center_x - 25, center_y + 20)
    assert canvas.locator('[data-selection-marquee]').count() == 0
    assert page.locator('[data-client-key="m1"]').get_attribute('data-selected') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_two_click_marquee_escape_cancels_and_direct_click_still_selects(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    box = page.locator('[data-client-key="m1"] line').bounding_box()
    center_x = box['x'] + box['width'] / 2
    center_y = box['y'] + box['height'] / 2
    page.mouse.click(center_x - 25, center_y - 20)
    page.mouse.move(center_x + 25, center_y + 20)
    assert page.locator('[data-selection-marquee]').count() == 1
    page.keyboard.press('Escape')
    assert page.locator('[data-selection-marquee]').count() == 0
    page.locator('[data-client-key="m1"] line').click(force=True)
    assert page.locator('[data-client-key="m1"]').get_attribute('data-selected') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_middle_navigation_is_transparent_and_double_middle_fits(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    assert '终点' in page.locator('[data-modeling-instruction]').inner_text()
    # Keep the two measured-Fit operations in the same visible viewport;
    # Playwright otherwise scrolls this lower toolbar into view on click.
    page.locator('[data-cad-fit]').scroll_into_view_if_needed()
    box = canvas.bounding_box()
    x, y = box['x'] + box['width'] * .65, box['y'] + box['height'] * .55
    before = canvas.locator('[data-world-layer]').get_attribute('transform')
    page.mouse.move(x, y)
    page.mouse.down(button='middle')
    page.mouse.move(x + 60, y + 30, steps=5)
    page.mouse.up(button='middle')
    assert canvas.locator('[data-world-layer]').get_attribute('transform') != before
    assert page.locator('[data-workspace-tool="MEMBER"]').get_attribute('aria-pressed') == 'true'
    assert '终点' in page.locator('[data-modeling-instruction]').inner_text()
    expected_fit = """async()=>{const {readCoordinateSpace,visibleSvgViewport}=await import('/static/projects/workspace/coordinate-space.js');const svg=document.querySelector('#workspace-canvas'),v=visibleSvgViewport(svg,readCoordinateSpace(svg));const nodes=JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft.nodes;const xs=nodes.map(n=>n.x_mm),ys=nodes.map(n=>n.y_mm);const cx=(Math.min(...xs)+Math.max(...xs))/2,cy=(Math.min(...ys)+Math.max(...ys))/2;const scale=Math.min((v.width-80)/Math.max(100,Math.max(...xs)-Math.min(...xs)),(v.height-80)/Math.max(100,Math.max(...ys)-Math.min(...ys)));return {a:scale,d:-scale,e:v.left+v.width/2-scale*cx,f:v.top+v.height/2+scale*cy};}"""
    expected_middle = page.evaluate(expected_fit)
    page.mouse.click(x, y, button='middle', click_count=2)
    actual = page.evaluate("()=>{const m=document.querySelector('[data-world-layer]').transform.baseVal.consolidate().matrix;return {a:m.a,d:m.d,e:m.e,f:m.f}}")
    assert actual == pytest.approx(expected_middle,abs=1e-4)
    page.locator('[data-cad-fit]').scroll_into_view_if_needed()
    page.locator('[data-cad-fit]').click()
    # Native focus can scroll the document during click; evaluate its actual
    # resulting visible viewport, not the pre-click rectangle.
    expected_toolbar = page.evaluate(expected_fit)
    actual = page.evaluate("()=>{const m=document.querySelector('[data-world-layer]').transform.baseVal.consolidate().matrix;return {a:m.a,d:m.d,e:m.e,f:m.f}}")
    assert actual == pytest.approx(expected_toolbar,abs=1e-4)
    assert '终点' in page.locator('[data-modeling-instruction]').inner_text()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_escape_and_repeat_last_tool_respect_input_focus(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('#workspace-canvas').click(position={'x': 200, 'y': 200})
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
    page.locator('#workspace-canvas').focus()
    page.keyboard.press('Escape')
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute('aria-pressed') == 'true'
    page.keyboard.press('Enter')
    assert page.locator('[data-workspace-tool="NODE"]').get_attribute('aria-pressed') == 'true'
    page.keyboard.press('Escape')
    page.locator('.ux-precision summary').click()
    command = page.locator('[data-cad-command-input]')
    command.fill('12.4,7.6')
    command.press('Space')
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute('aria-pressed') == 'true'
    assert command.input_value().endswith(' ')
    page.locator('#workspace-canvas').focus()
    page.keyboard.press('Space')
    assert page.locator('[data-workspace-tool="NODE"]').get_attribute('aria-pressed') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_completed_member_can_repeat_with_enter_and_space(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    page.locator('#workspace-canvas').click(position={'x': 300, 'y': 100})
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 2
    canvas = page.locator('#workspace-canvas')
    canvas.focus()
    page.keyboard.press('Escape')
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute('aria-pressed') == 'true'
    page.keyboard.press('Enter')
    assert page.locator('[data-workspace-tool="MEMBER"]').get_attribute('aria-pressed') == 'true'
    page.keyboard.press('Escape')
    canvas.focus()
    page.keyboard.press('Space')
    assert page.locator('[data-workspace-tool="MEMBER"]').get_attribute('aria-pressed') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_shift_temporarily_inverts_ortho_without_changing_button(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    page.locator('.ux-precision summary').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('#workspace-canvas').focus()
    ortho = page.locator('[data-cad-ortho]')
    indicator = page.locator('#workspace-snap-indicator')
    assert ortho.get_attribute('aria-pressed') == 'false'
    page.keyboard.down('Shift')
    assert 'ORTHO: 开' in indicator.inner_text()
    assert ortho.get_attribute('aria-pressed') == 'false'
    page.keyboard.up('Shift')
    assert 'ORTHO: 关' in indicator.inner_text()
    ortho.click()
    page.locator('#workspace-canvas').focus()
    page.keyboard.down('Shift')
    assert 'ORTHO: 关' in indicator.inner_text()
    assert ortho.get_attribute('aria-pressed') == 'true'
    page.keyboard.up('Shift')
    assert 'ORTHO: 开' in indicator.inner_text()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_grid_display_and_snap_controls_are_independent(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    grid = page.locator('[data-cad-grid-visible]')
    snap = page.locator('[data-cad-snap]')
    objects = page.locator('[data-cad-object-snap]')
    assert grid.count() == 1 and objects.count() == 1
    assert page.locator('[data-canvas-grid]').count() == 1
    assert (grid.get_attribute('aria-pressed'), snap.get_attribute('aria-pressed'), objects.get_attribute('aria-pressed')) == ('true', 'true', 'true')
    grid.click()
    assert page.locator('[data-canvas-grid]').count() == 0
    assert snap.get_attribute('aria-pressed') == 'true'
    grid.click()
    snap.click()
    assert page.locator('[data-canvas-grid]').count() == 1
    assert objects.get_attribute('aria-pressed') == 'true'
    assert snap.get_attribute('aria-pressed') == 'false'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_drafting_status_remains_at_viewport_bottom(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    page.evaluate('window.scrollTo(0, 0)')
    status = page.locator('#workspace-status-bar').bounding_box()
    viewport_height = page.evaluate('window.innerHeight')
    assert status is not None
    assert abs(status['y'] + status['height'] - viewport_height) <= 2


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_node_snap_marker_and_tracking_are_visual_only(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="NODE"]').click()
    box = page.locator('[data-client-key="n1"] circle').bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    before = page.locator('[data-object-kind="GeometryNode"]').count()
    page.mouse.move(x, y)
    marker = page.locator('[data-cad-snap-marker][data-snap-type="NODE"]')
    assert marker.count() == 1
    assert '节点' in marker.text_content()
    page.mouse.move(x + 90, y)
    assert page.locator('[data-cad-tracking-guide]').count() == 1
    assert page.locator('[data-object-kind="GeometryNode"]').count() == before
    page.locator('[data-cad-tracking]').click()
    assert page.locator('[data-cad-tracking-guide]').count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_object_snap_toggle_does_not_turn_off_grid_snap(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="NODE"]').click()
    node = page.locator('[data-client-key="n1"] circle').bounding_box()
    x, y = node['x'] + node['width'] / 2, node['y'] + node['height'] / 2
    page.mouse.move(x, y)
    assert page.locator('[data-cad-snap-marker][data-snap-type="NODE"]').count() == 1
    page.locator('[data-cad-object-snap]').click()
    page.mouse.move(x + 1, y + 1)
    assert page.locator('[data-cad-snap-marker][data-snap-type="GRID"]').count() == 1
    assert page.locator('[data-cad-snap]').get_attribute('aria-pressed') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_hover_preselection_does_not_change_selection(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    member = page.locator('[data-client-key="m1"]')
    member.locator('line').hover(force=True)
    assert member.get_attribute('data-hovered') == 'true'
    assert member.get_attribute('data-selected') == 'false'
    assert page.locator('#workspace-properties-panel [data-property-identity]').count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_node_grip_drag_previews_and_preserves_identity(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-client-key="n1"] circle').click(force=True)
    page.locator('[data-cad-overlap-chooser]').get_by_role('button', name='节点 左').click()
    grip = page.locator('[data-cad-node-grip]')
    assert grip.count() == 1
    box = grip.bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 50, y - 20, steps=5)
    assert page.locator('[data-cad-grip-preview]').count() >= 1
    assert page.locator('[data-object-kind="GeometryNode"]').count() == len(draft['nodes'])
    page.mouse.up()
    assert page.locator('[data-cad-grip-preview]').count() == 0
    assert page.locator('[data-client-key="n1"]').count() == 1
    assert page.locator('[data-client-key="m1"]').count() == 1
    assert page.locator('[data-client-key="n1"] circle').first.get_attribute('cx') != '0'
    assert page.locator('#workspace-save-status').text_content() == '未保存修改：有'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_grip_rejects_move_onto_existing_node_without_topology_change(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-client-key="n1"] circle').click(force=True)
    page.locator('[data-cad-overlap-chooser]').get_by_role('button', name='节点 左').click()
    start = page.locator('[data-cad-node-grip]').bounding_box()
    end = page.locator('[data-client-key="n2"] circle').bounding_box()
    sx, sy = start['x'] + start['width'] / 2, start['y'] + start['height'] / 2
    ex, ey = end['x'] + end['width'] / 2, end['y'] + end['height'] / 2
    page.mouse.move(sx, sy)
    page.mouse.down()
    page.mouse.move(ex, ey, steps=10)
    page.mouse.up()
    assert '目标位置已有节点' in page.locator('#workspace-error').inner_text()
    assert page.locator('[data-client-key="n1"] circle').first.get_attribute('cx') == '0'
    assert page.locator('[data-object-kind="GeometryNode"]').count() == len(draft['nodes'])
    assert page.locator('[data-object-kind="Connection"]').count() == len(draft['connections'])
    assert page.locator('#workspace-save-status').text_content() == '未保存修改：无'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_node_move_rejects_disconnecting_interior_joint(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['nodes'].append({'client_key': 'n3', 'x_mm': 500, 'y_mm': 0, 'label': '中点'})
    draft['connections'].append({'client_key': 'c3', 'geometry_node_client_key': 'n3', 'participating_member_client_keys': ['m1']})
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-client-key="n3"] circle').click(force=True)
    page.locator('[data-cad-overlap-chooser]').get_by_role('button', name='节点 中点').click()
    grip = page.locator('[data-cad-node-grip]').bounding_box()
    x, y = grip['x'] + grip['width'] / 2, grip['y'] + grip['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y - 50, steps=5)
    page.mouse.up()
    assert page.locator('[data-client-key="n3"] circle').first.get_attribute('cy') == '0'
    assert '连接' in page.locator('#workspace-error').inner_text()
    assert page.locator('#workspace-save-status').inner_text() == '未保存修改：无'
    y_input = page.locator('[data-property-y]')
    y_input.fill('100')
    y_input.press('Tab')
    assert page.locator('[data-property-y]').input_value() == '0'
    assert page.locator('#workspace-save-status').inner_text() == '未保存修改：无'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_double_click_focuses_editable_properties(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-client-key="n1"] circle').dblclick(force=True)
    assert page.locator('[data-property-identity]').text_content() == '节点 左'
    assert page.evaluate("document.activeElement?.hasAttribute('data-property-x')") is True


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_ambiguous_nearby_objects_require_explicit_choice(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    node = page.locator('[data-client-key="n1"] circle')
    node.scroll_into_view_if_needed()
    box = node.bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    page.mouse.click(x + 8.5, y - 4.5)
    chooser = page.locator('[data-cad-overlap-chooser]')
    assert chooser.count() == 1
    assert '节点 左' in chooser.inner_text()
    assert '连接' in chooser.inner_text()
    assert page.locator('[data-client-key="n1"]').get_attribute('data-selected') == 'false'
    chooser.get_by_role('button', name='节点 左').click()
    assert chooser.count() == 0
    assert page.locator('[data-client-key="n1"]').get_attribute('data-selected') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_exact_overlap_requires_explicit_choice(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-client-key="n1"] circle').click(force=True)
    chooser = page.locator('[data-cad-overlap-chooser]')
    assert chooser.count() == 1
    assert '节点 左' in chooser.inner_text()
    assert '连接' in chooser.inner_text()
    assert page.locator('[data-client-key="n1"]').get_attribute('data-selected') == 'false'
    chooser.get_by_role('button', name='节点 左').click()
    assert page.locator('[data-client-key="n1"]').get_attribute('data-selected') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_crossing_marquee_has_distinct_visual_feedback(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    box = page.locator('#workspace-canvas').bounding_box()
    # Measured Fit now excludes the fixed status bar. Use actual blank Canvas
    # above the model rather than assuming its old visual center.
    x, y = box['x'] + box['width'] / 2, box['y'] + 100
    page.mouse.click(x + 40, y - 40)
    page.mouse.move(x - 40, y + 40)
    assert page.locator('[data-selection-marquee]').get_attribute('data-selection-mode') == 'CROSSING'
    page.keyboard.press('Escape')
    page.mouse.click(x - 40, y - 40)
    page.mouse.move(x + 40, y + 40)
    assert page.locator('[data-selection-marquee]').get_attribute('data-selection-mode') == 'WINDOW'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_undo_redo_create_and_delete_with_keyboard(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas.click(position={'x': 200, 'y': 200})
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
    canvas.focus()
    page.keyboard.press('ControlOrMeta+z')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0
    page.keyboard.press('ControlOrMeta+Shift+z')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
    page.locator('[data-workspace-tool="SELECT"]').click()
    page.locator('[data-object-kind="GeometryNode"] circle').click(force=True)
    page.keyboard.press('Delete')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0
    canvas.focus()
    page.keyboard.press('ControlOrMeta+z')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
    page.keyboard.press('ControlOrMeta+y')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_undo_after_save_keeps_current_server_version(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas.click(position={'x': 200, 'y': 200})
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    saved_version = page.locator('#workspace-draft-version').inner_text()
    canvas.focus()
    page.keyboard.press('ControlOrMeta+z')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0
    assert page.locator('#workspace-draft-version').inner_text() == saved_version
    assert page.locator('#workspace-save-status').inner_text() == '未保存修改：有'
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-status-bar').textContent.includes('未保存修改：无')")
    assert page.locator('#workspace-draft-version').inner_text() != saved_version


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_undo_after_save_does_not_rewrite_historical_analysis_run(context, workspace_page, monkeypatch):
    from copy import deepcopy
    from analysis.models import AnalysisRun
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    historical = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    original = (historical.model_revision.source_draft_version,
                deepcopy(historical.model_revision.physical_snapshot_json),
                deepcopy(historical.result_json))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('#workspace-canvas').click(position={'x': 200, 'y': 200})
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.locator('#workspace-canvas').focus()
    page.keyboard.press('ControlOrMeta+z')
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    monkeypatch.setenv('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
    historical = AnalysisRun.objects.select_related('model_revision').get(pk=historical.pk)
    assert (historical.model_revision.source_draft_version,
            historical.model_revision.physical_snapshot_json,
            historical.result_json) == original
    project.refresh_from_db()
    assert project.draft_version > original[0]


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_member_creation_with_new_endpoint_is_one_undo_step(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    canvas = page.locator('#workspace-canvas')
    canvas.click(position={'x': 300, 'y': 100})
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == len(draft['physical_members']) + 1
    assert page.locator('[data-object-kind="GeometryNode"]').count() == len(draft['nodes']) + 1
    canvas.focus()
    page.keyboard.press('ControlOrMeta+z')
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == len(draft['physical_members'])
    assert page.locator('[data-object-kind="GeometryNode"]').count() == len(draft['nodes'])


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_undo_keeps_native_editable_input_untouched(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('#workspace-canvas').click(position={'x': 200, 'y': 200})
    page.locator('.ux-precision summary').click()
    command = page.locator('[data-cad-command-input]')
    command.fill('12,34')
    command.press('ControlOrMeta+z')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_new_edit_after_undo_discards_redo(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas.click(position={'x': 180, 'y': 180})
    canvas.click(position={'x': 260, 'y': 180})
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 2
    canvas.focus()
    page.keyboard.press('ControlOrMeta+z')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1
    canvas.click(position={'x': 340, 'y': 180})
    assert page.locator('[data-cad-redo]').is_disabled()
    canvas.focus()
    page.keyboard.press('ControlOrMeta+Shift+z')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 2


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_undo_redo_support_and_load_property_edits(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-client-key="s1"] path').click(force=True)
    support = page.locator('[data-property-support-type]')
    support.select_option('ROLLER_X')
    canvas.focus()
    assert page.locator('[data-property-support-type]').count() == 1
    page.keyboard.press('ControlOrMeta+z')
    assert page.locator('[data-property-support-type]').input_value() == 'PINNED'
    page.keyboard.press('ControlOrMeta+Shift+z')
    assert page.locator('[data-property-support-type]').input_value() == 'ROLLER_X'
    page.locator('[data-client-key="l1"] [data-load-stem]').click(force=True)
    load = page.locator('[data-property-fy]')
    load.fill('-250')
    load.press('Tab')
    canvas.focus()
    page.keyboard.press('ControlOrMeta+z')
    assert page.locator('[data-property-fy]').input_value() == '-100'
    page.keyboard.press('ControlOrMeta+y')
    assert page.locator('[data-property-fy]').input_value() == '-250'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_property_edit_syncs_undo_button_and_saved_checkpoint(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['connections'] = []
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-client-key="n1"] circle').click(force=True)
    assert page.locator('[data-cad-undo]').is_disabled()
    label = page.locator('[data-property-label]')
    label.fill('新标签')
    label.press('Tab')
    assert page.locator('[data-cad-undo]').is_enabled()
    assert page.locator('#workspace-save-status').inner_text() == '未保存修改：有'
    label = page.locator('[data-property-label]')
    label.fill('左')
    label.press('Tab')
    assert page.locator('#workspace-save-status').inner_text() == '未保存修改：无'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_undo_redo_node_grip_move(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    canvas = page.locator('#workspace-canvas')
    page.locator('[data-client-key="n1"] circle').click(force=True)
    page.locator('[data-cad-overlap-chooser]').get_by_role('button', name='节点 左').click()
    box = page.locator('[data-cad-node-grip]').bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 60, y - 20, steps=5)
    page.mouse.up()
    moved_x = page.locator('[data-client-key="n1"] circle').first.get_attribute('cx')
    assert moved_x != '0'
    canvas.focus()
    page.keyboard.press('ControlOrMeta+z')
    assert page.locator('[data-client-key="n1"] circle').first.get_attribute('cx') == '0'
    page.keyboard.press('ControlOrMeta+Shift+z')
    assert page.locator('[data-client-key="n1"] circle').first.get_attribute('cx') == moved_x


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_pointer_dynamic_xy_and_explicit_relative_input(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas = page.locator('#workspace-canvas')
    box = canvas.bounding_box()
    page.mouse.move(box['x'] + 220, box['y'] + 220)
    overlay = page.locator('[data-cad-dynamic-overlay]')
    assert overlay.count() == 1
    assert overlay.is_visible()
    x_input = overlay.locator('[data-cad-x]')
    y_input = overlay.locator('[data-cad-y]')
    x_input.fill('12.4')
    x_input.press('Tab')
    assert page.evaluate("document.activeElement?.hasAttribute('data-cad-y')") is True
    y_input.fill('7.6')
    y_input.press('Enter')
    points = page.locator('[data-object-kind="GeometryNode"] circle')
    assert points.count() == 1
    assert (points.first.get_attribute('cx'), points.first.get_attribute('cy')) == ('12.4', '7.6')
    page.locator('.ux-precision summary').click()
    page.locator('[data-cad-relative-x]').fill('100')
    page.locator('[data-cad-relative-y]').fill('0')
    page.locator('[data-cad-relative-place]').click()
    assert points.count() == 2
    assert (points.last.get_attribute('cx'), points.last.get_attribute('cy')) == ('112.4', '7.6')
    page.locator('[data-cad-dynamic-input]').click()
    page.mouse.move(box['x'] + 240, box['y'] + 240)
    assert overlay.is_hidden()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_blank_dynamic_coordinate_is_not_zero(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas = page.locator('#workspace-canvas')
    box = canvas.bounding_box()
    page.mouse.move(box['x'] + 220, box['y'] + 220)
    x_input = page.locator('[data-cad-x]')
    y_input = page.locator('[data-cad-y]')
    x_input.fill('')
    y_input.fill('12')
    y_input.press('Enter')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 0
    assert '有效' in page.locator('#workspace-error').inner_text()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_decimal_node_save_reload_and_connected_node_noop(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    page.locator('.ux-precision summary').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    command = page.locator('[data-cad-command-input]')
    for point in ('12.4,7.6', '112.4,7.6'):
        command.fill(point)
        command.press('Enter')
    page.locator('[data-member-material]').select_option(str(material.id))
    page.locator('[data-member-section]').select_option(str(section.id))
    page.locator('[data-cad-fit]').click()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"] circle').click(force=True)
    page.locator('[data-client-key="node-2"] circle').click(force=True)
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('[data-client-key="node-1"] circle').click(force=True)
    assert '无' in page.locator('#workspace-save-status').inner_text()
    page.reload()
    saved = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    assert [(node['x_mm'], node['y_mm']) for node in saved['nodes']] == [(12.4,7.6),(112.4,7.6)]
    assert len(saved['physical_members']) == 1


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_numeric_node_reentry_does_not_layer_duplicate(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    page.locator('.ux-precision summary').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    command = page.locator('[data-cad-command-input]')
    for _ in range(2):
        command.fill('12.4,7.6')
        command.press('Enter')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 1


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_direct_joint_click_selects_node_and_shift_click_toggles(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-client-key="c1"] rect').click(force=True)
    page.locator('[data-cad-overlap-chooser]').get_by_role('button', name='节点 左').click()
    assert page.locator('[data-client-key="n1"]').get_attribute('data-selected') == 'true'
    page.locator('[data-client-key="c1"] rect').click(force=True, modifiers=['Shift'])
    page.locator('[data-cad-overlap-chooser]').get_by_role('button', name='节点 左').click()
    assert page.locator('[data-client-key="n1"]').get_attribute('data-selected') == 'false'
    page.locator('[data-client-key="n1"] circle').click(force=True)
    page.locator('[data-cad-overlap-chooser]').get_by_role('button', name='节点 左').click()
    page.locator('[data-client-key="n2"] circle').click(force=True, modifiers=['Shift'])
    assert page.locator('[data-client-key="n1"]').get_attribute('data-selected') == 'true'
    assert page.locator('[data-client-key="n2"]').get_attribute('data-selected') == 'true'
    assert '已选择 2 个对象' in page.locator('#workspace-properties-panel').inner_text()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_explicit_connection_delete_preserves_surviving_member(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {applyEditorAction} = await import('/static/projects/workspace/editor.js');
      const draft={nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:''},{client_key:'n2',x_mm:100,y_mm:0,label:''}],physical_members:[{client_key:'m1',start_node_client_key:'n1',end_node_client_key:'n2',material_id:1,section_id:1,label:'',is_active:true}],connections:[{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:['m1']}],supports:[],node_loads:[]};
      const next=applyEditorAction(draft,{type:'DELETE_OBJECTS',targets:[{kind:'CONNECTION',clientKey:'c1'}]});
      return {connections:next.connections.length,members:next.physical_members.length,original:draft.connections.length};
    }""")
    assert result == {'connections':0,'members':1,'original':1}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_middle_pan_does_not_consume_next_left_click(context, workspace_page):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    box = page.locator('#workspace-canvas').bounding_box()
    page.mouse.move(box['x']+box['width']*.5, box['y']+box['height']*.7)
    page.mouse.down(button='middle')
    page.mouse.move(box['x']+box['width']*.55, box['y']+box['height']*.7, steps=5)
    page.mouse.up(button='middle')
    page.locator('[data-client-key="m1"] line').click(force=True)
    assert page.locator('[data-client-key="m1"]').get_attribute('data-selected') == 'true'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_blank_project_creates_first_member_from_explicit_material_and_section(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)

    assert page.get_by_text(f"当前账号：{owner.username}").is_visible()
    assert page.get_by_text("可编辑（项目所有者）").is_visible()
    page.locator("[data-member-material]").select_option(str(material.id))
    page.locator("[data-member-section]").select_option(str(section.id))

    canvas = page.locator("#workspace-canvas")
    box = canvas.bounding_box()
    page.locator('[data-workspace-tool="NODE"]').click()
    canvas.click(position={"x": box["width"] * 0.35, "y": box["height"] * 0.5})
    canvas.click(position={"x": box["width"] * 0.65, "y": box["height"] * 0.5})
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"]').click()
    page.locator('[data-client-key="node-2"]').click()

    assert page.locator('[data-client-key="member-1"]').count() == 1
    page.evaluate("document.cookie = 'csrftoken=' + 'a'.repeat(32) + '; path=/'")
    page.locator("#workspace-save").click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    member = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft.physical_members[0]")
    assert member["material_id"] == material.id
    assert member["section_id"] == section.id


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_renderer_emits_stable_physical_svg(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(
        actor=owner,
        project=project,
        payload=valid_payload(material, section),
    )
    page = workspace_page(user=owner, project=project)

    rendered = page.evaluate(
        """async () => {
          const { renderWorkspace } = await import('/static/projects/workspace/renderer.js');
          const svg = document.getElementById('workspace-canvas');
          const bootstrap = JSON.parse(document.getElementById('workspace-bootstrap').textContent);
          const before = JSON.stringify(bootstrap.draft);
          renderWorkspace(svg, bootstrap.draft, { selectedObject: { kind: 'PhysicalMember', clientKey: 'm1' }, focusedObject: { kind: 'PhysicalMember', clientKey: 'm1' } });
          const first = svg.innerHTML;
          renderWorkspace(svg, bootstrap.draft, { selectedObject: { kind: 'PhysicalMember', clientKey: 'm1' }, focusedObject: { kind: 'PhysicalMember', clientKey: 'm1' } });
          return {
            unchangedDraft: before === JSON.stringify(bootstrap.draft),
            stable: first === svg.innerHTML,
            objects: [...svg.querySelectorAll('[data-object-kind]')].map((element) => ({
              key: element.dataset.clientKey,
              kind: element.dataset.objectKind,
              tabindex: element.getAttribute('tabindex'),
              role: element.getAttribute('role'),
              label: element.getAttribute('aria-label'),
              selected: element.getAttribute('data-selected'),
              focused: element.getAttribute('data-focused'),
            })),
                text: svg.textContent,
                markup: svg.innerHTML,
                selectedOutline: svg.querySelector('[data-client-key="m1"] [data-selection-outline]') !== null,
                bodyDash: svg.querySelector('[data-client-key="m1"] [data-member-body]').getAttribute('stroke-dasharray'),
                loadDirection: [...svg.querySelector('[data-client-key="l1"]').querySelectorAll('line')].map((line) => ({ y1: Number(line.getAttribute('y1')), y2: Number(line.getAttribute('y2')) })),
          };
        }"""
    )

    assert rendered['unchangedDraft'] is True
    assert rendered['stable'] is True
    assert {(item['key'], item['kind']) for item in rendered['objects']} == {
        ('n1', 'GeometryNode'), ('n2', 'GeometryNode'), ('m1', 'PhysicalMember'),
        ('c1', 'Connection'), ('s1', 'Support'), ('l1', 'NodeLoad'),
    }
    assert all(item['tabindex'] == '0' and item['role'] == 'button' and item['label'] for item in rendered['objects'])
    assert any(item['key'] == 'm1' and item['selected'] == 'true' and item['focused'] == 'true' for item in rendered['objects'])
    assert rendered['selectedOutline'] is True
    assert rendered['bodyDash'] == 'none'
    assert 'AnalysisElement' not in rendered['markup']
    assert rendered['loadDirection'][0]['y1'] > rendered['loadDirection'][0]['y2']


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_parser_and_state_transitions(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { parseCadInput } = await import('/static/projects/workspace/cad-input.js');
      const { transition } = await import('/static/projects/workspace/cad-state.js');
      const o = {x:100,y:200}; const s = (state,event) => transition(state,event);
      return {
        absolute: parseCadInput(' 1000 , 500 ', o), relative: parseCadInput('@ -2.5, 3', o), polar: parseCadInput('1000 < 30', o),
        empty: parseCadInput(' ', o), incomplete: parseCadInput('@100,', o), malformed: parseCadInput('NaN,0', o),
        absoluteWithoutOrigin: parseCadInput('1000,500', null),
        tools: ['SELECT','NODE','MEMBER'].map(tool => s({state:'IDLE',fieldIndex:null},{type:'SELECT_TOOL',tool})),
        pointer: [s({state:'DRAW_NODE',fieldIndex:null},{type:'POINTER_POINT',point:{x:1,y:2}}),s({state:'DRAW_MEMBER_WAIT_START',fieldIndex:null},{type:'POINTER_POINT',point:{x:1,y:2}}),s({state:'DRAW_MEMBER_WAIT_END',fieldIndex:null},{type:'POINTER_POINT',point:{x:1,y:2}}),s({state:'DYNAMIC_INPUT',fieldIndex:0},{type:'POINTER_POINT',point:{x:1,y:2}})],
        dynamic: [s({state:'DRAW_MEMBER_WAIT_END',fieldIndex:null},{type:'INPUT_CHANGE',mode:'DYNAMIC',field:'DISTANCE',value:'1'}),s({state:'DRAW_MEMBER_WAIT_END',fieldIndex:null},{type:'INPUT_CHANGE',mode:'DYNAMIC',field:'ANGLE',value:'30'})],
        enter: ['DRAW_NODE','DRAW_MEMBER_WAIT_START','DRAW_MEMBER_WAIT_END','DYNAMIC_INPUT'].map((state) => s({state,fieldIndex:state==='DYNAMIC_INPUT'?0:null},{type:'ENTER',valid:true,point:{x:1,y:2}})),
        invalid: s({state:'DRAW_MEMBER_WAIT_END',fieldIndex:null},{type:'ENTER',valid:false}), esc: s({state:'DRAW_MEMBER_WAIT_END',fieldIndex:null},{type:'ESC'}),
        missingPoint: s({state:'DRAW_MEMBER_WAIT_START',fieldIndex:null},{type:'ENTER',valid:true}), nonFinitePoint: s({state:'DRAW_MEMBER_WAIT_END',fieldIndex:null},{type:'POINTER_POINT',point:{x:NaN,y:0}}),
      };
    }""")
    assert result['absolute'] == {'ok': True, 'kind': 'ABSOLUTE', 'point': {'x': 1000, 'y': 500}}
    assert result['relative'] == {'ok': True, 'kind': 'RELATIVE', 'point': {'x': 97.5, 'y': 203}}
    assert result['polar']['kind'] == 'POLAR' and result['polar']['point']['x'] == pytest.approx(100 + 1000 * 3**0.5 / 2)
    assert result['empty']['code'] == 'EMPTY' and result['incomplete']['code'] == 'INCOMPLETE' and result['malformed']['code'] == 'MALFORMED'
    assert result['absoluteWithoutOrigin']['ok'] is True
    assert result['tools'] == [{'state':'SELECTING','fieldIndex':None},{'state':'DRAW_NODE','fieldIndex':None},{'state':'DRAW_MEMBER_WAIT_START','fieldIndex':None}]
    assert result['pointer'] == [{'state':'DRAW_NODE','fieldIndex':None},{'state':'DRAW_MEMBER_WAIT_END','fieldIndex':None},{'state':'DRAW_MEMBER_WAIT_START','fieldIndex':None},{'state':'DYNAMIC_INPUT','fieldIndex':0}]
    assert result['dynamic'] == [{'state':'DYNAMIC_INPUT','fieldIndex':0},{'state':'DYNAMIC_INPUT','fieldIndex':1}]
    assert result['enter'] == [{'state':'DRAW_NODE','fieldIndex':None},{'state':'DRAW_MEMBER_WAIT_END','fieldIndex':None},{'state':'DRAW_MEMBER_WAIT_START','fieldIndex':None},{'state':'DRAW_MEMBER_WAIT_START','fieldIndex':None}]
    assert result['invalid'] == {'state':'DRAW_MEMBER_WAIT_END','fieldIndex':None} and result['esc'] == {'state':'IDLE','fieldIndex':None}
    assert result['missingPoint'] == {'state':'DRAW_MEMBER_WAIT_START','fieldIndex':None} and result['nonFinitePoint'] == {'state':'DRAW_MEMBER_WAIT_END','fieldIndex':None}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_cad_keyboard_tab_accessibility(context, workspace_page):
    owner, project, _, _ = context; page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => { const { transition } = await import('/static/projects/workspace/cad-state.js'); return [transition({state:'DYNAMIC_INPUT',fieldIndex:0},{type:'TAB'}),transition({state:'DYNAMIC_INPUT',fieldIndex:1},{type:'TAB'}),transition({state:'DRAW_NODE',fieldIndex:null},{type:'TAB'})]; }""")
    assert result == [{'state':'DYNAMIC_INPUT','fieldIndex':1},{'state':'DYNAMIC_INPUT','fieldIndex':0},{'state':'DRAW_NODE','fieldIndex':None}]


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_member_numeric_endpoint_uses_visible_dynamic_fields(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    page.locator('.ux-precision summary').click()
    page.locator("[data-member-material]").select_option(str(material.id))
    page.locator("[data-member-section]").select_option(str(section.id))
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator("[data-cad-command-input]").fill("0,0")
    page.locator("[data-cad-command-input]").press("Enter")
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"]').click()

    assert page.locator("[data-cad-distance]").is_enabled()
    assert page.locator("[data-cad-angle]").is_enabled()
    page.locator("[data-cad-distance]").fill("1000")
    page.locator("[data-cad-angle]").fill("30")
    page.locator("[data-cad-angle]").press("Enter")

    assert page.locator('[data-client-key="member-1"]').count() == 1
    assert page.locator('[data-client-key="node-2"]').count() == 1
    assert "1000" in page.locator("#workspace-delta-length").text_content()
    assert "30" in page.locator("#workspace-angle").text_content()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_member_dynamic_tab_escape_and_blank_pointer_endpoint(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    page.locator('.ux-precision summary').click()
    page.locator("[data-member-material]").select_option(str(material.id))
    page.locator("[data-member-section]").select_option(str(section.id))
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator("[data-cad-command-input]").fill("0,0")
    page.locator("[data-cad-command-input]").press("Enter")
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"]').click()

    distance = page.locator("[data-cad-distance]")
    angle = page.locator("[data-cad-angle]")
    distance.focus()
    distance.press("Tab")
    page.wait_for_function("document.activeElement === document.querySelector('[data-cad-angle]')")
    angle.press("Tab")
    page.wait_for_function("document.activeElement === document.querySelector('[data-cad-distance]')")
    distance.press("Escape")
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute("aria-pressed") == "true"

    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"]').click()
    canvas = page.locator("#workspace-canvas")
    box = canvas.bounding_box()
    canvas.click(position={"x": box["width"] * 0.72, "y": box["height"] * 0.35})
    assert page.locator('[data-client-key="member-1"]').count() == 1
    assert page.locator('[data-client-key="node-2"]').count() == 1


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_member_pointer_preview_and_esc_cancel_all_transient_modeling(context, workspace_page):
    """Removing preview rendering or leaving a tool active after Esc breaks this contract."""
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('.ux-precision summary').click()
    canvas = page.locator("#workspace-canvas")
    canvas_box = canvas.bounding_box()
    original_nodes = page.locator('[data-object-kind="GeometryNode"]').count()
    original_members = page.locator('[data-object-kind="PhysicalMember"]').count()

    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    canvas.hover(position={"x": canvas_box["width"] * 0.55, "y": canvas_box["height"] * 0.3})

    preview = page.locator("[data-cad-member-preview]")
    assert preview.count() == 1
    assert preview.evaluate("element => getComputedStyle(element).pointerEvents") == "none"
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == original_members

    page.locator("[data-cad-command-input]").press("Escape")
    assert preview.count() == 0
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute("aria-pressed") == "true"
    canvas.click(position={"x": canvas_box["width"] * 0.65, "y": canvas_box["height"] * 0.25})
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == original_members

    page.locator('[data-workspace-tool="NODE"]').click()
    command = page.locator("[data-cad-command-input]")
    command.fill("1200,700")
    command.press("Escape")
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute("aria-pressed") == "true"
    canvas.click(position={"x": canvas_box["width"] * 0.7, "y": canvas_box["height"] * 0.4})
    assert page.locator('[data-object-kind="GeometryNode"]').count() == original_nodes


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_pointer_snap_markers_and_unconnected_intersection_warning_are_visual_only(context, workspace_page):
    """Removing a marker/warning or accidentally creating topology must fail this journey."""
    owner, project, material, section = context
    crossing = valid_payload(material, section)
    crossing["nodes"] = [
        {"client_key": "n1", "x_mm": 0, "y_mm": 0, "label": ""},
        {"client_key": "n2", "x_mm": 1000, "y_mm": 1000, "label": ""},
        {"client_key": "n3", "x_mm": 0, "y_mm": 1000, "label": ""},
        {"client_key": "n4", "x_mm": 1000, "y_mm": 0, "label": ""},
    ]
    crossing["physical_members"] = [
        {"client_key": "m1", "start_node_client_key": "n1", "end_node_client_key": "n2", "material_id": material.id, "section_id": section.id, "label": "", "is_active": True},
        {"client_key": "m2", "start_node_client_key": "n3", "end_node_client_key": "n4", "material_id": material.id, "section_id": section.id, "label": "", "is_active": True},
    ]
    crossing["connections"] = []
    crossing["supports"] = []
    crossing["node_loads"] = []
    save_physical_draft(actor=owner, project=project, payload=crossing)
    page = workspace_page(user=owner, project=project)
    canvas = page.locator("#workspace-canvas")
    connection_count = page.locator('[data-object-kind="Connection"]').count()
    page.locator('[data-workspace-tool="NODE"]').click()

    page.locator('[data-client-key="n1"] circle').hover(force=True)
    assert '节点' in page.locator('[data-cad-snap-marker][data-snap-type="NODE"]').text_content()

    canvas_box = canvas.bounding_box()
    canvas.hover(position={"x": canvas_box["width"] * 0.2, "y": canvas_box["height"] * 0.3}, force=True)
    assert '网格' in page.locator('[data-cad-snap-marker][data-snap-type="GRID"]').text_content()

    crossing_screen = page.evaluate("""() => {
      const world = document.querySelector('[data-world-layer]');
      const point = new DOMPoint(500, 500).matrixTransform(world.getScreenCTM());
      return {x: point.x, y: point.y};
    }""")
    page.mouse.move(crossing_screen["x"], crossing_screen["y"])
    marker = page.locator('[data-cad-snap-marker][data-snap-type="INT"]')
    assert '交点' in marker.text_content()
    assert marker.evaluate("element => getComputedStyle(element).pointerEvents") == "none"
    assert "这里有构件交叉，但尚未建立连接。" in page.locator("[data-modeling-instruction]").text_content()
    assert page.locator('[data-object-kind="Connection"]').count() == connection_count


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_grid_snap_off_preserves_object_candidates(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('.ux-precision summary').click()
    result = page.evaluate("""async () => {
      const { resolvePointerPoint } = await import('/static/projects/workspace/geometry.js');
      const candidate = { kind:'NODE', canonicalKey:'NODE:n1', worldPoint:{x:12,y:34} };
      return resolvePointerPoint({ worldPointer:{x:12.1,y:34.1}, screenPointer:{x:12.1,y:34.1}, candidates:[candidate], viewTransform:{a:1,b:0,c:0,d:1,e:0,f:0}, origin:{x:0,y:0}, ortho:false, gridEnabled:false, explicitNumeric:false });
    }""")
    assert result['candidateKey'] == 'NODE:n1'
    page.locator("[data-cad-snap]").click()
    assert "对象捕捉: 开" in page.locator("#workspace-snap-indicator").text_content()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_visible_cad_controls_toggle_and_fit_without_module_imports(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('.ux-precision summary').click()

    ortho = page.locator("[data-cad-ortho]")
    snap = page.locator("[data-cad-snap]")
    fit = page.locator("[data-cad-fit]")
    assert ortho.get_attribute("aria-pressed") == "false"
    assert snap.get_attribute("aria-pressed") == "true"
    ortho.click()
    snap.click()
    assert ortho.get_attribute("aria-pressed") == "true"
    assert snap.get_attribute("aria-pressed") == "false"
    assert "ORTHO: 开" in page.locator("#workspace-snap-indicator").text_content()
    assert "SNAP: 关" in page.locator("#workspace-snap-indicator").text_content()

    canvas = page.locator("#workspace-canvas")
    before = canvas.locator("[data-world-layer]").get_attribute("transform")
    canvas.hover()
    page.mouse.wheel(0, -500)
    zoomed = canvas.locator("[data-world-layer]").get_attribute("transform")
    assert zoomed != before
    fit.click()
    fitted = canvas.locator("[data-world-layer]").get_attribute("transform")
    assert fitted != zoomed
    fit.click()
    assert canvas.locator("[data-world-layer]").get_attribute("transform") == fitted


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_numeric_modeling_accepts_absolute_relative_and_polar_input(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.locator('.ux-precision summary').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    command = page.locator("[data-cad-command-input]")

    for value in ("1000,500", "@1000,0", "1000<30"):
        command.fill(value)
        command.press("Enter")

    points = page.locator('[data-object-kind="GeometryNode"] circle').evaluate_all(
        "nodes => nodes.map(node => ({x:Number(node.getAttribute('cx')), y:Number(node.getAttribute('cy'))}))"
    )
    assert points[0] == {"x": 1000, "y": 500}
    assert points[1] == {"x": 2000, "y": 500}
    assert points[2]["x"] == pytest.approx(2000 + 1000 * 3**0.5 / 2)
    assert points[2]["y"] == pytest.approx(1000)
    command.fill("待取消")
    command.press("Escape")
    assert command.input_value() == ""
    command.press("Tab")
    assert page.evaluate("document.activeElement !== document.querySelector('[data-cad-command-input]')") is True


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_property_and_delete_controls_edit_persist_and_block_dependencies(context, workspace_page):
    from materials.models import Material
    from materials.services import create_section

    owner, project, material, section = context
    alternate_material = Material.objects.create(
        owner_user=owner, name="替代材料", E_MPa="2400", density_g_per_mm3="0.0008", source_type="MEASURED",
    )
    alternate_section = create_section(owner=owner, name="替代截面", definition={
        "schema_version": "section-definition-v1", "type": "rectangle",
        "width_mm": 2.0, "height_mm": 6.0, "density_g_per_mm3": 0.0008,
    })
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('.ux-precision summary').click()

    page.locator('[data-client-key="n2"] circle').click(force=True)
    page.locator("[data-property-x]").fill("1200")
    page.locator("[data-property-y]").fill("100")
    page.locator("[data-property-label]").fill("右端节点")
    page.locator("[data-property-label]").press("Tab")

    page.locator('[data-client-key="m1"] line').click(force=True)
    page.locator("[data-property-material]").select_option(str(alternate_material.id))
    page.locator("[data-property-section]").select_option(str(alternate_section.id))
    page.locator("[data-property-label]").fill("上弦杆")
    page.locator("[data-property-label]").press("Tab")
    page.locator("[data-property-active]").uncheck()

    page.locator('[data-client-key="c1"]').focus()
    page.keyboard.press("Enter")
    assert page.locator("[data-property-x]").input_value() == "0"
    page.on('dialog', lambda dialog: dialog.dismiss())
    page.locator("[data-property-delete]").click()
    assert page.locator("#workspace-error").text_content() == ""
    assert page.locator('[data-client-key="c1"]').count() == 1

    page.locator('[data-workspace-tool="NODE"]').click()
    command = page.locator("[data-cad-command-input]")
    command.fill("3000,3000")
    command.press("Enter")
    page.locator('[data-client-key="node-1"]').focus()
    page.keyboard.press("Enter")
    page.locator("[data-property-delete]").click()
    assert page.locator('[data-client-key="node-1"]').count() == 0

    page.evaluate("document.cookie = 'csrftoken=' + 'a'.repeat(32) + '; path=/'")
    page.locator("#workspace-save").click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    page.locator('[data-client-key="n2"] circle').click(force=True)
    assert page.locator("[data-property-x]").input_value() == "1200"
    assert page.locator("[data-property-y]").input_value() == "100"
    assert page.locator("[data-property-label]").input_value() == "右端节点"
    page.locator('[data-client-key="m1"] line').click(force=True)
    assert page.locator("[data-property-material]").input_value() == str(alternate_material.id)
    assert page.locator("[data-property-section]").input_value() == str(alternate_section.id)
    assert page.locator("[data-property-label]").input_value() == "上弦杆"
    assert page.locator("[data-property-active]").is_checked() is False


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_snap_resolver_priority_grid_and_intersection_boundary(context, workspace_page):
    owner, project, _, _ = context; page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => { const { resolvePointerPoint } = await import('/static/projects/workspace/geometry.js'); const base={worldPointer:{x:493,y:75},screenPointer:{x:493,y:75},viewTransform:{a:1,b:0,c:0,d:1,e:0,f:0},origin:{x:100,y:75},ortho:false,gridEnabled:true,explicitNumeric:false}; const candidates=[{kind:'INTERSECTION',canonicalKey:'INTERSECTION:m1|m2',worldPoint:{x:493,y:75}},{kind:'NODE',canonicalKey:'NODE:n2',worldPoint:{x:500,y:75}},{kind:'NODE',canonicalKey:'NODE:n1',worldPoint:{x:500,y:75}},{kind:'NODE',canonicalKey:'',worldPoint:{x:0,y:0}}]; const draft={connections:[]}; const before=JSON.stringify(candidates); return {node:resolvePointerPoint({...base,candidates}), reversed:resolvePointerPoint({...base,candidates:[...candidates].reverse()}), endpointNearest:resolvePointerPoint({...base,candidates:[{kind:'NODE',canonicalKey:'NODE:n1',worldPoint:{x:501,y:75}},{kind:'ENDPOINT',canonicalKey:'ENDPOINT:m1:START',worldPoint:{x:494,y:75}}]}), affine:resolvePointerPoint({...base,worldPointer:{x:0,y:0},screenPointer:{x:10,y:0},viewTransform:{a:.1,b:0,c:0,d:.1,e:0,f:0},candidates:[{kind:'NODE',canonicalKey:'NODE:scaled',worldPoint:{x:200,y:0}}]}), int:resolvePointerPoint({...base,candidates:[candidates[0]]}), malformed:resolvePointerPoint({...base,candidates:[null,{kind:'NODE',canonicalKey:'bad',worldPoint:{x:493,y:75}},{kind:'NODE',canonicalKey:{toString:()=> 'NODE:coerced'},worldPoint:{x:493,y:75}},{kind:'NODE',canonicalKey:'INTERSECTION:m1|m2',worldPoint:{x:493,y:75}},{kind:'INTERSECTION',canonicalKey:'INTERSECTION:m2|m1',worldPoint:{x:493,y:75}},{kind:'INTERSECTION',canonicalKey:'XXXXXXXXXXXXXa|b',worldPoint:{x:493,y:75}}]}), outside:resolvePointerPoint({...base,screenPointer:{x:506,y:75},candidates:[candidates[0]]}), numeric:resolvePointerPoint({...base,worldPointer:{x:1000,y:500},ortho:true,candidates,explicitNumeric:true}), unchanged:before===JSON.stringify(candidates), connectionCount:draft.connections.length}; }""")
    assert result['node'] == {'point':{'x':500,'y':75},'snapType':'NODE','candidateKey':'NODE:n1'}
    assert result['reversed'] == result['node'] and result['int']['snapType'] == 'INT' and result['outside']['snapType'] == 'GRID'
    assert result['endpointNearest'] == {'point':{'x':494,'y':75},'snapType':'NODE','candidateKey':'ENDPOINT:m1:START'} and result['affine']['candidateKey'] == 'NODE:scaled'
    assert result['malformed']['snapType'] == 'GRID'
    assert result['numeric'] == {'point':{'x':1000,'y':500},'snapType':None,'candidateKey':None} and result['unchanged'] is True and result['connectionCount'] == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_grid_midpoint_and_ortho_resolution(context, workspace_page):
    owner, project, _, _ = context; page = workspace_page(user=owner, project=project)
    result=page.evaluate("""async()=>{const {gridNearest,resolvePointerPoint}=await import('/static/projects/workspace/geometry.js');const f=(worldPointer,origin)=>resolvePointerPoint({worldPointer,screenPointer:worldPointer,candidates:[],viewTransform:{a:1,b:0,c:0,d:1,e:0,f:0},origin,ortho:true,gridEnabled:true,explicitNumeric:false});return {g:[493,247,50,-50,-150].map(gridNearest),h:f({x:493,y:90},{x:100,y:75}),v:f({x:125,y:487},{x:125,y:100}),tie:f({x:200,y:200},{x:0,y:0})}}""")
    assert result['g']==[493,247,50,-50,-150] and result['h']['point']=={'x':493,'y':75} and result['v']['point']=={'x':125,'y':487} and result['tie']['point']=={'x':200,'y':0}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_one_mm_grid_snap_and_ortho_preserve_locked_decimals(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {GRID_SPACING} = await import('/static/projects/workspace/canvas-interaction.js');
      const {gridNearest,resolvePointerPoint} = await import('/static/projects/workspace/geometry.js');
      const run = (point, origin) => resolvePointerPoint({worldPointer:point,
        screenPointer:point,candidates:[],viewTransform:{a:1,b:0,c:0,d:1,e:0,f:0},
        origin,ortho:true,gridEnabled:true,explicitNumeric:false}).point;
      return {spacing:GRID_SPACING,x:gridNearest(12.4),y:gridNearest(28.7),
        horizontal:run({x:13.2,y:7.8},{x:12.4,y:7.6}),
        vertical:run({x:12.6,y:29.2},{x:12.4,y:28.7})};
    }""")
    assert result == {'spacing': 1, 'x': 12, 'y': 29,
                      'horizontal': {'x': 13, 'y': 7.6},
                      'vertical': {'x': 12.4, 'y': 29}}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_grid_pattern_lod_stays_bounded_without_changing_snap(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {renderWorkspace} = await import('/static/projects/workspace/renderer.js');
      const {resolvePointerPoint} = await import('/static/projects/workspace/geometry.js');
      const svg=document.querySelector('#workspace-canvas');
      const draft=JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft;
      const snap=viewTransform=>resolvePointerPoint({worldPointer:{x:12.4,y:28.7},
        screenPointer:{x:12.4,y:28.7},candidates:[],viewTransform,
        origin:{x:0,y:0},ortho:false,gridEnabled:true,explicitNumeric:false}).point;
      const near={a:20,b:0,c:0,d:-20,e:0,f:0};
      const far={a:.05,b:0,c:0,d:-.05,e:0,f:0};
      renderWorkspace(svg,draft,{viewTransform:near});
      const nearLevels=svg.querySelector('[data-canvas-grid]').getAttribute('data-grid-visible-levels');
      renderWorkspace(svg,draft,{viewTransform:far});
      return {patterns:svg.querySelectorAll('[data-canvas-grid] pattern').length,
        lines:svg.querySelectorAll('[data-canvas-grid] line').length,
        nearLevels,farLevels:svg.querySelector('[data-canvas-grid]').getAttribute('data-grid-visible-levels'),
        nearSnap:snap(near),farSnap:snap(far)};
    }""")
    assert result == {'patterns': 3, 'lines': 0, 'nearLevels': 'minor medium major',
                      'farLevels': 'major', 'nearSnap': {'x': 12, 'y': 29},
                      'farSnap': {'x': 12, 'y': 29}}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('width,height', [(500, 500), (1000, 1000), (2000, 1000)])
def test_cad_large_view_pointer_navigation_keeps_grid_dom_bounded(context, workspace_page, width, height):
    owner, project, material, section = context
    draft = valid_payload(material, section)
    draft['nodes'][1]['x_mm'] = width
    draft['nodes'] += [
        {'client_key': 'n3', 'x_mm': width, 'y_mm': height, 'label': ''},
        {'client_key': 'n4', 'x_mm': 0, 'y_mm': height, 'label': ''},
    ]
    draft['physical_members'] += [
        {'client_key': 'm2', 'start_node_client_key': 'n2', 'end_node_client_key': 'n3', 'material_id': material.id, 'section_id': section.id, 'label': '', 'is_active': True},
        {'client_key': 'm3', 'start_node_client_key': 'n3', 'end_node_client_key': 'n4', 'material_id': material.id, 'section_id': section.id, 'label': '', 'is_active': True},
        {'client_key': 'm4', 'start_node_client_key': 'n4', 'end_node_client_key': 'n1', 'material_id': material.id, 'section_id': section.id, 'label': '', 'is_active': True},
    ]
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-cad-fit]').click()
    canvas = page.locator('#workspace-canvas')
    box = canvas.bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    requests = []
    page.on('request', lambda request: requests.append(request.url))
    page.locator('[data-workspace-tool="NODE"]').click()
    for offset in range(0, 100, 10):
        page.mouse.move(x + offset, y + offset / 2)
    before = canvas.locator('[data-world-layer]').get_attribute('transform')
    page.mouse.wheel(0, -300)
    page.mouse.down(button='middle')
    page.mouse.move(x + 35, y + 25, steps=5)
    page.mouse.up(button='middle')
    assert canvas.locator('[data-world-layer]').get_attribute('transform') != before
    assert canvas.locator('[data-canvas-grid] pattern').count() == 3
    assert canvas.locator('[data-canvas-grid] line').count() == 0
    assert canvas.locator('[data-cad-snap-marker]').count() <= 1
    assert requests == []


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_renderer_displays_snap_indicator_types_as_text(context, workspace_page):
    owner, project, _, _ = context; page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => { const { renderSnapIndicator } = await import('/static/projects/workspace/renderer.js'); const indicator=document.querySelector('#workspace-snap-indicator'); return ['NODE','INT','GRID'].map(snapType=>{renderSnapIndicator(indicator,{snapType});return {text:indicator.textContent, type:indicator.dataset.snapType};}); }""")
    assert result == [
        {'text':'SNAP: NODE','type':'NODE'},
        {'text':'SNAP: INT','type':'INT'},
        {'text':'SNAP: GRID','type':'GRID'},
    ]


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_editor_crossing_members_do_not_create_connection(context, workspace_page):
    owner, project, _, _ = context; page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => { const { applyEditorAction } = await import('/static/projects/workspace/editor.js'); const draft={schema_version:'physical-draft-v1',version:4,nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:''},{client_key:'n2',x_mm:100,y_mm:100,label:''},{client_key:'n3',x_mm:0,y_mm:100,label:''},{client_key:'n4',x_mm:100,y_mm:0,label:''}],physical_members:[{client_key:'m1',start_node_client_key:'n1',end_node_client_key:'n2',material_id:1,section_id:1,label:'',is_active:true}],connections:[],supports:[],node_loads:[]}; const crossing=applyEditorAction(draft,{type:'CREATE_MEMBER',member:{client_key:'m2',start_node_client_key:'n3',end_node_client_key:'n4',material_id:1,section_id:1,label:'',is_active:true}}); return {before:draft.connections.length,joints:crossing.connections.map(item=>item.geometry_node_client_key).sort(),unchanged:JSON.stringify(draft)}; }""")
    assert result['before'] == 0 and result['joints'] == ['n3', 'n4']


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_editor_mutations_are_immutable(context, workspace_page):
    owner, project, _, _ = context; page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => { const { applyEditorAction, EditorActionError } = await import('/static/projects/workspace/editor.js'); const { applyWorkspaceEditorAction } = await import('/static/projects/workspace/state.js'); const draft={schema_version:'physical-draft-v1',version:4,nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:'a'},{client_key:'n2',x_mm:100,y_mm:0,label:'b'}],physical_members:[{client_key:'m1',start_node_client_key:'n1',end_node_client_key:'n2',material_id:1,section_id:1,label:'m',is_active:true}],connections:[],supports:[],node_loads:[]}; const original=JSON.stringify(draft); const fail=(action,source=draft)=>{const before=JSON.stringify(source);try{applyEditorAction(source,action)}catch(error){return {name:error.name,code:error.code,unchanged:before===JSON.stringify(source)}}}; const node=applyEditorAction(draft,{type:'CREATE_NODE',node:{client_key:'n3',x_mm:50,y_mm:50,label:'c'}}); const member=applyEditorAction(node,{type:'CREATE_MEMBER',member:{client_key:'m2',start_node_client_key:'n1',end_node_client_key:'n3',material_id:2,section_id:3,label:'m2',is_active:true}}); const connection=applyEditorAction(member,{type:'CREATE_CONNECTION',connection:{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:['m1','m2']}}); const support=applyEditorAction(connection,{type:'CREATE_SUPPORT',support:{client_key:'s1',target_connection_client_key:'c1',support_type:'PINNED',restrained_axis:null}}); const load=applyEditorAction(support,{type:'CREATE_NODE_LOAD',nodeLoad:{client_key:'l1',target_connection_client_key:'c1',fx_N:1,fy_N:-2,label:'l'}}); const updated=applyEditorAction(load,{type:'UPDATE_OBJECT',target:{kind:'NODE_LOAD',clientKey:'l1'},changes:{fx_N:5,label:'new'}}); const deleted=applyEditorAction(updated,{type:'DELETE_OBJECT',target:{kind:'NODE_LOAD',clientKey:'l1'}}); const local=applyWorkspaceEditorAction({draft, draftVersion:4, readOnly:false},{type:'CREATE_NODE',node:{client_key:'n4',x_mm:4,y_mm:4,label:''}}); return {originalUnchanged:original===JSON.stringify(draft), collectionsNew:node.nodes!==draft.nodes&&member.physical_members!==node.physical_members&&connection.connections!==member.connections&&support.supports!==connection.supports&&load.node_loads!==support.node_loads, created:[node.nodes.at(-1).client_key,member.physical_members.at(-1).client_key,connection.connections.at(-1).client_key,support.supports.at(-1).client_key,load.node_loads.at(-1).client_key], updated:updated.node_loads[0], deletedLoads:deleted.node_loads.length, state:{dirty:local.dirty,version:local.draftVersion,key:local.draft.nodes.at(-1).client_key}, failures:{duplicate:fail({type:'CREATE_NODE',node:{client_key:'n1',x_mm:1,y_mm:1,label:''}}),malformed:fail({type:'CREATE_NODE',node:{client_key:'bad'}}),missing:fail({type:'CREATE_MEMBER',member:{client_key:'bad',start_node_client_key:'missing',end_node_client_key:'n1',material_id:1,section_id:1,label:'',is_active:true}}),forbidden:fail({type:'UPDATE_OBJECT',target:{kind:'CONNECTION',clientKey:'c1'},changes:{label:'x'}}),dependency:fail({type:'DELETE_OBJECT',target:{kind:'PHYSICAL_MEMBER',clientKey:'m1'}},connection)}, analysis:JSON.stringify(deleted).includes('AnalysisElement')}; }""")
    assert result['originalUnchanged'] is True and result['collectionsNew'] is True
    assert result['created'] == ['n3','m2','c1','s1','l1'] and result['updated'] == {'client_key':'l1','target_connection_client_key':'c1','fx_N':5,'fy_N':-2,'label':'new'} and result['deletedLoads'] == 0
    assert result['state'] == {'dirty':True,'version':4,'key':'n4'} and result['analysis'] is False
    assert result['failures'] == {
        'duplicate': {'name':'EditorActionError','code':'EDITOR_DUPLICATE_CLIENT_KEY','unchanged':True},
        'malformed': {'name':'EditorActionError','code':'EDITOR_INVALID_ACTION','unchanged':True},
        'missing': {'name':'EditorActionError','code':'EDITOR_REFERENCE_NOT_FOUND','unchanged':True},
        'forbidden': {'name':'EditorActionError','code':'EDITOR_UPDATE_FIELD_NOT_ALLOWED','unchanged':True},
        'dependency': None,
    }


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_editor_enforces_full_reference_update_and_delete_matrix(context, workspace_page):
    owner, project, _, _ = context; page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { applyEditorAction } = await import('/static/projects/workspace/editor.js');
      const draft={schema_version:'physical-draft-v1',version:4,nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:'a'},{client_key:'n2',x_mm:1,y_mm:0,label:'b'}],physical_members:[{client_key:'m1',start_node_client_key:'n1',end_node_client_key:'n2',material_id:1,section_id:1,label:'m',is_active:true},{client_key:'m2',start_node_client_key:'n1',end_node_client_key:'n2',material_id:1,section_id:1,label:'m2',is_active:true}],connections:[{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:['m1']}],supports:[{client_key:'s1',target_connection_client_key:'c1',support_type:'PINNED',restrained_axis:null}],node_loads:[{client_key:'l1',target_connection_client_key:'c1',fx_N:1,fy_N:2,label:'l'}]};
      const fail=(action,source=draft)=>{const before=JSON.stringify(source);try{applyEditorAction(source,action)}catch(error){return {code:error.code,unchanged:before===JSON.stringify(source)}}};
      const node=applyEditorAction(draft,{type:'UPDATE_OBJECT',target:{kind:'GEOMETRY_NODE',clientKey:'n1'},changes:{x_mm:3,label:'moved'}});
      const member=applyEditorAction(node,{type:'UPDATE_OBJECT',target:{kind:'PHYSICAL_MEMBER',clientKey:'m1'},changes:{material_id:2,section_id:3,label:'changed',is_active:false}});
      const support=applyEditorAction(member,{type:'UPDATE_OBJECT',target:{kind:'SUPPORT',clientKey:'s1'},changes:{support_type:'ROLLER',restrained_axis:'Y'}});
      const crossKind=applyEditorAction(support,{type:'CREATE_NODE',node:{client_key:'m1',x_mm:9,y_mm:9,label:'same-other-kind'}});
      const supportRemoved=applyEditorAction(support,{type:'DELETE_OBJECT',target:{kind:'SUPPORT',clientKey:'s1'}});
      const loadRemoved=applyEditorAction(supportRemoved,{type:'DELETE_OBJECT',target:{kind:'NODE_LOAD',clientKey:'l1'}});
      const connectionRemoved=applyEditorAction(loadRemoved,{type:'DELETE_OBJECTS',targets:[{kind:'PHYSICAL_MEMBER',clientKey:'m1'},{kind:'PHYSICAL_MEMBER',clientKey:'m2'},{kind:'CONNECTION',clientKey:'c1'}]});
      const spare=applyEditorAction(connectionRemoved,{type:'CREATE_NODE',node:{client_key:'n3',x_mm:3,y_mm:3,label:''}});
      const nodeRemoved=applyEditorAction(spare,{type:'DELETE_OBJECT',target:{kind:'GEOMETRY_NODE',clientKey:'n3'}});
      return {updates:[node.nodes[0],member.physical_members[0],support.supports[0]], deletions:[supportRemoved.supports.length,loadRemoved.node_loads.length,connectionRemoved.connections.length,nodeRemoved.nodes.some(x=>x.client_key==='n3')], crossKind:crossKind.nodes.at(-1).client_key, failures:{duplicateParticipants:fail({type:'CREATE_CONNECTION',connection:{client_key:'bad1',geometry_node_client_key:'n1',participating_member_client_keys:['m1','m1']}}),unsortedParticipants:fail({type:'CREATE_CONNECTION',connection:{client_key:'bad2',geometry_node_client_key:'n1',participating_member_client_keys:['m2','m1']}}),missingConnection:fail({type:'CREATE_CONNECTION',connection:{client_key:'bad3',geometry_node_client_key:'missing',participating_member_client_keys:['m1']}}),missingSupport:fail({type:'CREATE_SUPPORT',support:{client_key:'s2',target_connection_client_key:'missing',support_type:'PINNED',restrained_axis:null}}),missingLoad:fail({type:'CREATE_NODE_LOAD',nodeLoad:{client_key:'l2',target_connection_client_key:'missing',fx_N:0,fy_N:0,label:''}}),nodeDependency:fail({type:'DELETE_OBJECT',target:{kind:'GEOMETRY_NODE',clientKey:'n1'}}),connectionDependency:fail({type:'DELETE_OBJECT',target:{kind:'CONNECTION',clientKey:'c1'}}),unknownKind:fail({type:'UPDATE_OBJECT',target:{kind:'BOGUS',clientKey:'x'},changes:{label:'x'}})}};
    }""")
    assert result['updates'] == [
        {'client_key':'n1','x_mm':3,'y_mm':0,'label':'moved'},
        {'client_key':'m1','start_node_client_key':'n1','end_node_client_key':'n2','material_id':2,'section_id':3,'label':'changed','is_active':False},
        {'client_key':'s1','target_connection_client_key':'c1','support_type':'ROLLER','restrained_axis':'Y'},
    ]
    assert result['deletions'] == [0,0,0,False] and result['crossKind'] == 'm1'
    assert result['failures'] == {
        'duplicateParticipants': {'code':'EDITOR_INVALID_ACTION','unchanged':True},
        'unsortedParticipants': {'code':'EDITOR_INVALID_ACTION','unchanged':True},
        'missingConnection': {'code':'EDITOR_REFERENCE_NOT_FOUND','unchanged':True},
        'missingSupport': {'code':'EDITOR_REFERENCE_NOT_FOUND','unchanged':True},
        'missingLoad': {'code':'EDITOR_REFERENCE_NOT_FOUND','unchanged':True},
        'nodeDependency': None,
        'connectionDependency': None,
        'unknownKind': {'code':'EDITOR_INVALID_ACTION','unchanged':True},
    }


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_canvas_picking_pan_zoom_and_fit(context, workspace_page):
    owner, project, _, _ = context; page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => { const { pickAt, reduceView, GRID_ORIGIN, GRID_SPACING } = await import('/static/projects/workspace/canvas-interaction.js'); const objects=[{kind:'PHYSICAL_MEMBER',clientKey:'m1',hit:{type:'SEGMENT',start:{x:0,y:0},end:{x:100,y:0}}},{kind:'GEOMETRY_NODE',clientKey:'n1',hit:{type:'POINT',point:{x:10,y:10}}},{kind:'SUPPORT',clientKey:'s2',hit:{type:'POINT',point:{x:15,y:10}}},{kind:'SUPPORT',clientKey:'s1',hit:{type:'POINT',point:{x:15,y:10}}},{kind:'NODE_LOAD',clientKey:'l1',hit:{type:'POINT',point:{x:15,y:10}}}]; const draft={nodes:[{client_key:'n1',x_mm:1,y_mm:2}],connections:[]}; const before=JSON.stringify(draft); const view={a:1,b:0,c:0,d:-1,e:10,f:20}; let invalid=null;try{reduceView(view,{type:'ZOOM',factor:0,anchorScreen:{x:0,y:0}})}catch(error){invalid=error.message}; return {point:pickAt({x:15,y:10},objects), nearest:pickAt({x:11,y:10},[{kind:'SUPPORT',clientKey:'far',hit:{type:'POINT',point:{x:15,y:10}}},{kind:'SUPPORT',clientKey:'near',hit:{type:'POINT',point:{x:10,y:10}}}]), segment:pickAt({x:50,y:6},objects), empty:pickAt({x:500,y:500},objects), reversed:pickAt({x:15,y:10},[...objects].reverse()), pan:reduceView(view,{type:'PAN',deltaScreen:{x:5,y:-3}}), zoom:reduceView(view,{type:'ZOOM',factor:2,anchorScreen:{x:100,y:50}}), max:reduceView(view,{type:'ZOOM',factor:100,anchorScreen:{x:0,y:0}}), min:reduceView(view,{type:'ZOOM',factor:.00001,anchorScreen:{x:0,y:0}}), fit:reduceView(view,{type:'FIT_VIEW',worldBounds:{minX:0,minY:0,maxX:100,maxY:0},viewport:{width:400,height:300}}), emptyFit:reduceView(view,{type:'FIT_VIEW',worldBounds:null,viewport:{width:400,height:300}}), grid:{origin:GRID_ORIGIN,spacing:GRID_SPACING}, unchanged:before===JSON.stringify(draft),invalid}; }""")
    assert result['point'] == {'kind':'SUPPORT','clientKey':'s1'} and result['reversed'] == result['point']
    assert result['nearest'] == {'kind':'SUPPORT','clientKey':'near'} and result['segment'] == {'kind':'PHYSICAL_MEMBER','clientKey':'m1'} and result['empty'] is None
    assert result['pan'] == {'a':1,'b':0,'c':0,'d':-1,'e':15,'f':17}
    assert result['zoom'] == {'a':2,'b':0,'c':0,'d':-2,'e':-80,'f':-10}
    assert result['max']['a'] == 20 and result['min']['a'] == .05
    assert result['invalid'] == 'ZOOM_FACTOR_INVALID'
    assert result['fit'] == {'a':2.2,'b':0,'c':0,'d':-2.2,'e':90,'f':150} and result['emptyFit'] == {'a':1,'b':0,'c':0,'d':-1,'e':10,'f':20}
    assert result['grid'] == {'origin':{'x':0,'y':0},'spacing':1} and result['unchanged'] is True


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_svg_objects_are_keyboard_focusable(context, workspace_page):
    owner, project, material, section = context; save_physical_draft(actor=owner,project=project,payload=valid_payload(material,section)); page=workspace_page(user=owner,project=project)
    result=page.evaluate("""async()=>{const {renderWorkspace}=await import('/static/projects/workspace/renderer.js');const {selectionFromElement}=await import('/static/projects/workspace/canvas-interaction.js');const svg=document.querySelector('#workspace-canvas');const draft=JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft;renderWorkspace(svg,draft,{viewTransform:{a:2,b:0,c:0,d:-2,e:10,f:20}});const member=svg.querySelector('[data-client-key="m1"]');return {selection:selectionFromElement(member),tabindex:member.getAttribute('tabindex'),role:member.getAttribute('role'),transform:svg.querySelector('[data-world-layer]').getAttribute('transform')};}""")
    assert result == {'selection':{'kind':'PHYSICAL_MEMBER','clientKey':'m1'},'tabindex':'0','role':'button','transform':'matrix(2 0 0 -2 10 20)'}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_canvas_binds_mouse_keyboard_and_view_events(context, workspace_page):
    owner, project, material, section = context; save_physical_draft(actor=owner,project=project,payload=valid_payload(material,section)); page=workspace_page(user=owner,project=project)
    result=page.evaluate("""()=>{const svg=document.querySelector('#workspace-canvas');const member=svg.querySelector('[data-client-key="m1"]');const box=member.getBoundingClientRect();member.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:box.left+box.width/2,clientY:box.top+box.height/2}));const mouse=svg.querySelector('[data-client-key="m1"]').dataset.selected;const keyboard=svg.querySelector('[data-client-key="m1"]');keyboard.focus();keyboard.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));const key=svg.querySelector('[data-client-key="m1"]').dataset.selected;const before=svg.querySelector('[data-world-layer]').getAttribute('transform');svg.dispatchEvent(new WheelEvent('wheel',{deltaY:-100,clientX:100,clientY:50,bubbles:true,cancelable:true}));const after=svg.querySelector('[data-world-layer]').getAttribute('transform');return {mouse,key,before,after};}""")
    before_scale = float(result['before'].split('(')[1].split()[0])
    after_scale = float(result['after'].split('(')[1].split()[0])
    assert result['mouse'] == 'true' and result['key'] == 'true' and result['before'] != result['after'] and after_scale > before_scale


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_canvas_shows_orientation_grid_fit_and_pointer_coordinates(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)

    canvas = page.locator('#workspace-canvas')
    axes = page.locator('[data-canvas-orientation]')
    grid = page.locator('[data-canvas-grid]')
    assert axes.count() == 1
    assert axes.text_content() == '+X → +Y ↑'
    assert grid.count() == 1
    assert grid.evaluate("(element) => getComputedStyle(element).pointerEvents") == 'none'

    member = page.locator('[data-client-key="m1"] line')
    assert member.evaluate("(element) => getComputedStyle(element).pointerEvents") == 'none'
    assert page.locator('[data-client-key="m1"] [data-symbol-hit]').evaluate("(element) => getComputedStyle(element).pointerEvents") == 'stroke'
    assert member.bounding_box()['width'] > 200
    canvas.hover(position={'x': 350, 'y': 220})
    assert 'mm' in page.locator('#workspace-pointer-x').text_content()
    assert 'mm' in page.locator('#workspace-pointer-y').text_content()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_report_requires_an_explicit_analysis_run_selection(context, workspace_page):
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    project.refresh_from_db()
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    assert run.status == "SUCCESS"
    page = workspace_page(user=owner, project=project)

    assert page.locator('#workspace-report-open').count() == 1
    assert page.locator('#workspace-run-select').count() == 1
    assert page.locator('#workspace-report-view').count() == 1
    assert page.locator('#workspace-run-select').input_value() == ''


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_report_without_successful_run_shows_analyze_guidance(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)

    page.wait_for_function("document.querySelector('#workspace-report-view').textContent.length > 0")
    assert page.locator('#workspace-report-view').text_content() == '还没有可用的计算书资料。请先完成一次成功分析。'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_report_reasoning_ignores_stale_loads_and_disables_failed_load(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { bindReportReasoning } = await import('/static/projects/workspace/report-reasoning.js');
      const root = document.createElement('section'); document.body.append(root);
      const pending = new Map(); const posts = []; const errors = [];
      const get = (url) => new Promise((resolve) => pending.set(url, resolve));
      const post = async (url, fields) => { posts.push({url, fields}); return {response:{ok:true},body:{ok:true,analysis_run_id:Number(url.match(/\\d+/)[0]),reasoning:fields}}; };
      const workspace = bindReportReasoning({root, template:'/runs/{run_id}/reasoning/', get, post, showError:(error)=>errors.push(error.message)});
      const one = workspace.load(1); const two = workspace.load(2);
      pending.get('/runs/2/reasoning/')({response:{ok:true},body:{ok:true,analysis_run_id:2,reasoning:{final_conclusion:'RUN TWO'}}}); await two;
      pending.get('/runs/1/reasoning/')({response:{ok:true},body:{ok:true,analysis_run_id:1,reasoning:{final_conclusion:'RUN ONE'}}}); await one;
      const afterRace = {heading:root.querySelector('h3')?.textContent, value:root.querySelector('[name=final_conclusion]')?.value};
      root.querySelector('form').requestSubmit(); await new Promise((resolve)=>setTimeout(resolve, 0));
      const failed = workspace.load(3); pending.get('/runs/3/reasoning/')({response:{ok:false},body:{ok:false,error:{message:'LOAD FAILED'}}}); await failed;
      return {afterRace, posts, failedForm:!!root.querySelector('form'), failedText:root.textContent, errors};
    }""")
    assert result['afterRace'] == {'heading': '我的设计说明', 'value': 'RUN TWO'}
    assert result['posts'][0]['url'] == '/runs/2/reasoning/'
    assert result['posts'][0]['fields']['final_conclusion'] == 'RUN TWO'
    assert result['failedForm'] is False
    assert '加载失败' in result['failedText']
    assert result['errors'] == ['LOAD FAILED']


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_report_selection_invalidates_previously_displayed_report(context, workspace_page):
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    project.refresh_from_db()
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run.id))
    page.wait_for_function("document.querySelector('#workspace-report-view h2')")
    assert '计算书资料' in page.locator('#workspace-report-view').text_content()

    page.locator('#workspace-run-select').select_option('')

    page.wait_for_function("document.querySelector('#workspace-report-view').textContent === ''")
    page.wait_for_function("document.querySelectorAll('#workspace-report-reasoning form').length === 0")
    assert page.locator('#workspace-report-view').text_content() == ''
    assert page.locator('#workspace-report-reasoning form').count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_modeling_tools_mutate_draft_and_save(context, workspace_page):
    """The student-facing tools, rather than reducer imports, drive the local draft."""
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)

    page.locator('[data-workspace-tool="NODE"]').click()
    canvas = page.locator('#workspace-canvas')
    box = canvas.bounding_box()
    assert box is not None
    canvas.click(position={'x': 300, 'y': 180})
    node_count = page.locator('[data-object-kind="GeometryNode"]').count()
    assert node_count == 3
    assert page.locator('#workspace-save-status').text_content() == '未保存修改：有'

    page.locator('[data-workspace-tool="MEMBER"]').click()
    connection_rect = page.locator('[data-client-key="c1"] rect')
    connection_rect.click(force=True)
    assert page.locator('[data-modeling-instruction]').text_content() == '请选择构件的终点（节点或空白位置）。按 Esc 可取消。'
    end_node = page.locator('[data-object-kind="GeometryNode"]').last.locator('circle')
    end_node.click(force=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 2

    connection = page.locator('[data-object-kind="Connection"]').last
    assert connection.count() == 1

    page.locator('[data-workspace-tool="SUPPORT"]').click()
    connection.locator('rect').click(force=True)
    assert page.locator('[data-object-kind="Support"]').count() == 2

    page.locator('[data-workspace-tool="LOAD"]').click()
    connection.locator('rect').click(force=True)
    assert page.locator('[data-object-kind="NodeLoad"]').count() == 2

    page.evaluate("document.cookie = 'csrftoken=' + 'a'.repeat(32) + '; path=/'")
    assert 'csrftoken=' in page.evaluate('document.cookie')
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent === '未保存修改：无'")
    assert page.locator('#workspace-draft-version').text_content() == '当前草稿 v2'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_modeling_tools_do_not_create_connection_at_crossing(context, workspace_page):
    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload['nodes'][0]['y_mm'] = payload['nodes'][1]['y_mm'] = -200.0
    save_physical_draft(actor=owner, project=project, payload=payload)
    page = workspace_page(user=owner, project=project)

    page.locator('.ux-precision summary').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    command = page.locator('[data-cad-command-input]')
    for point in ('400,-400', '400,400'):
        command.fill(point)
        command.press('Enter')
    page.locator('[data-cad-fit]').click()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-client-key="node-1"] circle').click(force=True)
    page.locator('[data-client-key="node-2"] circle').click(force=True)
    assert page.locator('[data-object-kind="Connection"]').count() == 3


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_modeling_tools_are_unavailable_for_read_only_viewer(context, workspace_page):
    from competitions.models import EventMembership

    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    viewer = owner.__class__.objects.create_user(username='workspace_viewer', password='pass', role='MANAGER')
    EventMembership.objects.create(user=viewer, event=project.event, membership_type=EventMembership.Type.MANAGER)
    page = workspace_page(user=viewer, project=project)
    page.locator('[data-draft-object-kind="CONNECTION"][data-draft-object-key="c1"]').click()
    assert page.locator('[data-property-connection-node]').count() == 0
    assert page.locator('[data-property-participant]').count() == 0
    assert page.locator('[data-workspace-tool]').count() == 0
    assert page.locator('#workspace-save').is_disabled()
    canvas = page.locator('#workspace-canvas')
    before_zoom = canvas.locator('[data-world-layer]').get_attribute('transform')
    zoom_in = page.get_by_role('button', name='放大画布')
    zoom_in.focus()
    page.keyboard.press('Enter')
    assert canvas.locator('[data-world-layer]').get_attribute('transform') != before_zoom
    fit = page.get_by_role('button', name='显示全图')
    fit.focus()
    page.keyboard.press('Enter')
    assert page.evaluate("document.activeElement === document.querySelector('[data-cad-fit]')") is True


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_properties_edit_support_and_load_and_persist(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)

    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('#workspace-canvas').click(position={'x': 300, 'y': 180})
    page.locator('[data-workspace-tool="SELECT"]').click()
    page.locator('[data-object-kind="GeometryNode"]').last.locator('circle').click(force=True)
    assert page.locator('[data-property-identity]').text_content() == '节点 N3'
    assert 'node-1' not in page.locator('[data-property-identity]').text_content()
    page.locator('[data-client-key="m1"] line').click(force=True)
    assert page.locator('[data-property-identity]').text_content() == '构件 杆件'
    page.locator('[data-client-key="c1"]').focus()
    page.keyboard.press('Enter')
    assert page.locator('[data-property-identity]').text_content() == '节点 左'
    assert page.locator('[data-workspace-tool="SELECT"]').get_attribute('aria-pressed') == 'true'

    page.locator('[data-client-key="s1"] path').click(force=True)
    assert page.locator('[data-property-identity]').text_content() == '支座 S1'
    support_type = page.locator('[data-property-support-type]')
    support_type.select_option('ROLLER_X')
    assert support_type.input_value() == 'ROLLER_X'
    support_type.select_option('ROLLER_Y')
    assert support_type.input_value() == 'ROLLER_Y'
    assert page.locator('#workspace-save-status').text_content() == '未保存修改：有'

    page.locator('[data-client-key="l1"] [data-load-stem]').click(force=True)
    assert page.locator('[data-property-identity]').text_content() == '荷载 荷载'
    page.locator('[data-property-fx]').fill('0')
    page.locator('[data-property-fy]').fill('-250')
    assert page.locator('[data-property-fx]').input_value() == '0'
    assert page.locator('[data-property-fy]').input_value() == '-250'

    page.evaluate("document.cookie = 'csrftoken=' + 'a'.repeat(32) + '; path=/'")
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent === '未保存修改：无'")
    page.reload()

    page.locator('[data-client-key="s1"] path').click(force=True)
    assert page.locator('[data-property-support-type]').input_value() == 'ROLLER_Y'
    page.locator('[data-client-key="l1"] [data-load-stem]').click(force=True)
    assert page.locator('[data-property-fx]').input_value() == '0'
    assert page.locator('[data-property-fy]').input_value() == '-250'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_save_check_error_presentation(context, workspace_page):
    owner, project, material, section = context; page=workspace_page(user=owner,project=project)
    result=page.evaluate("""async()=>{const {applyWorkspaceEditorAction,applyWorkspaceSaveSuccess,focusWorkspaceIssue}=await import('/static/projects/workspace/state.js');const {createWorkspaceWorkflow}=await import('/static/projects/workspace/workflow.js');const {normalizeApiError,presentWorkspaceError}=await import('/static/projects/workspace/errors.js');const bootstrap=JSON.parse(document.querySelector('#workspace-bootstrap').textContent);const initial={draft:bootstrap.draft,draftVersion:0,dirty:false,selectedObject:null,focusedObject:null};const dirty=applyWorkspaceEditorAction(initial,{type:'CREATE_NODE',node:{client_key:'n1',x_mm:1,y_mm:2,label:'n'}});const responses=[{response:{ok:true},body:{ok:true,draft_version:7,validation:{errors:[],warnings:[]}}},{response:{ok:false},body:{ok:false,error:{code:'STALE_DRAFT',message:'ignored',details:{}}}},{response:{ok:true},body:{ok:false,draft_version:7,issues:[{code:'BACKEND_ISSUE',human_message:'后端检查发现问题',physical_object:{kind:'PHYSICAL_MEMBER',client_key:'m1'}}]}}];const calls=[];const workflow=createWorkspaceWorkflow({urls:{save:'/save/',check:'/check/'},request:async(url,payload)=>{calls.push({url,payload});return responses.shift();}});const saveResponse=await workflow.saveDraft(dirty.draft);const saved=applyWorkspaceSaveSuccess(dirty,saveResponse,dirty.draft);const later=applyWorkspaceEditorAction(dirty,{type:'CREATE_NODE',node:{client_key:'n2',x_mm:3,y_mm:4,label:'later'}});const pendingEdit=applyWorkspaceSaveSuccess(later,saveResponse,dirty.draft);let stale;try{await workflow.saveDraft(saved.draft)}catch(error){stale=presentWorkspaceError(error)}const checked=await workflow.checkModel(saved.draftVersion);const focused=focusWorkspaceIssue(saved,checked.issues[0]);const normalized=normalizeApiError({error:{code:'INVALID_DRAFT',message:'x',details:{field:'nodes'}}});const network=presentWorkspaceError({code:'REQUEST_FAILED',message:'Failed to fetch'});return {dirty:{dirty:dirty.dirty,version:dirty.draftVersion},saved:{dirty:saved.dirty,version:saved.draftVersion,draftVersion:saved.draft.version},pendingEdit:{dirty:pendingEdit.dirty,version:pendingEdit.draftVersion,draftVersion:pendingEdit.draft.version,nodes:pendingEdit.draft.nodes.length},stale,network,check:{url:calls[2].url,payload:calls[2].payload,issues:checked.issues.length},focused:{selected:focused.selectedObject,focused:focused.focusedObject},normalized,calls,mechanics:typeof window.Truss2DSolver};}""")
    assert result['dirty'] == {'dirty':True,'version':0} and result['saved'] == {'dirty':False,'version':7,'draftVersion':7}
    assert result['stale'] == {'what':'无法保存当前模型','why':'当前模型版本已发生变化，请重新加载后再继续。','nextAction':'重新加载页面后再继续编辑。','technicalCode':'STALE_DRAFT'}
    assert result['pendingEdit'] == {'dirty':True,'version':7,'draftVersion':7,'nodes':2}
    assert result['network'] == {'what':'当前操作未完成','why':'网络或服务器暂时不可用。','nextAction':'请检查网络连接后重试。','technicalCode':'REQUEST_FAILED'}
    assert result['check'] == {'url':'/check/','payload':{'expected_draft_version':7},'issues':1}
    assert result['focused'] == {'selected':{'kind':'PHYSICAL_MEMBER','clientKey':'m1'},'focused':{'kind':'PHYSICAL_MEMBER','clientKey':'m1'}}
    assert result['normalized'] == {'code':'INVALID_DRAFT','message':'x','details':{'field':'nodes'}} and result['calls'][0]['url'] == '/save/' and result['mechanics'] == 'undefined'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_prediction_workspace_states_and_skip(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { createPredictionWorkspace } = await import('/static/projects/workspace/prediction.js');
      const draft = { version: 7, physical_members: [
        {client_key:'m1', is_active:true}, {client_key:'m2', is_active:true}, {client_key:'inactive', is_active:false}
      ]};
      const urls = {current:'/current/', create:'/create/', completeTemplate:'/predictions/{prediction_id}/complete/'};
      const ok = (body) => ({response:{ok:true}, body});
      const none = createPredictionWorkspace({urls, draft, get:async()=>ok({ok:true,state:'NONE',source_draft_version:7}), post:async()=>{throw new Error('not called')}});
      await none.loadPrediction();
      const noneBefore = none.predictionForAnalyze();
      const startCalls = [];
      const draftFlow = createPredictionWorkspace({urls, draft, get:async()=>ok({ok:true,state:'DRAFT',prediction:{prediction_id:42,status:'DRAFT',payload:{}}}), post:async(url,payload)=>{startCalls.push({url,payload}); return ok({ok:true,prediction_id:42,status:'COMPLETED',payload:payload.payload});}});
      await draftFlow.loadPrediction();
      const choiceStates = draftFlow.memberChoices().map((choice)=>{draftFlow.setMemberJudgment('m1',choice);return draftFlow.state().judgments.m1});
      draftFlow.setMemberJudgment('m1','TENSION');
      draftFlow.setMemberJudgment('m2','ZERO_FORCE');
      draftFlow.selectMaximumDisplacement({kind:'CONNECTION',clientKey:'c1'});
      draftFlow.appendRepresentativePath({kind:'CONNECTION',clientKey:'c1'});
      draftFlow.appendRepresentativePath({kind:'PHYSICAL_MEMBER',clientKey:'m1'});
      draftFlow.appendRepresentativePath({kind:'CONNECTION',clientKey:'c2'});
      const payload = draftFlow.predictionPayload();
      const draftBeforeSkip = draftFlow.predictionForAnalyze();
      draftFlow.skipPrediction();
      const skipped = {state:draftFlow.state().state, keptId:draftFlow.state().prediction.prediction_id, binding:draftFlow.predictionForAnalyze()};
      await draftFlow.completePrediction(payload);
      const completed = {state:draftFlow.state().state, binding:draftFlow.predictionForAnalyze(), call:startCalls[0]};
      const restored = createPredictionWorkspace({urls, draft, get:async()=>ok({ok:true,state:'COMPLETED',prediction:{prediction_id:43,status:'COMPLETED',payload}}), post:async()=>{throw new Error('readonly')}});
      await restored.loadPrediction();
      let prematurePosts = 0;
      const loading = createPredictionWorkspace({urls, draft, get:async()=>ok({ok:true,state:'NONE'}), post:async()=>{prematurePosts += 1; return ok({ok:true,prediction_id:44,status:'DRAFT',payload:{}});}});
      const whileLoading = await loading.startPrediction();
      const refreshedCalls = [];
      const refreshed = createPredictionWorkspace({urls, draft, get:async()=>ok({ok:true,state:'DRAFT',prediction:{prediction_id:51,status:'DRAFT',payload:{}}}), post:async(url,payload)=>{refreshedCalls.push({url,payload});return ok({ok:true,prediction_id:51,status:'COMPLETED',payload:payload.payload});}});
      await refreshed.loadPrediction();
      await refreshed.refreshDraft({version:8,physical_members:[{client_key:'m1',is_active:true},{client_key:'m3',is_active:true}]});
      refreshed.selectMaximumDisplacement({kind:'CONNECTION',clientKey:'c1'});
      refreshed.appendRepresentativePath({kind:'CONNECTION',clientKey:'c1'}); refreshed.appendRepresentativePath({kind:'PHYSICAL_MEMBER',clientKey:'m1'}); refreshed.appendRepresentativePath({kind:'CONNECTION',clientKey:'c2'});
      await refreshed.completePrediction();
      const ambiguous = createPredictionWorkspace({urls, draft, get:async()=>({response:{ok:false},body:{ok:false,error:{code:'PREDICTION_AMBIGUOUS',message:'ambiguous'}}}), post:async()=>{throw new Error('ambiguous')}});
      await ambiguous.loadPrediction();
      const completedStart = await restored.startPrediction();
      return {none:none.state(), noneBefore, draft:{state:draftFlow.state().state,beforeSkip:draftBeforeSkip,payload}, skipped, completed, restored:{state:restored.state().state,binding:restored.predictionForAnalyze(),readonly:restored.state().readonly,startState:completedStart.state}, loading:{state:whileLoading.state,posts:prematurePosts}, refreshed:refreshedCalls[0], ambiguous:ambiguous.state(), choiceStates, mechanics:typeof window.Truss2DSolver};
    }""")
    assert result['none']['state'] == 'NONE' and result['noneBefore'] is None
    assert result['draft']['beforeSkip'] is None
    assert result['draft']['payload']['member_judgments'] == [
        {'physical_member_client_key':'m1','predicted_state':'TENSION'},
        {'physical_member_client_key':'m2','predicted_state':'ZERO_FORCE'},
    ]
    assert result['draft']['payload']['max_displacement_location'] == {'kind':'CONNECTION','connection_client_key':'c1'}
    assert result['draft']['payload']['representative_load_path'] == [
        {'kind':'CONNECTION','connection_client_key':'c1'}, {'kind':'PHYSICAL_MEMBER','physical_member_client_key':'m1'}, {'kind':'CONNECTION','connection_client_key':'c2'},
    ]
    assert result['skipped'] == {'state':'DRAFT','keptId':42,'binding':None}
    assert result['completed']['state'] == 'COMPLETED' and result['completed']['binding'] == 42
    assert result['completed']['call'] == {'url':'/predictions/42/complete/','payload':{'expected_draft_version':7,'payload':result['draft']['payload']}}
    assert result['restored'] == {'state':'COMPLETED','binding':43,'readonly':True,'startState':'COMPLETED'}
    assert result['loading'] == {'state':'NONE','posts':0}
    assert result['refreshed']['payload']['expected_draft_version'] == 8
    assert result['refreshed']['payload']['payload']['member_judgments'] == [
        {'physical_member_client_key':'m1','predicted_state':'UNSURE'}, {'physical_member_client_key':'m3','predicted_state':'UNSURE'},
    ]
    assert result['ambiguous']['state'] == 'AMBIGUOUS' and result['ambiguous']['prediction'] is None
    assert result['choiceStates'] == ['TENSION','COMPRESSION','ZERO_FORCE','UNSURE'] and result['mechanics'] == 'undefined'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_analyze_level_one_and_stale_run(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { createResultsWorkspace, showLevelOne } = await import('/static/projects/workspace/results.js');
      const data = {ok:true,analysis_run_id:31,model_revision_id:7,source_draft_version:4,status:'SUCCESS',result_json:{schema_version:'truss2d-result-v1',member_results:[{analysis_member_id:'m1:1',physical_member_id:'m1',state:'TENSION'},{analysis_member_id:'m2:1',physical_member_id:'m2',state:'COMPRESSION'},{analysis_member_id:'m3:1',physical_member_id:'m3',state:'ZERO'}]},level_one:{maximum_displacement:{maximum_displacement_mm:4.2,candidate_analysis_node_ids:['connection:c2']}}};
      const calls = [];
      const workspace = createResultsWorkspace({urls:{analyze:'/analyze/',resultTemplate:'/analyses/{run_id}/data/'},post:async(url,payload)=>{calls.push({url,payload});return {response:{ok:true},body:{ok:true,analysis_run_id:31,status:'SUCCESS'}};},get:async(url)=>{calls.push({url});return {response:{ok:true},body:data};}});
      const withoutPrediction = await workspace.analyze(4, null);
      const completedPrediction = await workspace.analyze(4, 12);
      const current = showLevelOne(completedPrediction.run, completedPrediction.data, 4);
      const stale = showLevelOne(completedPrediction.run, completedPrediction.data, 5);
      const failed = createResultsWorkspace({urls:{analyze:'/analyze/',resultTemplate:'/analyses/{run_id}/data/'},post:async()=>({response:{ok:false},body:{ok:false,error:{code:'STALE_DRAFT',message:'stale'}}}),get:async()=>{throw new Error('must not fetch')}});
      let failure = null; try { await failed.analyze(4, null); } catch (error) { failure = error.code; }
      return {calls,withoutPrediction,completedPrediction,current,stale,failure,failedState:failed.state(),mechanics:typeof window.Truss2DSolver};
    }""")
    assert result['calls'][0] == {'url':'/analyze/','payload':{'expected_draft_version':4,'prediction_id':None}}
    assert result['calls'][2] == {'url':'/analyze/','payload':{'expected_draft_version':4,'prediction_id':12}}
    assert result['withoutPrediction']['predictionId'] is None and result['completedPrediction']['predictionId'] == 12
    assert result['current']['stale'] is False and result['stale']['stale'] is True
    assert result['current']['maximum'] == {'maximum_displacement_mm':4.2,'candidate_analysis_node_ids':['connection:c2']}
    assert result['current']['members'] == [
        {'physicalMemberClientKey':'m1','state':'TENSION'}, {'physicalMemberClientKey':'m2','state':'COMPRESSION'}, {'physicalMemberClientKey':'m3','state':'ZERO'},
    ]
    assert result['failure'] == 'STALE_DRAFT' and result['failedState']['run'] is None
    assert result['mechanics'] == 'undefined'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_compare_explain_states_and_canvas_link(context, workspace_page):
    owner, project, material, section = context; save_physical_draft(actor=owner,project=project,payload=valid_payload(material,section)); page=workspace_page(user=owner,project=project)
    result=page.evaluate("""async()=>{const x=await import('/static/projects/workspace/results.js');const c=x.showComparison({comparison_available:true,member_comparisons:[{physical_member_client_key:'m1',comparison_status:'MATCH',actual:{actual_state:'MIXED',segments:[{analysis_member_id:'m1:1',teaching_state:'TENSION'},{analysis_member_id:'m1:2',teaching_state:'COMPRESSION'}]}}]});const n=x.showComparison({comparison_available:false,reason:'NO_PREDICTION'});const e=x.showExplanation({blocks:[{subject:{kind:'PHYSICAL_MEMBER',physical_member_client_key:'m1'},message_zh_CN:{level_1:'后端说明'},facts:{segments:[{analysis_member_id:'m1:1'}]}}]});const svg=document.querySelector('#workspace-canvas');const f=x.focusPhysicalMember('m1',(key)=>svg.querySelector('[data-client-key="'+key+'"]').getAttribute('tabindex'));return {c,n,e,f,mechanics:typeof window.Truss2DSolver}}""")
    assert result['c'][0]['status'] == 'MATCH' and result['c'][0]['actual']['actual_state'] == 'MIXED'
    assert result['n']['reason'] == 'NO_PREDICTION' and result['e'][0]['text'] == '后端说明'
    assert result['f'] == '0' and result['mechanics'] == 'undefined'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_beginner_labels_mixed_evidence_and_frozen_copy(context, workspace_page):
    """Raw client keys, generic MIXED copy, or stale wording regressions must fail."""
    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["physical_members"][0]["label"] = ""
    save_physical_draft(actor=owner, project=project, payload=payload)
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { createStudentLabelResolver } = await import('/static/projects/workspace/labels.js');
      const { renderComparison, renderLevelOne, renderEngineeringDetails } = await import('/static/projects/workspace/results.js');
      const draft = JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft;
      const labels = createStudentLabelResolver(draft);
      const fallbackLabels = createStudentLabelResolver({
        nodes:[{client_key:'n1',label:''}], physical_members:[{client_key:'m1',label:''}],
        connections:[{client_key:'c1'}], supports:[{client_key:'s1'}], node_loads:[{client_key:'l1',label:''}],
      });
      const comparisonRoot = document.createElement('section');
      document.body.append(comparisonRoot);
      renderComparison(comparisonRoot, {comparison_available:true,member_comparisons:[{
        physical_member_client_key:'m1', predicted_state:'TENSION', comparison_status:'NOT_COMPARABLE',
        actual:{actual_state:'MIXED',segments:[
          {analysis_member_id:'m1:1',axial_force_N:12.5,teaching_state:'TENSION'},
          {analysis_member_id:'m1:2',axial_force_N:-4.25,teaching_state:'COMPRESSION'},
        ]},
      }]}, () => {}, labels);
      const staleRoot = document.createElement('section');
      document.body.append(staleRoot);
      renderLevelOne(staleRoot, {runId:4,stale:true,predictionUsed:true,maximum:null,members:[],overlay:{}});
      const engineeringRoot = document.createElement('section');
      document.body.append(engineeringRoot);
      renderEngineeringDetails(engineeringRoot, {displacements:[],reactions:[],members:[],total_mass_g:null}, true);
      return {
        labels:['GEOMETRY_NODE','PHYSICAL_MEMBER','CONNECTION','SUPPORT','NODE_LOAD'].map((kind) => fallbackLabels.label(kind, ({GEOMETRY_NODE:'n1',PHYSICAL_MEMBER:'m1',CONNECTION:'c1',SUPPORT:'s1',NODE_LOAD:'l1'})[kind])),
        comparison:comparisonRoot.textContent,
        stale:staleRoot.textContent,
        engineeringStale:engineeringRoot.textContent,
      };
    }""")
    assert result["labels"] == ["节点 N1", "构件 M1", "连接 C1", "支座 S1", "荷载 L1"]
    assert "一根实际构件在分析模型中可能被分成多个分析段，这些分析段的受力状态并不完全相同。" in result["comparison"]
    assert "分析段 1" in result["comparison"] and "12.5 N" in result["comparison"] and "受拉" in result["comparison"]
    assert "分析段 2" in result["comparison"] and "-4.25 N" in result["comparison"] and "受压" in result["comparison"]
    assert "m1" not in result["comparison"]
    assert "预测已参与本次分析流程" in result["stale"] and "Prediction" not in result["stale"]
    assert "不能代表当前草稿" in result["stale"] and "重新分析当前模型" in result["stale"]
    assert "不能代表当前草稿" in result["engineeringStale"] and "重新分析当前模型" in result["engineeringStale"]

    page.locator('[data-ux-stage-target="prediction"]').click()
    page.get_by_role("button", name="开始预测").click()
    prediction = page.locator("#workspace-prediction")
    assert prediction.get_by_role("button", name="近似零力").count() == 1
    assert "构件 M1" in prediction.locator("[data-prediction-members]").text_content()
    assert "m1" not in prediction.locator("[data-prediction-members]").text_content()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_canvas_member_selection_focuses_existing_teaching_item_without_loop(context, workspace_page):
    """Removing the selection observer or making it write selection recursively must fail."""
    from competitions.models import CompetitionEvent

    owner, project, material, section = context
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    save_bt01_draft(owner, project, material, section)
    page = workspace_page(user=owner, project=project)
    page.evaluate("document.cookie = 'csrftoken=' + 'a'.repeat(32) + '; path=/'")
    page.locator('[data-ux-stage-target="analyze"]').click()
    page.locator("#workspace-analyze").click()
    page.wait_for_function("document.querySelector('[data-teaching-member]')")
    member_key = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft.physical_members[0].client_key")

    page.locator(f'[data-client-key="{member_key}"] line').click(force=True)
    page.wait_for_function("key => document.activeElement?.dataset.teachingMember === key", arg=member_key)
    assert page.locator(f'[data-teaching-member="{member_key}"][data-teaching-focused="true"]').count() == 1
    assert page.evaluate("document.activeElement.dataset.teachingMember") == member_key


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_compare_explain_reachable_from_real_analysis_controls(context, workspace_page):
    from competitions.models import CompetitionEvent
    from tests.application.test_analysis_acceptance import save_bt01_draft

    owner, project, material, section = context
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    save_bt01_draft(owner, project, material, section)
    page = workspace_page(user=owner, project=project)
    page.evaluate("document.cookie = 'csrftoken=' + 'a'.repeat(32) + '; path=/'")

    page.locator('[data-ux-stage-target="analyze"]').click()
    page.locator("#workspace-analyze").click()
    page.wait_for_function("document.querySelector('[data-result-compare]')")
    page.locator("[data-result-compare]").click()
    page.wait_for_function("document.querySelector('[data-result-comparison]').textContent.length > 0")
    assert "这次没有保存预测，因此暂时无法比较" in page.locator("[data-result-comparison]").text_content()
    page.locator("[data-result-explain]").click()
    page.wait_for_function("document.querySelector('[data-result-explanation]').textContent.length > 0")
    assert page.locator("[data-result-explanation] [data-explanation-block]").count() > 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_explicit_run_refresh_selects_new_analysis_without_reload(context, workspace_page):
    from competitions.models import CompetitionEvent
    from tests.application.test_analysis_acceptance import save_bt01_draft

    owner, project, material, section = context
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    save_bt01_draft(owner, project, material, section)
    page = workspace_page(user=owner, project=project)
    page.evaluate("document.cookie = 'csrftoken=' + 'a'.repeat(32) + '; path=/'")

    assert page.locator("#workspace-run-select").input_value() == ""
    page.locator('[data-ux-stage-target="analyze"]').click()
    page.locator("#workspace-analyze").click()
    page.wait_for_function("document.querySelector('#workspace-run-select').value !== ''")
    selected = page.locator("#workspace-run-select").input_value()
    assert page.locator(f'#workspace-run-select option[value="{selected}"]').count() == 1
    page.wait_for_function("document.querySelector('#workspace-results').textContent.includes('第 1 次分析')")
    assert "第 1 次分析" in page.locator("#workspace-results").text_content()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_historical_explicit_run_selection_restores_all_student_artifacts(context, workspace_page):
    from analysis.orchestration import analyze_project
    from competitions.models import CompetitionEvent
    from learning.models import CalculationReportReasoning, Reflection
    from tests.application.test_analysis_acceptance import save_bt01_draft

    owner, project, material, section = context
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    save_bt01_draft(owner, project, material, section, fx_N=100.0)
    run_one = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    save_bt01_draft(owner, project, material, section, fx_N=125.0)
    run_two = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    save_bt01_draft(owner, project, material, section, fx_N=150.0)
    CalculationReportReasoning.objects.create(analysis_run=run_one, created_by=owner, final_conclusion="RUN ONE REASONING")
    CalculationReportReasoning.objects.create(analysis_run=run_two, created_by=owner, final_conclusion="RUN TWO REASONING")
    Reflection.objects.create(analysis_run=run_one, created_by=owner, original_reasoning="RUN ONE REFLECTION")
    Reflection.objects.create(analysis_run=run_two, created_by=owner, original_reasoning="RUN TWO REFLECTION")
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()

    for ordinal, (run, reasoning, reflection) in enumerate([
        (run_one, "RUN ONE REASONING", "RUN ONE REFLECTION"),
        (run_two, "RUN TWO REASONING", "RUN TWO REFLECTION"),
    ], start=1):
        page.locator("#workspace-run-select").select_option(str(run.id))
        page.wait_for_function(
            "number => document.querySelector('#workspace-report-view h3')?.textContent.includes(`第 ${number} 次分析`)",
            arg=ordinal,
        )
        assert f"第 {ordinal} 次分析" in page.locator("#workspace-results").text_content()
        assert "较早的模型版本" in page.locator("#workspace-results").text_content()
        assert page.locator('#workspace-report-reasoning [name="final_conclusion"]').input_value() == reasoning
        assert page.locator('#workspace-reflection [name="original_reasoning"]').input_value() == reflection
        assert f"第 {ordinal} 次分析" in page.locator("#workspace-report-view").text_content()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_run_context_clears_previous_payload_before_loading_or_failure(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { createRunContext } = await import('/static/projects/workspace/run-context.js');
      const select = document.createElement('select');
      const renders = [];
      const bodies = {
        '/runs': { ok:true, runs:[{analysis_run_id:1,status:'SUCCESS'},{analysis_run_id:2,status:'SUCCESS'}] },
        '/result/1': {ok:true}, '/comparison/1': {ok:true,comparison:{}}, '/explanation/1': {ok:true,explanation:{}}, '/report/1': {ok:true}, '/reasoning/1': {ok:true}, '/reflection/1': {ok:true,status:'COMPLETED'},
      };
      const get = async (url) => {
        if (url === '/result/2') return {response:{ok:false,status:500},body:{error:{code:'BROKEN',message:'broken'}}};
        return {response:{ok:true,status:200},body:bodies[url]};
      };
      const context = createRunContext({
        urls:{runs:'/runs',resultTemplate:'/result/{run_id}',comparisonTemplate:'/comparison/{run_id}',explanationTemplate:'/explanation/{run_id}',reportTemplate:'/report/{run_id}',reasoningTemplate:'/reasoning/{run_id}',reflectionTemplate:'/reflection/{run_id}'},
        select, get, onSelect:(payload)=>renders.push(payload ? payload.metadata.analysis_run_id : null),
      });
      await context.refreshRuns(); await context.selectRun(1);
      try { await context.selectRun(2); } catch (_) {}
      return {renders, current:context.state().currentRunId, payload:context.state().payload};
    }""")
    assert result == {'renders': [None, 1, None], 'current': 2, 'payload': None}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_switching_to_failed_run_clears_engineering_details_and_canvas_overlay(context, workspace_page):
    from analysis.models import AnalysisRun
    from analysis.orchestration import analyze_project

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    success = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    failed = AnalysisRun.objects.create(
        project=project,
        model_revision=success.model_revision,
        analysis_type=success.analysis_type,
        solver_version=success.solver_version,
        input_schema_version=success.input_schema_version,
        input_hash=success.input_hash,
        status=AnalysisRun.Status.SOLVER_FAILED,
        solver_input_json=success.solver_input_json,
        failure_code="CONTROLLED_FAILURE",
        result_schema_version="truss2d-result-v1",
        created_by=owner,
    )
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator("#workspace-run-select").select_option(str(success.id))
    page.wait_for_function("document.querySelector('[data-engineering-content] table')")
    assert page.locator('#workspace-canvas [data-result-state="TENSION"]').count() > 0

    page.locator("#workspace-run-select").select_option(str(failed.id))
    page.wait_for_function("runId => document.querySelector('#workspace-results').textContent.includes(`#${runId}`)", arg=failed.id)
    assert page.locator("[data-engineering-content]").text_content() == ""
    assert page.locator('#workspace-canvas [data-result-state]:not([data-result-state=""])').count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_historical_level_one_uses_revision_snapshot_labels_and_no_stale_overlay(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { showLevelOne } = await import('/static/projects/workspace/results.js');
      const snapshot = {nodes:[{id:'n1',label:'历史节点'}],connections:[{id:'c1',geometry_node_id:'n1'}],physical_members:[{id:'m1',label:'历史构件'}]};
      const data = {source_draft_version:1,result_json:{member_results:[{physical_member_id:'m1',state:'TENSION'}]},level_one:{maximum_displacement:{maximum_displacement_mm:1,candidate_analysis_node_ids:['connection:c1']}}};
      const view = showLevelOne({analysis_run_id:7,predictionId:null}, data, 2, snapshot);
      return {label:view.members[0].displayLabel,maximum:view.maximum.displayCandidateLabels,overlay:view.overlay,stale:view.stale};
    }""")
    assert result == {'label': '构件 历史构件', 'maximum': ['连接 C1'], 'overlay': {}, 'stale': True}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workflow_progress_projects_persisted_state_and_never_double_activates(context, workspace_page):
    """Reintroducing click-history setters or treating stale runs as current must fail."""
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { projectWorkflow } = await import('/static/projects/workspace/workflow-progress.js');
      const blank={version:0,physical_members:[]};
      const saved={version:3,physical_members:[{client_key:'m1',is_active:true}]};
      const cases={
        blank:projectWorkflow({draft:blank,prediction:{state:'NONE'},runs:[]}),
        saved:projectWorkflow({draft:saved,prediction:{state:'NONE'},runs:[]}),
        predicted:projectWorkflow({draft:saved,prediction:{state:'COMPLETED'},runs:[]}),
        analyzed:projectWorkflow({draft:saved,prediction:{state:'NONE'},runs:[{status:'SUCCESS',source_draft_version:3,is_stale:false}]}),
        staleOnly:projectWorkflow({draft:saved,prediction:{state:'NONE'},runs:[{status:'SUCCESS',source_draft_version:2,is_stale:true}]}),
        reflected:projectWorkflow({draft:saved,prediction:{state:'COMPLETED'},runs:[{status:'SUCCESS',source_draft_version:3,is_stale:false}],selectedRun:{status:'SUCCESS',source_draft_version:3,is_stale:false},reflection:{status:'COMPLETED'}}),
      };
      return {cases,activeCounts:Object.fromEntries(Object.entries(cases).map(([name,state])=>[name,Object.values(state).filter(value=>value.startsWith('active')).length]))};
    }""")
    assert result['cases']['blank'] == {'model':'active','prediction':'optional','analysis':'pending','understanding':'pending','reflection':'optional'}
    assert result['cases']['saved']['model'] == 'completed' and result['cases']['saved']['prediction'] == 'active-optional' and result['cases']['saved']['analysis'] == 'available'
    assert result['cases']['predicted']['prediction'] == 'completed' and result['cases']['predicted']['analysis'] == 'active'
    assert result['cases']['analyzed']['analysis'] == 'completed' and result['cases']['analyzed']['understanding'] == 'active'
    assert result['cases']['staleOnly']['analysis'] == 'available' and result['cases']['staleOnly']['understanding'] == 'pending'
    assert result['cases']['reflected']['reflection'] == 'completed' and result['cases']['reflected']['understanding'] == 'completed'
    assert all(count <= 1 for count in result['activeCounts'].values())

    page.reload()
    page.wait_for_function("document.querySelector('[data-workflow-step=prediction]').dataset.state === 'active-optional'")
    assert page.locator('[data-workflow-step][aria-current="step"]').count() == 1
    assert page.locator('[data-workflow-step="model"]').get_attribute('data-state') == 'completed'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_canvas_keyboard_pan_zoom_fit_and_status_semantics(context, workspace_page):
    """Removing any keyboard view path or status semantics must fail."""
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    canvas = page.locator('#workspace-canvas')
    canvas.focus()
    before_pan = canvas.locator('[data-world-layer]').get_attribute('transform')
    page.keyboard.press('ArrowRight')
    after_pan = canvas.locator('[data-world-layer]').get_attribute('transform')
    assert after_pan != before_pan

    zoom_in = page.get_by_role('button', name='放大画布')
    zoom_in.focus()
    page.keyboard.press('Enter')
    after_zoom_in = canvas.locator('[data-world-layer]').get_attribute('transform')
    assert after_zoom_in != after_pan
    zoom_out = page.get_by_role('button', name='缩小画布')
    zoom_out.focus()
    page.keyboard.press('Enter')
    assert canvas.locator('[data-world-layer]').get_attribute('transform') != after_zoom_in

    fit = page.get_by_role('button', name='显示全图')
    fit.focus()
    page.keyboard.press('Enter')
    assert page.evaluate("document.activeElement === document.querySelector('[data-cad-fit]')") is True
    assert canvas.get_attribute('tabindex') == '0'
    assert page.locator('#workspace-status-bar').get_attribute('role') == 'status'
    assert page.locator('[data-modeling-instruction]').get_attribute('role') == 'status'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_read_only_run_context_loads_completed_reflection_but_hides_draft(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const { createRunContext } = await import('/static/projects/workspace/run-context.js');
      const select=document.createElement('select'); let reflectionUrl=null;
      const get=async(url)=>{
        if(url==='/runs') return {response:{ok:true,status:200},body:{ok:true,runs:[{analysis_run_id:9,status:'SUCCESS'}]}};
        if(url==='/reflection/9'){reflectionUrl=url;return {response:{ok:true,status:200},body:{ok:true,status:'COMPLETED',original_reasoning:'已完成反思'}};}
        const body=url.startsWith('/comparison/')?{ok:true,comparison:{}}:url.startsWith('/explanation/')?{ok:true,explanation:{}}:{ok:true};
        return {response:{ok:true,status:200},body};
      };
      const context=createRunContext({urls:{runs:'/runs',resultTemplate:'/result/{run_id}',comparisonTemplate:'/comparison/{run_id}',explanationTemplate:'/explanation/{run_id}',reportTemplate:'/report/{run_id}',reasoningTemplate:'/reasoning/{run_id}',reflectionTemplate:'/reflection/{run_id}'},select,get,editable:false});
      await context.refreshRuns(); const payload=await context.selectRun(9);
      return {reflectionUrl,reflection:payload.reflection,reasoning:payload.reasoning};
    }""")
    assert result['reflectionUrl'] == '/reflection/9'
    assert result['reflection']['original_reasoning'] == '已完成反思'
    assert result['reasoning'] is None


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_read_only_manager_sees_completed_reflection_without_authoring_controls(context, workspace_page):
    from accounts.models import User
    from analysis.orchestration import analyze_project
    from competitions.models import EventMembership
    from learning.models import Reflection

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    Reflection.objects.create(
        analysis_run=run,
        created_by=owner,
        status=Reflection.Status.COMPLETED,
        original_reasoning="已完成的原判断",
        unexpected_results="已完成的差异",
        next_iteration_intent="已完成的下一步",
    )
    manager = User.objects.create_user("reflection-manager", role=User.Role.MANAGER)
    EventMembership.objects.create(user=manager, event=project.event, membership_type=EventMembership.Type.MANAGER)
    page = workspace_page(user=manager, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator("#workspace-run-select").select_option(str(run.id))
    page.wait_for_function("document.querySelector('#workspace-reflection textarea')")

    assert page.get_by_role('tab', name='我的设计说明').count() == 0
    page.get_by_role('tab', name='反思（可选）').click()
    assert page.locator('#workspace-reflection').is_visible()
    assert page.locator('#workspace-reflection [name="original_reasoning"]').input_value() == "已完成的原判断"
    assert page.locator("#workspace-reflection textarea:enabled").count() == 0
    assert page.locator("#workspace-reflection button").count() == 0
    assert page.locator("#workspace-report-reasoning").count() == 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_reflection_draft_complete_and_readonly(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    result = page.evaluate(
        """async () => {
          const { createReflectionWorkspace, renderReflection } = await import('/static/projects/workspace/reflection.js');
          const calls = [];
          const responses = {
            '/reflection/7/': { ok: true, status: 'DRAFT', original_reasoning: '原判断', unexpected_results: '', next_iteration_intent: '' },
            '/reflection/7/complete/': { ok: true, status: 'COMPLETED', original_reasoning: '原判断', unexpected_results: '不同', next_iteration_intent: '修改' },
          };
          const request = async (url, options = {}) => {
            calls.push({ url, options });
            return { response: { ok: true, status: 200 }, body: responses[url] };
          };
          const workspace = createReflectionWorkspace({
            urls: { reflectionTemplate: '/reflection/{run_id}/', reflectionCompleteTemplate: '/reflection/{run_id}/complete/' },
            request,
            get: request,
          });
          const draft = await workspace.loadReflection(7);
          const saved = await workspace.saveReflection({ unexpected_results: '' });
          const completed = await workspace.completeReflection();
          const root = document.createElement('section');
          renderReflection(root, draft, { readOnly: false, onSave: () => {}, onComplete: () => {}, onSkip: () => {} });
          const draftControls = [...root.querySelectorAll('textarea')].map((x) => ({ name: x.name, value: x.value, disabled: x.disabled }));
          const hasSkip = [...root.querySelectorAll('button')].some((x) => x.textContent.includes('稍后'));
          renderReflection(root, completed, { readOnly: false, onSave: () => {}, onComplete: () => {}, onSkip: () => {} });
          const completedText = root.textContent;
          const completedControls = [...root.querySelectorAll('textarea')].map((x) => x.disabled);
          return { draft, saved, completed, calls, draftControls, completedText, completedControls, hasSkip };
        }"""
    )
    assert result['draft']['status'] == 'DRAFT'
    assert result['saved']['unexpected_results'] == ''
    assert result['completed']['status'] == 'COMPLETED'
    assert result['calls'][0]['url'] == '/reflection/7/'
    assert result['calls'][1]['url'] == '/reflection/7/'
    assert result['calls'][1]['options'] == {'unexpected_results': ''}
    assert result['calls'][2]['url'] == '/reflection/7/complete/'
    assert all(item['disabled'] is False for item in result['draftControls'])
    assert all(result['completedControls'])
    assert '不能修改' in result['completedText']
    assert result['hasSkip'] is True


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_reflection_no_record_skip_is_soft_gate_and_read_only(context, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    result = page.evaluate(
        """async () => {
          const { createReflectionWorkspace, renderReflection } = await import('/static/projects/workspace/reflection.js');
          const workspace = createReflectionWorkspace({
            urls: { reflectionTemplate: '/reflection/{run_id}/', reflectionCompleteTemplate: '/reflection/{run_id}/complete/' },
            get: async () => ({ response: { ok: false, status: 404 }, body: { error: { code: 'REFLECTION_NOT_FOUND' } } }),
          });
          const noRecord = await workspace.loadReflection(8);
          const root = document.createElement('section');
          let skipped = 0;
          let started = 0;
          renderReflection(root, noRecord, { readOnly: false, onStart: () => { started += 1; }, onSkip: () => { skipped += 1; } });
          const studentButtons = [...root.querySelectorAll('button')].map((x) => x.textContent);
          root.querySelector('button:last-of-type').click();
          const studentText = root.textContent;
          renderReflection(root, noRecord, { readOnly: true, onSkip: () => { skipped += 1; } });
          return { noRecord, skipped, started, studentButtons, studentText, readOnlyButtons: root.querySelectorAll('button').length, hasAiContent: /AI|生成|自动/.test(studentText) };
        }"""
    )
    assert result['noRecord'] is None
    assert result['skipped'] == 1
    assert result['started'] == 0
    assert result['studentButtons'] == ['开始反思', '稍后再说']
    assert '稍后再说' in result['studentText']
    assert result['readOnlyButtons'] == 0
    assert result['hasAiContent'] is False


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_engineering_details_authoritative_values(context, workspace_page):
    from analysis.orchestration import analyze_project
    from tests.application.test_analysis_acceptance import save_bt01_draft

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=None)
    page = workspace_page(user=owner, project=project)
    result = page.evaluate(
        f"""async () => {{
          const {{ requestJson }} = await import('/static/projects/workspace/api.js');
          const {{ showEngineeringDetails, renderEngineeringDetails }} = await import('/static/projects/workspace/results.js');
          const response = await requestJson('/projects/{project.id}/analyses/{run.id}/data/');
          const details = showEngineeringDetails(response.body.result_json);
          const currentRoot = document.createElement('section');
          renderEngineeringDetails(currentRoot, details, false);
          const missingRoot = document.createElement('section');
          renderEngineeringDetails(missingRoot, showEngineeringDetails({{ node_displacements: details.displacements }}), false);
          const staleRoot = document.createElement('section');
          renderEngineeringDetails(staleRoot, details, true);
          const disclosure = document.querySelector('#workspace-engineering-details');
          return {{
            ok: response.body.ok,
            values: {{ displacement: details.displacements[1].ux_mm, reaction: details.reactions[0].rx_N, axial: details.members[0].axial_force_N, stress: details.members[0].axial_stress_MPa, mass: details.members[0].mass_g, totalMass: details.total_mass_g }},
            currentText: currentRoot.textContent,
            missingText: missingRoot.textContent,
            staleText: staleRoot.textContent,
            detailsClosed: disclosure.open === false,
            mechanics: typeof window.Truss2DSolver,
          }};
        }}"""
    )
    expected = run.result_json
    assert result['ok'] is True
    assert result['values'] == {
        'displacement': expected['node_displacements'][1]['ux_mm'],
        'reaction': expected['support_reactions'][0]['rx_N'],
        'axial': expected['member_results'][0]['axial_force_N'],
        'stress': expected['member_results'][0]['axial_stress_MPa'],
        'mass': expected['member_results'][0]['mass_g'],
        'totalMass': expected['total_mass_g'],
    }
    assert all(unit in result['currentText'] for unit in ['ux (mm)', 'Rx (N)', '轴力 (N)', '应力 (MPa)', '质量 (g)'])
    assert result['missingText'].endswith('总质量：—')
    assert '总质量：0 g' not in result['missingText']
    assert '不能代表当前草稿' in result['staleText']
    assert '请重新分析当前模型' in result['staleText']
    assert result['detailsClosed'] is True and result['mechanics'] == 'undefined'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_beginner_results_use_guidance_labels_and_rounded_values(context, workspace_page):
    from analysis.orchestration import analyze_project
    from tests.application.test_analysis_acceptance import save_bt01_draft

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator("#workspace-run-select").select_option(str(run.id))
    page.wait_for_function("document.querySelector('#workspace-results h2')")
    text = page.locator("#workspace-results").text_content()

    assert all(word in text for word in ["荷载", "支座", "传力", "受拉", "受压", "近似零力"])
    assert "构件" in text
    assert "connection:" not in text
    assert "hash" not in text.lower()
    assert page.locator("#workspace-results [data-student-rounded-value]").count() > 0


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_beginner_error_uses_what_why_next_and_collapsed_technical_detail(context, workspace_page):
    owner, project, material, section = context
    save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-client-key="n2"] circle').click(force=True)
    page.locator('[data-property-x]').fill('0')
    page.locator('[data-property-x]').press('Tab')

    error = page.locator("#workspace-error")
    assert error.locator("[data-error-what]").text_content()
    assert error.locator("[data-error-why]").text_content()
    assert "下一步" in error.locator("[data-error-next]").text_content()
    technical = error.locator("details[data-error-technical]")
    assert technical.get_attribute("open") is None
    assert "EDITOR_NODE_MOVE_ZERO_LENGTH" in technical.text_content()
    assert "EDITOR_NODE_MOVE_ZERO_LENGTH" not in error.locator("[data-error-what]").text_content()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_desktop_1024_layout_has_no_page_overflow_and_contains_report(context, workspace_page):
    from analysis.orchestration import analyze_project
    from tests.application.test_analysis_acceptance import save_bt01_draft

    owner, project, material, section = context
    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    page = workspace_page(user=owner, project=project)
    page.set_viewport_size({"width": 1024, "height": 900})
    page.reload()
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator("#workspace-run-select").select_option(str(run.id))
    page.wait_for_function("document.querySelector('#workspace-report-view table')")

    layout = page.evaluate("""() => ({
      pageWidth: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
      reportScroll: document.querySelector('#workspace-report-view').scrollWidth,
      reportClient: document.querySelector('#workspace-report-view').clientWidth,
    })""")
    assert layout["pageWidth"] <= layout["viewport"]
    assert layout["reportScroll"] <= layout["reportClient"]
    assert page.locator("#workspace-run-select").is_visible()
    page.locator('[data-ux-stage-target="build"]').click()
    assert page.locator("[data-cad-fit]").is_visible()
    page.locator('[data-ux-stage-target="analyze"]').click()
    assert page.locator("#workspace-analyze").is_visible()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_full_learning_loop(context, workspace_page):
    from competitions.models import CompetitionEvent
    from tests.application.test_analysis_acceptance import save_bt01_draft

    owner, project, material, section = context
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    save_bt01_draft(owner, project, material, section)
    page = workspace_page(user=owner, project=project)
    result = page.evaluate(
        f"""async () => {{
          document.cookie = 'csrftoken=' + 'a'.repeat(64) + '; path=/';
          const bootstrap = JSON.parse(document.querySelector('#workspace-bootstrap').textContent);
          const {{ requestJson }} = await import('/static/projects/workspace/api.js');
          const {{ createWorkspaceWorkflow }} = await import('/static/projects/workspace/workflow.js');
          const {{ createReflectionWorkspace, renderReflection }} = await import('/static/projects/workspace/reflection.js');
          const {{ showComparison, showExplanation, showEngineeringDetails, renderEngineeringDetails, showLevelOne, renderLevelOne }} = await import('/static/projects/workspace/results.js');
          const workflow = createWorkspaceWorkflow({{ urls: bootstrap.urls }});
          const editableDraft = {{ ...bootstrap.draft, physical_members: bootstrap.draft.physical_members.map((member) => ({{ ...member, label: '学习路径杆件' }})) }};
          const saved = await workflow.saveDraft(editableDraft);
          const checked = await workflow.checkModel(saved.draft_version);
          const prediction = await workflow.createPrediction(saved.draft_version);
          const completedPrediction = await workflow.completePrediction(prediction.prediction_id, saved.draft_version, {{
            schema_version: 'prediction-v1',
            member_judgments: [{{ physical_member_client_key: 'm1', predicted_state: 'TENSION' }}],
            max_displacement_location: {{ kind: 'CONNECTION', connection_client_key: 'c2' }},
            representative_load_path: [{{ kind: 'CONNECTION', connection_client_key: 'c1' }}, {{ kind: 'PHYSICAL_MEMBER', physical_member_client_key: 'm1' }}, {{ kind: 'CONNECTION', connection_client_key: 'c2' }}],
          }});
          const analyzed = await workflow.analyze(saved.draft_version, completedPrediction.prediction_id);
          const data = await workflow.result(analyzed.analysis_run_id);
          const comparisonResponse = await requestJson(bootstrap.urls.comparison_template.replace('{{run_id}}', analyzed.analysis_run_id));
          const explanationResponse = await requestJson(bootstrap.urls.explanation_template.replace('{{run_id}}', analyzed.analysis_run_id));
          const levelOneRoot = document.createElement('section');
          const levelOne = showLevelOne({{ ...analyzed, predictionId: completedPrediction.prediction_id }}, data, saved.draft_version);
          renderLevelOne(levelOneRoot, levelOne);
          const detailsRoot = document.createElement('section');
          renderEngineeringDetails(detailsRoot, showEngineeringDetails(data.result_json), false);
          const reflection = createReflectionWorkspace({{ urls: bootstrap.urls, workflow }});
          const absent = await reflection.loadReflection(analyzed.analysis_run_id);
          const draft = await reflection.saveReflection({{ original_reasoning: '先按受力路径判断。', unexpected_results: '结果与预想有差异。', next_iteration_intent: '下一版重新观察支座附近。' }});
          const completed = await reflection.completeReflection();
          const reflectionRoot = document.createElement('section');
          renderReflection(reflectionRoot, completed, {{ readOnly: false }});
          return {{
            build: editableDraft.physical_members[0].label,
            saveVersion: saved.draft_version,
            check: checked.ok,
            prediction: completedPrediction.status,
            analyze: analyzed.status,
            levelOne: levelOne.maximum !== null && levelOneRoot.textContent.includes('结论'),
            compare: showComparison(comparisonResponse.body.comparison).length > 0,
            explain: showExplanation(explanationResponse.body.explanation).length > 0,
            engineering: detailsRoot.textContent.includes('轴力 (N)') && detailsRoot.textContent.includes('总质量'),
            reflection: {{ absent, draft: draft.status, completed: completed.status, readonly: [...reflectionRoot.querySelectorAll('textarea')].every((field) => field.disabled) }},
            mechanics: typeof window.Truss2DSolver,
          }};
        }}"""
    )
    assert result['build'] == '学习路径杆件'
    assert result['saveVersion'] == 2
    assert result['check'] is True
    assert result['prediction'] == 'COMPLETED'
    assert result['analyze'] == 'SUCCESS'
    assert result['levelOne'] is True and result['compare'] is True and result['explain'] is True
    assert result['engineering'] is True
    assert result['reflection'] == {'absent': None, 'draft': 'DRAFT', 'completed': 'COMPLETED', 'readonly': True}
    assert result['mechanics'] == 'undefined'


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_workspace_soft_gates(context, workspace_page):
    from competitions.models import CompetitionEvent
    from tests.application.test_analysis_acceptance import save_bt01_draft

    owner, project, material, section = context
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    save_bt01_draft(owner, project, material, section)
    page = workspace_page(user=owner, project=project)
    result = page.evaluate(
        f"""async () => {{
          document.cookie = 'csrftoken=' + 'a'.repeat(64) + '; path=/';
          const bootstrap = JSON.parse(document.querySelector('#workspace-bootstrap').textContent);
          const {{ createWorkspaceWorkflow }} = await import('/static/projects/workspace/workflow.js');
          const {{ createPredictionWorkspace }} = await import('/static/projects/workspace/prediction.js');
          const {{ createReflectionWorkspace, renderReflection }} = await import('/static/projects/workspace/reflection.js');
          const workflow = createWorkspaceWorkflow({{ urls: bootstrap.urls }});
          const predictionUi = createPredictionWorkspace({{ urls: {{ current: bootstrap.urls.prediction_current, create: bootstrap.urls.prediction_create, completeTemplate: bootstrap.urls.prediction_complete_template }}, draft: bootstrap.draft }});
          await predictionUi.loadPrediction();
          const predictionDraft = await predictionUi.startPrediction();
          predictionUi.skipPrediction();
          const skippedState = predictionUi.state();
          const analyzed = await workflow.analyze(1, predictionUi.predictionForAnalyze());
          const firstData = await workflow.result(analyzed.analysis_run_id);
          const currentPrediction = await workflow.loadPrediction();
          const reflection = createReflectionWorkspace({{ urls: bootstrap.urls, workflow }});
          await reflection.loadReflection(analyzed.analysis_run_id);
          const reflectionDraft = await reflection.saveReflection({{ original_reasoning: '先观察整体受力。' }});
          const reflectionRoot = document.createElement('section');
          let skippedReflection = false;
          renderReflection(reflectionRoot, reflectionDraft, {{ onSkip: () => {{ skippedReflection = true; }} }});
          [...reflectionRoot.querySelectorAll('button')].find((button) => button.textContent.includes('稍后')).click();
          const afterSkip = await reflection.loadReflection(analyzed.analysis_run_id);
          const editedDraft = {{ ...bootstrap.draft, physical_members: bootstrap.draft.physical_members.map((member) => ({{ ...member, label: '跳过后继续编辑' }})) }};
          const savedAgain = await workflow.saveDraft(editedDraft);
          const analyzedAgain = await workflow.analyze(savedAgain.draft_version, null);
          const secondData = await workflow.result(analyzedAgain.analysis_run_id);
          return {{
            prediction: {{ created: predictionDraft.state, skipped: skippedState.skipped, binding: predictionUi.predictionForAnalyze(), current: currentPrediction.state, id: currentPrediction.prediction?.prediction_id }},
            firstAnalyze: {{ status: analyzed.status, predictionId: null, result: firstData.status }},
            reflection: {{ skippedReflection, status: afterSkip.status, value: afterSkip.original_reasoning }},
            continued: {{ savedVersion: savedAgain.draft_version, analyze: analyzedAgain.status, result: secondData.status }},
          }};
        }}"""
    )
    assert result['prediction']['created'] == 'DRAFT'
    assert result['prediction']['skipped'] is True and result['prediction']['binding'] is None
    assert result['prediction']['current'] == 'DRAFT' and result['prediction']['id'] is not None
    assert result['firstAnalyze'] == {'status': 'SUCCESS', 'predictionId': None, 'result': 'SUCCESS'}
    assert result['reflection'] == {'skippedReflection': True, 'status': 'DRAFT', 'value': '先观察整体受力。'}
    assert result['continued'] == {'savedVersion': 2, 'analyze': 'SUCCESS', 'result': 'SUCCESS'}
