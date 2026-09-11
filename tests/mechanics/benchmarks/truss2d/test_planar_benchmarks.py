"""B/T02、B/T03 与 B/T04：节点平衡、伸长相容和解析闭式参考。"""
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


def indeterminate_three_bar():
    return TrussModel('truss2d-input-v1',
        (Node('A',-1000,0),Node('B',0,1000),Node('C',1000,0),Node('D',0,0)),
        (Member('AB','A','B',200000,100),Member('BC','B','C',200000,100),Member('DB','D','B',200000,100)),
        (Support('A',True,True),Support('C',True,True),Support('D',True,True)),
        (NodalLoad('B',0,-10000),))


def test_indeterminate_three_bar_analytical_reference():
    """B/T04：由对称性、相容条件和杆件刚度推导的三杆超静定桁架。"""
    from mechanics.truss2d.solver import Truss2DSolver
    load_N=10_000.0
    h_mm=1_000.0
    ea_N=20_000_000.0
    root2=sqrt(2)
    result=Truss2DSolver().solve(indeterminate_three_bar())
    displacement={v.node_id:(v.ux_mm,v.uy_mm) for v in result.node_displacements}
    axial_force={v.member_id:v.axial_force_N for v in result.member_axial_forces}
    reaction={v.node_id:(v.rx_N,v.ry_N) for v in result.support_reactions}

    # Ky=EA/h*(1+1/sqrt(2))，因此 uy=-P*h/(EA*(1+1/sqrt(2)))。
    assert displacement['B'] == pytest.approx((0,-load_N*h_mm/(ea_N*(1+1/root2))),rel=1e-8,abs=1e-10)
    assert axial_force == pytest.approx({
        'AB':-load_N*(1-1/root2),
        'BC':-load_N*(1-1/root2),
        'DB':-load_N*(2-root2),
    },rel=1e-8,abs=1e-8)
    expected_reaction={
        'A':(load_N*(1-1/root2)/sqrt(2),load_N*(1-1/root2)/sqrt(2)),
        'C':(-load_N*(1-1/root2)/sqrt(2),load_N*(1-1/root2)/sqrt(2)),
        'D':(0,load_N*(2-root2)),
    }
    for node_id,expected in expected_reaction.items():
        assert reaction[node_id] == pytest.approx(expected,rel=1e-8,abs=1e-8)
    assert sum(value[0] for value in reaction.values()) == pytest.approx(0,abs=1e-8)
    assert sum(value[1] for value in reaction.values())-load_N == pytest.approx(0,abs=1e-8)
