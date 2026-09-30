"""Create the local-only B/T01 demo project without running an analysis."""

from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


DEMO_USERNAME = "demo_student"
DEMO_PASSWORD = "demo-only-password"
DEMO_EVENT_CODE = "DEMO-TRUSS-2026"
DEMO_EVENT_NAME = "结构设计竞赛 Demo"
DEMO_PROJECT_NAME = "B/T01 桁架 Demo"
DEMO_BLANK_PROJECT_NAME = "空白建模 Demo"
DEMO_MATERIAL_NAME = "Demo B/T01 竹材"
DEMO_SECTION_NAME = "Demo B/T01 矩形截面"


def _bt01_payload(material, section, version, schema_version="physical-draft-v2"):
    """Reuse the existing B/T01 benchmark inputs: P=100 N, L=1000 mm, E=2000 MPa, A=6 mm²."""
    payload = {
        "schema_version": schema_version,
        "expected_draft_version": version,
        "nodes": [
            {"client_key": "n1", "x_mm": 0.0, "y_mm": 0.0, "label": "左支座"},
            {"client_key": "n2", "x_mm": 1000.0, "y_mm": 0.0, "label": "右端"},
        ],
        "physical_members": [
            {
                "client_key": "m1",
                "start_node_client_key": "n1",
                "end_node_client_key": "n2",
                "material_id": material.id,
                "section_id": section.id,
                "label": "B/T01 杆件",
                "is_active": True,
            }
        ],
        "connections": [
            {"client_key": "c1", "geometry_node_client_key": "n1", "participating_member_client_keys": ["m1"]},
            {"client_key": "c2", "geometry_node_client_key": "n2", "participating_member_client_keys": ["m1"]},
        ],
        "supports": [
            {"client_key": "s1", "target_connection_client_key": "c1", "support_type": "PINNED", "restrained_axis": None},
            {"client_key": "s2", "target_connection_client_key": "c2", "support_type": "ROLLER", "restrained_axis": "Y"},
        ],
        "node_loads": [
            {"client_key": "l1", "target_connection_client_key": "c2", "fx_N": 100.0, "fy_N": 0.0, "label": "100 N 水平荷载"},
        ],
    }
    if schema_version == "physical-draft-v2":
        payload["member_joint_incidences"] = []
        payload.pop("connections")
        for row, node_key in zip(payload["supports"], ("n1", "n2")):
            row["target_node_client_key"] = node_key
            row.pop("target_connection_client_key")
        payload["node_loads"][0]["target_node_client_key"] = "n2"
        payload["node_loads"][0].pop("target_connection_client_key")
    return payload


class Command(BaseCommand):
    help = "Create or reuse a local DEBUG-only B/T01 demo project."

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true", help="Write the local development demo data.")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo is only available when DEBUG=True.")
        if not options["confirm"]:
            raise CommandError("Pass --confirm to create local development demo data.")

        from accounts.models import User
        from competitions.models import CompetitionEvent, EventMembership
        from materials.models import Material, Section
        from materials.services import create_section
        from modeling.services import save_physical_draft
        from projects.models import Project

        with transaction.atomic():
            account = User.objects.filter(username=DEMO_USERNAME).first()
            if account is None:
                account = User.objects.create_user(
                    username=DEMO_USERNAME,
                    password=DEMO_PASSWORD,
                    role=User.Role.USER,
                    must_change_password=False,
                )

            event = CompetitionEvent.objects.filter(event_code=DEMO_EVENT_CODE).first()
            if event is None:
                event = CompetitionEvent.objects.create(
                    name=DEMO_EVENT_NAME,
                    event_code=DEMO_EVENT_CODE,
                    competition_date=date(2030, 1, 1),
                    starts_at=timezone.make_aware(datetime(2030, 1, 1)),
                    ends_at=timezone.make_aware(datetime(2030, 1, 2)),
                )

            membership, _ = EventMembership.objects.get_or_create(
                user=account,
                event=event,
                membership_type=EventMembership.Type.PARTICIPANT,
                defaults={"is_active": True},
            )
            if not membership.is_active:
                membership.is_active = True
                membership.save(update_fields=["is_active"])

            project = Project.objects.filter(
                event=event,
                owner_user=account,
                name=DEMO_PROJECT_NAME,
            ).order_by("id").first()
            if project is None:
                project = Project.objects.create(
                    event=event,
                    owner_user=account,
                    name=DEMO_PROJECT_NAME,
                    analysis_type=Project.AnalysisType.TRUSS_2D,
                )

            blank_project = Project.objects.filter(
                event=event,
                owner_user=account,
                name=DEMO_BLANK_PROJECT_NAME,
            ).order_by("id").first()
            if blank_project is None:
                blank_project = Project.objects.create(
                    event=event,
                    owner_user=account,
                    name=DEMO_BLANK_PROJECT_NAME,
                    analysis_type=Project.AnalysisType.TRUSS_2D,
                )

            material = Material.objects.filter(owner_user=account, name=DEMO_MATERIAL_NAME).order_by("id").first()
            if material is None:
                material = Material.objects.create(
                    owner_user=account,
                    name=DEMO_MATERIAL_NAME,
                    E_MPa=Decimal("2000"),
                    density_g_per_mm3=Decimal("0.0007"),
                    source_type="MEASURED",
                    note="仅用于本机 B/T01 demo。",
                )

            section = Section.objects.filter(owner_user=account, name=DEMO_SECTION_NAME).order_by("id").first()
            if section is None:
                section = create_section(
                    owner=account,
                    name=DEMO_SECTION_NAME,
                    definition={
                        "schema_version": "section-definition-v1",
                        "type": "rectangle",
                        "width_mm": 1.0,
                        "height_mm": 6.0,
                        "density_g_per_mm3": 0.0007,
                    },
                )

            if project.draft_version == 0:
                save_physical_draft(
                    actor=account,
                    project=project,
                    payload=_bt01_payload(material, section, project.draft_version, project.draft_schema_version),
                )
                project.refresh_from_db()

        workspace_url = f"http://127.0.0.1:8000/projects/{project.id}/workspace/"
        blank_workspace_url = f"http://127.0.0.1:8000/projects/{blank_project.id}/workspace/"
        self.stdout.write(
            "\n".join(
                [
                    "Demo data ready.",
                    f"Account: {account.username}",
                    f"Password: {DEMO_PASSWORD} (development only)",
                    f"Event: {event.name}",
                    f"Project: {project.name}",
                    f"Workspace: {workspace_url}",
                    f"Blank project: {blank_project.name} — {blank_workspace_url}",
                    "Entry: runserver → login → open /events/ → choose a project.",
                    "手动验收（预置模型）：Model Check → Prediction（可跳过）→ Analyze → Compare / Explain → Report → Reasoning → Reflection。",
                    "手动验收（空白项目）：创建材料与矩形截面 → 建立第一根构件 → 保存并重新载入。",
                ]
            )
        )
