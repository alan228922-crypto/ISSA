import hashlib
import json

from accounts.models import User
from mechanics.sections.model import Rectangle
from mechanics.sections.properties import composite_properties, rectangle_properties

from .models import Section, Strip


class SectionServiceError(ValueError):
    """截面定义不能安全持久化时使用的机器可读错误。"""


def can_manage_material(actor,material):
    """所有权在服务端判断；Manager 默认不能修改学生材料。"""
    return actor.role==User.Role.DEVELOPER or actor.id==material.owner_user_id


def _canonical_definition(definition):
    # 先用固定格式整理截面資料，再產生指紋，讓相同定義可以被辨認出來。
    try:
        encoded = json.dumps(definition, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SectionServiceError("INVALID_SECTION_DEFINITION") from exc
    return json.loads(encoded), hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _rectangle(data):
    try:
        return Rectangle(
            width_mm=data["width_mm"], height_mm=data["height_mm"],
            density_g_per_mm3=data["density_g_per_mm3"],
            center_x_mm=data.get("center_x_mm", 0.0), center_y_mm=data.get("center_y_mm", 0.0),
            angle_deg=data.get("angle_deg", 0.0),
        )
    except KeyError as exc:
        raise SectionServiceError("INVALID_SECTION_DEFINITION") from exc


def _properties_json(properties):
    return {
        "A_mm2": properties.A_mm2, "centroid_x_mm": properties.centroid_x_mm,
        "centroid_y_mm": properties.centroid_y_mm, "Ix_mm4": properties.Ix_mm4,
        "Iy_mm4": properties.Iy_mm4, "mass_per_length_g_per_mm": properties.mass_per_length_g_per_mm,
        "strong_axis": properties.strong_axis, "weak_axis": properties.weak_axis,
    }


def create_section(*, owner, name, definition):
    """规范化定义、调用 mechanics.sections，并保存其权威计算结果。"""
    # 截面計算由純計算模組負責；這裡負責檢查擁有者、整理資料並保存結果。
    canonical_definition, definition_hash = _canonical_definition(definition)
    strip_id = canonical_definition.get("strip_id")
    if strip_id is not None and not Strip.objects.filter(id=strip_id, owner_user=owner).exists():
        raise SectionServiceError("FOREIGN_STRIP")
    section_type = canonical_definition.get("type")
    try:
        if section_type == "rectangle":
            properties = rectangle_properties(_rectangle(canonical_definition))
            persisted_type = "RECTANGLE"
        elif section_type == "composite":
            properties = composite_properties([_rectangle(component) for component in canonical_definition.get("components", [])])
            persisted_type = "COMPOSITE"
        else:
            raise SectionServiceError("UNSUPPORTED_SECTION_TYPE")
    except SectionServiceError:
        raise
    except ValueError as exc:
        raise SectionServiceError(str(exc)) from exc
    return Section.objects.create(
        owner_user=owner, name=name, section_type=persisted_type,
        definition_schema_version=canonical_definition.get("schema_version", "section-definition-v1"),
        definition_json=canonical_definition, properties_schema_version="section-properties-v1",
        properties_json=_properties_json(properties), definition_hash=definition_hash,
    )
