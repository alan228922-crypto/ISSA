"""K u = P 的純 Python/NumPy 桁架求解；不提供機構的假解或替代 solver。"""
from math import hypot, fsum
import numpy as np
from .assembly import assemble_global_stiffness
from .errors import MechanicsError, ValidationIssue
from .model import (TrussModel, TrussSolveResult, NodeDisplacement, SupportReaction,
                    MemberAxialForce, SolveDiagnostics)


# 閱讀提示：Solver 的主要任務是根據荷載和支承條件，算出每個節點移動多少。

# Solver 接收的是已經理想化和驗證過的 TrussModel，輸出的是位移、反力、軸力和數值診斷。
# 它不讀取 Django ORM，也不負責把結果翻譯成畫面文字。


class Truss2DSolver:
    """只解 ux/uy 與軸力的小位移線彈性桁架；所有支承位移為零。"""
    version = 'truss2d-0.1.0'

    def solve(self, model: TrussModel) -> TrussSolveResult:
        """先驗證、再組裝與縮減；singular 或非有限計算輸出均回機器代碼。"""
        # 對外入口統一攔截數值溢位等計算錯誤，讓上層收到穩定的 MechanicsError。
        with np.errstate(over='raise',invalid='raise',divide='raise'):
            try:
                return self._solve(model)
            except (FloatingPointError,OverflowError) as exc:
                raise MechanicsError((ValidationIssue('NUMERIC_RANGE'),)) from exc

    def _solve(self, model: TrussModel) -> TrussSolveResult:
        # 流程是：檢查模型 → 整理剛度和荷載 → 套用支承 → 求位移 → 求反力和軸力。
        # 如果模型沒有唯一答案，程式會回報錯誤，不會硬湊出一個答案。
        # assemble_global_stiffness() 會把節點荷載和支承限制整理成可解的矩陣資料。
        system=assemble_global_stiffness(model)
        matrix,loads=system.K_N_per_mm,system.P_N
        restrained=set(system.restrained_dofs)
        free=[i for i in range(len(loads)) if i not in restrained]
        displacements=np.zeros_like(loads)
        if free:
            # 被支承固定的方向位移是零，所以只需要計算其他可以移動的方向。
            # 計算完成後，位移仍以 mm 表示。
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
        # residual 在自由方向應接近零；在受約束方向則代表支座需要提供的反力。
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
