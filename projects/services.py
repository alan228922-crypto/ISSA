from competitions.authorization import can_modify_project as _can_modify_project
from competitions.authorization import can_view_project as _can_view_project
from competitions.models import CompetitionEvent
from mechanics.sections.model import Rectangle
from mechanics.sections.properties import composite_properties, rectangle_properties
from materials.services import SectionServiceError


def can_view_project(actor, project):
    """复用赛事与项目归属权限策略，不创建第二套权限系统。"""
    return _can_view_project(actor, event_id=project.event_id, owner_user_id=project.owner_user_id)


def can_modify_project(actor, project):
    """复用既有项目写入策略；经理只能查看学生项目。"""
    if project.event.status == CompetitionEvent.Status.PURGED:
        return False
    return _can_modify_project(actor, event_id=project.event_id, owner_user_id=project.owner_user_id)


def preview_section(*, actor, project, definition):
    """以既有纯截面引擎预览属性，不持久化任何项目或截面数据。"""
    if not can_modify_project(actor, project):
        raise SectionServiceError('PROJECT_WRITE_DENIED')
    if not isinstance(definition, dict) or definition.get('schema_version') != 'section-definition-v1':
        raise SectionServiceError('INVALID_SECTION_DEFINITION')
    try:
        if definition.get('type') == 'rectangle':
            properties = rectangle_properties(Rectangle(width_mm=definition['width_mm'], height_mm=definition['height_mm'], density_g_per_mm3=definition['density_g_per_mm3'], center_x_mm=definition.get('center_x_mm', 0.0), center_y_mm=definition.get('center_y_mm', 0.0), angle_deg=definition.get('angle_deg', 0.0)))
        elif definition.get('type') == 'composite':
            properties = composite_properties([Rectangle(width_mm=item['width_mm'], height_mm=item['height_mm'], density_g_per_mm3=item['density_g_per_mm3'], center_x_mm=item.get('center_x_mm', 0.0), center_y_mm=item.get('center_y_mm', 0.0), angle_deg=item.get('angle_deg', 0.0)) for item in definition['components']])
        else:
            raise SectionServiceError('UNSUPPORTED_SECTION_TYPE')
    except (KeyError, TypeError) as exc:
        raise SectionServiceError('INVALID_SECTION_DEFINITION') from exc
    except ValueError as exc:
        raise SectionServiceError(str(exc)) from exc
    return {'A_mm2': properties.A_mm2, 'centroid_x_mm': properties.centroid_x_mm, 'centroid_y_mm': properties.centroid_y_mm, 'Ix_mm4': properties.Ix_mm4, 'Iy_mm4': properties.Iy_mm4, 'mass_per_length_g_per_mm': properties.mass_per_length_g_per_mm, 'strong_axis': properties.strong_axis, 'weak_axis': properties.weak_axis}
