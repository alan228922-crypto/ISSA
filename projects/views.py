"""M3 JSON 端点只负责 HTTP 适配，数值与领域规则留在既有服务层。"""
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from analysis.models import AnalysisRun
from analysis.orchestration import AnalysisError, analyze_project, check_project
from analysis.report_completeness import evaluate_report_completeness
from analysis.reporting import ReportError, build_report_package
from analysis.results import maximum_displacement_summary
from materials.services import SectionServiceError
from learning.services import (
    DisclosureError,
    PredictionError,
    comparison_for_disclosure,
    explanation_for_disclosure,
    record_student_result_reveal,
)
from modeling.services import DraftSaveError, save_physical_draft

from .models import Project
from .services import can_view_project, preview_section


# 閱讀提示：View 負責接收請求和回傳結果；模型與力學規則由 service 處理。

# 端點大致分成三類：保存模型、檢查／執行分析、讀取分析與學習結果。
# View 會把 HTTP 請求轉成服務層需要的資料，再把服務層結果轉回 JSON；
# 權限、版本、力學和結果揭示規則不應在這裡重複實作。


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
    'INCOMPLETE_DRAFT': '当前草稿尚未完整，请先运行模型检查并补齐未指定的对象。',
    'INVALID_SECTION_DEFINITION': '截面定义格式不正确。',
    'OVERLAP_UNSUPPORTED': '当前不支持包含重叠区域的组合截面。',
    'SOLVER_FAILED': '分析计算未能完成，请检查模型后重试。',
    'RESULT_REVEAL_FAILED': '无法安全记录结果查看，请稍后重试。',
    'ANALYSIS_NOT_SUCCESS': '分析尚未成功完成，暂无可用的比较或解释结果。',
    'REPORT_ANALYSIS_NOT_SUCCESS': '该分析尚未成功完成，暂时无法生成计算书资料。',
    'INTERNAL_ERROR': '服务器暂时无法处理请求，请稍后重试。',
}


_level_one_result = maximum_displacement_summary


def _error(code, status, *, details=None):
    """统一输出稳定机器代码及面向学生的简体中文提示，不暴露异常详情。"""
    return JsonResponse({'ok': False, 'error': {'code': code, 'message': MESSAGES.get(code, '请求无法处理，请检查输入。'), 'details': details or {}}}, status=status)


def _json_body(request):
    # 先把瀏覽器送來的內容讀成資料；欄位是否正確交給後面的服務檢查。
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
    # 接收前端整份模型草稿，並交給服務層檢查後一次保存。
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
    # 先檢查模型能不能分析，但不建立正式分析紀錄。
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
    # 正式分析由分析流程統一處理；這裡只接收請求並回傳分析編號和狀態。
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    payload = _json_body(request)
    if payload is None:
        return _error('MALFORMED_JSON', 400)
    if (
        set(payload) - {'expected_draft_version', 'prediction_id'}
        or 'expected_draft_version' not in payload
        or type(payload.get('expected_draft_version')) is not int
        or (
            payload.get('prediction_id') is not None
            and type(payload.get('prediction_id')) is not int
        )
    ):
        return _error('INVALID_REQUEST', 400)
    try:
        run = analyze_project(project=project, actor=request.user, expected_draft_version=payload['expected_draft_version'], prediction_id=payload.get('prediction_id'))
    except KeyError:
        return _error('INVALID_REQUEST', 400)
    except AnalysisError as exc:
        return _error(exc.code, exc.status_code)
    except Exception:
        return _error('INTERNAL_ERROR', 500)
    response = {'ok': run.status == AnalysisRun.Status.SUCCESS, 'analysis_run_id': run.id, 'model_revision_id': run.model_revision_id, 'status': run.status, 'result_schema_version': run.result_schema_version}
    if run.status != AnalysisRun.Status.SUCCESS:
        response['error'] = {'code': run.failure_code, 'message': MESSAGES.get(run.failure_code, '模型未通过分析验证。'), 'details': run.diagnostics_json}
        return JsonResponse(response, status=422)
    return JsonResponse(response)


@login_required
@require_GET
def analysis_data(request, project_id, run_id):
    # 學生查看成功結果時會留下紀錄，讓系統知道結果已經揭示。
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    if not can_view_project(request.user, project):
        return _error('PROJECT_READ_DENIED', 403)
    run = AnalysisRun.objects.select_related('model_revision', 'solver_version').filter(pk=run_id, project_id=project.id).first()
    if run is None:
        return _error('PROJECT_NOT_FOUND', 404)
    if run.status == AnalysisRun.Status.SUCCESS:
        try:
            record_student_result_reveal(project=project, run=run, actor=request.user)
        except PredictionError as exc:
            return _error(exc.code, exc.status_code)
        except Exception:
            return _error('RESULT_REVEAL_FAILED', 500)
    response = {'ok': True, 'analysis_run_id': run.id, 'model_revision_id': run.model_revision_id, 'source_draft_version': run.model_revision.source_draft_version, 'model_hash': run.model_revision.model_hash, 'solver_version': run.solver_version.solver_version, 'input_hash': run.input_hash, 'input_schema_version': run.input_schema_version, 'result_schema_version': run.result_schema_version, 'status': run.status, 'failure_code': run.failure_code, 'diagnostics': run.diagnostics_json, 'result_json': run.result_json}
    if run.status == AnalysisRun.Status.SUCCESS: response['level_one'] = _level_one_result(run.result_json)
    return JsonResponse(response)


@login_required
@require_GET
def analysis_runs(request, project_id):
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    if not can_view_project(request.user, project):
        return _error('PROJECT_READ_DENIED', 403)
    runs = AnalysisRun.objects.select_related('model_revision').filter(project_id=project.id).order_by('-started_at', '-id')
    return JsonResponse({'ok': True, 'runs': [
        {
            'analysis_run_id': run.id,
            'status': run.status,
            'created_at': run.started_at,
            'model_revision_id': run.model_revision_id,
            'source_draft_version': run.model_revision.source_draft_version,
            'is_stale': run.model_revision.source_draft_version != project.draft_version,
        }
        for run in runs
    ]})


@login_required
@require_GET
def analysis_report(request, project_id, run_id):
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    if not can_view_project(request.user, project):
        return _error('PROJECT_READ_DENIED', 403)
    run = AnalysisRun.objects.filter(pk=run_id, project_id=project.id).first()
    if run is None:
        return _error('PROJECT_NOT_FOUND', 404)
    try:
        report = build_report_package(run=run, actor=request.user, project=project)
    except ReportError as exc:
        return _error(exc.code, exc.status_code, details=exc.details)
    except Exception:
        return _error('INTERNAL_ERROR', 500)
    return JsonResponse({'ok': True, 'report': report, 'completeness': evaluate_report_completeness(report)})


@login_required
@require_GET
def analysis_comparison(request, project_id, run_id):
    # 比較資料由專門服務產生；這裡不重新計算力學結果。
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    if not can_view_project(request.user, project):
        return _error('PROJECT_READ_DENIED', 403)
    run = AnalysisRun.objects.select_related('model_revision', 'prediction').filter(
        pk=run_id, project_id=project.id,
    ).first()
    if run is None:
        return _error('PROJECT_NOT_FOUND', 404)
    try:
        comparison = comparison_for_disclosure(project=project, run=run, actor=request.user)
    except DisclosureError as exc:
        return _error(exc.code, exc.status_code)
    except Exception:
        return _error('INTERNAL_ERROR', 500)
    return JsonResponse({'ok': True, 'comparison': comparison})


@login_required
@require_GET
def analysis_explanation(request, project_id, run_id):
    # 把分析證據整理成教學說明，再以 JSON 回傳給前端。
    project = _project(project_id)
    if project is None:
        return _error('PROJECT_NOT_FOUND', 404)
    if not can_view_project(request.user, project):
        return _error('PROJECT_READ_DENIED', 403)
    run = AnalysisRun.objects.select_related('model_revision', 'prediction').filter(
        pk=run_id, project_id=project.id,
    ).first()
    if run is None:
        return _error('PROJECT_NOT_FOUND', 404)
    try:
        explanation = explanation_for_disclosure(project=project, run=run, actor=request.user)
    except DisclosureError as exc:
        return _error(exc.code, exc.status_code)
    except Exception:
        return _error('INTERNAL_ERROR', 500)
    return JsonResponse({'ok': True, 'explanation': explanation})


@login_required
@require_POST
def section_preview(request, project_id):
    # 只預覽截面計算結果，不會建立或修改已保存的截面。
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
