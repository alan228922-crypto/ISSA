"""M5 Workspace page delivery; persistence and mechanics remain in existing services."""

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from modeling.models import Connection, GeometryNode, NodeLoad, PhysicalMember, Support
from materials.models import Material, Section

from .models import Project
from .services import can_view_project


def _draft(project):
    if project.draft_schema_version == "physical-draft-v2":
        from modeling.serialization import serialize_draft_v2

        return serialize_draft_v2(project)
    nodes = list(GeometryNode.objects.filter(project=project).order_by("client_key"))
    members = list(
        PhysicalMember.objects.filter(project=project)
        .select_related("start_geometry_node", "end_geometry_node")
        .order_by("client_key")
    )
    connections = list(
        Connection.objects.filter(project=project)
        .prefetch_related("participation_slots__member")
        .order_by("client_key")
    )
    return {
        "schema_version": "physical-draft-v1",
        "version": project.draft_version,
        "nodes": [
            {"client_key": node.client_key, "x_mm": node.x_mm, "y_mm": node.y_mm, "label": node.label}
            for node in nodes
        ],
        "physical_members": [
            {
                "client_key": member.client_key,
                "start_node_client_key": member.start_geometry_node.client_key if member.start_geometry_node_id else None,
                "end_node_client_key": member.end_geometry_node.client_key if member.end_geometry_node_id else None,
                "material_id": member.material_id,
                "section_id": member.section_id,
                "label": member.label,
                "is_active": member.is_active,
            }
            for member in members
        ],
        "connections": [
            {
                "client_key": connection.client_key,
                "geometry_node_client_key": connection.geometry_node.client_key if connection.geometry_node_id else None,
                "participating_member_client_keys": [
                    slot.member.client_key if slot.member_id else None
                    for slot in connection.participation_slots.all()
                ],
            }
            for connection in connections
        ],
        "supports": [
            {
                "client_key": support.client_key,
                "target_connection_client_key": support.target_connection.client_key if support.target_connection_id else None,
                "support_type": support.support_type,
                "restrained_axis": support.restrained_axis,
            }
            for support in Support.objects.filter(project=project).select_related("target_connection").order_by("client_key")
        ],
        "node_loads": [
            {
                "client_key": load.client_key,
                "target_connection_client_key": load.target_connection.client_key if load.target_connection_id else None,
                "fx_N": load.fx_N,
                "fy_N": load.fy_N,
                "label": load.label,
            }
            for load in NodeLoad.objects.filter(project=project).select_related("target_connection").order_by("client_key")
        ],
    }


def _urls(project):
    project_id = project.id
    base = f"/projects/{project_id}"
    return {
        "save": reverse("projects:model_save", kwargs={"project_id": project_id}),
        "check": reverse("projects:model_check", kwargs={"project_id": project_id}),
        "prediction_current": f"{base}/predictions/current/",
        "prediction_create": reverse("learning:prediction_create", kwargs={"project_id": project_id}),
        "prediction_complete_template": f"{base}/predictions/{{prediction_id}}/complete/",
        "analyze": reverse("projects:analyze", kwargs={"project_id": project_id}),
        "analysis_runs": reverse("projects:analysis_runs", kwargs={"project_id": project_id}),
        "result_template": f"{base}/analyses/{{run_id}}/data/",
        "report_template": f"{base}/analyses/{{run_id}}/report/",
        "reasoning_template": f"{base}/analyses/{{run_id}}/reasoning/",
        "comparison_template": f"{base}/analyses/{{run_id}}/comparison/",
        "explanation_template": f"{base}/analyses/{{run_id}}/explanation/",
        "reflection_template": f"{base}/analyses/{{run_id}}/reflection/",
        "reflection_complete_template": f"{base}/analyses/{{run_id}}/reflection/complete/",
        "materials": reverse("materials:index", kwargs={"project_id": project_id}),
    }


def _available_materials(owner):
    return [
        {
            "id": material.id,
            "name": material.name,
            "E_MPa": float(material.E_MPa),
            "density_g_per_mm3": (
                float(material.density_g_per_mm3) if material.density_g_per_mm3 is not None else None
            ),
        }
        for material in Material.objects.filter(owner_user=owner).order_by("name", "id")
    ]


def _available_sections(owner):
    return [
        {
            "id": section.id,
            "name": section.name,
            "section_type": section.section_type,
            "A_mm2": section.properties_json.get("A_mm2"),
            "Ix_mm4": section.properties_json.get("Ix_mm4"),
            "Iy_mm4": section.properties_json.get("Iy_mm4"),
        }
        for section in Section.objects.filter(owner_user=owner).order_by("name", "id")
    ]


@login_required
@require_GET
def workspace(request, project_id):
    project = Project.objects.select_related("event", "owner_user").filter(pk=project_id).first()
    if (
        project is None
        or project.analysis_type != Project.AnalysisType.TRUSS_2D
        or not can_view_project(request.user, project)
    ):
        raise Http404
    blocked_audit = project.draft_migration_audits.filter(status="BLOCKED").order_by("-created_at", "-pk").first()
    read_only = request.user.id != project.owner_user_id or blocked_audit is not None
    bootstrap = {
        "schema_version": "workspace-bootstrap-v1",
        "project": {"id": project.id, "name": project.name, "analysis_type": project.analysis_type},
        "draft": _draft(project),
        "read_only": read_only,
        "migration_blocked": blocked_audit is not None,
        "access": {
            "current_user": {"id": request.user.id, "username": request.user.username, "role": request.user.role},
            "owner": {"id": project.owner_user_id, "username": project.owner_user.username},
            "event": {"id": project.event_id, "name": project.event.name},
            "editable": not read_only,
            "read_only_reason": (f"旧模型转换已暂停：{blocked_audit.reason_code}。请先导出并核对旧草稿。" if blocked_audit else "你正在以只读身份查看此项目。" if read_only else ""),
        },
        "materials": _available_materials(project.owner_user),
        "sections": _available_sections(project.owner_user),
        "urls": _urls(project),
    }
    if blocked_audit:
        bootstrap["urls"]["legacy_export"] = reverse("projects:legacy_draft_export", kwargs={"project_id": project.id})
    return render(request, "projects/workspace.html", {"bootstrap": bootstrap})


@login_required
@require_GET
def legacy_draft_export(request, project_id):
    project = Project.objects.select_related("event", "owner_user").filter(pk=project_id).first()
    if project is None or not can_view_project(request.user, project):
        raise Http404
    audit = project.draft_migration_audits.filter(status="BLOCKED").order_by("-created_at", "-pk").first()
    if audit is None:
        raise Http404
    return JsonResponse({
        "schema_version": "legacy-draft-recovery-v1",
        "project_id": project.pk,
        "source_draft_version": audit.source_draft_version,
        "source_hash": audit.source_hash,
        "source_payload": audit.source_payload_json,
        "reason_code": audit.reason_code,
    }, json_dumps_params={"ensure_ascii": False})
