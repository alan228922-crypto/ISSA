import pytest
from django.test import Client
from django.urls import reverse

from tests.application.test_project_creation import context, creation_context

pytestmark = pytest.mark.django_db


def create_url(event):
    return f'/events/{event.pk}/projects/create/'


def test_get_create_form_has_only_name_and_no_side_effects(creation_context, client):
    from projects.models import Project
    owner, event, _, _ = creation_context
    client.force_login(owner)
    response = client.get(create_url(event))
    assert response.status_code == 200
    assert set(response.context['form'].fields) == {'name'}
    assert 'csrfmiddlewaretoken' in response.content.decode()
    assert Project.objects.count() == 0


def test_create_post_redirects_directly_to_workspace(creation_context, client):
    from projects.models import Project
    owner, event, _, _ = creation_context
    client.force_login(owner)
    response = client.post(create_url(event), {'name': '新项目'})
    assert response.status_code == 302
    project = Project.objects.get()
    assert response.url == reverse('projects:workspace', args=[project.pk])
    workspace = client.get(response.url)
    assert workspace.status_code == 200
    assert workspace.context['bootstrap']['draft']['schema_version'] == 'physical-draft-v2'
    assert project.draft_version == 0
    assert client.post(create_url(event), {'name': '不同名称'}).url == response.url
    project.refresh_from_db()
    assert project.name == '新项目'
    assert Project.objects.count() == 1


@pytest.mark.parametrize('change', ['membership', 'event', 'user'])
def test_post_revalidates_after_form_open(creation_context, client, change):
    from competitions.models import EventMembership
    from projects.models import Project
    owner, event, _, _ = creation_context
    client.force_login(owner)
    assert client.get(create_url(event)).status_code == 200
    if change == 'membership':
        EventMembership.objects.filter(user=owner, event=event).update(is_active=False)
    elif change == 'event':
        event.status = 'FINISHED_GRACE'
        event.save()
    else:
        owner.is_active = False
        owner.save()
    response = client.post(create_url(event), {'name': '不应建立'})
    assert response.status_code in {302, 403}
    assert Project.objects.count() == 0


@pytest.mark.parametrize('name', ['', '  ', 'a' * 201])
def test_invalid_name_is_a_safe_field_error(creation_context, client, name):
    from projects.models import Project
    owner, event, _, _ = creation_context
    client.force_login(owner)
    response = client.post(create_url(event), {'name': name})
    assert response.status_code == 200
    assert response.context['form'].errors['name']
    assert Project.objects.count() == 0


@pytest.mark.parametrize('field', ['owner_user', 'event_id', 'draft_schema_version', 'analysis_type', 'draft'])
def test_tampered_fields_cannot_change_authority(creation_context, client, field):
    from projects.models import Project
    owner, event, _, _ = creation_context
    client.force_login(owner)
    response = client.post(create_url(event), {'name': '项目', field: 'attack'})
    assert response.status_code == 400
    assert Project.objects.count() == 0
    assert 'attack' not in response.content.decode()


def test_create_csrf_methods_and_password_gate(creation_context, client):
    from projects.models import Project
    owner, event, _, _ = creation_context
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(owner)
    assert csrf_client.post(create_url(event), {'name': '项目'}).status_code == 403
    client.force_login(owner)
    assert client.put(create_url(event)).status_code == 405
    owner.must_change_password = True
    owner.save()
    assert '/accounts/password-change/' in client.post(create_url(event), {'name': '项目'}).url
    assert Project.objects.count() == 0


@pytest.mark.parametrize('count,state', [(0, 'CREATE'), (1, 'CONTINUE'), (2, 'MULTIPLE')])
def test_event_landing_presentation_uses_cardinality(creation_context, client, count, state):
    from projects.models import Project
    owner, event, _, _ = creation_context
    for index in range(count):
        Project.objects.create(event=event, owner_user=owner, name=f'方案 {index}')
    client.force_login(owner)
    response = client.get('/events/')
    entry = response.context['event_entries'][0]
    assert entry['project_entry_state'] == state
    body = response.content.decode()
    assert (create_url(event) in body) is (count == 0)
    assert len(entry['projects']) == count
    if count == 1:
        assert '继续建模' in body
    if count > 1:
        assert '多个' in body and '请选择' in body


def test_unknown_error_and_html_name_are_safe(creation_context, client, monkeypatch):
    from projects import creation_views
    owner, event, _, _ = creation_context
    client.force_login(owner)
    client.post(create_url(event), {'name': '<script>alert(1)</script>'})
    assert '<script>alert(1)</script>' not in client.get('/events/').content.decode()

    def unavailable(**kwargs):
        raise RuntimeError('SECRET_PAYLOAD schema internal-id')

    monkeypatch.setattr(creation_views, 'create_or_open_project', unavailable)
    response = client.post(create_url(event), {'name': '项目'})
    assert response.status_code == 500
    assert 'SECRET_PAYLOAD' not in response.content.decode()


@pytest.mark.parametrize('role,status', [('MANAGER','ACTIVE'),('DEVELOPER','ACTIVE'),('USER','DRAFT'),('USER','FINISHED_GRACE'),('USER','PURGED')])
def test_ineligible_actor_has_no_create_cta_and_cannot_post(creation_context, client, role, status):
    from projects.models import Project
    owner, event, _, _ = creation_context
    owner.role = role
    owner.save()
    event.status = status
    event.save()
    client.force_login(owner)
    assert create_url(event) not in client.get('/events/').content.decode()
    response = client.post(create_url(event), {'name': '不应建立'})
    assert response.status_code == 403
    assert Project.objects.count() == 0
