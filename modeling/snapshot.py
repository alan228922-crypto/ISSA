"""从 mutable ORM draft 生成纯 physical-snapshot-v1。"""

from .completeness import draft_completeness_issues

# ============================================================
# 檔案閱讀指南
#
# 這個檔案把資料庫中的 mutable draft 讀出來，整理成單純的 Python 字典。
# 這份字典包含節點、物理構件、連接點、支承、荷載、材料和截面數值。
# 它是 Revision 和 Solver 之間的資料邊界：之後材料或截面被修改，舊 Snapshot 仍不變。
# ============================================================

# 閱讀提示：snapshot 是目前草稿的固定副本，後續分析會使用這份副本。
def build_physical_snapshot(project):
    """冻结数值，避免之后 Material/Section 的修改改变旧 Revision。"""
    if project.draft_schema_version == "physical-draft-v2":
        return _build_physical_snapshot_v2(project)
    if draft_completeness_issues(project):
        raise ValueError("INCOMPLETE_DRAFT")
    # 函數輸入是 ORM Project；輸出是 physical-snapshot-v1 字典，不會建立 Solver 物件。
    # 讀取關聯資料時固定排序，讓相同的設計每次都能產生相同內容，方便產生穩定 hash。
    # 先固定資料順序，確保同一個模型每次產生的 snapshot 都相同。
    nodes=sorted(project.geometry_nodes.all(),key=lambda x:x.client_key)
    members=sorted(project.physical_members.select_related('material','section').all(),key=lambda x:x.client_key)
    connections=sorted(project.connections.prefetch_related('participating_members').all(),key=lambda x:x.client_key)
    return {'schema_version':'physical-snapshot-v1','analysis_type':project.analysis_type,
      'units':{'length':'mm','force':'N','stress':'MPa','mass':'g'},
      'nodes':[{'id':x.client_key,'x_mm':x.x_mm,'y_mm':x.y_mm,'label':x.label} for x in nodes],
      'physical_members':[{'id':x.client_key,'start_node_id':x.start_geometry_node.client_key,'end_node_id':x.end_geometry_node.client_key,'label':x.label,'is_active':x.is_active,
        'material':{'source_id':str(x.material_id),'E_MPa':float(x.material.E_MPa),'density_g_per_mm3':float(x.material.density_g_per_mm3) if x.material.density_g_per_mm3 is not None else None},
        'section':{'source_id':str(x.section_id),'definition_hash':x.section.definition_hash,'A_mm2':x.section.properties_json['A_mm2'],'Ix_mm4':x.section.properties_json['Ix_mm4'],'Iy_mm4':x.section.properties_json['Iy_mm4']}} for x in members],
      'connections':[{'id':x.client_key,'geometry_node_id':x.geometry_node.client_key,'participating_member_ids':sorted(m.client_key for m in x.participating_members.all())} for x in connections],
      'supports':[{'id':x.client_key,'connection_id':x.target_connection.client_key,'support_type':x.support_type,'restrained_axis':x.restrained_axis} for x in sorted(project.supports.select_related('target_connection'),key=lambda x:x.client_key)],
      'node_loads':[{'id':x.client_key,'connection_id':x.target_connection.client_key,'fx_N':x.fx_N,'fy_N':x.fy_N,'label':x.label} for x in sorted(project.node_loads.select_related('target_connection'),key=lambda x:x.client_key)]}


def _build_physical_snapshot_v2(project):
    from .services import _audited_exceptions
    from .topology import find_unrepresented_passes, ordered_member_nodes

    if draft_completeness_issues(project):
        raise ValueError("INCOMPLETE_DRAFT")
    nodes = sorted(project.geometry_nodes.all(), key=lambda row: row.client_key)
    members = sorted(project.physical_members.select_related("start_geometry_node", "end_geometry_node", "material", "section"), key=lambda row: row.client_key)
    incidences = sorted(project.member_joint_incidences.select_related("member", "node"), key=lambda row: (row.member.client_key, row.node.client_key))
    coordinates = {row.client_key: (row.x_mm, row.y_mm) for row in nodes}
    member_rows = [{"client_key": row.client_key, "start_node_client_key": row.start_geometry_node.client_key, "end_node_client_key": row.end_geometry_node.client_key} for row in members]
    pairs = {(row.member.client_key, row.node.client_key) for row in incidences}
    _, exceptions = _audited_exceptions(project, coordinates, member_rows)
    try:
        for row in member_rows:
            ordered_member_nodes(row, coordinates, pairs)
        if find_unrepresented_passes(nodes=coordinates, members=member_rows, incidences=pairs, exemptions=exceptions):
            raise ValueError("INCOMPLETE_DRAFT")
    except (KeyError, ValueError) as exc:
        raise ValueError("INCOMPLETE_DRAFT") from exc
    return {
        "schema_version": "physical-snapshot-v2", "analysis_type": project.analysis_type,
        "units": {"length": "mm", "force": "N", "stress": "MPa", "mass": "g"},
        "nodes": [{"id": row.client_key, "x_mm": row.x_mm, "y_mm": row.y_mm, "label": row.label} for row in nodes],
        "physical_members": [{
            "id": row.client_key,
            "start_node_id": row.start_geometry_node.client_key,
            "end_node_id": row.end_geometry_node.client_key,
            "label": row.label, "is_active": row.is_active,
            "material": {"source_id": str(row.material_id), "E_MPa": float(row.material.E_MPa), "density_g_per_mm3": float(row.material.density_g_per_mm3) if row.material.density_g_per_mm3 is not None else None},
            "section": {"source_id": str(row.section_id), "definition_hash": row.section.definition_hash, "A_mm2": row.section.properties_json["A_mm2"], "Ix_mm4": row.section.properties_json["Ix_mm4"], "Iy_mm4": row.section.properties_json["Iy_mm4"]},
        } for row in members],
        "member_joint_incidences": [{"member_id": row.member.client_key, "node_id": row.node.client_key} for row in incidences],
        "supports": [{"id": row.client_key, "node_id": row.target_node.client_key, "support_type": row.support_type, "restrained_axis": row.restrained_axis} for row in sorted(project.supports.select_related("target_node"), key=lambda row: row.client_key)],
        "node_loads": [{"id": row.client_key, "node_id": row.target_node.client_key, "fx_N": row.fx_N, "fy_N": row.fy_N, "label": row.label} for row in sorted(project.node_loads.select_related("target_node"), key=lambda row: row.client_key)],
    }
