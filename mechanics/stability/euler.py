"""Euler 解析公式，不推斷支承有效長度，不宣稱真實破壞荷載。"""
from math import pi
from mechanics.common.numeric import finite_value, finite_result


def euler_critical_load(*, E_MPa: float, I_mm4: float, L_mm: float, K: float) -> float:
    """以明確 E/I/L/K 計算 Pcr（N），K 沒有 default；不自動挑選 weak axis。

    Pcr=π²EI/(KL)²；E=N/mm²、I=mm⁴、L=mm、K 無因次，結果為 N。
    僅是公式驗證；O-001 的有效長度、控制 I 與教學風險政策仍需審查。
    """
    # 結果是理想細長壓桿在給定有效長度係數下的理論臨界荷載；
    # 函數刻意要求呼叫端明確提供 K 與 I，避免在沒有支承或方向資訊時自行猜測。
    e=finite_value(E_MPa,'E_MPa',positive=True)
    inertia=finite_value(I_mm4,'I_mm4',positive=True)
    length=finite_value(L_mm,'L_mm',positive=True)
    factor=finite_value(K,'K',positive=True)
    try:
        return finite_result(pi*pi*e*inertia/(factor*length)**2,positive=True)
    except (OverflowError,ZeroDivisionError) as exc:
        raise ValueError('NUMERIC_RANGE') from exc
