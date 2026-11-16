"""安全、可执行的说明；不透传异常原文。"""
MESSAGES = {
    'PERMISSION_DENIED': '没有这场赛事的管理权限。请联系赛事负责人确认有效的管理员资格。',
    'ROLE_NOT_ALLOWED': '这里只能建立参赛账号。请返回参赛队伍管理。',
    'EVENT_PURGED': '赛事资料已清理，不能继续管理参赛资格。请返回赛事列表。',
    'EVENT_STATUS_NOT_ALLOWED': '赛事当前只允许查看历史，不能变更参赛资格。请返回队伍列表。',
    'EVENT_ACCESS_EXPIRED': '赛事操作期限已结束，不能继续变更。请联系赛事负责人。',
    'PROVISIONING_STATUS_POLICY_GAP': '进行中的赛事暂不支持批量开户。请使用单笔新增队伍。',
    'INVALID_PROVISIONING_ROW': '输入格式不正确。请检查队伍编号、初始凭证及文件列后重新预览。',
    'DUPLICATE_INPUT': '同一队伍重复出现。请移除重复列后重新预览。',
    'ACCOUNT_ALREADY_EXISTS': '账号已存在。请核实同一队伍后使用“加入既有账号”。',
    'INVALID_PREVIEW': '确认资料无效或已变更。请重新预览，不要重复使用旧页面。',
    'EXPIRED_PREVIEW': '预览已过期。请重新输入并预览后再确认。',
    'PREVIEW_STATE_CHANGED': '账号或参赛资格已经变化。请刷新队伍列表，重新核实并预览。',
    'PARTICIPANT_MANAGEMENT_BUSY': '赛事暂时繁忙，尚未完成操作。请稍后重新确认。',
    'USER_ROLE_CONFLICT': '账号身分不符合参赛要求。请联系赛事负责人，不要覆盖既有账号。',
    'ACCOUNT_INACTIVE': '账号目前停用。此处不能恢复账号，请联系赛事负责人。',
    'MEMBERSHIP_NOT_FOUND': '找不到此赛事的参赛资格。请返回队伍列表重新选择。',
}


def participant_error_message(code):
    return MESSAGES.get(code, '暂时无法完成操作。请返回队伍列表重新预览；若仍失败，请联系赛事负责人。')
