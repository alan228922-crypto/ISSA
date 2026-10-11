from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView,LogoutView
from django.db.models import Exists, OuterRef
from django.shortcuts import redirect,render
from analysis.models import AnalysisRun
from competitions.authorization import can_view_event
from learning.models import Prediction
from modeling.models import GeometryNode
from projects.models import Project
from projects.services import can_view_project

from .forms import ForcedPasswordChangeForm


class AccountLoginView(LoginView):
    template_name='accounts/login.html'
    next_page='/events/'


class AccountLogoutView(LogoutView):
    next_page='/accounts/login/'


@login_required
def event_landing(request):
    """仅显示当前用户依既有赛事/项目读取策略可进入的项目。"""
    from competitions.models import CompetitionEvent

    events = [
        event
        for event in CompetitionEvent.objects.order_by("competition_date", "event_code", "id")
        if can_view_event(request.user, event)
    ]
    projects_by_event = {event.id: [] for event in events}
    for project in (
        Project.objects.select_related("event", "owner_user")
        .filter(event_id__in=projects_by_event)
        .filter(analysis_type=Project.AnalysisType.TRUSS_2D)
        .annotate(
            ux_has_nodes=Exists(GeometryNode.objects.filter(project_id=OuterRef("pk"))),
            ux_has_current_result=Exists(AnalysisRun.objects.filter(
                project_id=OuterRef("pk"), status=AnalysisRun.Status.SUCCESS,
                model_revision__source_draft_version=OuterRef("draft_version"),
            )),
            ux_has_result=Exists(AnalysisRun.objects.filter(project_id=OuterRef("pk"), status=AnalysisRun.Status.SUCCESS)),
            ux_has_current_prediction=Exists(Prediction.objects.filter(
                project_id=OuterRef("pk"), source_draft_version=OuterRef("draft_version"),
                status=Prediction.Status.COMPLETED,
            )),
        )
        .order_by("event__competition_date", "event__event_code", "name", "id")
    ):
        if can_view_project(request.user, project):
            if not project.ux_has_nodes:
                project.ux_status, project.ux_next = "尚未建模", "从第一根构件开始"
            elif project.ux_has_current_result:
                project.ux_status, project.ux_next = "已完成分析", "查看结果并总结"
            elif project.ux_has_current_prediction:
                project.ux_status, project.ux_next = "已完成预测", "开始分析"
            elif project.ux_has_result:
                project.ux_status, project.ux_next = "模型已修改", "检查修改后的模型"
            else:
                project.ux_status, project.ux_next = "已有模型", "检查模型并进行预测或分析"
            projects_by_event[project.event_id].append(project)
    event_entries = [
        {"event": event, "projects": projects_by_event[event.id]}
        for event in events
    ]
    return render(request, "accounts/event_landing.html", {"event_entries": event_entries})


@login_required
def password_change(request):
    # 強制改密完成後同步更新 session，避免使用者已換密碼卻被舊 session 立即登出。
    if request.method=='POST':
        form=ForcedPasswordChangeForm(request.user,request.POST)
        if form.is_valid():
            user=form.save()
            user.must_change_password=False
            user.save(update_fields=['must_change_password'])
            update_session_auth_hash(request,user)
            return redirect('/events/')
    else:
        form=ForcedPasswordChangeForm(request.user)
    return render(request,'accounts/password_change.html',{'form':form})
