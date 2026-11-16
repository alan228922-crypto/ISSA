from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from competitions.authorization import can_manage_event
from competitions.models import CompetitionEvent, EventMembership
from competitions.provisioning import ProvisioningError, preview_team_import


@pytest.fixture
def event(db):
    now = timezone.now()
    return CompetitionEvent.objects.create(
        name='资格赛事', event_code='M8', competition_date=now.date(),
        starts_at=now, ends_at=now + timedelta(days=1),
    )


@pytest.mark.parametrize('role,active,assigned,participant,expected', [
    ('DEVELOPER', True, False, None, True),
    ('DEVELOPER', False, False, None, False),
    ('MANAGER', True, True, None, True),
    ('MANAGER', False, True, None, False),
    ('MANAGER', True, False, None, False),
    ('USER', True, True, None, False),
    ('MANAGER', True, True, True, False),
    ('MANAGER', True, True, False, True),
    ('DEVELOPER', True, True, True, False),
])
def test_manager_authority_requires_active_global_role_and_exact_membership(
    event, role, active, assigned, participant, expected,
):
    actor = User.objects.create_user('actor', role=role, is_active=active)
    if assigned:
        EventMembership.objects.create(user=actor, event=event, membership_type='MANAGER')
    if participant is not None:
        EventMembership.objects.create(
            user=actor, event=event, membership_type='PARTICIPANT', is_active=participant,
        )
    assert can_manage_event(actor, event) is expected
    if not expected:
        with pytest.raises(ProvisioningError):
            preview_team_import(actor, event, 'teams.csv', 'team_number,captain_student_id\n1,synthetic\n')


@pytest.mark.parametrize('change', ['disabled', 'role', 'membership', 'event'])
def test_cached_actor_and_event_are_not_authority(event, change):
    actor = User.objects.create_user('manager', role='MANAGER')
    membership = EventMembership.objects.create(user=actor, event=event, membership_type='MANAGER')
    if change == 'disabled':
        User.objects.filter(pk=actor.pk).update(is_active=False)
    elif change == 'role':
        User.objects.filter(pk=actor.pk).update(role='USER')
    elif change == 'membership':
        EventMembership.objects.filter(pk=membership.pk).update(is_active=False)
    else:
        CompetitionEvent.objects.filter(pk=event.pk).update(status='ACTIVE')
    with pytest.raises(ProvisioningError):
        preview_team_import(actor, event, 'teams.csv', 'team_number,captain_student_id\n1,synthetic\n')


def test_inactive_manager_membership_and_other_event_do_not_grant_authority(event):
    actor = User.objects.create_user('manager', role='MANAGER')
    membership = EventMembership.objects.create(user=actor, event=event, membership_type='MANAGER', is_active=False)
    assert can_manage_event(actor, event) is False
    membership.is_active = True
    membership.save()
    other = CompetitionEvent.objects.create(
        name='另一场', event_code='OTHER', competition_date=event.competition_date,
        starts_at=event.starts_at, ends_at=event.ends_at,
    )
    assert can_manage_event(actor, other) is False
