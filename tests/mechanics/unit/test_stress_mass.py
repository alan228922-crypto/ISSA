"""σ=N/A 與 density*A*L 的獨立單位驗證，分類不可改寫原始數值。"""
import pytest


@pytest.mark.parametrize('force,expected,state',[(100,5,'TENSION'),(-100,-5,'COMPRESSION'),(0,0,'ZERO'),(1e-10,5e-12,'ZERO')])
def test_stress_sign_and_zero_tolerance(force,expected,state):
    from mechanics.truss2d.postprocess import member_stress
    result=member_stress('m',force,20)
    assert result.axial_stress_MPa == pytest.approx(expected,rel=1e-12,abs=1e-20)
    assert result.state == state


def test_mass_units_and_total():
    from mechanics.truss2d.postprocess import member_mass,total_mass_g
    # .001 g/mm³ * 20 mm² * 1000 mm = 20 g；加另一支 10 g 得 30 g。
    a=member_mass('a',.001,20,1000)
    b=member_mass('b',.001,20,500)
    assert (a.mass_g,b.mass_g,total_mass_g((a,b))) == pytest.approx((20,10,30),rel=1e-12,abs=1e-12)
    assert member_mass('zero',0,20,1000).mass_g == 0
    assert total_mass_g(()) == 0
    with pytest.raises(ValueError,match='DUPLICATE'):
        total_mass_g((a,a))


@pytest.mark.parametrize('value',[0,-1,float('nan'),float('inf'),True,'20'])
def test_invalid_area_rejected(value):
    from mechanics.truss2d.postprocess import member_stress,member_mass
    with pytest.raises(ValueError): member_stress('m',100,value)
    with pytest.raises(ValueError): member_mass('m',.001,value,1000)


@pytest.mark.parametrize('value',[-1,float('nan'),float('inf'),True,'1'])
def test_invalid_density_and_tolerance(value):
    from mechanics.truss2d.postprocess import member_mass,member_stress
    with pytest.raises(ValueError): member_mass('m',value,20,1000)
    with pytest.raises(ValueError): member_stress('m',1,20,zero_force_atol_N=value)


def test_invalid_length_force_and_unrepresentable_output():
    from mechanics.truss2d.postprocess import member_mass,member_stress
    for value in [0,-1,float('nan'),float('inf')]:
        with pytest.raises(ValueError): member_mass('m',.001,20,value)
    for value in [float('nan'),float('inf'),True,10**400]:
        with pytest.raises(ValueError): member_stress('m',value,20)
    with pytest.raises(ValueError,match='NUMERIC_RANGE'):
        member_mass('m',1e308,1e308,1e308)
    with pytest.raises(ValueError,match='NUMERIC_RANGE'):
        member_stress('m',1e308,1e-308)
