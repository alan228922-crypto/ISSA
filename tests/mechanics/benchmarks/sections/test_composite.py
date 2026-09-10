"""B/S01 非重疊組合：面積重心與平行軸定理的獨立手算案例。"""
import pytest
from mechanics.sections.model import Rectangle


def test_symmetric_composite():
    from mechanics.sections.properties import composite_properties
    p = composite_properties((Rectangle(2,2,.001,0,-2), Rectangle(2,2,.001,0,2)))
    # A=8；Ix=2*(2*2³/12+4*2²)=104/3；Iy=2*(2*2³/12)=8/3。
    assert (p.A_mm2,p.centroid_x_mm,p.centroid_y_mm,p.Ix_mm4,p.Iy_mm4,
            p.mass_per_length_g_per_mm) == pytest.approx((8,0,0,104/3,8/3,.008), rel=1e-12,abs=1e-12)


def test_asymmetric_composite_and_translation():
    from mechanics.sections.properties import composite_properties
    for dx,dy in [(0,0),(12,-4)]:
        p = composite_properties((Rectangle(4,2,.001,dx,dy), Rectangle(2,2,.002,3+dx,2+dy)))
        # 面積 8:4，重心 (1,2/3)；Ix=4+32/3，Iy=12+24。
        # 使用面積加權而非密度加權；密度只影響 mass/length。
        assert (p.A_mm2,p.centroid_x_mm,p.centroid_y_mm,p.Ix_mm4,p.Iy_mm4,
                p.mass_per_length_g_per_mm) == pytest.approx((12,1+dx,2/3+dy,44/3,36,.016),rel=1e-12,abs=1e-12)


@pytest.mark.parametrize('angle,ix,iy', [(90,36,4),(45,20,20)])
def test_rotated_rectangle(angle,ix,iy):
    from mechanics.sections.properties import composite_properties
    p = composite_properties((Rectangle(6,2,0,angle_deg=angle),))
    assert (p.Ix_mm4,p.Iy_mm4) == pytest.approx((ix,iy),rel=1e-12,abs=1e-12)


@pytest.mark.parametrize('components', [(),(Rectangle(2,2,0),Rectangle(2,2,0,1,0))])
def test_empty_or_overlapping_composite_is_unsupported(components):
    from mechanics.sections.properties import composite_properties
    with pytest.raises(ValueError, match='EMPTY_SECTION|OVERLAP_UNSUPPORTED'):
        composite_properties(components)


def test_rotated_overlap_is_not_silently_double_counted():
    from mechanics.sections.properties import composite_properties
    with pytest.raises(ValueError,match='OVERLAP_UNSUPPORTED'):
        composite_properties((Rectangle(6,2,0,angle_deg=45),Rectangle(6,2,0,angle_deg=-45)))


def test_edge_contact_allowed():
    from mechanics.sections.properties import composite_properties
    assert composite_properties((Rectangle(2,2,0),Rectangle(2,2,0,2,0))).A_mm2 == 8


def test_nonfinite_orientation_rejected():
    from mechanics.sections.properties import composite_properties
    with pytest.raises(ValueError, match='INVALID_NUMERIC_VALUE'):
        composite_properties((Rectangle(2,2,0,angle_deg=float('nan')),))
