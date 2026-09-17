from accounts.models import User
from .models import EventMembership


def _has_membership(actor,event_id,membership_type):
    # 權限要同時看使用者角色和活動成員身分，不能只靠全域角色決定。
    return EventMembership.objects.filter(user=actor,event_id=event_id,membership_type=membership_type,is_active=True).exists()


def can_view_event(actor,event):
    # Developer 可以管理所有活動；其他使用者必須是目前活動的有效成員。
    return actor.role==User.Role.DEVELOPER or _has_membership(actor,event.id,EventMembership.Type.MANAGER) or _has_membership(actor,event.id,EventMembership.Type.PARTICIPANT)


def can_manage_event(actor,event):
    return actor.role==User.Role.DEVELOPER or _has_membership(actor,event.id,EventMembership.Type.MANAGER)


def can_create_role(actor,event,role):
    if actor.role==User.Role.DEVELOPER:
        return True
    return role==User.Role.USER and can_manage_event(actor,event)


def can_view_project(actor,*,event_id,owner_user_id):
    # 活動經理可以查看活動內的專案；一般參與者只能查看自己擁有的專案。
    if actor.role==User.Role.DEVELOPER:
        return True
    if _has_membership(actor,event_id,EventMembership.Type.MANAGER):
        return True
    return actor.id==owner_user_id and _has_membership(actor,event_id,EventMembership.Type.PARTICIPANT)


def can_modify_project(actor,*,event_id,owner_user_id):
    # 修改專案需要是專案擁有者，而且必須仍是目前活動的有效參與者。
    return actor.role==User.Role.DEVELOPER or (actor.id==owner_user_id and _has_membership(actor,event_id,EventMembership.Type.PARTICIPANT))


def can_analyze_project(actor,*,event_id,owner_user_id):
    return can_modify_project(actor,event_id=event_id,owner_user_id=owner_user_id)
