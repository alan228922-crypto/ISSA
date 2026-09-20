"""M5 Workspace page delivery; persistence and mechanics remain in existing services."""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from modeling.models import Connection, GeometryNode, NodeLoad, PhysicalMember, Support

from .models import Project
from .services import can_view_project


def _draft(project):
    nodes = list(GeometryNode.objects.filter(project=project).order_by("client_key"))
    members = list(
        PhysicalMember.objects.filter(project=project)
        .select_related("start_geometry_node", "end_geometry_node")
        .order_by("client_key")
    )
    connections = list(
        Connection.objects.filter(project=project)
        .prefetch_related("participating_members")
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
                "start_node_client_key": member.start_geometry_node.client_key,
                "end_node_client_key": member.end_geometry_node.client_key,
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
                "geometry_node_client_key": connection.geometry_node.client_key,
                "participating_member_client_keys": list(
                    connection.participating_members.order_by("client_key").values_list("client_key", flat=True)
                ),
            }
            for connection in connections
        ],
        "supports": [
            {
                "client_key": support.client_key,
                "target_connection_client_key": support.target_connection.client_key,
                "support_type": support.support_type,
                "restrained_axis": support.restrained_axis,
            }
            for support in Support.objects.filter(project=project).select_related("target_connection").order_by("client_key")
        ],
        "node_loads": [
            {
                "client_key": load.client_key,
                "target_connection_client_key": load.target_connection.client_key,
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
    }


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
    bootstrap = {
        "schema_version": "workspace-bootstrap-v1",
        "project": {"id": project.id, "name": project.name, "analysis_type": project.analysis_type},
        "draft": _draft(project),
        "read_only": request.user.id != project.owner_user_id,
        "urls": _urls(project),
    }
    return render(request, "projects/workspace.html", {"bootstrap": bootstrap})
