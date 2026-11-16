"""一般 SSR 的可访问性、真实表单和安全错误呈现边界。"""
import pytest
from django.urls import reverse
from tests.application.test_physical_draft import context

pytestmark = pytest.mark.django_db


def assert_shell(response, status=200):
    assert response.status_code == status
    body = response.content.decode()
    assert 'ui/product.css' in body
    assert 'name="viewport"' in body
    assert 'id="main-content"' in body
    assert '跳至主要内容' in body
    assert '<footer' in body
    assert 'cdn.' not in body and 'fonts.googleapis' not in body
    return body


def test_login_retains_next_and_server_errors_in_shared_shell(client):
    assert_shell(client.get('/accounts/login/?next=/events/'))
    body = assert_shell(client.post('/accounts/login/?next=/events/', {'username': 'unknown-ui-user', 'password': 'not-a-real-password', 'next': '/events/'}))
    assert 'role="alert"' in body
    assert 'name="next"' in body
    assert 'not-a-real-password' not in body
    assert 'csrfmiddlewaretoken' in body


def test_password_change_keeps_input_error_associations(client):
    from accounts.models import User
    user = User.objects.create_user('ui-password', password='OldReviewPassword99!', must_change_password=True)
    client.force_login(user)
    response = client.post('/accounts/password-change/', {'old_password': 'bad', 'new_password1': 'one', 'new_password2': 'two'})
    body = assert_shell(response)
    assert 'aria-invalid="true"' in body
    assert 'id_old_password_error' in body
    assert 'aria-describedby=' in body
    assert user.must_change_password


@pytest.mark.parametrize('route', ['materials:index', 'materials:material_create', 'materials:section_create', 'materials:composite_section_create'])
def test_resource_entry_pages_have_shared_shell_without_fixture_data(client, context, route):
    owner, project, _, _ = context
    client.force_login(owner)
    body = assert_shell(client.get(reverse(route, kwargs={'project_id': project.pk})))
    assert '固定合成' not in body
    assert 'preview.js' not in body
    assert '272.50' not in body


def test_management_denial_is_readable_and_preserves_forbidden_status(client, context):
    owner, project, _, _ = context
    client.force_login(owner)
    response = client.get(f'/competitions/{project.event_id}/manage/')
    body = assert_shell(response, 403)
    assert 'role="alert"' in body
    assert 'password_hash' not in body


def test_existing_workspace_receives_no_ssr_reset(client, context):
    owner, project, _, _ = context
    client.force_login(owner)
    response = client.get(reverse('projects:workspace', kwargs={'project_id': project.pk}))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'workspace-bootstrap' in body
    assert 'ui/product.css' not in body
    assert 'ui/header.css' in body


def test_logout_keeps_post_only_csrf_contract(context):
    from django.test import Client
    owner, _, _, _ = context
    client = Client(enforce_csrf_checks=True)
    client.force_login(owner)
    assert client.get('/accounts/logout/').status_code == 405
    assert client.post('/accounts/logout/').status_code == 403
    response = client.get('/events/')
    assert 'method="post" action="/accounts/logout/"' in response.content.decode()
    csrf = client.cookies['csrftoken'].value
    assert client.post('/accounts/logout/', {'csrfmiddlewaretoken': csrf}).status_code == 302
    assert client.get('/events/').status_code == 302
