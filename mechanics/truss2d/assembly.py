"""二維桁架直接剛度法：每節點只有 ux、uy，不建立通用 FEM 抽象。"""
from dataclasses import dataclass
from math import hypot
import numpy as np
from numpy.typing import NDArray
from .model import Node, Member, TrussModel
from .errors import MechanicsError, ValidationIssue
from .validation import validate_truss_model


@dataclass(frozen=True)
class AssembledSystem:
    """K 是 (2n,2n) N/mm 矩陣，P 是 (2n,) N 向量，索引對應輸入節點序列。"""
    K_N_per_mm: NDArray[np.float64]
    P_N: NDArray[np.float64]
    dof_map: dict[str, tuple[int,int]]
    restrained_dofs: tuple[int, ...]


def element_stiffness(member: Member, node_i: Node, node_j: Node) -> NDArray[np.float64]:
    """已驗證桿件的 4×4 剛度，DOF 為 [ui_x,ui_y,uj_x,uj_y]。

    E=MPa=N/mm²、A=mm²、L=mm，故 EA/L=N/mm。
    c=dx/L、s=dy/L 是全域方向餘弦；軸向伸長為 [-c,-s,c,s]·u。
    僅有軸向能量，所以全域剛度等於 EA/L 乘此投影向量的外積。
    """
    dx,dy = node_j.x_mm-node_i.x_mm, node_j.y_mm-node_i.y_mm
    length = hypot(dx,dy)
    direction = np.array([-dx/length,-dy/length,dx/length,dy/length],dtype=np.float64)
    with np.errstate(over='raise',invalid='raise'):
        try:
            matrix = (member.E_MPa*member.A_mm2/length)*np.outer(direction,direction)
            if not np.isfinite(matrix).all():
                raise FloatingPointError
        except (FloatingPointError,OverflowError) as exc:
            raise MechanicsError((ValidationIssue('NUMERIC_RANGE',entity_type='member',entity_ids=(member.id,)),)) from exc
    return matrix


def assemble_global_stiffness(model: TrussModel) -> AssembledSystem:
    """驗證後組裝 K/P，固定零位移支承索引；重複節點外力相加。"""
    issues=validate_truss_model(model)
    if any(i.severity=='ERROR' for i in issues):
        raise MechanicsError(issues)
    # [N0.ux,N0.uy,N1.ux,N1.uy,...]；正 x 向右、正 y 向上。
    dof_map={node.id:(2*i,2*i+1) for i,node in enumerate(model.nodes)}
    nodes={node.id:node for node in model.nodes}
    size=2*len(nodes)
    matrix=np.zeros((size,size),dtype=np.float64)
    loads=np.zeros(size,dtype=np.float64)
    with np.errstate(over='raise',invalid='raise'):
        try:
            for member in model.members:
                indices=dof_map[member.node_i]+dof_map[member.node_j]
                matrix[np.ix_(indices,indices)] += element_stiffness(member,nodes[member.node_i],nodes[member.node_j])
            for load in model.nodal_loads:
                loads[list(dof_map[load.node_id])] += (load.fx_N,load.fy_N)
        except (FloatingPointError,OverflowError) as exc:
            raise MechanicsError((ValidationIssue('NUMERIC_RANGE'),)) from exc
    restrained=set()
    for support in model.supports:
        for dof,flag in zip(dof_map[support.node_id],(support.restrain_ux,support.restrain_uy)):
            if flag:
                restrained.add(dof)
    return AssembledSystem(matrix,loads,dof_map,tuple(sorted(restrained)))
