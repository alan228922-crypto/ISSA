"""学生自助建立边界；不承担帐号 provisioning 或旧 Draft 转换。"""
from dataclasses import dataclass
from datetime import datetime
import time

from django.db import OperationalError, transaction, connection
from django.db.models import F
from django.utils import timezone

from accounts.models import User
from competitions.models import CompetitionEvent, EventMembership
from .models import Project


class ProjectCreationError(ValueError):
    def __init__(self, code: str, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class ProjectCreationResult:
    project: Project
    created: bool


def project_creation_error(*, actor: User, event: CompetitionEvent, now: datetime) -> str | None:
    if not (getattr(actor, 'is_authenticated', False) and actor.is_active and actor.role == User.Role.USER):
        return 'PROJECT_CREATE_DENIED'
    if not EventMembership.objects.filter(user_id=actor.pk, event_id=event.pk,
            membership_type=EventMembership.Type.PARTICIPANT, is_active=True).exists():
        return 'PROJECT_CREATE_DENIED'
    if event.status == CompetitionEvent.Status.PURGED:
        return 'EVENT_PURGED'
    if event.status != CompetitionEvent.Status.ACTIVE:
        return 'EVENT_NOT_ACTIVE'
    if event.purge_at is None or now >= event.purge_at:
        return 'EVENT_ACCESS_EXPIRED'
    return None


def create_or_open_project(*, actor: User, event_id: int, name: str) -> ProjectCreationResult:
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 200:
        raise ProjectCreationError('INVALID_PROJECT_NAME', 400)
    if not getattr(actor, 'is_authenticated', False):
        raise ProjectCreationError('PROJECT_CREATE_DENIED', 403)
    # 快速拒绝无权限请求；锁等待后仍会在事务内再次读取全部资格。
    event = CompetitionEvent.objects.filter(pk=event_id).first()
    if event is None:
        raise ProjectCreationError('EVENT_NOT_FOUND', 404)
    current_actor = User.objects.filter(pk=actor.pk).first()
    if current_actor is None:
        raise ProjectCreationError('PROJECT_CREATE_DENIED', 403)
    error = project_creation_error(actor=current_actor, event=event, now=timezone.now())
    if error:
        raise ProjectCreationError(error, 403)
    for attempt in range(5):
        try:
            return _create_or_open_once(actor_id=actor.pk, event_id=event_id, name=name.strip())
        except OperationalError as exc:
            if connection.vendor != 'sqlite' or not any(word in str(exc).lower() for word in ('locked', 'busy')):
                raise
            if attempt == 4:
                raise ProjectCreationError('PROJECT_CREATE_BUSY', 503) from exc
            time.sleep(0.05 * (attempt + 1))


def _create_or_open_once(*, actor_id: int, event_id: int, name: str) -> ProjectCreationResult:
    with transaction.atomic():
        # SQLite 忽略 select_for_update；先取得写锁再读取 cardinality。
        # 值不变的 UPDATE 不调用 save()、不更新 Event 时间或状态。
        if not CompetitionEvent.objects.filter(pk=event_id).update(status=F('status')):
            raise ProjectCreationError('EVENT_NOT_FOUND', 404)
        event = CompetitionEvent.objects.get(pk=event_id)
        current_actor = User.objects.select_for_update().filter(pk=actor_id).first()
        if current_actor is None:
            raise ProjectCreationError('PROJECT_CREATE_DENIED', 403)
        list(EventMembership.objects.select_for_update().filter(user_id=actor_id, event_id=event_id).order_by('pk'))
        error = project_creation_error(actor=current_actor, event=event, now=timezone.now())
        if error:
            raise ProjectCreationError(error, 403)
        existing = list(Project.objects.select_for_update().filter(event_id=event_id, owner_user_id=actor_id).order_by('pk')[:2])
        if len(existing) > 1:
            raise ProjectCreationError('PROJECT_MULTIPLE_EXISTING', 409)
        if existing:
            project = existing[0]
            if (project.analysis_type != 'TRUSS_2D'
                or project.draft_schema_version not in {'physical-draft-v1', 'physical-draft-v2'}
                or project.draft_migration_audits.filter(status='BLOCKED').exists()):
                raise ProjectCreationError('PROJECT_EXISTING_UNAVAILABLE', 409)
            return ProjectCreationResult(project, False)
        project = Project.objects.create(event=event, owner_user=current_actor, name=name.strip(),
            analysis_type='TRUSS_2D', draft_schema_version='physical-draft-v2', draft_version=0)
        return ProjectCreationResult(project, True)
