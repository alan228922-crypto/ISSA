import pytest
from tests.application.test_cad_transform_commands import run_js


def test_rotate_explicit_world_center_preserves_identity():
    r=run_js("console.log(JSON.stringify(applyEditorAction(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a','b'],transform:{kind:'ROTATE',angle:90,center:{x:0,y:0}}})));")
    for n,point in zip(r['nodes'],[(0,0),(0,100),(-80,100)]):assert (n['x_mm'],n['y_mm'])==pytest.approx(point,abs=1e-10)
    assert [n['client_key'] for n in r['nodes']]==['n1','n2','n3']


def test_rotate_invalid_explicit_center_rejects():
    r=run_js("console.log(JSON.stringify(attempt(d,{type:'TRANSFORM_MEMBER_GROUP',memberKeys:['a','b'],transform:{kind:'ROTATE',angle:90,center:{x:NaN,y:0}}})));")
    assert r.get('error')=='TRANSFORM_INVALID_VALUE'


@pytest.mark.parametrize('mode,value,expected',[('TOTAL',150,150),('DELTA',40,140),('DELTA',-20,80)])
def test_resize_member_shared_endpoint_preserves_all_references(mode,value,expected):
    r=run_js("const original=JSON.stringify(d);const out=applyEditorAction(d,{type:'RESIZE_MEMBER',memberKey:'a',nodeKey:'n2',mode:'MODE',value:VALUE});console.log(JSON.stringify({out,original:d,unchanged:JSON.stringify(d)===original}));".replace('MODE',mode).replace('VALUE',str(value)))
    assert r['unchanged'];assert r['out']['nodes'][1]['x_mm']==expected;assert r['out']['nodes'][0]==r['original']['nodes'][0]
    for name in ['physical_members','supports','node_loads','member_joint_incidences']:assert r['out'][name]==r['original'][name]


@pytest.mark.parametrize('mode,value',[('TOTAL','0'),('DELTA','-100'),('TOTAL','Infinity'),('TOTAL','NaN')])
def test_resize_invalid_length_is_atomic(mode,value):
    r=run_js("const before=JSON.stringify(d);const result=attempt(d,{type:'RESIZE_MEMBER',memberKey:'a',nodeKey:'n2',mode:'MODE',value:VALUE});console.log(JSON.stringify({result,unchanged:before===JSON.stringify(d)}));".replace('MODE',mode).replace('VALUE',value))
    assert r['unchanged'] and r['result'].get('error')


def test_resize_preserves_interior_incidence_or_rejects_whole_proposal():
    r=run_js("d.nodes.push({client_key:'mid',x_mm:100,y_mm:40,label:''});d.member_joint_incidences.push({member_client_key:'b',node_client_key:'mid'});const before=JSON.stringify(d);const result=attempt(d,{type:'RESIZE_MEMBER',memberKey:'a',nodeKey:'n2',mode:'TOTAL',value:150});console.log(JSON.stringify({result,unchanged:JSON.stringify(d)===before}));")
    assert r['unchanged'] and r['result'].get('error')


def test_stretch_shared_node_existing_update_keeps_identity_and_attachments():
    r=run_js("const out=applyEditorAction(d,{type:'UPDATE_OBJECT',target:{kind:'GEOMETRY_NODE',clientKey:'n2'},changes:{x_mm:120,y_mm:-10}});console.log(JSON.stringify({out,original:d}));")
    assert r['out']['nodes'][1]['client_key']=='n2';assert (r['out']['nodes'][1]['x_mm'],r['out']['nodes'][1]['y_mm'])==(120,-10)
    for name in ['physical_members','supports','node_loads']:assert r['out'][name]==r['original'][name]


def test_resize_start_endpoint_with_attachment_references_and_fixed_opposite():
    r=run_js("d.supports[0].target_node_client_key='n1';d.node_loads[0].target_node_client_key='n1';const out=applyEditorAction(d,{type:'RESIZE_MEMBER',memberKey:'a',nodeKey:'n1',mode:'TOTAL',value:150});console.log(JSON.stringify({out,original:d}));")
    assert (r['out']['nodes'][0]['x_mm'],r['out']['nodes'][0]['y_mm'])==(-50,0);assert r['out']['nodes'][1:]==r['original']['nodes'][1:]
    for name in ['physical_members','supports','node_loads']:assert r['out'][name]==r['original'][name]
