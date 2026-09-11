"""在截面公式之前攔截非數值與不合法尺寸。"""
from math import isfinite
from numbers import Real
from .model import Rectangle


def validate_rectangle(rectangle: Rectangle) -> None:
    """尺寸須正、密度可為零；bool 不視為物理數值，不做字串或單位轉換。"""
    for field in ('width_mm', 'height_mm', 'density_g_per_mm3', 'center_x_mm', 'center_y_mm', 'angle_deg'):
        value = getattr(rectangle, field)
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError('INVALID_NUMERIC_VALUE:' + field)
        try:
            finite = isfinite(value)
        except OverflowError as exc:
            raise ValueError('NUMERIC_RANGE:' + field) from exc
        if not finite:
            raise ValueError('INVALID_NUMERIC_VALUE:' + field)
    if rectangle.width_mm <= 0 or rectangle.height_mm <= 0:
        raise ValueError('INVALID_SECTION_DIMENSION')
    if rectangle.density_g_per_mm3 < 0:
        raise ValueError('INVALID_DENSITY')
