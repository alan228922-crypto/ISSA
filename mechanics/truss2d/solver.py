"""K u = P 的純 Python/NumPy 桁架求解；不提供機構的假解或替代 solver。"""
from math import hypot, fsum
import numpy as np
from .assembly import assemble_global_stiffness
from .errors import MechanicsError, ValidationIssue
from .model import (TrussModel, TrussSolveResult, NodeDisplacement, SupportReaction,
                    MemberAxialForce, SolveDiagnostics)


# 閱讀提示：Solver 的主要任務是由荷載和支承條件求出節點位移。


class Truss2DSolver:
    """只解 ux/uy 與軸力的小位移線彈性桁架；所有支承位移為零。"""
    version = 'truss2d-0.1.0'

    def solve(self, model: TrussModel) -> TrussSolveResult:
        """先驗證、再組裝與縮減；singular 或非有限計算輸出均回機器代碼。"""
        with np.errstate(over='raise',invalid='raise',divide='raise'):
            try:
                return self._solve(model)
            except (FloatingPointError,OverflowError) as exc:
                raise MechanicsError((ValidationIssue('NUMERIC_RANGE'),)) from exc

    def _solve(self, model: TrussModel) -> TrussSolveResult:
        # 流程順序是「驗證 → 組裝 K/P → 套用支承 → 求自由 DOF 位移 → 回算反力與軸力」。
        # 這裡使用小位移、線彈性直接剛度法；若結構沒有唯一解，會回報機器碼，
        # 不以人工彈簧或偽逆製造一個看似合理的答案。
        system=assemble_global_stiffness(model)
        matrix,loads=system.K_N_per_mm,system.P_N
        restrained=set(system.restrained_dofs)
        free=[i for i in range(len(loads)) if i not in restrained]
        displacements=np.zeros_like(loads)
        if free:
            # 受約束 DOF 的位移已知為零，因此只解未受約束的縮減方程。
            # 先做對角尺度化是為了減少數值量級差，還原後的位移仍以 mm 表示。
            reduced=matrix[np.ix_(free,free)]
            diagonal=np.diag(reduced)
            if np.any(diagonal<=0):
                raise MechanicsError((ValidationIssue('SINGULAR_GLOBAL_STIFFNESS'),))
            # 對角尺度化只改善單位/剛度量級差；不增加人工彈簧或使用偽逆。
            # matrix_rank 使用 float64 尺寸×machine epsilon 判斷數值 rank，
            # 不能据此宣稱某一種結構機構；病態近奇異亦可能被拒絕。
            scale=np.sqrt(diagonal)
            normalized=reduced/scale[:,None]/scale[None,:]
            try:
                if np.linalg.matrix_rank(normalized)<len(free):
                    raise np.linalg.LinAlgError('rank deficient')
                displacements[free]=np.linalg.solve(normalized,loads[free]/scale)/scale
            except np.linalg.LinAlgError as exc:
                raise MechanicsError((ValidationIssue('SINGULAR_GLOBAL_STIFFNESS'),)) from exc
        if not np.isfinite(displacements).all():
            raise FloatingPointError('nonfinite displacement')
        # 原完整方程的內力為 Ku；扣掉外載 P，受約束方向剩餘量即支座反力。
        # 必須使用完整 P，包含直接作用在支承節點上的力。
        residual=matrix@displacements-loads
        reactions=np.zeros_like(loads)
        reactions[list(restrained)]=residual[list(restrained)]
        nodes={n.id:n for n in model.nodes}
        forces=[]
        for member in model.members:
            a,b=nodes[member.node_i],nodes[member.node_j]
            dx,dy=b.x_mm-a.x_mm,b.y_mm-a.y_mm
            length=hypot(dx,dy)
            ui=displacements[list(system.dof_map[member.node_i])]
            uj=displacements[list(system.dof_map[member.node_j])]
            # N=EA/L * [(uj-ui)·(c,s)]：伸長為正即受拉；縮短為負即受壓。
            # 端點順序反轉同時反轉方向與位移差，故 N 的拉壓定義不變。
            force=member.E_MPa*member.A_mm2/length*((uj[0]-ui[0])*dx/length+(uj[1]-ui[1])*dy/length)
            if not np.isfinite(force):
                raise FloatingPointError('nonfinite axial force')
            forces.append(MemberAxialForce(member.id,float(force)))
        node_u=tuple(NodeDisplacement(n.id,*map(float,displacements[list(system.dof_map[n.id])])) for n in model.nodes)
        support_r=tuple(SupportReaction(n.id,*map(float,reactions[list(system.dof_map[n.id])]))
                        for n in model.nodes if any(i in restrained for i in system.dof_map[n.id]))
        diagnostics=SolveDiagnostics(len(loads),len(free),len(restrained),
            float(np.max(np.abs(residual[free]))) if free else 0.0,
            fsum(float(v) for v in (reactions+loads)[0::2]),
            fsum(float(v) for v in (reactions+loads)[1::2]))
        return TrussSolveResult(self.version,model.schema_version,node_u,support_r,tuple(forces),diagnostics)
