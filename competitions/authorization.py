from accounts.models import User
from .models import CompetitionEvent, EventMembership


def _active_actor(actor):
    return bool(getattr(actor, 'is_authenticated', False) and getattr(actor, 'is_active', False))


def _event_status(event_id):
    # 读取当前持久化状态，不允许缓存的 Event 对象绕过关闭状态。
    return CompetitionEvent.objects.filter(pk=event_id).values_list('status', flat=True).first()


def _has_membership(actor,event_id,membership_type):
    # 權限要同時看使用者角色和活動成員身分，不能只靠全域角色決定。
    return EventMembership.objects.filter(user=actor,event_id=event_id,membership_type=membership_type,is_active=True).exists()


def can_view_event(actor,event):
    if not _active_actor(actor) or _event_status(event.pk) in {None, CompetitionEvent.Status.PURGED}:
        return False
    # Developer 可以管理所有活動；其他使用者必須是目前活動的有效成員。
    return actor.role==User.Role.DEVELOPER or _has_membership(actor,event.id,EventMembership.Type.MANAGER) or _has_membership(actor,event.id,EventMembership.Type.PARTICIPANT)


def can_manage_event(actor,event):
    if not _active_actor(actor):
        return False
    current = User.objects.filter(pk=actor.pk, is_active=True).first()
    if current is None or _event_status(event.pk) in {None, CompetitionEvent.Status.PURGED}:
        return False
    types = set(EventMembership.objects.filter(
        user=current, event_id=event.pk, is_active=True,
    ).values_list('membership_type', flat=True))
    if {EventMembership.Type.PARTICIPANT, EventMembership.Type.MANAGER} <= types:
        return False
    return current.role == User.Role.DEVELOPER or (
        current.role == User.Role.MANAGER and EventMembership.Type.MANAGER in types
    )


def participant_management_error(*, actor, event, operation, now):
    if not can_manage_event(actor, event):
        return 'PERMISSION_DENIED'
    current = CompetitionEvent.objects.get(pk=event.pk)
    if operation not in {'DRAFT_CSV_CREATE', 'CREATE_USER', 'JOIN_EXISTING', 'REACTIVATE', 'DEACTIVATE'}:
        return 'INVALID_PROVISIONING_ROW'
    if current.status == CompetitionEvent.Status.ACTIVE:
        if now >= current.purge_at:
            return 'EVENT_ACCESS_EXPIRED'
        if operation == 'DRAFT_CSV_CREATE':
            return 'PROVISIONING_STATUS_POLICY_GAP'
        return None
    if current.status != CompetitionEvent.Status.DRAFT:
        return 'EVENT_STATUS_NOT_ALLOWED'
    return None


def can_create_role(actor,event,role):
    return can_manage_event(actor,event) and (
        User.objects.filter(pk=actor.pk, role=User.Role.DEVELOPER).exists() or role==User.Role.USER
    )


def can_view_project(actor,*,event_id,owner_user_id):
    if not _active_actor(actor) or _event_status(event_id) in {None, CompetitionEvent.Status.PURGED}:
        return False
    # 活動經理可以查看活動內的專案；一般參與者只能查看自己擁有的專案。
    if actor.role==User.Role.DEVELOPER:
        return True
    if _has_membership(actor,event_id,EventMembership.Type.MANAGER):
        return True
    return actor.id==owner_user_id and _has_membership(actor,event_id,EventMembership.Type.PARTICIPANT)


def can_modify_project(actor,*,event_id,owner_user_id):
    if not _active_actor(actor) or _event_status(event_id) not in {CompetitionEvent.Status.DRAFT, CompetitionEvent.Status.ACTIVE}:
        return False
    # 修改專案需要是專案擁有者，而且必須仍是目前活動的有效參與者。
    return actor.role==User.Role.DEVELOPER or (actor.id==owner_user_id and _has_membership(actor,event_id,EventMembership.Type.PARTICIPANT))


def can_analyze_project(actor,*,event_id,owner_user_id):
    return can_modify_project(actor,event_id=event_id,owner_user_id=owner_user_id)
