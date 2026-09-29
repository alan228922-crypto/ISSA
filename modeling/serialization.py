"""Schema-specific editable Draft serialization; no inferred topology."""

from .models import GeometryNode, MemberJointIncidence, NodeLoad, PhysicalMember, Support


def serialize_draft_v2(project):
    nodes = GeometryNode.objects.filter(project=project).order_by("client_key")
    members = PhysicalMember.objects.filter(project=project).select_related("start_geometry_node", "end_geometry_node").order_by("client_key")
    incidences = MemberJointIncidence.objects.filter(project=project).select_related("member", "node").order_by("member__client_key", "node__client_key")
    return {
        "schema_version": "physical-draft-v2",
        "version": project.draft_version,
        "nodes": [{"client_key": node.client_key, "x_mm": node.x_mm, "y_mm": node.y_mm, "label": node.label} for node in nodes],
        "physical_members": [{
            "client_key": member.client_key,
            "start_node_client_key": member.start_geometry_node.client_key if member.start_geometry_node_id else None,
            "end_node_client_key": member.end_geometry_node.client_key if member.end_geometry_node_id else None,
            "material_id": member.material_id,
            "section_id": member.section_id,
            "label": member.label,
            "is_active": member.is_active,
        } for member in members],
        "member_joint_incidences": [{"member_client_key": row.member.client_key, "node_client_key": row.node.client_key} for row in incidences],
        "supports": [{
            "client_key": support.client_key,
            "target_node_client_key": support.target_node.client_key if support.target_node_id else None,
            "support_type": support.support_type,
            "restrained_axis": support.restrained_axis,
        } for support in Support.objects.filter(project=project).select_related("target_node").order_by("client_key")],
        "node_loads": [{
            "client_key": load.client_key,
            "target_node_client_key": load.target_node.client_key if load.target_node_id else None,
            "fx_N": load.fx_N,
            "fy_N": load.fy_N,
            "label": load.label,
        } for load in NodeLoad.objects.filter(project=project).select_related("target_node").order_by("client_key")],
    }
