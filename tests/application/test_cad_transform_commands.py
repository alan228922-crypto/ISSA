"""Pure frontend command boundary; literals independent of transform implementation."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[2]
JS = BASE / 'projects/static/projects/workspace'


def run_js(body):
    node = shutil.which('node')
    assert node, 'Node is required for the pure ES-module command tests'
    script = f'''import {{applyEditorAction}} from {json.dumps((JS/'editor.js').as_uri())};
import {{captureMemberGroup}} from {json.dumps((JS/'transform-geometry.js').as_uri())};
const d={{schema_version:'physical-draft-v2',version:0,nodes:[{{client_key:'n1',x_mm:0,y_mm:0,label:'A'}},{{client_key:'n2',x_mm:100,y_mm:0,label:'B'}},{{client_key:'n3',x_mm:100,y_mm:80,label:'C'}}],physical_members:[{{client_key:'a',start_node_client_key:'n1',end_node_client_key:'n2',material_id:1,section_id:1,label:'底杆',is_active:true}},{{client_key:'b',start_node_client_key:'n2',end_node_client_key:'n3',material_id:1,section_id:1,label:'立杆',is_active:true}}],member_joint_incidences:[],supports:[{{client_key:'s',target_node_client_key:'n1',support_type:'PINNED',restrained_axis:null}}],node_loads:[{{client_key:'l',target_node_client_key:'n3',fx_N:0,fy_N:-20,label:'力'}}]}};
const resources={{materialIds:[1],sectionIds:[1]}};
const attempt=(draft,action)=>{{try{{return {{draft:applyEditorAction(draft,action)}}}}catch(e){{return {{error:e.code||e.message}}}}}};
{body}
'''
    result = subprocess.run([node, '--input-type=module', '-e', script], cwd=BASE, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_paste_group_remaps_shared_endpoints_without_attachments():
    r = run_js("const original=JSON.stringify(d);const group=captureMemberGroup(d,['a','b']);const out=applyEditorAction(d,{type:'PASTE_MEMBER_GROUP',group,offset:{x:20,y:20},resources});console.log(JSON.stringify({out,unchanged:JSON.stringify(d)===original}));")
    assert r['unchanged']
    d=r['out'];assert len(d['nodes'])==6 and len(d['physical_members'])==4
    assert len({n['client_key'] for n in d['nodes']})==6
    assert len({m['client_key'] for m in d['physical_members']})==4
    new=d['physical_members'][2:];assert new[0]['end_node_client_key']==new[1]['start_node_client_key']
    assert {(n['x_mm'],n['y_mm']) for n in d['nodes'][3:]}=={(20,20),(120,20),(120,100)}
    assert all(m['material_id']==m['section_id']==1 for m in new)
    assert len(d['supports'])==len(d['node_loads'])==1


@pytest.mark.parametrize('offset', [{'x':0,'y':0},{'x':float('inf'),'y':1}])
def test_paste_invalid_is_atomic(offset):
    text="{x:Infinity,y:1}" if offset['x']==float('inf') else json.dumps(offset)
    r=run_js(f"const before=JSON.stringify(d);const r=attempt(d,{{type:'PASTE_MEMBER_GROUP',group:captureMemberGroup(d,['a']),offset:{text},resources}});console.log(JSON.stringify({{r,unchanged:before===JSON.stringify(d)}}));")
    assert r['r'].get('error') and r['unchanged']


def test_paste_rejects_unavailable_catalog_reference():
    r=run_js("console.log(JSON.stringify(attempt(d,{type:'PASTE_MEMBER_GROUP',group:captureMemberGroup(d,['a']),offset:{x:20,y:20},resources:{materialIds:[],sectionIds:[1]}})));")
    assert r.get('error')


def test_paste_explicit_interior_joint_is_preserved():
    r=run_js("d.nodes.push({client_key:'mid',x_mm:50,y_mm:0,label:''});d.member_joint_incidences.push({member_client_key:'a',node_client_key:'mid'});const out=applyEditorAction(d,{type:'PASTE_MEMBER_GROUP',group:captureMemberGroup(d,['a']),offset:{x:20,y:20},resources});console.log(JSON.stringify(out));")
    assert len(r['nodes'])==7 and len(r['member_joint_incidences'])==2
    row=r['member_joint_incidences'][1];n=next(n for n in r['nodes'] if n['client_key']==row['node_client_key']);assert (n['x_mm'],n['y_mm'])==(70,20)
    assert row['member_client_key']==r['physical_members'][-1]['client_key']


def test_translate_atomic_group_keeps_identity_attachments_and_values():
    r=run_js("const out=applyEditorAction(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a','b'],transform:{kind:'TRANSLATE',dx:100.25,dy:-50.5}});console.log(JSON.stringify({out,original:d}));")
    assert [(n['x_mm'],n['y_mm']) for n in r['out']['nodes']]==[(100.25,-50.5),(200.25,-50.5),(200.25,29.5)]
    assert [n['client_key'] for n in r['out']['nodes']]==['n1','n2','n3']
    for name in ['physical_members','supports','node_loads','member_joint_incidences']:assert r['out'][name]==r['original'][name]


def test_translate_shared_boundary_rejects_without_partial_mutation():
    r=run_js("const before=JSON.stringify(d);const r=attempt(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a'],transform:{kind:'TRANSLATE',dx:10,dy:0}});console.log(JSON.stringify({r,unchanged:before===JSON.stringify(d)}));")
    assert r['r'].get('error')=='TRANSFORM_SHARED_NODE' and r['unchanged']


def test_translate_interior_incidence_boundary_blocks_external_member():
    r=run_js("d.nodes.push({client_key:'mid',x_mm:50,y_mm:0,label:''});d.member_joint_incidences.push({member_client_key:'a',node_client_key:'mid'});d.physical_members[1].start_node_client_key='mid';console.log(JSON.stringify(attempt(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a'],transform:{kind:'TRANSLATE',dx:10,dy:0}})));")
    assert r.get('error')=='TRANSFORM_SHARED_NODE'


@pytest.mark.parametrize('dx,dy', [('NaN','0'),('Infinity','0'),('0','-Infinity')])
def test_translate_nonfinite_rejected(dx,dy):
    r=run_js("console.log(JSON.stringify(attempt(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a','b'],transform:{kind:'TRANSLATE',dx:DX,dy:DY}})));".replace("DX",dx).replace("DY",dy))
    assert r.get('error')=='TRANSFORM_INVALID_VALUE'


def test_translate_into_existing_node_is_rejected():
    r=run_js("d.physical_members=d.physical_members.slice(0,1);console.log(JSON.stringify(attempt(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a'],transform:{kind:'TRANSLATE',dx:0,dy:80}})));")
    assert r.get('error')


@pytest.mark.parametrize('angle,expected',[(90,[(50,-50),(50,50)]),(-45,[(14.64466094067262,35.35533905932737),(85.35533905932738,-35.35533905932737)]),(22.5,[(3.806023374435661,-19.134171618254488),(96.19397662556435,19.134171618254488)])])
def test_rotate_independent_member_world_ccw(angle,expected):
    r=run_js("d.physical_members=d.physical_members.slice(0,1);const out=applyEditorAction(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a'],transform:{kind:'ROTATE',angle:ANGLE}});console.log(JSON.stringify({out,original:d}));".replace('ANGLE',str(angle)))
    for row,point in zip(r['out']['nodes'][:2],expected):assert (row['x_mm'],row['y_mm'])==pytest.approx(point,abs=1e-10)
    assert r['out']['nodes'][2]==r['original']['nodes'][2]
    for name in ['physical_members','supports','node_loads']:assert r['out'][name]==r['original'][name]


def test_rotate_unique_endpoint_centroid_and_interior_incidence():
    r=run_js("d.nodes.push({client_key:'mid',x_mm:50,y_mm:0,label:''});d.member_joint_incidences.push({member_client_key:'a',node_client_key:'mid'});console.log(JSON.stringify(applyEditorAction(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a','b'],transform:{kind:'ROTATE',angle:90}})));")
    for n,expected in zip(r['nodes'],[(280/3,-40),(280/3,60),(40/3,60),(280/3,10)]):assert (n['x_mm'],n['y_mm'])==pytest.approx(expected,abs=1e-10)
    assert r['member_joint_incidences']==[{'member_client_key':'a','node_client_key':'mid'}]


def test_rotate_shared_boundary_blocks():
    r=run_js("console.log(JSON.stringify(attempt(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a'],transform:{kind:'ROTATE',angle:90}})));")
    assert r.get('error')=='TRANSFORM_SHARED_NODE'


@pytest.mark.parametrize('angle',['NaN','Infinity'])
def test_rotate_nonfinite_rejects(angle):
    r=run_js("console.log(JSON.stringify(attempt(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a','b'],transform:{kind:'ROTATE',angle:ANGLE}})));".replace('ANGLE',angle))
    assert r.get('error')=='TRANSFORM_INVALID_VALUE'


def test_transforms_single_history_entry_dirty_and_undo_redo():
    r=run_js("""const {createWorkspaceState,applyWorkspaceEditorAction,undoWorkspaceEdit,redoWorkspaceEdit}=await import('./projects/static/projects/workspace/state.js');
let s=createWorkspaceState({draft:d,read_only:false});const original=JSON.stringify(s.draft);
s=applyWorkspaceEditorAction(s,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a','b'],transform:{kind:'TRANSLATE',dx:20,dy:20}});
const moved=s;const undo=undoWorkspaceEdit(s);const redo=redoWorkspaceEdit(undo);
const same=applyWorkspaceEditorAction(redo,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a','b'],transform:{kind:'TRANSLATE',dx:0,dy:0}});
console.log(JSON.stringify({past:s.history.past.length,dirty:s.dirty,undo:JSON.stringify(undo.draft)===original,redo:JSON.stringify(redo.draft)===JSON.stringify(moved.draft),same:same===redo}));""")
    assert r=={'past':1,'dirty':True,'undo':True,'redo':True,'same':True}
