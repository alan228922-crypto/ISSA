from collections import Counter

from django.db.models import Q

from projects.services import can_view_project

from .models import AnalysisRun, ValidationLog
from .results import maximum_displacement_summary


class ReportError(ValueError):
    def __init__(self, code, status_code=400, *, details=None):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.details = details or {}


ASSUMPTIONS = {
    "analysis_type": "TRUSS_2D",
    "kinematics": "2D_LINEAR_ELASTIC_SMALL_DISPLACEMENT",
    "joint_model": "PIN_JOINTED",
    "member_behavior": "AXIAL_ONLY",
    "degrees_of_freedom": ["ux", "uy"],
    "load_model": "NODAL_FX_FY",
    "units": {"length": "mm", "force": "N", "stress": "MPa", "mass": "g"},
}


def _status_block(items, *, required=True):
    if isinstance(items, list):
        return {"status": "READY", "items": items}

    return {
        "status": "MISSING" if required else "NOT_APPLICABLE",
        "items": None,
    }


def _validation_logs(run, revision):
    logs = ValidationLog.objects.filter(
        Q(analysis_run_id=run.id) | Q(model_revision_id=revision.id),
        project_id=run.project_id,
    ).order_by("id")
    return [
        {
            "id": log.id,
            "stage": log.stage,
            "code": log.code,
            "severity": log.severity,
            "category": log.category,
            "entity_refs": log.entity_refs,
            "numeric_context": log.numeric_context,
        }
        for log in logs
    ]


def _materials_sections(snapshot):
    materials = {}
    sections = {}
    for member in snapshot.get("physical_members", []):
        material = member.get("material") or {}
        section = member.get("section") or {}
        material_id = material.get("source_id")
        section_id = section.get("source_id") or section.get("definition_hash")
        if material_id is not None:
            materials.setdefault(material_id, {"id": material_id, **material})
        if section_id is not None:
            sections.setdefault(section_id, {"id": section_id, **section})
    return {
        "materials": list(materials.values()),
        "sections": list(sections.values()),
    }


def _state_summary(member_results):
    return dict(Counter(
        item.get("state")
        for item in member_results
        if isinstance(item, dict) and isinstance(item.get("state"), str)
    ))


def build_report_package(*, run, actor, project=None):
    """Assemble an ephemeral report from one explicit historical AnalysisRun."""
    try:
        run = AnalysisRun.objects.select_related(
            "project__event", "model_revision", "solver_version",
        ).get(pk=run.pk)
    except AnalysisRun.DoesNotExist as exc:
        raise ReportError("PROJECT_NOT_FOUND", 404) from exc

    if project is not None and run.project_id != project.id:
        raise ReportError("PROJECT_NOT_FOUND", 404)
    if not can_view_project(actor, run.project):
        raise ReportError("PROJECT_READ_DENIED", 403)
    if run.status != AnalysisRun.Status.SUCCESS:
        raise ReportError(
            "REPORT_ANALYSIS_NOT_SUCCESS",
            422,
            details={"analysis_run_id": run.id, "analysis_status": run.status},
        )

    revision = run.model_revision
    snapshot = revision.physical_snapshot_json
    solver_input = run.solver_input_json
    result = run.result_json if isinstance(run.result_json, dict) else {}
    member_results = result.get("member_results")
    node_displacements = result.get("node_displacements")
    support_reactions = result.get("support_reactions")
    current_draft_version = run.project.draft_version
    source_draft_version = revision.source_draft_version
    validation_logs = _validation_logs(run, revision)
    material_section_data = _materials_sections(snapshot)

    return {
        "metadata": {
            "project_id": run.project_id,
            "project_name": run.project.name,
            "event_id": run.project.event_id,
            "event_code": run.project.event.event_code,
            "analysis_run_id": run.id,
            "analysis_status": run.status,
            "model_revision_id": revision.id,
            "source_draft_version": source_draft_version,
            "model_hash": revision.model_hash,
            "solver_version": run.solver_version.solver_version,
            "input_schema_version": run.input_schema_version,
            "result_schema_version": run.result_schema_version,
            "generated_at": run.finished_at.isoformat() if run.finished_at else None,
        },
        "assumptions": ASSUMPTIONS,
        "materials_sections": {
            "status": "READY",
            "materials": material_section_data["materials"],
            "sections": material_section_data["sections"],
            "items": material_section_data["materials"] + material_section_data["sections"],
        },
        "geometry_connectivity": {
            "status": "READY",
            "nodes": snapshot.get("nodes"),
            "physical_members": snapshot.get("physical_members"),
            "connections": snapshot.get("connections"),
            "analysis_member_mapping": solver_input.get("physical_member_mapping"),
        },
        "supports_loads": {
            "status": "READY",
            "supports": snapshot.get("supports"),
            "loads": snapshot.get("node_loads"),
        },
        "results_summary": {
            "status": "READY",
            "maximum_displacement": maximum_displacement_summary(result),
            "state_counts": _state_summary(member_results or []),
            "total_mass_g": result.get("total_mass_g"),
            "result_schema_version": run.result_schema_version,
        },
        "node_results": {
            "status": "READY" if isinstance(node_displacements, list) and isinstance(support_reactions, list) else "MISSING",
            "items": node_displacements if isinstance(node_displacements, list) and isinstance(support_reactions, list) else None,
            "support_reactions": support_reactions if isinstance(support_reactions, list) else None,
        },
        "member_results": _status_block(member_results),
        "validation_limitations": {
            "status": "READY",
            "analysis_status": run.status,
            "failure_code": run.failure_code,
            "diagnostics": run.diagnostics_json,
            "validation_logs": validation_logs,
            "euler": {"status": "UNAVAILABLE"},
            "professional_code_review": {"status": "NOT_APPLICABLE"},
        },
        "provenance": {
            "analysis_run_id": run.id,
            "model_revision_id": revision.id,
            "source_draft_version": source_draft_version,
            "current_draft_version": current_draft_version,
            "model_hash": revision.model_hash,
            "input_hash": run.input_hash,
            "solver_version": run.solver_version.solver_version,
            "is_stale": current_draft_version != source_draft_version,
        },
    }
