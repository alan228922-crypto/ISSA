"""純值輸入；幾何與連接已由上層明確決定，核心不合併節點。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    """分析節點座標（mm）；+x 向右、+y 向上，僅有 ux/uy。"""
    id: str
    x_mm: float
    y_mm: float


@dataclass(frozen=True)
class Member:
    """分析桿件；E 為 MPa、A 為 mm²，不是持久化 PhysicalMember。"""
    id: str
    node_i: str
    node_j: str
    E_MPa: float
    A_mm2: float


@dataclass(frozen=True)
class Support:
    """只表達全域平移零位移約束；不決定 Roller UI 或角度政策。"""
    node_id: str
    restrain_ux: bool
    restrain_uy: bool


@dataclass(frozen=True)
class NodalLoad:
    """節點外力（N），fx/fy 正方向與全域座標一致。"""
    node_id: str
    fx_N: float
    fy_N: float


@dataclass(frozen=True)
class TrussModel:
    """分析輸入快照；序列複製成 tuple，避免呼叫者改動 list 改變分析語意。"""
    schema_version: str
    nodes: tuple[Node, ...]
    members: tuple[Member, ...]
    supports: tuple[Support, ...]
    nodal_loads: tuple[NodalLoad, ...]

    def __post_init__(self) -> None:
        for field, kind in (('nodes',Node),('members',Member),('supports',Support),('nodal_loads',NodalLoad)):
            values = tuple(getattr(self,field))
            if any(type(value) is not kind for value in values):
                raise TypeError(f'{field} requires pure {kind.__name__} values')
            object.__setattr__(self,field,values)
