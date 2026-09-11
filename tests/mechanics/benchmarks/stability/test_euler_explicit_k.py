"""B/E01 純 Euler 公式；explicit I/K 不代表已確認控制軸或有效長度政策。"""
from math import pi
import pytest


@pytest.mark.parametrize('k,expected',[(1,2*pi*pi),(2,.5*pi*pi),(.5,8*pi*pi)])
def test_explicit_k_formula(k,expected):
    from mechanics.stability.euler import euler_critical_load
    # E=200000 MPa，I=10 mm⁴，L=1000 mm：EI/L²=2 N。
    assert euler_critical_load(E_MPa=200000,I_mm4=10,L_mm=1000,K=k) == pytest.approx(expected,rel=1e-12,abs=1e-12)


def test_K_has_no_default():
    from mechanics.stability.euler import euler_critical_load
    with pytest.raises(TypeError):
        euler_critical_load(E_MPa=200000,I_mm4=10,L_mm=1000)


@pytest.mark.parametrize('field',['E_MPa','I_mm4','L_mm','K'])
@pytest.mark.parametrize('value',[0,-1,float('nan'),float('inf'),True,'1'])
def test_invalid_euler_parameters(field,value):
    from mechanics.stability.euler import euler_critical_load
    kw=dict(E_MPa=200000,I_mm4=10,L_mm=1000,K=1)
    kw[field]=value
    with pytest.raises(ValueError): euler_critical_load(**kw)


def test_euler_unrepresentable_result():
    from mechanics.stability.euler import euler_critical_load
    with pytest.raises(ValueError,match='NUMERIC_RANGE'):
        euler_critical_load(E_MPa=1e308,I_mm4=1e308,L_mm=1,K=1)
