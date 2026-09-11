"""面積、重心與重心軸慣性矩；不包含材料強度或屈曲產品政策。"""
from math import isclose, cos, sin, radians, fsum, ulp, isfinite
from collections.abc import Sequence
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
    try:
        area = b * h
        ix, iy = b * h**3 / 12, h * b**3 / 12
        c, s = cos(radians(rectangle.angle_deg)), sin(radians(rectangle.angle_deg))
        ix, iy = ix*c*c + iy*s*s, ix*s*s + iy*c*c
        mass = area * rectangle.density_g_per_mm3
    except OverflowError as exc:
        raise ValueError('NUMERIC_RANGE') from exc
    # 有限輸入不保證乘方結果仍可表示；不可把 NaN/Inf 當成成功的截面結果。
    if not all(isfinite(v) for v in (area,ix,iy,mass)) or min(area,ix,iy) <= 0:
        raise ValueError('NUMERIC_RANGE')
    return SectionProperties(area, rectangle.center_x_mm, rectangle.center_y_mm,
                             ix, iy, mass, *_axes(ix, iy))


def _overlaps(a: Rectangle, b: Rectangle) -> bool:
    # 分離軸測試僅判斷兩矩形是否有正面積交集，不做 union/subtraction。
    # 使用相對中心，避免不必要的絕對座標消去。四個局部軸即足以判定矩形分離。
    def axes(r: Rectangle) -> tuple[tuple[float, float], tuple[float, float]]:
        c, s = cos(radians(r.angle_deg)), sin(radians(r.angle_deg))
        return ((c, s), (-s, c))
    aa, bb = axes(a), axes(b)
    dx, dy = b.center_x_mm-a.center_x_mm, b.center_y_mm-a.center_y_mm
    for x,y in aa+bb:
        ra = abs(x*aa[0][0]+y*aa[0][1])*a.width_mm/2 + abs(x*aa[1][0]+y*aa[1][1])*a.height_mm/2
        rb = abs(x*bb[0][0]+y*bb[0][1])*b.width_mm/2 + abs(x*bb[1][0]+y*bb[1][1])*b.height_mm/2
        distance = abs(dx*x+dy*y)
        # 投影含數次乘加；8 ULP 僅吸收浮點捨入，並非允許幾何重疊的產品政策。
        # 可分辨的正面積重疊仍拒絕；benchmark 數值容差不因此改變。
        if distance >= ra+rb - 8*ulp(max(distance, ra+rb)):
            return False
    return True


def composite_properties(components: Sequence[Rectangle]) -> SectionProperties:
    """非重疊矩形的面積重心與平行軸定理；重疊回報不支援，保留 O-005。"""
    if not components:
        raise ValueError('EMPTY_SECTION')
    parts = [rectangle_properties(r) for r in components]
    for i,a in enumerate(components):
        if any(_overlaps(a,b) for b in components[i+1:]):
            raise ValueError('OVERLAP_UNSUPPORTED')
    try:
        area = fsum(p.A_mm2 for p in parts)
        # 重心由面積加權，不由密度加權。以首中心為參考減少大座標消去誤差。
        x0, y0 = parts[0].centroid_x_mm, parts[0].centroid_y_mm
        cx = x0 + fsum(p.A_mm2*(p.centroid_x_mm-x0) for p in parts)/area
        cy = y0 + fsum(p.A_mm2*(p.centroid_y_mm-y0) for p in parts)/area
        # Ix=Σ(Ix_local+A*dy²)，Iy=Σ(Iy_local+A*dx²)，單位 mm⁴。
        ix = fsum(p.Ix_mm4+p.A_mm2*(p.centroid_y_mm-cy)**2 for p in parts)
        iy = fsum(p.Iy_mm4+p.A_mm2*(p.centroid_x_mm-cx)**2 for p in parts)
        mass = fsum(p.mass_per_length_g_per_mm for p in parts)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError('NUMERIC_RANGE') from exc
    # 各子截面可表示，並不保證平行軸項或總和可表示。
    if not all(isfinite(v) for v in (area,cx,cy,ix,iy,mass)) or min(area,ix,iy)<=0:
        raise ValueError('NUMERIC_RANGE')
    return SectionProperties(area,cx,cy,ix,iy,mass,*_axes(ix,iy))
