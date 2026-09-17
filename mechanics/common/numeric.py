"""固定單位下的數值邊界檢查；不猜測單位或自動轉換字串。"""
from math import isfinite
from numbers import Real


# 閱讀提示：這裡提供所有力學計算共用的數值檢查，避免 NaN 或無限大進入公式。


def finite_value(value: float, field: str, *, positive: bool = False,
                 nonnegative: bool = False) -> float:
    """回傳可表示的 float；尺寸/剛度需正，密度/數值容差可為零。"""
    # 把輸入確認為有限數字，並依呼叫端要求檢查必須大於零或不得小於零。
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
    # 計算完成後再次檢查結果，避免溢位或無效數字被當成正常答案。
    if not isfinite(value) or (positive and value<=0):
        raise ValueError('NUMERIC_RANGE')
    return value
