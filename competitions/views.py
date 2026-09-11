from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404,render
from .models import CompetitionEvent
from .provisioning import ProvisioningError,confirm_team_import,preview_team_import


@login_required
def provision_preview(request,event_id):
    event=get_object_or_404(CompetitionEvent,pk=event_id)
    if request.method!='POST' or 'csv_file' not in request.FILES:
        return HttpResponseForbidden('请上传 CSV 文件。')
    try:
        preview=preview_team_import(request.user,event,request.FILES['csv_file'].name,request.FILES['csv_file'].read().decode())
    except ProvisioningError as exc:
        return HttpResponseForbidden(str(exc))
    return render(request,'competitions/provision_preview.html',{'preview':preview,'event':event})


@login_required
def provision_confirm(request,event_id):
    event=get_object_or_404(CompetitionEvent,pk=event_id)
    try:
        result=confirm_team_import(request.user,event,request.POST['token'])
    except (KeyError,ProvisioningError) as exc:
        return HttpResponseForbidden(str(exc))
    return render(request,'competitions/provision_result.html',{'result':result})
