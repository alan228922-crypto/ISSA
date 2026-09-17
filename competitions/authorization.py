from accounts.models import User
from .models import EventMembership


def _has_membership(actor,event_id,membership_type):
    # 权限以活动成员关系为准，避免仅凭用户角色放大访问范围。
    return EventMembership.objects.filter(user=actor,event_id=event_id,membership_type=membership_type,is_active=True).exists()


def can_view_event(actor,event):
    # 开发者是全局运维角色，其他角色必须持有当前活动的有效成员关系。
    return actor.role==User.Role.DEVELOPER or _has_membership(actor,event.id,EventMembership.Type.MANAGER) or _has_membership(actor,event.id,EventMembership.Type.PARTICIPANT)


def can_manage_event(actor,event):
    return actor.role==User.Role.DEVELOPER or _has_membership(actor,event.id,EventMembership.Type.MANAGER)


def can_create_role(actor,event,role):
    if actor.role==User.Role.DEVELOPER:
        return True
    return role==User.Role.USER and can_manage_event(actor,event)


def can_view_project(actor,*,event_id,owner_user_id):
    # 项目读取允许活动经理查看，但参与者只能读取自己拥有的项目。
    if actor.role==User.Role.DEVELOPER:
        return True
    if _has_membership(actor,event_id,EventMembership.Type.MANAGER):
        return True
    return actor.id==owner_user_id and _has_membership(actor,event_id,EventMembership.Type.PARTICIPANT)


def can_modify_project(actor,*,event_id,owner_user_id):
    # 写入权限不授予经理；项目所有者仍须是当前活动的有效参与者。
    return actor.role==User.Role.DEVELOPER or (actor.id==owner_user_id and _has_membership(actor,event_id,EventMembership.Type.PARTICIPANT))


def can_analyze_project(actor,*,event_id,owner_user_id):
    return can_modify_project(actor,event_id=event_id,owner_user_id=owner_user_id)
