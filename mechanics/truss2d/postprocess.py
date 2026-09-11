"""由權威軸力衍生應力、拉壓分類與理論質量；不修改 Solver 結果。"""
from collections.abc import Sequence
from dataclasses import dataclass
from math import fsum
from mechanics.common.numeric import finite_value, finite_result


@dataclass(frozen=True)
class MemberStress:
    """軸向應力（MPa）與數值拉壓分類，不是材料破壞判斷。"""
    member_id: str
    axial_stress_MPa: float
    state: str


@dataclass(frozen=True)
class MemberMass:
    """單一 analysis member 長度（mm）與理論質量（g）。"""
    member_id: str
    length_mm: float
    mass_g: float


def member_stress(member_id: str, axial_force_N: float, A_mm2: float,
                  *, zero_force_atol_N: float = 1e-9) -> MemberStress:
    """σ=N/A：N/mm²=MPa，受拉正、受壓負；零分類容差以 N 為單位。"""
    force=finite_value(axial_force_N,'axial_force_N')
    area=finite_value(A_mm2,'A_mm2',positive=True)
    tolerance=finite_value(zero_force_atol_N,'zero_force_atol_N',nonnegative=True)
    # 容差只決定 ZERO 標籤，不把原力或應力截成零，不是風險分級門檻。
    state='ZERO' if abs(force)<=tolerance else ('TENSION' if force>0 else 'COMPRESSION')
    return MemberStress(member_id,finite_result(force/area),state)


def member_mass(member_id: str, density_g_per_mm3: float, A_mm2: float,
                L_mm: float) -> MemberMass:
    """mass=ρAL；(g/mm³)×mm²×mm=g，與載重或自重生成無關。"""
    density=finite_value(density_g_per_mm3,'density_g_per_mm3',nonnegative=True)
    area=finite_value(A_mm2,'A_mm2',positive=True)
    length=finite_value(L_mm,'L_mm',positive=True)
    return MemberMass(member_id,length,finite_result(density*area*length,positive=density>0))


def total_mass_g(members: Sequence[MemberMass]) -> float:
    """加總互不重複的 analysis member；physical 拆分回映由未來 Idealization 負責。"""
    if len({m.member_id for m in members}) != len(members):
        raise ValueError('DUPLICATE_MEMBER_ID')
    values=[finite_value(m.mass_g,'mass_g',nonnegative=True) for m in members]
    try:
        return finite_result(fsum(values))
    except OverflowError as exc:
        raise ValueError('NUMERIC_RANGE') from exc
