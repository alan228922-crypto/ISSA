"""穩定的機器代碼與定位資訊；學生文案由未來上層轉譯。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    """錯誤上下文不含 UI 文案；numeric_context 以不可變鍵值對保存。"""
    code: str
    severity: str = 'ERROR'
    entity_type: str = 'model'
    entity_ids: tuple[str, ...] = ()
    field: str | None = None
    numeric_context: tuple[tuple[str, float], ...] = ()


class MechanicsError(ValueError):
    """預期的契約或數值失敗；上層可讀取 issues，不需解析例外字串。"""
    def __init__(self, issues: tuple[ValidationIssue, ...]):
        self.issues = tuple(issues)
        super().__init__(','.join(issue.code for issue in self.issues))
