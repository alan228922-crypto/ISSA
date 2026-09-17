import pytest

from modeling.services import save_physical_draft
from tests.application.test_physical_draft import context, valid_payload


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
                selectedStrokeDasharray: getComputedStyle(svg.querySelector('[data-client-key="m1"] line')).strokeDasharray,
                loadDirection: [...svg.querySelector('[data-client-key="l1"]').querySelectorAll('line')].map((line) => ({ y1: Number(line.getAttribute('y1')), y2: Number(line.getAttribute('y2')) })),
          };
        }"""
    )

    assert rendered['unchangedDraft'] is True
    assert rendered['stable'] is True
    assert {(item['key'], item['kind']) for item in rendered['objects']} == {
        ('n1', 'GeometryNode'), ('n2', 'GeometryNode'), ('m1', 'PhysicalMember'),
        ('c1', 'Connection'), ('support-c1', 'Support'), ('l1', 'NodeLoad'),
    }
    assert all(item['tabindex'] == '0' and item['role'] == 'button' and item['label'] for item in rendered['objects'])
    assert any(item['key'] == 'm1' and item['selected'] == 'true' and item['focused'] == 'true' for item in rendered['objects'])
    assert rendered['selectedStrokeDasharray'] != 'none'
    assert 'AnalysisElement' not in rendered['markup']
    assert rendered['loadDirection'][0]['y1'] < rendered['loadDirection'][0]['y2']


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
    assert result['g']==[500,200,100,0,-100] and result['h']['point']=={'x':500,'y':75} and result['v']['point']=={'x':125,'y':500} and result['tie']['point']=={'x':200,'y':0}


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
