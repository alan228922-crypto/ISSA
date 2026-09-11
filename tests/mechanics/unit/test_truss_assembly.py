"""兩桿串聯中共享節點的剛度應相加；重複載重累加，支承採 DOF 聯集。"""
from dataclasses import replace
import numpy as np
import pytest
from mechanics.truss2d.model import TrussModel,Node,Member,Support,NodalLoad


def chain():
    return TrussModel('truss2d-input-v1',(Node('a',0,0),Node('b',10,0),Node('c',30,0)),
        (Member('ab','a','b',100,2),Member('bc','b','c',100,2)),
        (Support('a',True,True),Support('b',False,True),Support('c',False,True)),
        (NodalLoad('c',7,0),NodalLoad('c',3,-2)))


def test_global_K_P_and_dof_mapping():
    from mechanics.truss2d.assembly import assemble_global_stiffness
    system=assemble_global_stiffness(chain())
    assert system.dof_map == {'a':(0,1),'b':(2,3),'c':(4,5)}
    assert system.restrained_dofs == (0,1,3,5)
    assert system.K_N_per_mm.dtype == np.float64
    np.testing.assert_allclose(system.K_N_per_mm,
        [[20,0,-20,0,0,0],[0,0,0,0,0,0],[-20,0,30,0,-10,0],
         [0,0,0,0,0,0],[0,0,-10,0,10,0],[0,0,0,0,0,0]],rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(system.P_N,[0,0,0,0,10,-2],rtol=0,atol=1e-12)


def test_dof_order_follows_input_sequence():
    from mechanics.truss2d.assembly import assemble_global_stiffness
    model=chain()
    assert assemble_global_stiffness(replace(model,nodes=model.nodes[::-1])).dof_map == {'c':(0,1),'b':(2,3),'a':(4,5)}


def test_invalid_model_does_not_reach_assembly():
    from mechanics.truss2d.assembly import assemble_global_stiffness
    from mechanics.truss2d.errors import MechanicsError
    with pytest.raises(MechanicsError) as error:
        assemble_global_stiffness(replace(chain(),members=()))
    assert 'EMPTY_MODEL' in {i.code for i in error.value.issues}


def test_stiffness_numeric_overflow_is_structured():
    from mechanics.truss2d.assembly import assemble_global_stiffness
    from mechanics.truss2d.errors import MechanicsError
    model=chain()
    with pytest.raises(MechanicsError) as error:
        assemble_global_stiffness(replace(model,members=(replace(model.members[0],E_MPa=1e308,A_mm2=1e308),model.members[1])))
    assert 'NUMERIC_RANGE' in {i.code for i in error.value.issues}
