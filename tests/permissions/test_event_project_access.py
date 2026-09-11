from datetime import date,datetime,timedelta
import pytest
from django.utils import timezone


@pytest.fixture
def event(db):
    from competitions.models import CompetitionEvent
    return CompetitionEvent.objects.create(name='赛事 A',event_code='A',competition_date=date(2026,11,7),starts_at=timezone.make_aware(datetime(2026,11,7)),ends_at=timezone.make_aware(datetime(2026,11,8)))


@pytest.mark.django_db
def test_developer_has_global_event_and_project_context_access(event):
    from accounts.models import User
    from competitions.authorization import can_view_event,can_view_project
    actor=User.objects.create_user('dev',role=User.Role.DEVELOPER)
    assert can_view_event(actor,event) is True
    assert can_view_project(actor,event_id=event.id,owner_user_id=999) is True


@pytest.mark.django_db
def test_manager_is_limited_to_assigned_event_and_read_only_student_context(event):
    from accounts.models import User
    from competitions.models import CompetitionEvent,EventMembership
    from competitions.authorization import can_manage_event,can_view_project,can_modify_project,can_analyze_project
    other=CompetitionEvent.objects.create(name='赛事 B',event_code='B',competition_date=date(2026,12,7),starts_at=timezone.make_aware(datetime(2026,12,7)),ends_at=timezone.make_aware(datetime(2026,12,8)))
    manager=User.objects.create_user('manager',role=User.Role.MANAGER)
    EventMembership.objects.create(user=manager,event=event,membership_type=EventMembership.Type.MANAGER)
    assert can_manage_event(manager,event) is True
    assert can_manage_event(manager,other) is False
    assert can_view_project(manager,event_id=event.id,owner_user_id=999) is True
    assert can_modify_project(manager,event_id=event.id,owner_user_id=999) is False
    assert can_analyze_project(manager,event_id=event.id,owner_user_id=999) is False


@pytest.mark.django_db
def test_participant_can_only_access_own_context_in_joined_event(event):
    from accounts.models import User
    from competitions.models import EventMembership
    from competitions.authorization import can_view_project
    user=User.objects.create_user('team',role=User.Role.USER)
    EventMembership.objects.create(user=user,event=event,membership_type=EventMembership.Type.PARTICIPANT)
    assert can_view_project(user,event_id=event.id,owner_user_id=user.id) is True
    assert can_view_project(user,event_id=event.id,owner_user_id=999) is False
