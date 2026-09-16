"""Prediction JSON endpoints adapt HTTP to the existing lifecycle services."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from projects.models import Project
from projects.services import can_view_project

from .models import Prediction
from .services import PredictionError, complete_prediction, create_prediction


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


@login_required
@require_POST
def prediction_create(request, project_id):
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
    try:
        prediction = create_prediction(
            project=project,
            actor=request.user,
            expected_draft_version=payload["expected_draft_version"],
        )
    except PredictionError as exc:
        return _service_error(exc)
    except Exception:
        return _error("INTERNAL_ERROR", 500)
    return _prediction_response(prediction, status=201)


@login_required
@require_POST
def prediction_complete(request, project_id, prediction_id):
    project = _project(project_id)
    if project is None:
        return _error("PROJECT_NOT_FOUND", 404)
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
    try:
        prediction = complete_prediction(
            prediction=prediction,
            actor=request.user,
            expected_draft_version=payload["expected_draft_version"],
            payload=payload["payload"],
        )
    except PredictionError as exc:
        return _service_error(exc)
    except Exception:
        return _error("INTERNAL_ERROR", 500)
    return _prediction_response(prediction)


@login_required
@require_GET
def prediction_detail(request, project_id, prediction_id):
    project = _project(project_id)
    if project is None:
        return _error("PROJECT_NOT_FOUND", 404)
    prediction = Prediction.objects.filter(
        pk=prediction_id, project_id=project.id
    ).first()
    if prediction is None:
        return _error("PREDICTION_NOT_FOUND", 404)
    if not can_view_project(request.user, project):
        return _error("PROJECT_READ_DENIED", 403)
    return _prediction_response(prediction)
