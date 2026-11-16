from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousOperation
from django.http import Http404, HttpResponse, UnreadablePostError
from django.http.multipartparser import MultiPartParserError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .authorization import can_manage_event, participant_management_error
from .forms import CreateParticipantForm, JoinParticipantForm, ReactivateParticipantForm, DeactivateParticipantForm
from .models import CompetitionEvent, EventMembership
from .participant_services import ParticipantManagementError, preview_participant_change, confirm_participant_change
from .participant_inputs import MAX_CSV_BYTES
from .presentation import participant_error_message
from .provisioning import ProvisioningError, confirm_team_import, preview_team_import


def _error(code, status=400, *, request=None):
    message = participant_error_message(code)
    try:
        return render(request, "shared/request_error.html", {"error_message": message}, status=status)
    except Exception:
        # Rendering failures must still fail closed without exposing preview data.
        return HttpResponse(message, status=status, content_type="text/plain; charset=utf-8")


def _safe_management(view):
    @wraps(view)
    @sensitive_variables()
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except ParticipantManagementError as exc:
            return _error(exc.code, exc.status_code, request=args[0] if args else kwargs.get("request"))
        except Http404:
            return _error('PERMISSION_DENIED', 404, request=args[0] if args else kwargs.get("request"))
        except (SuspiciousOperation, MultiPartParserError, UnreadablePostError, UnicodeError):
            return _error('INVALID_PROVISIONING_ROW', request=args[0] if args else kwargs.get("request"))
        except Exception:
            return _error('INTERNAL_ERROR', 500, request=args[0] if args else kwargs.get("request"))
    return wrapped


@sensitive_post_parameters()
@login_required
@require_POST
@_safe_management
@sensitive_variables()
def provision_preview(request, event_id):
    event = get_object_or_404(CompetitionEvent, pk=event_id)
    upload = request.FILES.get('csv_file')
    if not upload or upload.size > MAX_CSV_BYTES or set(request.POST) - {'csrfmiddlewaretoken'} or set(request.FILES) != {'csv_file'}:
        return _error('INVALID_PROVISIONING_ROW', request=request)
    try:
        preview = preview_team_import(request.user, event, upload.name, upload.read().decode('utf-8-sig'))
    except UnicodeError:
        return _error('INVALID_PROVISIONING_ROW', request=request)
    except ProvisioningError as exc:
        return _error(exc.code, exc.status_code, request=request)
    except Exception:
        return _error('INTERNAL_ERROR', 500, request=request)
    return render(request, 'competitions/provision_preview.html', {
        'preview': preview, 'event': event,
        'error_messages': [participant_error_message(code) for code in preview['errors']],
    })


@sensitive_post_parameters()
@login_required
@require_POST
@_safe_management
@sensitive_variables()
def provision_confirm(request, event_id):
    event = get_object_or_404(CompetitionEvent, pk=event_id)
    if set(request.POST) - {'preview_ref', 'csrfmiddlewaretoken'} or 'preview_ref' not in request.POST:
        return _error('INVALID_PREVIEW', request=request)
    try:
        result = confirm_team_import(request.user, event, request.POST['preview_ref'])
    except ProvisioningError as exc:
        return _error(exc.code, exc.status_code, request=request)
    except Exception:
        return _error('INTERNAL_ERROR', 500, request=request)
    request.session['participant_management_notice'] = {'event_ref': event.pk, 'outcome': result['outcome']}
    return redirect('participant_list', event_id=event.pk)


def _management_event(request, event_id):
    event = CompetitionEvent.objects.filter(pk=event_id).first()
    if event is None or not can_manage_event(request.user, event):
        raise ParticipantManagementError('PERMISSION_DENIED', 403)
    error = participant_management_error(actor=request.user, event=event, operation='CREATE_USER', now=timezone.now())
    if error and event.status != CompetitionEvent.Status.FINISHED_GRACE:
        raise ParticipantManagementError(error, 403)
    return event, error is not None


@login_required
@require_GET
@_safe_management
def event_management(request, event_id):
    event, readonly = _management_event(request, event_id)
    return render(request, 'competitions/event_management.html', {'event': event, 'readonly': readonly})


@login_required
@require_GET
@_safe_management
def participant_list(request, event_id):
    event, readonly = _management_event(request, event_id)
    participants = EventMembership.objects.filter(event=event, membership_type='PARTICIPANT').select_related('user').order_by('user__username', 'pk')
    notice = request.session.get('participant_management_notice')
    processed = type(notice) is dict and notice.get('event_ref') == event.pk and notice.get('outcome') in {'SUCCESS', 'NOOP'}
    if processed:
        request.session.pop('participant_management_notice')
    return render(request, 'competitions/participant_list.html', {
        'event': event, 'readonly': readonly, 'participants': participants, 'processed': processed,
        'noop': processed and notice['outcome'] == 'NOOP',
    })


ACTION_COPY = {
    'CREATE_USER': ('新增队伍', '确认新增'), 'JOIN_EXISTING': ('加入既有账号', '确认加入'),
    'REACTIVATE': ('恢复资格', '确认恢复'), 'DEACTIVATE': ('停用资格', '确认停用'),
}


def _post_fields_allowed(request, allowed):
    return not request.FILES and not set(request.POST) - set(allowed) - {'csrfmiddlewaretoken'} and all(
        len(request.POST.getlist(key)) == 1 for key in request.POST
    )


def _confirmation(request, event, operation, preview):
    title, confirm_label = ACTION_COPY[operation]
    return render(request, 'competitions/participant_confirm.html', {
        'event': event, 'preview': preview, 'operation': operation, 'title': title, 'confirm_label': confirm_label,
    })


@sensitive_variables()
def _participant_form(request, event_id, form_class, operation):
    event, readonly = _management_event(request, event_id)
    if readonly:
        raise ParticipantManagementError('EVENT_STATUS_NOT_ALLOWED', 403)
    if request.method == 'POST' and not _post_fields_allowed(request, form_class.base_fields):
        raise ParticipantManagementError('INVALID_PROVISIONING_ROW')
    form = form_class(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        preview = preview_participant_change(actor=request.user, event_id=event.pk, operation=operation, fields=form.cleaned_data)
        return _confirmation(request, event, operation, preview)
    return render(request, 'competitions/participant_form.html', {'event': event, 'form': form, 'title': ACTION_COPY[operation][0]})


@sensitive_post_parameters()
@login_required
@require_http_methods(['GET', 'POST'])
@_safe_management
def participant_new(request, event_id):
    return _participant_form(request, event_id, CreateParticipantForm, 'CREATE_USER')


@sensitive_post_parameters()
@login_required
@require_http_methods(['GET', 'POST'])
@_safe_management
def participant_join(request, event_id):
    return _participant_form(request, event_id, JoinParticipantForm, 'JOIN_EXISTING')


def _membership_preview(request, event_id, membership_id, operation, form_class):
    event, readonly = _management_event(request, event_id)
    if readonly:
        raise ParticipantManagementError('EVENT_STATUS_NOT_ALLOWED', 403)
    if not _post_fields_allowed(request, form_class.base_fields):
        raise ParticipantManagementError('INVALID_PROVISIONING_ROW')
    form = form_class(request.POST)
    if not form.is_valid():
        raise ParticipantManagementError('INVALID_PROVISIONING_ROW')
    preview = preview_participant_change(actor=request.user, event_id=event.pk, operation=operation,
                                         fields={**form.cleaned_data, 'membership_id': membership_id})
    return _confirmation(request, event, operation, preview)


@sensitive_post_parameters()
@login_required
@require_POST
@_safe_management
def participant_reactivate_preview(request, event_id, membership_id):
    return _membership_preview(request, event_id, membership_id, 'REACTIVATE', ReactivateParticipantForm)


@sensitive_post_parameters()
@login_required
@require_POST
@_safe_management
def participant_deactivate_preview(request, event_id, membership_id):
    return _membership_preview(request, event_id, membership_id, 'DEACTIVATE', DeactivateParticipantForm)


@sensitive_post_parameters()
@login_required
@require_POST
@_safe_management
def participant_confirm(request, event_id):
    if not _post_fields_allowed(request, {'operation', 'preview_ref'}) or set(request.POST) - {'csrfmiddlewaretoken'} != {'operation', 'preview_ref'}:
        raise ParticipantManagementError('INVALID_PREVIEW')
    operation = request.POST['operation']
    if operation not in ACTION_COPY:
        raise ParticipantManagementError('INVALID_PROVISIONING_ROW')
    # 不能先用 view 生命周期拒绝：service 必须有机会清除已过期 credential。
    result = confirm_participant_change(actor=request.user, event_id=event_id, operation=operation, preview_ref=request.POST['preview_ref'])
    request.session['participant_management_notice'] = {'event_ref': event_id, 'outcome': result['outcome']}
    return redirect('participant_list', event_id=event_id)


@login_required
@require_GET
@_safe_management
def provision_upload(request, event_id):
    event, readonly = _management_event(request, event_id)
    error = participant_management_error(actor=request.user, event=event, operation='DRAFT_CSV_CREATE', now=timezone.now())
    if error:
        raise ParticipantManagementError(error, 403)
    return render(request, 'competitions/provision_upload.html', {'event': event})
