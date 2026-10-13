"""Explicit deletion intent: preview purity, bounded topology and public journeys."""
import pytest
from playwright.sync_api import expect
from tests.application.test_physical_draft import context
from tests.browser.test_cad_core_drawing import open_core, move_world

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
