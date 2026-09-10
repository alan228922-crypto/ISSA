"""B/S01 矩形：expected 為手算常數，容差是數值比較而非安全係數。"""
import pytest


def test_rectangle_analytical_properties():
    from mechanics.sections.model import Rectangle
    from mechanics.sections.properties import rectangle_properties
    # b=6 沿 x、h=2 沿 y；A=12，Ix=6*2³/12=4，Iy=2*6³/12=36。
    # 重心明確設在 (10,-3) mm；自體重心軸慣性矩不隨平移改變。
    p = rectangle_properties(Rectangle(6, 2, 0.001, 10, -3))
    assert (p.A_mm2, p.centroid_x_mm, p.centroid_y_mm, p.Ix_mm4, p.Iy_mm4,
            p.mass_per_length_g_per_mm) == pytest.approx((12, 10, -3, 4, 36, .012), rel=1e-12, abs=1e-12)
    assert (p.strong_axis, p.weak_axis) == ('Y', 'X')


def test_square_equal_axes():
    from mechanics.sections.model import Rectangle
    from mechanics.sections.properties import rectangle_properties
    p = rectangle_properties(Rectangle(2, 2, 0))
    assert (p.strong_axis, p.weak_axis) == ('EQUAL', 'EQUAL')


@pytest.mark.parametrize('field,value', [('width_mm',0),('height_mm',-1),
    ('density_g_per_mm3',-1),('center_x_mm',float('nan')),('height_mm',float('inf')),
    ('width_mm',True),('width_mm','6')])
def test_invalid_rectangle_input(field, value):
    from mechanics.sections.model import Rectangle
    from mechanics.sections.properties import rectangle_properties
    kw = dict(width_mm=6, height_mm=2, density_g_per_mm3=.001)
    kw[field] = value
    with pytest.raises(ValueError):
        rectangle_properties(Rectangle(**kw))
