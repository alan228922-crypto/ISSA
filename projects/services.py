from competitions.authorization import can_modify_project as _can_modify_project
from competitions.authorization import can_view_project as _can_view_project


def can_view_project(actor, project):
    """复用赛事与项目归属权限策略，不创建第二套权限系统。"""
    return _can_view_project(actor, event_id=project.event_id, owner_user_id=project.owner_user_id)


def can_modify_project(actor, project):
    """复用既有项目写入策略；经理只能查看学生项目。"""
    return _can_modify_project(actor, event_id=project.event_id, owner_user_id=project.owner_user_id)
