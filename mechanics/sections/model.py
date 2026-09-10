"""截面輸入與不可變的純數值結果。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Rectangle:
    """矩形 b 沿 x、h 沿 y；位置是截面座標系內的重心（mm），密度為 g/mm³。"""
    width_mm: float
    height_mm: float
    density_g_per_mm3: float
    center_x_mm: float = 0.0
    center_y_mm: float = 0.0
    angle_deg: float = 0.0  # 矩形局部 x 軸相對截面 x 軸逆時針角度。


@dataclass(frozen=True)
class SectionProperties:
    """Ix/Iy 是通過組合重心、平行截面 x/y 的面積二次矩（mm⁴）。

    strong/weak 僅比較這兩條座標軸，不宣稱為主軸，亦不決定 Euler 控制軸。
    """
    A_mm2: float
    centroid_x_mm: float
    centroid_y_mm: float
    Ix_mm4: float
    Iy_mm4: float
    mass_per_length_g_per_mm: float
    strong_axis: str
    weak_axis: str
