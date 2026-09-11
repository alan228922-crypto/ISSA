"""B/T02、B/T03：節點平衡與伸長相容的手算 reference；B/T04 尚無可信 fixture。"""
from dataclasses import replace
from math import sqrt
import pytest
from mechanics.truss2d.model import TrussModel,Node,Member,Support,NodalLoad


def triangle():
    return TrussModel('truss2d-input-v1',(Node('a',0,0),Node('b',2000,0),Node('c',1000,1000)),
        (Member('ab','a','b',200000,100),Member('ac','a','c',200000,100),Member('bc','b','c',200000,100)),
        (Support('a',True,True),Support('b',False,True)),(NodalLoad('c',0,-1000),))


def test_triangle_hand_calculation():
    from mechanics.truss2d.solver import Truss2DSolver
    result=Truss2DSolver().solve(triangle())
    n={v.member_id:v.axial_force_N for v in result.member_axial_forces}
    u={v.node_id:(v.ux_mm,v.uy_mm) for v in result.node_displacements}
    r={v.node_id:(v.rx_N,v.ry_N) for v in result.support_reactions}
    # 平衡：各反力 P/2=500；斜桿 N=-P/√2；底桿 N=P/2。
    assert n == pytest.approx({'ab':500,'ac':-1000/sqrt(2),'bc':-1000/sqrt(2)},rel=1e-8,abs=1e-8)
    assert r['a'] == pytest.approx((0,500),rel=1e-8,abs=1e-8)
    assert r['b'] == pytest.approx((0,500),rel=1e-8,abs=1e-8)
    # EA=20,000,000 N；底桿伸長 .05 mm；頂點 ux=.025。
    # 左斜桿伸長=-.05 mm=(ux+uy)/√2，所以 uy=-.025-.05√2。
    assert u['b'] == pytest.approx((.05,0),rel=1e-8,abs=1e-10)
    assert u['c'] == pytest.approx((.025,-.025-.05*sqrt(2)),rel=1e-8,abs=1e-10)


def test_symmetric_planar_truss():
    from mechanics.truss2d.solver import Truss2DSolver
    model=TrussModel('truss2d-input-v1',tuple(Node(k,x,y) for k,x,y in
        [('a',0,0),('b',1000,1000),('c',2000,0),('d',3000,1000),('e',4000,0)]),
        tuple(Member(k,i,j,200000,100) for k,i,j in
        [('ab','a','b'),('bc','b','c'),('cd','c','d'),('de','d','e'),('ac','a','c'),('ce','c','e'),('bd','b','d')]),
        (Support('a',True,True),Support('e',False,True)),(NodalLoad('b',0,-100),NodalLoad('d',0,-100)))
    result=Truss2DSolver().solve(model)
    n={v.member_id:v.axial_force_N for v in result.member_axial_forces}
    u={v.node_id:v for v in result.node_displacements}
    # 結構及載重關於 x=2000 對稱，反力各 100 N。
    for r in result.support_reactions:
        assert (r.rx_N,r.ry_N) == pytest.approx((0,100),rel=1e-8,abs=1e-8)
    for a,b in [('ab','de'),('bc','cd'),('ac','ce')]:
        assert n[a] == pytest.approx(n[b],rel=1e-8,abs=1e-8)
    assert u['b'].uy_mm == pytest.approx(u['d'].uy_mm,rel=1e-8,abs=1e-10)
    assert u['b'].ux_mm+u['d'].ux_mm == pytest.approx(u['e'].ux_mm,rel=1e-8,abs=1e-10)


def test_input_reordering_preserves_results():
    from mechanics.truss2d.solver import Truss2DSolver
    model=triangle()
    a=Truss2DSolver().solve(model)
    b=Truss2DSolver().solve(replace(model,nodes=model.nodes[::-1],members=model.members[::-1],supports=model.supports[::-1]))
    for result_field,id_field,value_fields in [('node_displacements','node_id',('ux_mm','uy_mm')),
        ('support_reactions','node_id',('rx_N','ry_N')),('member_axial_forces','member_id',('axial_force_N',))]:
        expected={getattr(v,id_field):tuple(getattr(v,k) for k in value_fields) for v in getattr(a,result_field)}
        for v in getattr(b,result_field):
            assert tuple(getattr(v,k) for k in value_fields) == pytest.approx(expected[getattr(v,id_field)],rel=1e-8,abs=1e-8)


@pytest.mark.skip(reason='B/T04 BLOCKED — MISSING TRUSTED BENCHMARK REFERENCE')
def test_indeterminate_truss_reference_pending():
    """沒有可信 reference 時明確顯示 gate 未通過，不生成假的 expected fixture。"""
