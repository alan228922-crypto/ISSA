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
