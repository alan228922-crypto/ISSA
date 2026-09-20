"""Prediction evidence validation and lifecycle; deliberately independent of mechanics."""

from time import sleep

from django.db import IntegrityError, OperationalError, transaction
from django.utils import timezone

from accounts.models import User
from analysis.models import AnalysisRun
from competitions.models import CompetitionEvent, EventMembership
from modeling.models import Connection, PhysicalMember
from projects.models import Project
from projects.services import can_modify_project, can_view_project

from .comparison import ComparisonError, build_comparison
from .explanation import ExplanationError, build_explanation
from .models import CalculationReportReasoning, Prediction, Reflection, StudentResultReveal


class PredictionError(ValueError):
    def __init__(self, code, status_code=400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class DisclosureError(ValueError):
    """Stable HTTP-facing failures for derived result disclosure."""

    def __init__(self, code, status_code):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class ReflectionError(ValueError):
    def __init__(self, code, status_code=400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class ReasoningError(ValueError):
    def __init__(self, code, status_code=400):
        super().__init__(code); self.code = code; self.status_code = status_code


REASONING_FIELDS = {"modeling_rationale", "material_section_rationale", "support_load_rationale", "result_interpretation", "design_change_rationale", "scheme_comparison", "final_conclusion"}


def _authorize_reasoning_author(project, actor):
    if not can_modify_project(actor, project) or actor.id != project.owner_user_id or actor.role in {User.Role.MANAGER, User.Role.DEVELOPER}:
        raise ReasoningError("REASONING_WRITE_DENIED", 403)


def reasoning_for_run(*, run, actor):
    if run.status != AnalysisRun.Status.SUCCESS: raise ReasoningError("REASONING_RUN_NOT_SUCCESS", 422)
    if actor.id != run.project.owner_user_id: raise ReasoningError("REASONING_READ_DENIED", 403)
    return CalculationReportReasoning.objects.filter(analysis_run=run).first()


def save_reasoning(*, run, actor, fields):
    if run.status != AnalysisRun.Status.SUCCESS: raise ReasoningError("REASONING_RUN_NOT_SUCCESS", 422)
    if not isinstance(fields, dict) or set(fields) - REASONING_FIELDS or any(not isinstance(value, str) or len(value) > 5000 for value in fields.values()): raise ReasoningError("REASONING_INVALID_FIELDS", 422)
    with transaction.atomic():
        project = Project.objects.select_for_update().select_related("event").get(pk=run.project_id)
        _authorize_reasoning_author(project, actor)
        reasoning, _ = CalculationReportReasoning.objects.get_or_create(analysis_run=run, defaults={"created_by": actor})
        for field, value in fields.items(): setattr(reasoning, field, value)
        reasoning.save(update_fields=[*fields, "updated_at"])
        return reasoning


_STATES = {"TENSION", "COMPRESSION", "ZERO_FORCE", "UNSURE"}
_PREDICTION_LOCK_RETRY_ATTEMPTS = 5


def _schema_error():
    raise PredictionError("PREDICTION_INVALID_SCHEMA", 400)


def _string(value):
    return isinstance(value, str) and bool(value)


def _only_keys(value, allowed, error):
    if not isinstance(value, dict) or set(value) - allowed:
        raise PredictionError(error, 400)


def _display(value, allowed):
    _only_keys(value, allowed, "PREDICTION_INVALID_SCHEMA")
    if any(not _string(item) for item in value.values()):
        _schema_error()


def _member_judgments(project, payload):
    judgments = payload.get("member_judgments")
    if not isinstance(judgments, list):
        _schema_error()
    keys = []
    for judgment in judgments:
        _only_keys(
            judgment,
            {"physical_member_client_key", "predicted_state", "display"},
            "PREDICTION_INVALID_SCHEMA",
        )
        if "display" in judgment:
            _display(judgment["display"], {"member_label"})
        key = judgment.get("physical_member_client_key")
        if not _string(key) or judgment.get("predicted_state") not in _STATES:
            _schema_error()
        keys.append(key)

    active_keys = set(
        PhysicalMember.objects.filter(project=project, is_active=True).values_list("client_key", flat=True)
    )
    if len(keys) != len(set(keys)) or set(keys) != active_keys:
        raise PredictionError("PREDICTION_INCOMPLETE", 400)


def _topology(project):
    members = {
        member.client_key: member
        for member in PhysicalMember.objects.filter(project=project).select_related(
            "start_geometry_node", "end_geometry_node"
        )
    }
    connections = {
        connection.client_key: connection
        for connection in Connection.objects.filter(project=project).prefetch_related("participating_members")
    }
    return members, connections


def _is_incident(connection, member):
    return (
        member in connection.participating_members.all()
        and connection.geometry_node_id in {
            member.start_geometry_node_id,
            member.end_geometry_node_id,
        }
    )


def _physical_point(point, members, connections):
    if not isinstance(point, dict):
        _schema_error()
    kind = point.get("kind")
    if kind == "CONNECTION":
        _only_keys(point, {"kind", "connection_client_key", "display"}, "PREDICTION_INVALID_SCHEMA")
        if "display" in point:
            _display(point["display"], {"geometry_node_client_key", "geometry_node_label"})
        key = point.get("connection_client_key")
        if not _string(key) or key not in connections:
            raise PredictionError("INVALID_PHYSICAL_POINT_REF", 400)
        return ("connection", key)
    if kind != "MEMBER_ENDPOINT":
        _schema_error()

    _only_keys(
        point,
        {"kind", "physical_member_client_key", "endpoint", "display"},
        "PREDICTION_INVALID_SCHEMA",
    )
    if "display" in point:
        _display(
            point["display"],
            {"member_label", "geometry_node_client_key", "geometry_node_label"},
        )
    key, endpoint = point.get("physical_member_client_key"), point.get("endpoint")
    if not _string(key) or endpoint not in {"START", "END"} or key not in members:
        raise PredictionError("INVALID_PHYSICAL_POINT_REF", 400)
    member = members[key]
    node_id = member.start_geometry_node_id if endpoint == "START" else member.end_geometry_node_id
    if any(_is_incident(connection, member) and connection.geometry_node_id == node_id for connection in connections.values()):
        raise PredictionError("INVALID_PHYSICAL_POINT_REF", 400)
    return ("free", key, endpoint)


def _load_path(path, members, connections):
    if not isinstance(path, list) or len(path) < 3 or len(path) % 2 == 0:
        raise PredictionError("INVALID_LOAD_PATH", 400)
    entities = []
    for index, item in enumerate(path):
        expected_kind = "CONNECTION" if index % 2 == 0 else "PHYSICAL_MEMBER"
        key_name = "connection_client_key" if expected_kind == "CONNECTION" else "physical_member_client_key"
        _only_keys(item, {"kind", key_name}, "INVALID_LOAD_PATH")
        if item.get("kind") != expected_kind:
            raise PredictionError("INVALID_LOAD_PATH", 400)
        key = item.get(key_name)
        lookup = connections if expected_kind == "CONNECTION" else members
        if not _string(key) or key not in lookup:
            raise PredictionError("INVALID_LOAD_PATH", 400)
        entities.append((expected_kind, key))
    if len(entities) != len(set(entities)):
        raise PredictionError("INVALID_LOAD_PATH", 400)
    for index in range(1, len(entities), 2):
        member = members[entities[index][1]]
        if not _is_incident(connections[entities[index - 1][1]], member):
            raise PredictionError("INVALID_LOAD_PATH", 400)
        if not _is_incident(connections[entities[index + 1][1]], member):
            raise PredictionError("INVALID_LOAD_PATH", 400)


def validate_prediction_payload(project, payload):
    """Validate only stored prediction-v1 shape and physical topology."""
    # 預測記錄的是學生看得到的物理構件，不直接使用 Solver 內部切出的分析節點。
    if not isinstance(payload, dict) or payload.get("schema_version") != "prediction-v1":
        _schema_error()
    _only_keys(
        payload,
        {
            "schema_version",
            "member_judgments",
            "max_displacement_location",
            "representative_load_path",
        },
        "PREDICTION_INVALID_SCHEMA",
    )
    _member_judgments(project, payload)
    members, connections = _topology(project)
    _physical_point(payload.get("max_displacement_location"), members, connections)
    _load_path(payload.get("representative_load_path"), members, connections)
    return payload


def _authorize_student_owner(project, actor):
    """Prediction evidence belongs only to the active participant who owns the Project."""
    if (
        project.event.status == CompetitionEvent.Status.PURGED
        or actor.role in {User.Role.MANAGER, User.Role.DEVELOPER}
        or actor.id != project.owner_user_id
        or not EventMembership.objects.filter(
            user=actor,
            event_id=project.event_id,
            membership_type=EventMembership.Type.PARTICIPANT,
            is_active=True,
        ).exists()
    ):
        raise PredictionError("PROJECT_WRITE_DENIED", 403)


def _authorize_reflection_author(project, actor):
    if project.event.status != CompetitionEvent.Status.ACTIVE:
        raise ReflectionError("REFLECTION_EVENT_NOT_ACTIVE", 403)
    if (
        actor.role in {User.Role.MANAGER, User.Role.DEVELOPER}
        or actor.id != project.owner_user_id
        or not EventMembership.objects.filter(
            user=actor,
            event_id=project.event_id,
            membership_type=EventMembership.Type.PARTICIPANT,
            is_active=True,
        ).exists()
    ):
        raise ReflectionError("REFLECTION_WRITE_DENIED", 403)


def _locked_reflection(reflection):
    try:
        project = Project.objects.select_for_update().select_related("event").get(
            pk=reflection.analysis_run.project_id
        )
        reflection = Reflection.objects.select_for_update().get(pk=reflection.pk, analysis_run__project=project)
    except Reflection.DoesNotExist as exc:
        raise ReflectionError("REFLECTION_NOT_FOUND", 404) from exc
    return project, reflection


def create_reflection(*, run, actor):
    # 只有分析成功且學生已看過結果後，才可以建立反思，避免提前看到答案。
    with transaction.atomic():
        try:
            run = AnalysisRun.objects.select_related("project__event", "model_revision").get(
                pk=run.pk,
                project=run.project,
                model_revision__project=run.project,
            )
        except AnalysisRun.DoesNotExist as exc:
            raise ReflectionError("REFLECTION_NOT_FOUND", 404) from exc
        project = Project.objects.select_for_update().select_related("event").get(pk=run.project_id)
        _authorize_reflection_author(project, actor)
        if run.status != AnalysisRun.Status.SUCCESS:
            raise ReflectionError("REFLECTION_RUN_NOT_SUCCESS", 422)
        if not StudentResultReveal.objects.filter(
            project=project,
            source_draft_version=run.model_revision.source_draft_version,
        ).exists():
            raise ReflectionError("REFLECTION_NOT_ELIGIBLE", 422)
        if Reflection.objects.filter(analysis_run=run).exists():
            raise ReflectionError("REFLECTION_ALREADY_EXISTS", 409)
        return Reflection.objects.create(analysis_run=run, created_by=actor)


def update_reflection(*, reflection, actor, fields):
    # 反思在草稿狀態可以修改；完成後鎖定，保留學生當時的學習紀錄。
    allowed = {"original_reasoning", "unexpected_results", "next_iteration_intent"}
    if not isinstance(fields, dict) or set(fields) - allowed or any(
        not isinstance(value, str) or len(value) > 2000 for value in fields.values()
    ):
        raise ReflectionError("REFLECTION_INVALID_FIELDS", 422)
    with transaction.atomic():
        project, reflection = _locked_reflection(reflection)
        _authorize_reflection_author(project, actor)
        if reflection.status == Reflection.Status.COMPLETED:
            raise ReflectionError("REFLECTION_ALREADY_COMPLETED", 409)
        if reflection.status != Reflection.Status.DRAFT:
            raise ReflectionError("REFLECTION_NOT_DRAFT", 409)
        for field, value in fields.items():
            setattr(reflection, field, value)
        reflection.save(update_fields=[*fields, "updated_at"])
        return reflection


def complete_reflection(*, reflection, actor):
    # 完成反思時會檢查三段文字是否填好，並記錄完成時間。
    with transaction.atomic():
        project, reflection = _locked_reflection(reflection)
        _authorize_reflection_author(project, actor)
        if reflection.status == Reflection.Status.COMPLETED:
            raise ReflectionError("REFLECTION_ALREADY_COMPLETED", 409)
        if reflection.status != Reflection.Status.DRAFT:
            raise ReflectionError("REFLECTION_NOT_DRAFT", 409)
        if any(not getattr(reflection, field).strip() for field in (
            "original_reasoning", "unexpected_results", "next_iteration_intent",
        )):
            raise ReflectionError("REFLECTION_INCOMPLETE", 422)
        reflection.status = Reflection.Status.COMPLETED
        reflection.completed_at = timezone.now()
        reflection.save(update_fields=["status", "completed_at", "updated_at"])
        return reflection


def get_reflection_for_read(*, reflection, actor):
    try:
        reflection = Reflection.objects.select_related("analysis_run__project").get(pk=reflection.pk)
    except Reflection.DoesNotExist as exc:
        raise ReflectionError("REFLECTION_NOT_FOUND", 404) from exc
    project = reflection.analysis_run.project
    if actor.id == project.owner_user_id:
        return reflection
    if reflection.status == Reflection.Status.COMPLETED and can_view_project(actor, project):
        return reflection
    raise ReflectionError("REFLECTION_READ_DENIED", 403)


def _current_predictions(project):
    return list(Prediction.objects.filter(
        project=project, source_draft_version=project.draft_version,
    ).order_by("id"))


def discover_current_prediction(project, actor=None):
    """Return the sole current-draft Prediction, or fail closed on ambiguity."""
    predictions = _current_predictions(project)
    if not predictions:
        return {"state": "NONE", "source_draft_version": project.draft_version}
    if len(predictions) != 1 or predictions[0].status not in {Prediction.Status.DRAFT, Prediction.Status.COMPLETED}:
        raise PredictionError("PREDICTION_AMBIGUOUS", 409)
    return {"state": predictions[0].status, "prediction": predictions[0]}


def _create_prediction_once(*, project, actor, expected_draft_version):
    with transaction.atomic():
        project = Project.objects.select_for_update().select_related("event").get(pk=project.pk)
        _authorize_student_owner(project, actor)
        if project.draft_version != expected_draft_version:
            raise PredictionError("PREDICTION_STALE_DRAFT", 409)
        current = discover_current_prediction(project)
        if current["state"] != "NONE":
            current["prediction"]._created_for_current_draft = False
            return current["prediction"]
        try:
            with transaction.atomic():
                prediction = Prediction.objects.create(
                    project=project,
                    source_draft_version=project.draft_version,
                    created_by=actor,
                    prediction_schema_version="prediction-v1",
                    payload_json={},
                )
                prediction._created_for_current_draft = True
                return prediction
        except IntegrityError:
            current = discover_current_prediction(project)
            if current["state"] == "NONE":
                raise
            current["prediction"]._created_for_current_draft = False
            return current["prediction"]


def create_prediction(*, project, actor, expected_draft_version):
    """Create or resume the sole server-bound Prediction for the current draft."""
    for attempt in range(_PREDICTION_LOCK_RETRY_ATTEMPTS):
        try:
            return _create_prediction_once(project=project, actor=actor, expected_draft_version=expected_draft_version)
        except OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == _PREDICTION_LOCK_RETRY_ATTEMPTS - 1:
                raise
            sleep(0.05 * (attempt + 1))


def complete_prediction(*, prediction, actor, expected_draft_version, payload):
    """Atomically validate and complete a current, unrevealed prediction draft."""
    # 完成預測前會再次確認模型版本、結果是否已揭示，以及構件是否仍然存在。
    error_code = None
    with transaction.atomic():
        project = Project.objects.select_for_update().select_related("event").get(pk=prediction.project_id)
        prediction = Prediction.objects.select_for_update().get(pk=prediction.pk, project=project)
        _authorize_student_owner(project, actor)

        if prediction.status == Prediction.Status.COMPLETED:
            raise PredictionError("PREDICTION_ALREADY_COMPLETED", 409)
        if prediction.status == Prediction.Status.INVALIDATED:
            raise PredictionError("PREDICTION_INVALIDATED", 409)
        if prediction.source_draft_version != project.draft_version:
            prediction.status = Prediction.Status.INVALIDATED
            prediction.invalidated_at = timezone.now()
            prediction.invalidation_code = "PREDICTION_STALE_DRAFT"
            prediction.save(update_fields=["status", "invalidated_at", "invalidation_code"])
            error_code = "PREDICTION_STALE_DRAFT"
        elif expected_draft_version != project.draft_version:
            raise PredictionError("PREDICTION_STALE_DRAFT", 409)
        elif StudentResultReveal.objects.filter(
            project=project, source_draft_version=prediction.source_draft_version
        ).exists():
            raise PredictionError("PREDICTION_AFTER_RESULT_REVEAL", 409)
        else:
            prediction.payload_json = validate_prediction_payload(project, payload)
            prediction.status = Prediction.Status.COMPLETED
            prediction.completed_at = timezone.now()
            prediction.save(update_fields=["payload_json", "status", "completed_at"])
    if error_code:
        raise PredictionError(error_code, 409)
    return prediction


def record_student_result_reveal(*, project, run, actor) -> StudentResultReveal | None:
    """Record first owner disclosure for the successful Run's source draft."""
    with transaction.atomic():
        project = Project.objects.select_for_update().select_related("event").get(pk=project.pk)
        if not can_view_project(actor, project):
            raise PredictionError("PROJECT_READ_DENIED", 403)
        try:
            run = AnalysisRun.objects.select_related("model_revision").get(
                pk=run.pk, project=project, model_revision__project=project,
            )
        except AnalysisRun.DoesNotExist as exc:
            raise PredictionError("PROJECT_NOT_FOUND", 404) from exc
        if actor.role in {User.Role.MANAGER, User.Role.DEVELOPER}:
            return None
        _authorize_student_owner(project, actor)
        if run.status != AnalysisRun.Status.SUCCESS:
            return None
        reveal, _ = StudentResultReveal.objects.get_or_create(
            project=project,
            source_draft_version=run.model_revision.source_draft_version,
            defaults={"first_analysis_run": run, "revealed_to_user": actor},
        )
        return reveal


def _record_reveal_after_derivation(*, project, run, actor):
    """Commit the existing owner-only reveal evidence before returning facts."""
    try:
        record_student_result_reveal(project=project, run=run, actor=actor)
    except PredictionError as exc:
        raise DisclosureError(exc.code, exc.status_code) from exc
    except Exception as exc:
        raise DisclosureError("RESULT_REVEAL_FAILED", 500) from exc


def comparison_for_disclosure(*, project, run, actor):
    """Derive comparison facts, then record owner disclosure atomically before return."""
    if run.status != AnalysisRun.Status.SUCCESS:
        raise DisclosureError("ANALYSIS_NOT_SUCCESS", 422)
    try:
        comparison = build_comparison(run=run)
    except ComparisonError as exc:
        raise DisclosureError(exc.code, 409) from exc
    _record_reveal_after_derivation(project=project, run=run, actor=actor)
    return comparison


def explanation_for_disclosure(*, project, run, actor):
    """Derive explanation facts, then record owner disclosure before return."""
    if run.status != AnalysisRun.Status.SUCCESS:
        raise DisclosureError("ANALYSIS_NOT_SUCCESS", 422)
    try:
        explanation = build_explanation(run=run)
    except ExplanationError as exc:
        raise DisclosureError(exc.code, 409) from exc
    _record_reveal_after_derivation(project=project, run=run, actor=actor)
    return explanation
