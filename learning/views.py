"""Prediction JSON endpoints adapt HTTP to the existing lifecycle services."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from analysis.models import AnalysisRun
from projects.models import Project
from projects.services import can_view_project

from .models import Prediction, Reflection
from .services import (
    PredictionError, ReflectionError, complete_prediction, complete_reflection,
    create_prediction, create_reflection, get_reflection_for_read, update_reflection,
)


# 閱讀提示：這裡只負責接收預測／反思請求，生命週期規則交給 learning service。


MESSAGES = {
    "MALFORMED_JSON": "请求内容不是有效的 JSON。",
    "INVALID_REQUEST": "请求字段不完整或格式不正确。",
    "PROJECT_NOT_FOUND": "未找到指定的项目。",
    "PROJECT_READ_DENIED": "您没有查看该项目的权限。",
    "PROJECT_WRITE_DENIED": "您没有修改该项目预测的权限。",
    "PREDICTION_NOT_FOUND": "未找到指定的预测记录。",
    "PREDICTION_INVALID_SCHEMA": "预测内容格式不正确。",
    "PREDICTION_INCOMPLETE": "请完成所有预测内容后再提交。",
    "INVALID_PHYSICAL_POINT_REF": "预测位置不属于当前模型。",
    "INVALID_LOAD_PATH": "代表性传力路径与当前模型不一致。",
    "PREDICTION_STALE_DRAFT": "预测对应的模型版本已过期，请重新创建预测。",
    "PREDICTION_ALREADY_COMPLETED": "该预测已经完成，不能再次修改。",
    "PREDICTION_INVALIDATED": "该预测已经失效，不能再次修改。",
    "PREDICTION_AFTER_RESULT_REVEAL": "该模型版本的分析结果已查看，不能再完成预测。",
    "INTERNAL_ERROR": "服务器暂时无法处理请求，请稍后重试。",
    "REFLECTION_NOT_FOUND": "未找到该分析记录的反思。",
    "REFLECTION_WRITE_DENIED": "您没有填写该反思的权限。",
    "REFLECTION_READ_DENIED": "您没有查看该反思的权限。",
    "REFLECTION_ALREADY_EXISTS": "该分析记录已有反思。",
    "REFLECTION_ALREADY_COMPLETED": "该反思已经完成，不能再修改。",
    "REFLECTION_NOT_DRAFT": "该反思不处于可编辑草稿状态。",
    "REFLECTION_NOT_ELIGIBLE": "尚未满足填写反思的结果查看条件。",
    "REFLECTION_RUN_NOT_SUCCESS": "分析尚未成功完成，暂不能填写反思。",
    "REFLECTION_INCOMPLETE": "请完成三项反思内容后再提交。",
    "REFLECTION_INVALID_FIELDS": "反思字段不正确或超出长度限制。",
    "REFLECTION_EVENT_NOT_ACTIVE": "当前赛事状态不允许填写反思。",
}

_VALIDATION_CODES = {
    "PREDICTION_INVALID_SCHEMA",
    "PREDICTION_INCOMPLETE",
    "INVALID_PHYSICAL_POINT_REF",
    "INVALID_LOAD_PATH",
}


def _error(code, status):
    return JsonResponse(
        {
            "ok": False,
            "error": {
                "code": code,
                "message": MESSAGES.get(code, "请求无法处理，请检查输入。"),
                "details": {},
            },
        },
        status=status,
    )


def _json_body(request):
    # 先限制輸入為 JSON object；預測與反思的細節驗證由 lifecycle service 統一處理。
    try:
        payload = json.loads(request.body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _project(project_id):
    return (
        Project.objects.select_related("event", "owner_user")
        .filter(pk=project_id)
        .first()
    )


def _prediction_response(prediction, *, status=200):
    # 將 Prediction 的狀態與版本欄位固定成前端可依賴的回應格式。
    return JsonResponse(
        {
            "ok": True,
            "prediction_id": prediction.id,
            "project_id": prediction.project_id,
            "source_draft_version": prediction.source_draft_version,
            "status": prediction.status,
            "prediction_schema_version": prediction.prediction_schema_version,
            "payload": prediction.payload_json,
            "created_at": prediction.created_at.isoformat(),
            "completed_at": (
                prediction.completed_at.isoformat() if prediction.completed_at else None
            ),
            "invalidated_at": (
                prediction.invalidated_at.isoformat() if prediction.invalidated_at else None
            ),
            "invalidation_code": prediction.invalidation_code,
        },
        status=status,
    )


def _service_error(exc):
    status = 422 if exc.code in _VALIDATION_CODES else exc.status_code
    return _error(exc.code, status)


def _reflection_response(reflection, *, status=200):
    # 反思回應保留其綁定的分析版本，讓前端知道這段學習紀錄對應哪一次分析。
    return JsonResponse({
        "ok": True,
        "analysis_run_id": reflection.analysis_run_id,
        "project_id": reflection.analysis_run.project_id,
        "source_draft_version": reflection.analysis_run.model_revision.source_draft_version,
        "status": reflection.status,
        "original_reasoning": reflection.original_reasoning,
        "unexpected_results": reflection.unexpected_results,
        "next_iteration_intent": reflection.next_iteration_intent,
        "reflection_schema_version": reflection.reflection_schema_version,
        "created_at": reflection.created_at.isoformat(),
        "updated_at": reflection.updated_at.isoformat(),
        "completed_at": reflection.completed_at.isoformat() if reflection.completed_at else None,
    }, status=status)


def _reflection_run(project, run_id):
    return AnalysisRun.objects.select_related("model_revision").filter(pk=run_id, project=project).first()


def _reflection_error(exc):
    return _error(exc.code, exc.status_code)


@login_required
@require_POST
def prediction_create(request, project_id):
    # 建立的是綁定目前草稿版本的空白預測，不在這個端點直接接受預測內容。
    try:
        project = _project(project_id)
        if project is None:
            return _error("PROJECT_NOT_FOUND", 404)
        payload = _json_body(request)
        if payload is None:
            return _error("MALFORMED_JSON", 400)
        if set(payload) != {"expected_draft_version"} or type(
            payload.get("expected_draft_version")
        ) is not int:
            return _error("INVALID_REQUEST", 400)
        prediction = create_prediction(
            project=project,
            actor=request.user,
            expected_draft_version=payload["expected_draft_version"],
        )
        return _prediction_response(prediction, status=201)
    except PredictionError as exc:
        return _service_error(exc)
    except Exception:
        return _error("INTERNAL_ERROR", 500)


@login_required
@require_POST
def prediction_complete(request, project_id, prediction_id):
    # 完成預測前由服務層再次檢查草稿版本、拓撲與揭示狀態，避免答案時序被繞過。
    try:
        project = _project(project_id)
        if project is None:
            return _error("PROJECT_NOT_FOUND", 404)
        if not can_view_project(request.user, project):
            return _error("PROJECT_WRITE_DENIED", 403)
        prediction = Prediction.objects.filter(
            pk=prediction_id, project_id=project.id
        ).first()
        if prediction is None:
            return _error("PREDICTION_NOT_FOUND", 404)
        payload = _json_body(request)
        if payload is None:
            return _error("MALFORMED_JSON", 400)
        if (
            set(payload) != {"expected_draft_version", "payload"}
            or type(payload.get("expected_draft_version")) is not int
            or not isinstance(payload.get("payload"), dict)
        ):
            return _error("INVALID_REQUEST", 400)
        prediction = complete_prediction(
            prediction=prediction,
            actor=request.user,
            expected_draft_version=payload["expected_draft_version"],
            payload=payload["payload"],
        )
        return _prediction_response(prediction)
    except PredictionError as exc:
        return _service_error(exc)
    except Exception:
        return _error("INTERNAL_ERROR", 500)


@login_required
@require_GET
def prediction_detail(request, project_id, prediction_id):
    # 詳細資料可供預測頁恢復草稿；是否可編輯仍由回應狀態與服務層規則決定。
    try:
        project = _project(project_id)
        if project is None:
            return _error("PROJECT_NOT_FOUND", 404)
        if not can_view_project(request.user, project):
            return _error("PROJECT_READ_DENIED", 403)
        prediction = Prediction.objects.filter(
            pk=prediction_id, project_id=project.id
        ).first()
        if prediction is None:
            return _error("PREDICTION_NOT_FOUND", 404)
        return _prediction_response(prediction)
    except Exception:
        return _error("INTERNAL_ERROR", 500)


@login_required
@require_http_methods(["GET", "POST"])
def reflection_detail(request, project_id, run_id):
    try:
        project = _project(project_id)
        if project is None:
            return _error("PROJECT_NOT_FOUND", 404)
        if not can_view_project(request.user, project):
            return _error("PROJECT_READ_DENIED", 403)
        run = _reflection_run(project, run_id)
        if run is None:
            return _error("PROJECT_NOT_FOUND", 404)
        reflection = Reflection.objects.filter(analysis_run=run).first()
        if request.method == "GET":
            if reflection is None:
                return _error("REFLECTION_NOT_FOUND", 404)
            return _reflection_response(get_reflection_for_read(reflection=reflection, actor=request.user))
        payload = _json_body(request)
        if payload is None:
            return _error("MALFORMED_JSON", 400)
        allowed = {"original_reasoning", "unexpected_results", "next_iteration_intent"}
        if set(payload) - allowed:
            return _error("INVALID_REQUEST", 400)
        if reflection is None:
            reflection = create_reflection(run=run, actor=request.user)
            if payload:
                reflection = update_reflection(reflection=reflection, actor=request.user, fields=payload)
            return _reflection_response(reflection, status=201)
        return _reflection_response(update_reflection(reflection=reflection, actor=request.user, fields=payload))
    except ReflectionError as exc:
        return _reflection_error(exc)
    except Exception:
        return _error("INTERNAL_ERROR", 500)


@login_required
@require_POST
def reflection_complete(request, project_id, run_id):
    try:
        project = _project(project_id)
        if project is None:
            return _error("PROJECT_NOT_FOUND", 404)
        if not can_view_project(request.user, project):
            return _error("PROJECT_READ_DENIED", 403)
        run = _reflection_run(project, run_id)
        if run is None:
            return _error("PROJECT_NOT_FOUND", 404)
        payload = _json_body(request)
        if payload is None:
            return _error("MALFORMED_JSON", 400)
        if payload != {}:
            return _error("INVALID_REQUEST", 400)
        reflection = Reflection.objects.filter(analysis_run=run).first()
        if reflection is None:
            return _error("REFLECTION_NOT_FOUND", 404)
        return _reflection_response(complete_reflection(reflection=reflection, actor=request.user))
    except ReflectionError as exc:
        return _reflection_error(exc)
    except Exception:
        return _error("INTERNAL_ERROR", 500)
