from accounts.models import User
from .models import EventMembership


def _has_membership(actor,event_id,membership_type):
    return EventMembership.objects.filter(user=actor,event_id=event_id,membership_type=membership_type,is_active=True).exists()


def can_view_event(actor,event):
    return actor.role==User.Role.DEVELOPER or _has_membership(actor,event.id,EventMembership.Type.MANAGER) or _has_membership(actor,event.id,EventMembership.Type.PARTICIPANT)


def can_manage_event(actor,event):
    return actor.role==User.Role.DEVELOPER or _has_membership(actor,event.id,EventMembership.Type.MANAGER)


def can_create_role(actor,event,role):
    if actor.role==User.Role.DEVELOPER:
        return True
    return role==User.Role.USER and can_manage_event(actor,event)


def can_view_project(actor,*,event_id,owner_user_id):
    if actor.role==User.Role.DEVELOPER:
        return True
    if _has_membership(actor,event_id,EventMembership.Type.MANAGER):
        return True
    return actor.id==owner_user_id and _has_membership(actor,event_id,EventMembership.Type.PARTICIPANT)


def can_modify_project(actor,*,event_id,owner_user_id):
    return actor.role==User.Role.DEVELOPER or (actor.id==owner_user_id and _has_membership(actor,event_id,EventMembership.Type.PARTICIPANT))


def can_analyze_project(actor,*,event_id,owner_user_id):
    return can_modify_project(actor,event_id=event_id,owner_user_id=owner_user_id)
