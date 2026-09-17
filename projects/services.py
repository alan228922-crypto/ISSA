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


def purge_project_operational_data(*, project_id, actor_id=None):
    """Purge one Project's operational graph and return its durable receipt.

    Internal application boundary: the caller owns purge authorization/scheduling.
    Repeating a completed purge returns the original receipt, including its actor.
    Protected historical links remain protected outside this ordered transaction.
    """
    # 依照資料依賴關係刪除專案資料，並保留一份刪除紀錄，方便確認是否已處理過。
    from collections import Counter
    from django.db import transaction

    from analysis.models import AnalysisRun, ModelRevision, ValidationLog
    from learning.models import Prediction, Reflection, StudentResultReveal
    from modeling.models import Connection, GeometryNode, NodeLoad, PhysicalMember, Support
    from projects.models import Project, ProjectOperationalPurgeAudit

    with transaction.atomic():
        # Share the Project lock with operational writers. Check the receipt after
        # this query so a concurrent completed purge is visible when the lock frees.
        project = Project.objects.select_for_update().filter(pk=project_id).first()
        audit = ProjectOperationalPurgeAudit.objects.filter(project_id=project_id).first()
        if audit is not None:
            return audit
        if project is None:
            raise Project.DoesNotExist(f"Project {project_id} has no purge receipt")

        counts = Counter()
        _, deleted_counts = Reflection.objects.filter(analysis_run__project_id=project_id).delete()
        counts.update(deleted_counts)
        for model in (
            StudentResultReveal, ValidationLog, AnalysisRun, Prediction, ModelRevision,
            Support, NodeLoad, Connection, PhysicalMember, GeometryNode,
        ):
            _, deleted_counts = model.objects.filter(project_id=project_id).delete()
            counts.update(deleted_counts)
        event_id = project.event_id
        _, deleted_counts = project.delete()
        counts.update(deleted_counts)
        return ProjectOperationalPurgeAudit.objects.create(
            project_id=project_id,
            event_id=event_id,
            actor_id=actor_id,
            deletion_counts_json=dict(counts),
        )


def preview_section(*, actor, project, definition):
    """以既有纯截面引擎预览属性，不持久化任何项目或截面数据。"""
    # 預覽只做截面計算，不會把尚未確認的截面資料寫入專案。
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
