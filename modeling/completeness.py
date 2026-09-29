"""Current-draft reference preflight; canonical snapshots remain strict."""

from .models import Connection, NodeLoad, PhysicalMember, Support


def draft_completeness_issues(project):
    """Return actionable missing-reference issues without building a snapshot."""
    issues = []

    def add(code, kind, obj, message):
        issues.append({
            "code": code,
            "severity": "ERROR",
            "stage": "DRAFT",
            "entity_refs": [f"{kind.lower()}:{obj.client_key}"],
            "human_message": message,
            "physical_object": {"kind": kind, "client_key": obj.client_key},
        })

    for member in PhysicalMember.objects.filter(project=project).order_by("client_key"):
        name = member.label.strip() or member.client_key
        if member.start_geometry_node_id is None:
            add("MISSING_MEMBER_START_NODE", "PHYSICAL_MEMBER", member, f"构件 {name} 还没有起点，请重新指定节点。")
        if member.end_geometry_node_id is None:
            add("MISSING_MEMBER_END_NODE", "PHYSICAL_MEMBER", member, f"构件 {name} 还没有终点，请重新指定节点。")
        if member.material_id is None:
            add("MISSING_MEMBER_MATERIAL", "PHYSICAL_MEMBER", member, f"构件 {name} 还没有选择材料。")
        if member.section_id is None:
            add("MISSING_MEMBER_SECTION", "PHYSICAL_MEMBER", member, f"构件 {name} 还没有选择截面。")

    if project.draft_schema_version == "physical-draft-v2":
        for support in Support.objects.filter(project=project).order_by("client_key"):
            if support.target_node_id is None:
                add("MISSING_SUPPORT_NODE", "SUPPORT", support, f"支座 {support.client_key} 还没有指定作用位置。")
        for load in NodeLoad.objects.filter(project=project).order_by("client_key"):
            if load.target_node_id is None:
                add("MISSING_LOAD_NODE", "NODE_LOAD", load, f"荷载 {load.client_key} 还没有指定作用位置。")
        return issues

    for connection in Connection.objects.filter(project=project).prefetch_related("participation_slots").order_by("client_key"):
        if connection.geometry_node_id is None:
            add("MISSING_CONNECTION_NODE", "CONNECTION", connection, f"连接 {connection.client_key} 还没有指定位置节点。")
        if any(slot.member_id is None for slot in connection.participation_slots.all()):
            add("MISSING_CONNECTION_PARTICIPANT", "CONNECTION", connection, f"连接 {connection.client_key} 还有参与构件需要重新指定。")

    for support in Support.objects.filter(project=project).select_related("target_connection").order_by("client_key"):
        if support.target_connection_id is None or support.target_connection.geometry_node_id is None:
            add("MISSING_SUPPORT_NODE", "SUPPORT", support, f"支座 {support.client_key} 还没有指定作用位置。")
    for load in NodeLoad.objects.filter(project=project).select_related("target_connection").order_by("client_key"):
        if load.target_connection_id is None or load.target_connection.geometry_node_id is None:
            add("MISSING_LOAD_NODE", "NODE_LOAD", load, f"荷载 {load.client_key} 还没有指定作用位置。")
    return issues
