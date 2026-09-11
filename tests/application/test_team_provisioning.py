from datetime import date,datetime
from django.utils import timezone
import pytest


@pytest.fixture
def event(db):
    from competitions.models import CompetitionEvent
    return CompetitionEvent.objects.create(name='赛事',event_code='E1',competition_date=date(2026,11,7),starts_at=timezone.make_aware(datetime(2026,11,7)),ends_at=timezone.make_aware(datetime(2026,11,8)))


@pytest.fixture
def manager(event):
    from accounts.models import User
    from competitions.models import EventMembership
    actor=User.objects.create_user('manager',role=User.Role.MANAGER)
    EventMembership.objects.create(user=actor,event=event,membership_type=EventMembership.Type.MANAGER)
    return actor


def test_preview_generates_username_without_persisting_credentials(manager,event):
    from competitions.provisioning import preview_team_import
    preview=preview_team_import(manager,event,'teams.csv','team_number,captain_student_id\n1,S123\n')
    assert preview['rows'][0]['username']=='2026110701'
    assert preview['errors']==[]
    assert 'S123' not in str(preview['audit'])


def test_confirm_creates_hashed_user_membership_and_sanitized_audit(manager,event):
    from accounts.models import User
    from competitions.models import BulkImportBatch,EventMembership
    from competitions.provisioning import confirm_team_import,preview_team_import
    preview=preview_team_import(manager,event,'../../teams.csv','team_number,captain_student_id\n1,S123\n')
    result=confirm_team_import(manager,event,preview['token'])
    user=User.objects.get(username='2026110701')
    assert result['created_count']==1 and user.check_password('S123') and user.must_change_password
    assert EventMembership.objects.filter(user=user,event=event,membership_type='PARTICIPANT').exists()
    audit=BulkImportBatch.objects.get()
    assert audit.source_filename=='teams.csv'
    assert 'S123' not in str(audit.__dict__)


def test_invalid_row_rolls_back_everything(manager,event):
    from accounts.models import User
    from competitions.models import BulkImportBatch,EventMembership
    from competitions.provisioning import ProvisioningError,confirm_team_import,preview_team_import
    preview=preview_team_import(manager,event,'teams.csv','team_number,captain_student_id\n1,S123\nBAD,\n')
    with pytest.raises(ProvisioningError):
        confirm_team_import(manager,event,preview['token'])
    assert User.objects.filter(username__startswith='20261107').count()==0
    assert EventMembership.objects.filter(event=event,membership_type='PARTICIPANT').count()==0
    assert BulkImportBatch.objects.count()==1


def test_provisioning_revalidates_permissions_and_status(manager,event):
    from competitions.models import CompetitionEvent
    from competitions.provisioning import ProvisioningError,confirm_team_import,preview_team_import
    preview=preview_team_import(manager,event,'teams.csv','team_number,captain_student_id\n1,S123\n')
    event.status=CompetitionEvent.Status.PURGED
    event.save()
    with pytest.raises(ProvisioningError,match='EVENT_PURGED'):
        confirm_team_import(manager,event,preview['token'])


def test_manager_cannot_create_privileged_accounts_through_provisioning(manager,event):
    from competitions.provisioning import ProvisioningError,preview_team_import
    with pytest.raises(ProvisioningError,match='ROLE_NOT_ALLOWED'):
        preview_team_import(manager,event,'teams.csv','team_number,captain_student_id\n1,S123\n',requested_role='MANAGER')
