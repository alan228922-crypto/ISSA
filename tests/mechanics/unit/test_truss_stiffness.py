"""單元矩陣參考來自 EA/L 與軸向伸長的投影，不呼叫 production 產生 expected。"""
import numpy as np
import pytest
from mechanics.truss2d.model import Node, Member


def test_horizontal_and_inclined_stiffness():
    from mechanics.truss2d.assembly import element_stiffness
    # EA/L=20 N/mm；[ui_x,ui_y,uj_x,uj_y]，水平桿只有 x 耦合。
    m=Member('m','a','b',100,2)
    np.testing.assert_allclose(element_stiffness(m,Node('a',0,0),Node('b',10,0)),
        [[20,0,-20,0],[0,0,0,0],[-20,0,20,0],[0,0,0,0]],rtol=1e-12,atol=1e-12)
    # 3-4-5 方向 c=.6,s=.8，EA/L=40，外積係數為 .36/.48/.64。
    k=element_stiffness(m,Node('a',0,0),Node('b',3,4))
    np.testing.assert_allclose(k,[[14.4,19.2,-14.4,-19.2],[19.2,25.6,-19.2,-25.6],
        [-14.4,-19.2,14.4,19.2],[-19.2,-25.6,19.2,25.6]],rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(k,k.T,rtol=0,atol=1e-12)


@pytest.mark.parametrize('e,a,l,want',[(200,2,10,40),(100,4,10,40),(100,2,20,10)])
def test_E_A_inverse_L_scaling(e,a,l,want):
    from mechanics.truss2d.assembly import element_stiffness
    assert element_stiffness(Member('m','a','b',e,a),Node('a',0,0),Node('b',l,0))[0,0] == pytest.approx(want)
