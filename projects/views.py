"""M3 JSON 端点只负责 HTTP 适配，数值与领域规则留在既有服务层。"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from analysis.models import AnalysisRun
from analysis.orchestration import AnalysisError, analyze_project, check_project
from materials.services import SectionServiceError
from modeling.services import DraftSaveError, save_physical_draft

from .models import Project
from .services import can_view_project, preview_section


MESSAGES = {
    'MALFORMED_JSON': '请求内容不是有效的 JSON。',
    'INVALID_REQUEST': '请求字段不完整或格式不正确。',
    'STALE_DRAFT': '当前模型已被其他操作更新，请刷新后重试。',
    'PROJECT_WRITE_DENIED': '您没有修改该项目的权限。',
    'PROJECT_ANALYZE_DENIED': '您没有分析该项目的权限。',
    'PROJECT_CHECK_DENIED': '您没有检查该项目的权限。',
    'PROJECT_READ_DENIED': '您没有查看该项目的权限。',
    'PROJECT_NOT_FOUND': '未找到指定的项目或分析记录。',
    'INVALID_DRAFT': '模型数据未通过验证，请检查输入。',
    'INVALID_SECTION_DEFINITION': '截面定义格式不正确。',
    'OVERLAP_UNSUPPORTED': '当前不支持包含重叠区域的组合截面。',
    'SOLVER_FAILED': '分析计算未能完成，请检查模型后重试。',
}


def _error(code, status, *, details=None):
    """统一输出稳定机器代码及面向学生的简体中文提示，不暴露异常详情。"""
    return JsonResponse({'ok': False, 'error': {'code': code, 'message': MESSAGES.get(code, '请求无法处理，请检查输入。'), 'details': details or {}}}, status=status)


def _json_body(request):
    try:
        payload = json.loads(request.body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _project(project_id):
    return Project.objects.select_related('event', 'owner_user').filter(pk=project_id).first()


@login_required
@require_POST
def model_save(request, project_id):
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    payload = _json_body(request)
    if payload is None:
        return _error('MALFORMED_JSON', 400)
    try:
        result = save_physical_draft(actor=request.user, project=project, payload=payload)
    except DraftSaveError as exc:
        status = 403 if exc.code == 'PROJECT_WRITE_DENIED' else 409 if exc.code == 'STALE_DRAFT' else 422
        return _error(exc.code, status)
    return JsonResponse({'ok': True, 'project_id': project.id, 'draft_version': result['draft_version'], 'schema_version': payload['schema_version'], 'validation': result['validation']})


@login_required
@require_POST
def model_check(request, project_id):
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    payload = _json_body(request)
    if payload is None:
        return _error('MALFORMED_JSON', 400)
    try:
        result = check_project(project=project, actor=request.user, expected_draft_version=payload['expected_draft_version'])
    except KeyError:
        return _error('INVALID_REQUEST', 400)
    except AnalysisError as exc:
        return _error(exc.code, exc.status_code)
    return JsonResponse(result)


@login_required
@require_POST
def analyze(request, project_id):
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    payload = _json_body(request)
    if payload is None:
        return _error('MALFORMED_JSON', 400)
    try:
        run = analyze_project(project=project, actor=request.user, expected_draft_version=payload['expected_draft_version'], prediction_id=payload.get('prediction_id'))
    except KeyError:
        return _error('INVALID_REQUEST', 400)
    except AnalysisError as exc:
        return _error(exc.code, exc.status_code)
    response = {'ok': run.status == AnalysisRun.Status.SUCCESS, 'analysis_run_id': run.id, 'model_revision_id': run.model_revision_id, 'status': run.status, 'result_schema_version': run.result_schema_version}
    if run.status != AnalysisRun.Status.SUCCESS:
        response['error'] = {'code': run.failure_code, 'message': MESSAGES.get(run.failure_code, '模型未通过分析验证。'), 'details': run.diagnostics_json}
        return JsonResponse(response, status=422)
    return JsonResponse(response)


@login_required
@require_GET
def analysis_data(request, project_id, run_id):
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    if not can_view_project(request.user, project):
        return _error('PROJECT_READ_DENIED', 403)
    run = AnalysisRun.objects.select_related('model_revision', 'solver_version').filter(pk=run_id, project_id=project.id).first()
    if run is None:
        return _error('PROJECT_NOT_FOUND', 404)
    return JsonResponse({'ok': True, 'analysis_run_id': run.id, 'model_revision_id': run.model_revision_id, 'model_hash': run.model_revision.model_hash, 'solver_version': run.solver_version.solver_version, 'input_hash': run.input_hash, 'input_schema_version': run.input_schema_version, 'result_schema_version': run.result_schema_version, 'status': run.status, 'failure_code': run.failure_code, 'diagnostics': run.diagnostics_json, 'result_json': run.result_json})


@login_required
@require_POST
def section_preview(request, project_id):
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    definition = _json_body(request)
    if definition is None:
        return _error('MALFORMED_JSON', 400)
    try:
        properties = preview_section(actor=request.user, project=project, definition=definition)
    except SectionServiceError as exc:
        status = 403 if exc.args[0] == 'PROJECT_WRITE_DENIED' else 422
        return _error(exc.args[0], status)
    return JsonResponse({'ok': True, 'schema_version': 'section-properties-v1', 'properties': properties})
