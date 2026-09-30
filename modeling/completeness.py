"""Current-draft reference preflight; canonical snapshots remain strict."""

from .models import Connection, GeometryNode, NodeLoad, PhysicalMember, Support


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
        from .services import _audited_exceptions
        from .topology import find_unrepresented_passes, ordered_member_nodes

        node_rows = list(GeometryNode.objects.filter(project=project).order_by("client_key"))
        nodes = {row.client_key: (row.x_mm, row.y_mm) for row in node_rows}
        members = list(PhysicalMember.objects.filter(project=project).select_related("start_geometry_node", "end_geometry_node"))
        member_rows = [{
            "client_key": row.client_key,
            "start_node_client_key": row.start_geometry_node.client_key if row.start_geometry_node_id else None,
            "end_node_client_key": row.end_geometry_node.client_key if row.end_geometry_node_id else None,
        } for row in members]
        pairs = set(project.member_joint_incidences.values_list("member__client_key", "node__client_key"))
        attached = {key for row in member_rows for key in (row["start_node_client_key"], row["end_node_client_key"]) if key is not None}
        attached.update(node_key for _, node_key in pairs)
        pair_exemptions, exceptions = _audited_exceptions(project, nodes, member_rows)
        by_point = {}
        for node_row in node_rows:
            point = nodes[node_row.client_key]
            for other in by_point.get(point, []):
                if frozenset((node_row.client_key, other)) not in pair_exemptions:
                    add("DUPLICATE_NODE_COORDINATE", "GEOMETRY_NODE", node_row, f"节点 {node_row.client_key} 与 {other} 位于同一位置，但没有经审核的独立身份。")
            by_point.setdefault(point, []).append(node_row.client_key)
        for row, member in zip(member_rows, members):
            if row["start_node_client_key"] is None or row["end_node_client_key"] is None:
                continue
            try:
                ordered_member_nodes(row, nodes, pairs)
            except (KeyError, ValueError):
                add("INVALID_MEMBER_INCIDENCE", "PHYSICAL_MEMBER", member, f"构件 {member.client_key} 的节点参与关系无效。")
        by_key = {row.client_key: row for row in members}
        for member_key, node_key in find_unrepresented_passes(nodes=nodes, members=member_rows, incidences=pairs, exemptions=exceptions):
            member = by_key[member_key]
            add("MEMBER_PASSES_THROUGH_NODE_WITHOUT_INCIDENCE", "PHYSICAL_MEMBER", member, f"构件 {member_key} 穿过节点 {node_key}，但尚未建立参与关系。")
        for support in Support.objects.filter(project=project).order_by("client_key"):
            if support.target_node_id is None:
                add("MISSING_SUPPORT_NODE", "SUPPORT", support, f"支座 {support.client_key} 还没有指定作用位置。")
            elif support.target_node.client_key not in attached:
                add("UNATTACHED_SUPPORT_NODE", "SUPPORT", support, f"支座 {support.client_key} 所在节点尚未参与任何构件。")
        for load in NodeLoad.objects.filter(project=project).order_by("client_key"):
            if load.target_node_id is None:
                add("MISSING_LOAD_NODE", "NODE_LOAD", load, f"荷载 {load.client_key} 还没有指定作用位置。")
            elif load.target_node.client_key not in attached:
                add("UNATTACHED_LOAD_NODE", "NODE_LOAD", load, f"荷载 {load.client_key} 所在节点尚未参与任何构件。")
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
