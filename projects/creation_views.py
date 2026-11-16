"""项目创建的薄 SSR adapter；学生只提交名称，不提交归属与 schema。"""
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from competitions.models import CompetitionEvent
from .creation import ProjectCreationError, create_or_open_project, project_creation_error
from .forms import ProjectCreateForm

logger = logging.getLogger(__name__)

ERROR_COPY = {
    'PROJECT_CREATE_DENIED': '目前无法创建项目。请确认账号有效，并已取得此赛事的参赛资格。',
    'EVENT_NOT_ACTIVE': '赛事尚未开放或已结束，不能创建项目。请返回赛事页查看现有项目。',
    'EVENT_PURGED': '此赛事已关闭，不能创建或进入项目。请返回赛事页。',
    'EVENT_ACCESS_EXPIRED': '此赛事的操作期限已结束，不能创建项目。请返回赛事页。',
    'EVENT_NOT_FOUND': '找不到此赛事。请返回赛事页重新选择。',
    'PROJECT_MULTIPLE_EXISTING': '此赛事中已有多个项目，请返回赛事页选择现有项目。',
    'PROJECT_EXISTING_UNAVAILABLE': '已有项目暂时无法继续。请返回赛事页查看项目，或联系老师。',
    'PROJECT_CREATE_BUSY': '目前操作繁忙，项目尚未确认创建。请稍后重试或返回赛事页查看。',
    'INVALID_PROJECT_NAME': '请填写有效的项目名称（最多 200 个字）。',
    'INVALID_REQUEST': '无法提交这些内容。请仅填写项目名称后重试。',
}


@login_required
@require_http_methods(['GET', 'POST'])
def project_create(request, event_id):
    form = ProjectCreateForm(request.POST if request.method == 'POST' else None)

    def error_page(code, status):
        return render(request, 'projects/project_create.html', {
            'form': form, 'error': ERROR_COPY.get(code, '暂时无法完成操作。请返回赛事页，稍后重试。'),
        }, status=status)

    event = CompetitionEvent.objects.filter(pk=event_id).first()
    if event is None:
        return error_page('EVENT_NOT_FOUND', 404)
    eligibility = project_creation_error(actor=request.user, event=event, now=timezone.now())
    if eligibility:
        return error_page(eligibility, 403)
    if request.method == 'POST':
        if set(request.POST) - {'name', 'csrfmiddlewaretoken'} or len(request.POST.getlist('name')) > 1:
            return error_page('INVALID_REQUEST', 400)
        if form.is_valid():
            try:
                result = create_or_open_project(actor=request.user, event_id=event_id, name=form.cleaned_data['name'])
            except ProjectCreationError as exc:
                logger.info('project_create_denied', extra={'actor_id': request.user.pk, 'event_id': event_id, 'outcome': exc.code})
                return error_page(exc.code, exc.status_code)
            except Exception:
                logger.error('project_create_failed', extra={'actor_id': request.user.pk, 'event_id': event_id})
                return error_page('INTERNAL_ERROR', 500)
            logger.info('project_create', extra={'actor_id': request.user.pk, 'event_id': event_id,
                'project_id': result.project.pk, 'outcome': 'created' if result.created else 'reopened'})
            return redirect('projects:workspace', project_id=result.project.pk)
    return render(request, 'projects/project_create.html', {'form': form, 'event': event})
