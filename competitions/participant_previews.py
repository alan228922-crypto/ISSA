"""独立 DB Session 行存储；不使用管理员 auth Session 或客户端签名凭证。"""
from datetime import datetime, timezone as dt_timezone
import re
import secrets
import string

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables


def require_database_sessions():
    if getattr(settings, 'SESSION_ENGINE', 'django.contrib.sessions.backends.db') != 'django.contrib.sessions.backends.db' or Session.objects.db != 'default':
        raise ImproperlyConfigured('M8_REQUIRES_DEFAULT_DATABASE_SESSIONS')


@sensitive_variables()
def create_preview(*, actor, event, operation, targets, source_filename):
    require_database_sessions()
    now = timezone.now().timestamp()
    state = {
        'schema_version': 'participant-preview-v1', 'actor_ref': actor.pk,
        'event_ref': event.pk, 'operation': operation, 'targets': targets,
        'competition_date': event.competition_date.isoformat(),
        'issued_at': now, 'expires_at': now + 600, 'stage': 'PENDING',
        'source_filename': source_filename,
    }
    for _ in range(5):
        ref = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(32))
        if Session.objects.filter(session_key=ref).exists():
            continue
        Session.objects.create(session_key=ref, session_data=SessionStore().encode({'participant_preview': state}),
                               expire_date=datetime.fromtimestamp(state['expires_at'], dt_timezone.utc))
        return ref
    raise RuntimeError('PREVIEW_ALLOCATION_FAILED')


@sensitive_variables()
def load_preview(ref):
    require_database_sessions()
    if type(ref) is not str or not re.fullmatch('[a-z0-9]{32}', ref):
        return None, None
    row = Session.objects.filter(session_key=ref).first()
    data = row.get_decoded() if row else {}
    state = data.get('participant_preview')
    if type(state) is not dict or state.get('schema_version') != 'participant-preview-v1':
        return None, None
    return row, state


@sensitive_variables()
def consume_preview(row, state, receipt):
    tombstone = {key: state[key] for key in (
        'schema_version', 'actor_ref', 'event_ref', 'operation', 'issued_at', 'expires_at',
    )}
    tombstone.update(stage='CONSUMED', receipt_ref=receipt.pk)
    row.session_data = SessionStore().encode({'participant_preview': tombstone})
    row.save(update_fields=['session_data'])
