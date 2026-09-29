import math

from django.core.exceptions import ValidationError
from django.db import transaction

from materials.models import Material, Section
from projects.services import can_modify_project

from .models import (
    Connection, ConnectionParticipation, DraftMigrationAudit, GeometryNode,
    MemberJointIncidence, NodeLoad, PhysicalMember, Support,
)
from .topology import find_unrepresented_passes, ordered_member_nodes


class DraftSaveError(ValueError):
    """整稿保存失败的机器代码；调用方可映射到简体中文提示。"""

    def __init__(self, code):
        super().__init__(code)
        self.code = code
        self.status_code = 409 if code == "STALE_DRAFT" else 400


def _items(payload, key):
    # 節點、構件等主要資料必須以清單傳入，之後再檢查每個項目的識別名稱。
    value = payload.get(key)
    if not isinstance(value, list):
        raise DraftSaveError("INVALID_DRAFT")
    return value


def _keyed(items, key="client_key"):
    # client_key 是前端用來辨認同一個項目的名稱；重複名稱會讓資料彼此對不上。
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key] or item[key] in result:
            raise DraftSaveError("INVALID_CLIENT_KEY")
        result[item[key]] = item
    return result


def _instance(instance):
    # 集中檢查數值和模型規則，再保存資料，避免不同流程漏掉檢查。
    numeric_fields = (("x_mm", "y_mm") if isinstance(instance, GeometryNode) else
                      ("fx_N", "fy_N") if isinstance(instance, NodeLoad) else ())
    if any(not isinstance(getattr(instance, field), (int, float)) or isinstance(getattr(instance, field), bool) or not math.isfinite(getattr(instance, field)) for field in numeric_fields):
        raise DraftSaveError("INVALID_NUMERIC_VALUE")
    try:
        instance.full_clean()
    except ValidationError as exc:
        raise DraftSaveError("INVALID_DRAFT") from exc
    instance.save()
    return instance


def _owned(model, object_id, owner_id, error_code):
    # 材料和截面必須屬於專案擁有者，不能直接引用別人的資料。
    if object_id is None:
        return None
    try:
        obj = model.objects.get(id=object_id, owner_user_id=owner_id)
    except (model.DoesNotExist, TypeError, ValueError) as exc:
        raise DraftSaveError(error_code) from exc
    return obj


def _reference(objects, data, field, error_code):
    if field not in data:
        raise DraftSaveError("INVALID_DRAFT")
    client_key = data[field]
    if client_key is None:
        return None
    try:
        return objects[client_key]
    except (KeyError, TypeError) as exc:
        raise DraftSaveError(error_code) from exc


def save_physical_draft(*, actor, project, payload):
    """原子替换 mutable physical-draft-v1，物理层不创建任何 solver 实体。"""
    # ========================================================
    # 函數用途：用前端送來的完整資料，替換 Project 目前的 physical draft。
    #
    # 輸入是包含節點、物理構件、連接點、支承和荷載的字典；輸出是新的 draft_version。
    # 函數會先檢查權限、格式、數值和跨資料關係，再在同一個 transaction 中重建資料。
    # 這裡保存的是學生可編輯的設計草稿，不會直接建立 Solver 的分析物件。
    # ========================================================
    if not can_modify_project(actor, project):
        raise DraftSaveError("PROJECT_WRITE_DENIED")
    if project.draft_schema_version == "physical-draft-v2":
        return save_physical_draft_v2(actor=actor, project=project, payload=payload)
    if not isinstance(payload, dict) or payload.get("schema_version") != "physical-draft-v1":
        raise DraftSaveError("UNSUPPORTED_DRAFT_SCHEMA")
    try:
        expected_version = payload["expected_draft_version"]
    except KeyError as exc:
        raise DraftSaveError("INVALID_DRAFT") from exc
    if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 0:
        raise DraftSaveError("INVALID_DRAFT")

    nodes = _keyed(_items(payload, "nodes"))
    members = _keyed(_items(payload, "physical_members"))
    connections = _keyed(_items(payload, "connections"))
    supports = _keyed(_items(payload, "supports"))
    loads = _keyed(_items(payload, "node_loads"))

    with transaction.atomic():
        # 從這裡開始把整份草稿視為一次替換：舊圖刪除、新圖寫入、版本增加要一起成功。
        # 鎖住專案後，檢查版本、刪除舊草稿、寫入新草稿會一起完成，避免只完成一半。
        project = type(project).objects.select_for_update().get(pk=project.pk)
        if project.draft_schema_version != "physical-draft-v1":
            raise DraftSaveError("UNSUPPORTED_DRAFT_SCHEMA")
        if project.draft_version != expected_version:
            raise DraftSaveError("STALE_DRAFT")

        # Nullable references no longer cascade, so replace the whole owned
        # draft explicitly from leaves to roots inside this transaction.
        Support.objects.filter(project=project).delete()
        NodeLoad.objects.filter(project=project).delete()
        Connection.objects.filter(project=project).delete()
        PhysicalMember.objects.filter(project=project).delete()
        GeometryNode.objects.filter(project=project).delete()
        # 先建立節點，後面構件、連接點和荷載才能用 client_key 找到正確的資料。
        node_objects = {}
        for key, data in nodes.items():
            node_objects[key] = _instance(GeometryNode(
                project=project, client_key=key, x_mm=data.get("x_mm"), y_mm=data.get("y_mm"), label=data.get("label", ""),
            ))

        member_objects = {}
        # 構件會引用前面建立的節點，並且必須引用專案擁有者自己的材料和截面。
        for key, data in members.items():
            start = _reference(node_objects, data, "start_node_client_key", "UNKNOWN_NODE")
            end = _reference(node_objects, data, "end_node_client_key", "UNKNOWN_NODE")
            material = _owned(Material, data.get("material_id"), project.owner_user_id, "FOREIGN_MATERIAL")
            section = _owned(Section, data.get("section_id"), project.owner_user_id, "FOREIGN_SECTION")
            member_objects[key] = _instance(PhysicalMember(
                project=project, client_key=key, start_geometry_node=start, end_geometry_node=end,
                material=material, section=section, label=data.get("label", ""), is_active=data.get("is_active", True),
            ))

        connection_objects = {}
        # Connection 把幾何節點和參與的物理構件連起來，是支承與荷載的定位依據。
        for key, data in connections.items():
            node = _reference(node_objects, data, "geometry_node_client_key", "UNKNOWN_NODE")
            participant_keys = data.get("participating_member_client_keys")
            if not isinstance(participant_keys, list) or any(key is not None and (not isinstance(key, str) or not key) for key in participant_keys):
                raise DraftSaveError("INVALID_DRAFT")
            if len([key for key in participant_keys if key is not None]) != len(set(key for key in participant_keys if key is not None)):
                raise DraftSaveError("INVALID_DRAFT")
            participants = [_reference(member_objects, {"member": key}, "member", "UNKNOWN_MEMBER") for key in participant_keys]
            connection = _instance(Connection(project=project, client_key=key, geometry_node=node))
            ConnectionParticipation.objects.bulk_create([
                ConnectionParticipation(connection=connection, member=member, position=position)
                for position, member in enumerate(participants)
            ])
            connection_objects[key] = connection

        for key, data in supports.items():
            # 支承只能指向已存在的 Connection，不能直接指向任意座標。
            if not isinstance(data, dict):
                raise DraftSaveError("INVALID_DRAFT")
            connection = _reference(connection_objects, data, "target_connection_client_key", "UNKNOWN_CONNECTION")
            _instance(Support(project=project, client_key=key, target_connection=connection, support_type=data.get("support_type"), restrained_axis=data.get("restrained_axis")))

        for key, data in loads.items():
            # 荷載同樣綁定 Connection，保存 fx_N / fy_N 兩個全域方向的節點外力。
            connection = _reference(connection_objects, data, "target_connection_client_key", "UNKNOWN_CONNECTION")
            _instance(NodeLoad(project=project, client_key=key, target_connection=connection, fx_N=data.get("fx_N"), fy_N=data.get("fy_N"), label=data.get("label", "")))

        project.draft_version += 1
        project.save(update_fields=["draft_version", "updated_at"])
    return {"ok": True, "draft_version": project.draft_version, "validation": {"errors": [], "warnings": []}}


def _v2_expected_version(payload):
    if not isinstance(payload, dict) or payload.get("schema_version") != "physical-draft-v2":
        raise DraftSaveError("UNSUPPORTED_DRAFT_SCHEMA")
    value = payload.get("expected_draft_version")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DraftSaveError("INVALID_DRAFT")
    if "connections" in payload:
        raise DraftSaveError("UNSUPPORTED_DRAFT_SCHEMA")
    return value


def _audited_exceptions(project, nodes, members):
    audit = DraftMigrationAudit.objects.filter(project=project, status="CONVERTED").order_by("-created_at", "-pk").first()
    if audit is None:
        return set(), set()
    legacy = audit.legacy_exceptions_json or {}
    pair_exemptions = set()
    for item in legacy.get("same_coordinate_pairs", []):
        if len(item) != 4:
            continue
        first, second, x, y = item
        if nodes.get(first) == nodes.get(second) == (x, y):
            pair_exemptions.add(frozenset((first, second)))
    member_by_key = {row["client_key"]: row for row in members}
    pass_exemptions = set()
    for item in legacy.get("nonparticipating_passes", []):
        if len(item) != 8:
            continue
        member_key, node_key, x, y, x1, y1, x2, y2 = item
        member = member_by_key.get(member_key)
        if member is None or nodes.get(node_key) != (x, y):
            continue
        start = nodes.get(member["start_node_client_key"])
        end = nodes.get(member["end_node_client_key"])
        if start == (x1, y1) and end == (x2, y2):
            pass_exemptions.add((member_key, node_key))
    return pair_exemptions, pass_exemptions


def save_physical_draft_v2(*, actor, project, payload):
    """Atomically replace a v2 editable graph without inferring incidence."""
    if not can_modify_project(actor, project):
        raise DraftSaveError("PROJECT_WRITE_DENIED")
    expected_version = _v2_expected_version(payload)
    nodes = _keyed(_items(payload, "nodes"))
    members = _keyed(_items(payload, "physical_members"))
    supports = _keyed(_items(payload, "supports"))
    loads = _keyed(_items(payload, "node_loads"))
    incidence_rows = _items(payload, "member_joint_incidences")
    incidences = set()
    for row in incidence_rows:
        if not isinstance(row, dict):
            raise DraftSaveError("INVALID_DRAFT")
        pair = row.get("member_client_key"), row.get("node_client_key")
        if pair[0] not in members or pair[1] not in nodes:
            raise DraftSaveError("UNKNOWN_MEMBER_INCIDENCE")
        if pair in incidences:
            raise DraftSaveError("DUPLICATE_MEMBER_INCIDENCE")
        incidences.add(pair)
    coordinates = {}
    for key, row in nodes.items():
        point = row.get("x_mm"), row.get("y_mm")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in point):
            raise DraftSaveError("INVALID_NUMERIC_VALUE")
        coordinates[key] = point
    with transaction.atomic():
        project = type(project).objects.select_for_update().get(pk=project.pk)
        if project.draft_schema_version != "physical-draft-v2":
            raise DraftSaveError("UNSUPPORTED_DRAFT_SCHEMA")
        if project.draft_version != expected_version:
            raise DraftSaveError("STALE_DRAFT")
        pair_exemptions, pass_exemptions = _audited_exceptions(project, coordinates, list(members.values()))
        by_point = {}
        for key, point in coordinates.items():
            for other in by_point.get(point, []):
                if frozenset((key, other)) not in pair_exemptions:
                    raise DraftSaveError("DUPLICATE_NODE_COORDINATE")
            by_point.setdefault(point, []).append(key)
        for key, row in members.items():
            if "start_node_client_key" not in row or "end_node_client_key" not in row:
                raise DraftSaveError("INVALID_DRAFT")
            for field in ("start_node_client_key", "end_node_client_key"):
                if row[field] is not None and row[field] not in nodes:
                    raise DraftSaveError("UNKNOWN_NODE")
            try:
                ordered_member_nodes(row, coordinates, incidences)
            except (ValueError, KeyError) as exc:
                raise DraftSaveError(str(exc)) from exc
        if find_unrepresented_passes(nodes=coordinates, members=list(members.values()), incidences=incidences, exemptions=pass_exemptions):
            raise DraftSaveError("MEMBER_PASSES_THROUGH_NODE_WITHOUT_INCIDENCE")

        Support.objects.filter(project=project).delete()
        NodeLoad.objects.filter(project=project).delete()
        MemberJointIncidence.objects.filter(project=project).delete()
        Connection.objects.filter(project=project).delete()
        PhysicalMember.objects.filter(project=project).delete()
        GeometryNode.objects.filter(project=project).delete()
        node_objects = {}
        for key, row in nodes.items():
            node_objects[key] = _instance(GeometryNode(
                project=project, client_key=key, x_mm=row["x_mm"], y_mm=row["y_mm"], label=row.get("label", ""),
            ))
        member_objects = {}
        for key, row in members.items():
            member_objects[key] = _instance(PhysicalMember(
                project=project, client_key=key,
                start_geometry_node=_reference(node_objects, row, "start_node_client_key", "UNKNOWN_NODE"),
                end_geometry_node=_reference(node_objects, row, "end_node_client_key", "UNKNOWN_NODE"),
                material=_owned(Material, row.get("material_id"), project.owner_user_id, "FOREIGN_MATERIAL"),
                section=_owned(Section, row.get("section_id"), project.owner_user_id, "FOREIGN_SECTION"),
                label=row.get("label", ""), is_active=row.get("is_active", True),
            ))
        for member_key, node_key in sorted(incidences):
            _instance(MemberJointIncidence(project=project, member=member_objects[member_key], node=node_objects[node_key]))
        for key, row in supports.items():
            if not isinstance(row, dict) or "target_connection_client_key" in row:
                raise DraftSaveError("UNSUPPORTED_DRAFT_SCHEMA")
            _instance(Support(
                project=project, client_key=key,
                target_node=_reference(node_objects, row, "target_node_client_key", "UNKNOWN_NODE"),
                support_type=row.get("support_type"), restrained_axis=row.get("restrained_axis"),
            ))
        for key, row in loads.items():
            if not isinstance(row, dict) or "target_connection_client_key" in row:
                raise DraftSaveError("UNSUPPORTED_DRAFT_SCHEMA")
            _instance(NodeLoad(
                project=project, client_key=key,
                target_node=_reference(node_objects, row, "target_node_client_key", "UNKNOWN_NODE"),
                fx_N=row.get("fx_N"), fy_N=row.get("fy_N"), label=row.get("label", ""),
            ))
        project.draft_version += 1
        project.save(update_fields=["draft_version", "updated_at"])
    return {"ok": True, "draft_version": project.draft_version, "validation": {"errors": [], "warnings": []}}
