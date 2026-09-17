"""純值輸入；幾何與連接已由上層明確決定，核心不合併節點。"""
from dataclasses import dataclass

# 閱讀提示：這個檔案只定義分析資料，不負責計算。
# Node 是節點，Member 是構件，Support 是支承，NodalLoad 是節點荷載。


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
    # 這是 Solver 真正使用的模型。
    # 上層會先把資料庫中的設計資料整理成節點、構件、支承和荷載，Solver 不會自行猜測連接方式。
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


@dataclass(frozen=True)
class NodeDisplacement:
    """節點全域 ux/uy 位移（mm）；不經顯示位數四捨五入。"""
    node_id: str
    ux_mm: float
    uy_mm: float


@dataclass(frozen=True)
class SupportReaction:
    """全域支座反力（N）；自由方向明確回傳零。"""
    node_id: str
    rx_N: float
    ry_N: float


@dataclass(frozen=True)
class MemberAxialForce:
    """桿件軸力（N）：正值受拉，負值受壓。"""
    member_id: str
    axial_force_N: float


@dataclass(frozen=True)
class SolveDiagnostics:
    """數值平衡誤差（N）與 DOF 數量；不是結構安全評等。"""
    total_dof: int
    free_dof: int
    restrained_dof: int
    free_residual_N: float
    sum_fx_residual_N: float
    sum_fy_residual_N: float


@dataclass(frozen=True)
class TrussSolveResult:
    """核心權威輸出 u/R/N；stress、mass 與 Euler 留在獨立純計算層。"""
    # 這裡保存 Solver 的基本結果：位移、支承反力和構件軸力。
    # 應力、質量和屈曲提示會在後面另外計算。
    solver_version: str
    input_schema_version: str
    node_displacements: tuple[NodeDisplacement, ...]
    support_reactions: tuple[SupportReaction, ...]
    member_axial_forces: tuple[MemberAxialForce, ...]
    diagnostics: SolveDiagnostics
