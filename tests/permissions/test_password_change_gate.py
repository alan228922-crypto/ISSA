import pytest


@pytest.mark.django_db
def test_user_persists_role_and_forced_password_state():
    from accounts.models import User
    user=User.objects.create_user('team01',password='captain-id',role=User.Role.USER,must_change_password=True)
    assert user.role == User.Role.USER
    assert user.must_change_password is True
    assert user.password != 'captain-id'


@pytest.mark.django_db
def test_forced_password_change_blocks_direct_business_url_and_allows_password_change(client):
    from accounts.models import User
    user=User.objects.create_user('team01',password='captain-id',must_change_password=True)
    client.force_login(user)
    assert client.get('/events/').status_code == 302
    assert client.get('/accounts/password-change/').status_code == 200


@pytest.mark.django_db
def test_successful_login_redirects_to_event_landing_page(client):
    from accounts.models import User
    User.objects.create_user('team01',password='captain-id')

    response=client.post('/accounts/login/',{'username':'team01','password':'captain-id'})

    assert response.status_code == 302
    assert response.url == '/events/'


@pytest.mark.django_db
def test_successful_password_change_clears_forced_state(client):
    from accounts.models import User
    user=User.objects.create_user('team01',password='captain-id',must_change_password=True)
    client.force_login(user)
    response=client.post('/accounts/password-change/',{'old_password':'captain-id','new_password1':'new-safe-password-123','new_password2':'new-safe-password-123'})
    user.refresh_from_db()
    assert response.status_code == 302
    assert user.must_change_password is False
