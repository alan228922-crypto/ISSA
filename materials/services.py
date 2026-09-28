import hashlib
import json

from accounts.models import User
from django.db import transaction
from mechanics.sections.model import Rectangle
from mechanics.sections.properties import composite_properties, rectangle_properties

from .models import Material, ResourceDeletionAudit, Section, Strip


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


def _section_values(*, owner, name, definition):
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
    return {
        "name": name,
        "section_type": persisted_type,
        "definition_schema_version": canonical_definition.get("schema_version", "section-definition-v1"),
        "definition_json": canonical_definition,
        "properties_schema_version": "section-properties-v1",
        "properties_json": _properties_json(properties),
        "definition_hash": definition_hash,
    }


def create_section(*, owner, name, definition):
    """规范化定义、调用 mechanics.sections，并保存其权威计算结果。"""
    # 截面計算由純計算模組負責；這裡負責檢查擁有者、整理資料並保存結果。
    return Section.objects.create(owner_user=owner, **_section_values(owner=owner, name=name, definition=definition))


@transaction.atomic
def update_section(*, actor, section, name, definition):
    """重新计算并原子更新一个可管理的截面。"""
    if not can_manage_material(actor, section):
        raise SectionServiceError("FORBIDDEN")
    values = _section_values(owner=section.owner_user, name=name, definition=definition)
    for field, value in values.items():
        setattr(section, field, value)
    section.save(update_fields=(
        "name", "section_type", "definition_schema_version", "definition_json",
        "properties_schema_version", "properties_json", "definition_hash", "updated_at",
    ))
    return section


@transaction.atomic
def delete_resource(*, actor, resource):
    """Delete one shared resource and invalidate every affected current draft."""
    from django.db.models import F
    from modeling.models import PhysicalMember
    from projects.models import Project

    if not isinstance(resource, (Material, Section)):
        raise SectionServiceError("INVALID_RESOURCE")
    if not can_manage_material(actor, resource):
        raise SectionServiceError("FORBIDDEN")

    # Saves lock Projects before resolving catalog resources. Lock every owner
    # Project in the same order so no concurrent save can introduce a new
    # reference between impact discovery and resource deletion.
    list(Project.objects.select_for_update().filter(owner_user_id=resource.owner_user_id).order_by("pk"))
    current = type(resource).objects.select_for_update().filter(pk=resource.pk, owner_user_id=resource.owner_user_id).first()
    if current is None:
        raise SectionServiceError("RESOURCE_NOT_FOUND")

    field = "material" if isinstance(current, Material) else "section"
    members = PhysicalMember.objects.filter(**{field: current})
    affected_project_ids = list(members.order_by("project_id").values_list("project_id", flat=True).distinct())
    member_count = members.count()
    members.update(**{field: None})
    strip_count = 0
    if isinstance(current, Material):
        strips = Strip.objects.filter(material=current)
        strip_count = strips.count()
        strips.update(material=None)
    if affected_project_ids:
        Project.objects.filter(pk__in=affected_project_ids).update(draft_version=F("draft_version") + 1)

    receipt = ResourceDeletionAudit.objects.create(
        resource_kind=type(current).__name__.upper(),
        resource_id=current.pk,
        resource_name=current.name,
        actor_id=actor.pk,
        affected_project_ids=affected_project_ids,
        object_counts_json={"members": member_count, "strips": strip_count},
    )
    current.delete()
    return receipt


@transaction.atomic
def rebind_strip_material(*, actor, strip, material_id):
    """Assign an owned Material to a retained Strip, or leave it incomplete."""
    if not can_manage_material(actor, strip):
        raise SectionServiceError("FORBIDDEN")
    material = None
    if material_id is not None:
        try:
            material = Material.objects.select_for_update().get(pk=material_id, owner_user_id=strip.owner_user_id)
        except (Material.DoesNotExist, TypeError, ValueError) as exc:
            raise SectionServiceError("FOREIGN_MATERIAL") from exc
    current = Strip.objects.select_for_update().get(pk=strip.pk, owner_user_id=strip.owner_user_id)
    current.material = material
    current.full_clean()
    current.save(update_fields=["material"])
    return current
