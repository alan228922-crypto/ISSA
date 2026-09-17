import math

from django.core.exceptions import ValidationError
from django.db import transaction

from materials.models import Material, Section
from projects.services import can_modify_project

from .models import Connection, GeometryNode, NodeLoad, PhysicalMember, Support


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
    try:
        obj = model.objects.get(id=object_id, owner_user_id=owner_id)
    except (model.DoesNotExist, TypeError, ValueError) as exc:
        raise DraftSaveError(error_code) from exc
    return obj


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
    supports = _items(payload, "supports")
    loads = _keyed(_items(payload, "node_loads"))

    with transaction.atomic():
        # 從這裡開始把整份草稿視為一次替換：舊圖刪除、新圖寫入、版本增加要一起成功。
        # 鎖住專案後，檢查版本、刪除舊草稿、寫入新草稿會一起完成，避免只完成一半。
        project = type(project).objects.select_for_update().get(pk=project.pk)
        if project.draft_version != expected_version:
            raise DraftSaveError("STALE_DRAFT")

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
            try:
                start = node_objects[data["start_node_client_key"]]
                end = node_objects[data["end_node_client_key"]]
            except (KeyError, TypeError) as exc:
                raise DraftSaveError("UNKNOWN_NODE") from exc
            material = _owned(Material, data.get("material_id"), project.owner_user_id, "FOREIGN_MATERIAL")
            section = _owned(Section, data.get("section_id"), project.owner_user_id, "FOREIGN_SECTION")
            member_objects[key] = _instance(PhysicalMember(
                project=project, client_key=key, start_geometry_node=start, end_geometry_node=end,
                material=material, section=section, label=data.get("label", ""), is_active=data.get("is_active", True),
            ))

        connection_objects = {}
        # Connection 把幾何節點和參與的物理構件連起來，是支承與荷載的定位依據。
        for key, data in connections.items():
            try:
                node = node_objects[data["geometry_node_client_key"]]
                participant_keys = data["participating_member_client_keys"]
                participants = [member_objects[member_key] for member_key in participant_keys]
            except KeyError as exc:
                code = "UNKNOWN_NODE" if exc.args[0] == "geometry_node_client_key" or exc.args[0] in node_objects else "UNKNOWN_MEMBER"
                raise DraftSaveError(code) from exc
            if not isinstance(participant_keys, list):
                raise DraftSaveError("INVALID_DRAFT")
            connection = _instance(Connection(project=project, client_key=key, geometry_node=node))
            connection.participating_members.set(participants)
            connection_objects[key] = connection

        for data in supports:
            # 支承只能指向已存在的 Connection，不能直接指向任意座標。
            if not isinstance(data, dict):
                raise DraftSaveError("INVALID_DRAFT")
            try:
                connection = connection_objects[data["target_connection_client_key"]]
            except KeyError as exc:
                raise DraftSaveError("UNKNOWN_CONNECTION") from exc
            _instance(Support(project=project, target_connection=connection, support_type=data.get("support_type"), restrained_axis=data.get("restrained_axis")))

        for key, data in loads.items():
            # 荷載同樣綁定 Connection，保存 fx_N / fy_N 兩個全域方向的節點外力。
            try:
                connection = connection_objects[data["target_connection_client_key"]]
            except KeyError as exc:
                raise DraftSaveError("UNKNOWN_CONNECTION") from exc
            _instance(NodeLoad(project=project, client_key=key, target_connection=connection, fx_N=data.get("fx_N"), fy_N=data.get("fy_N"), label=data.get("label", "")))

        project.draft_version += 1
        project.save(update_fields=["draft_version", "updated_at"])
    return {"ok": True, "draft_version": project.draft_version, "validation": {"errors": [], "warnings": []}}
