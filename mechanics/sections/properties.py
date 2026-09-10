"""面積、重心與重心軸慣性矩；不包含材料強度或屈曲產品政策。"""
from math import isclose
from .model import Rectangle, SectionProperties
from .validation import validate_rectangle


def _axes(Ix_mm4: float, Iy_mm4: float) -> tuple[str, str]:
    # 相對容差只避免浮點誤差把相同座標軸剛度分成強弱；不是屈曲門檻。
    if isclose(Ix_mm4, Iy_mm4, rel_tol=1e-12, abs_tol=0.0):
        return 'EQUAL', 'EQUAL'
    return ('X', 'Y') if Ix_mm4 > Iy_mm4 else ('Y', 'X')


def rectangle_properties(rectangle: Rectangle) -> SectionProperties:
    """計算矩形重心性質；b/h 為 mm，A 為 mm²、Ix/Iy 為 mm⁴。"""
    validate_rectangle(rectangle)
    b, h = rectangle.width_mm, rectangle.height_mm
    # Ix 積分 y² dA，故高度 h 是三次方；Iy 則積分 x² dA。
    area = b * h
    ix, iy = b * h**3 / 12, h * b**3 / 12
    return SectionProperties(area, rectangle.center_x_mm, rectangle.center_y_mm,
                             ix, iy, area * rectangle.density_g_per_mm3, *_axes(ix, iy))
