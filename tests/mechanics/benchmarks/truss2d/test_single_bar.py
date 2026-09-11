"""B/T01：δ=PL/EA、N=P、左反力=-P 的獨立解析解。"""
from dataclasses import replace
import pytest
from mechanics.truss2d.model import TrussModel,Node,Member,Support,NodalLoad
from mechanics.truss2d.errors import MechanicsError


def bar(force=1000):
    return TrussModel('truss2d-input-v1',(Node('a',0,0),Node('b',1000,0)),
        (Member('ab','a','b',200000,100),),
        (Support('a',True,True),Support('b',False,True)),(NodalLoad('b',force,0),))


@pytest.mark.parametrize('force,displacement',[(1000,.05),(-1000,-.05),(0,0)])
def test_single_bar_analytical(force,displacement):
    from mechanics.truss2d.solver import Truss2DSolver
    result=Truss2DSolver().solve(bar(force))
    u={v.node_id:v for v in result.node_displacements}
    r={v.node_id:v for v in result.support_reactions}
    assert (u['a'].ux_mm,u['a'].uy_mm,u['b'].ux_mm,u['b'].uy_mm) == pytest.approx((0,0,displacement,0),rel=1e-10,abs=1e-12)
    assert (r['a'].rx_N,r['a'].ry_N,r['b'].rx_N,r['b'].ry_N) == pytest.approx((-force,0,0,0),rel=1e-10,abs=1e-9)
    assert result.member_axial_forces[0].axial_force_N == pytest.approx(force,rel=1e-10,abs=1e-9)
    assert result.solver_version and result.input_schema_version == 'truss2d-input-v1'
    assert result.diagnostics.free_dof == 1
    assert abs(result.diagnostics.free_residual_N) < 1e-9


def test_restrained_node_load_is_included_in_reaction():
    from mechanics.truss2d.solver import Truss2DSolver
    model=replace(bar(),nodal_loads=(NodalLoad('a',200,300),NodalLoad('b',1000,0)))
    r=Truss2DSolver().solve(model).support_reactions[0]
    assert (r.rx_N,r.ry_N) == pytest.approx((-1200,-300),rel=1e-10,abs=1e-9)


def test_all_dofs_restrained():
    from mechanics.truss2d.solver import Truss2DSolver
    model=replace(bar(),supports=(Support('a',True,True),Support('b',True,True)))
    result=Truss2DSolver().solve(model)
    assert all(u.ux_mm==u.uy_mm==0 for u in result.node_displacements)
    assert result.support_reactions[1].rx_N == -1000
    assert result.member_axial_forces[0].axial_force_N == 0


def test_internal_mechanism_is_structured_failure():
    from mechanics.truss2d.solver import Truss2DSolver
    # 正方形四邊無斜撐：三個支承約束去除剛體運動，仍有內部機構。
    model=TrussModel('truss2d-input-v1',tuple(Node(k,x,y) for k,x,y in
        [('a',0,0),('b',1000,0),('c',1000,1000),('d',0,1000)]),
        tuple(Member(k,i,j,200000,100) for k,i,j in [('ab','a','b'),('bc','b','c'),('cd','c','d'),('da','d','a')]),
        (Support('a',True,True),Support('b',False,True)),(NodalLoad('c',100,0),))
    with pytest.raises(MechanicsError) as error:
        Truss2DSolver().solve(model)
    assert 'SINGULAR_GLOBAL_STIFFNESS' in {i.code for i in error.value.issues}


def test_solver_validation_and_determinism():
    from mechanics.truss2d.solver import Truss2DSolver
    solver=Truss2DSolver()
    assert solver.solve(bar()) == solver.solve(bar())
    with pytest.raises(MechanicsError) as error:
        solver.solve(replace(bar(),supports=()))
    assert 'NO_SUPPORT' in {i.code for i in error.value.issues}
