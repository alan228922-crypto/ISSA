"""固定單位下的數值邊界檢查；不猜測單位或自動轉換字串。"""
from math import isfinite
from numbers import Real


def finite_value(value: float, field: str, *, positive: bool = False,
                 nonnegative: bool = False) -> float:
    """回傳可表示的 float；尺寸/剛度需正，密度/數值容差可為零。"""
    if isinstance(value,bool) or not isinstance(value,Real):
        raise ValueError('INVALID_NUMERIC_VALUE:'+field)
    try:
        number=float(value)
    except OverflowError as exc:
        raise ValueError('NUMERIC_RANGE:'+field) from exc
    if not isfinite(number):
        raise ValueError('INVALID_NUMERIC_VALUE:'+field)
    if (positive and number<=0) or (nonnegative and number<0):
        raise ValueError('INVALID_PARAMETER:'+field)
    return number


def finite_result(value: float, *, positive: bool = False) -> float:
    """阻止溢位或正值下溢被當成成功的數值結果。"""
    if not isfinite(value) or (positive and value<=0):
        raise ValueError('NUMERIC_RANGE')
    return value
