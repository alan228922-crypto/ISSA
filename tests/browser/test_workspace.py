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
        ('c1', 'Connection'), ('s1', 'Support'), ('l1', 'NodeLoad'),
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


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_editor_crossing_members_do_not_create_connection(context, workspace_page):
    owner, project, _, _ = context; page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => { const { applyEditorAction } = await import('/static/projects/workspace/editor.js'); const draft={schema_version:'physical-draft-v1',version:4,nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:''},{client_key:'n2',x_mm:100,y_mm:100,label:''},{client_key:'n3',x_mm:0,y_mm:100,label:''},{client_key:'n4',x_mm:100,y_mm:0,label:''}],physical_members:[{client_key:'m1',start_node_client_key:'n1',end_node_client_key:'n2',material_id:1,section_id:1,label:'',is_active:true}],connections:[],supports:[],node_loads:[]}; const crossing=applyEditorAction(draft,{type:'CREATE_MEMBER',member:{client_key:'m2',start_node_client_key:'n3',end_node_client_key:'n4',material_id:1,section_id:1,label:'',is_active:true}}); const connected=applyEditorAction(crossing,{type:'CREATE_CONNECTION',connection:{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:['m1']}}); return {before:draft.connections.length,crossing:crossing.connections.length,explicit:connected.connections.length,unchanged:JSON.stringify(draft)}; }""")
    assert result['before'] == 0 and result['crossing'] == 0 and result['explicit'] == 1


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
        'dependency': {'name':'EditorActionError','code':'EDITOR_DEPENDENCY_CONFLICT','unchanged':True},
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
      const connectionRemoved=applyEditorAction(loadRemoved,{type:'DELETE_OBJECT',target:{kind:'CONNECTION',clientKey:'c1'}});
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
        'nodeDependency': {'code':'EDITOR_DEPENDENCY_CONFLICT','unchanged':True},
        'connectionDependency': {'code':'EDITOR_DEPENDENCY_CONFLICT','unchanged':True},
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
    assert result['grid'] == {'origin':{'x':0,'y':0},'spacing':100} and result['unchanged'] is True


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
    result=page.evaluate("""()=>{const svg=document.querySelector('#workspace-canvas');const member=svg.querySelector('[data-client-key="m1"]');const box=member.getBoundingClientRect();member.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:box.left+box.width/2,clientY:box.top+box.height/2}));const mouse=svg.querySelector('[data-client-key="m1"]').dataset.selected;const keyboard=svg.querySelector('[data-client-key="m1"]');keyboard.focus();keyboard.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));const key=svg.querySelector('[data-client-key="m1"]').dataset.selected;svg.dispatchEvent(new WheelEvent('wheel',{deltaY:-100,clientX:100,clientY:50,bubbles:true,cancelable:true}));return {mouse,key,transform:svg.querySelector('[data-world-layer]').getAttribute('transform')};}""")
    assert result['mouse'] == 'true' and result['key'] == 'true' and result['transform'] == 'matrix(1.1 0 0 -1.1 -10 -5)'


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
