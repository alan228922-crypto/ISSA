from datetime import date, datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from tests.application.test_physical_draft import context


def make_event(*, name, code):
    return __import__("competitions.models", fromlist=["CompetitionEvent"]).CompetitionEvent.objects.create(
        name=name,
        event_code=code,
        competition_date=date(2026, 11, 7),
        starts_at=timezone.make_aware(datetime(2026, 11, 7)),
        ends_at=timezone.make_aware(datetime(2026, 11, 8)),
    )


def add_membership(*, user, event, membership_type):
    from competitions.models import EventMembership

    return EventMembership.objects.create(
        user=user,
        event=event,
        membership_type=membership_type,
    )


@pytest.mark.django_db
def test_participant_sees_only_owned_projects_with_workspace_links(client):
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project

    actor = User.objects.create_user("entry-owner")
    other = User.objects.create_user("entry-other")
    event = make_event(name="结构竞赛", code="ENTRY-A")
    add_membership(user=actor, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    owned = Project.objects.create(event=event, owner_user=actor, name="我的桁架")
    Project.objects.create(event=event, owner_user=other, name="他人的桁架")

    client.force_login(actor)
    response = client.get("/events/")

    assert response.status_code == 200
    assert "赛事与项目" in response.content.decode()
    assert "结构竞赛" in response.content.decode()
    assert "我的桁架" in response.content.decode()
    assert "他人的桁架" not in response.content.decode()
    assert reverse("projects:workspace", kwargs={"project_id": owned.id}) in response.content.decode()
    assert "进入工作区" in response.content.decode()


@pytest.mark.django_db
def test_project_card_uses_actual_model_and_analysis_progress(client, context):
    from analysis.orchestration import analyze_project
    from tests.application.test_analysis_acceptance import save_bt01_draft

    owner, project, material, section = context
    client.force_login(owner)
    project.draft_version = 1
    project.save(update_fields=["draft_version"])
    body = client.get("/events/").content.decode()
    assert "当前状态：尚未建模" in body
    assert "下一步：从第一个节点开始" in body

    save_bt01_draft(owner, project, material, section)
    run = analyze_project(project=project, actor=owner, expected_draft_version=project.draft_version)
    assert run.status == "SUCCESS"
    body = client.get("/events/").content.decode()
    assert "当前状态：已完成分析" in body
    assert "下一步：查看结果并总结" in body

    save_bt01_draft(owner, project, material, section, fx_N=125)
    body = client.get("/events/").content.decode()
    assert "当前状态：模型已修改" in body
    assert "下一步：检查修改后的模型" in body


@pytest.mark.django_db
def test_landing_shows_visible_event_when_it_has_no_enterable_project(client):
    from accounts.models import User
    from competitions.models import EventMembership

    actor = User.objects.create_user("entry-empty")
    event = make_event(name="空赛事", code="ENTRY-B")
    add_membership(user=actor, event=event, membership_type=EventMembership.Type.PARTICIPANT)

    client.force_login(actor)
    response = client.get("/events/")

    assert response.status_code == 200
    assert "空赛事" in response.content.decode()
    assert "目前没有可进入的项目。" in response.content.decode()
    assert "需要先取得赛事 / 项目权限后才能进入结构分析工作区。" in response.content.decode()


@pytest.mark.django_db
def test_manager_and_developer_follow_existing_project_view_policy(client):
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project

    owner = User.objects.create_user("entry-student")
    manager = User.objects.create_user("entry-manager", role=User.Role.MANAGER)
    developer = User.objects.create_user("entry-developer", role=User.Role.DEVELOPER)
    assigned_event = make_event(name="已分配赛事", code="ENTRY-C")
    other_event = make_event(name="其他赛事", code="ENTRY-D")
    add_membership(user=manager, event=assigned_event, membership_type=EventMembership.Type.MANAGER)
    assigned_project = Project.objects.create(event=assigned_event, owner_user=owner, name="受管项目")
    other_project = Project.objects.create(event=other_event, owner_user=owner, name="未分配项目")

    client.force_login(manager)
    manager_response = client.get("/events/")
    assert "受管项目" in manager_response.content.decode()
    assert "未分配项目" not in manager_response.content.decode()
    assert reverse("projects:workspace", kwargs={"project_id": assigned_project.id}) in manager_response.content.decode()

    client.force_login(developer)
    developer_response = client.get("/events/")
    assert "受管项目" in developer_response.content.decode()
    assert "未分配项目" in developer_response.content.decode()
    assert reverse("projects:workspace", kwargs={"project_id": other_project.id}) in developer_response.content.decode()


@pytest.mark.django_db
def test_landing_lists_multiple_authorized_projects_deterministically_without_creating_any(client):
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project

    actor = User.objects.create_user("entry-order")
    event = make_event(name="排序赛事", code="ENTRY-E")
    add_membership(user=actor, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    second = Project.objects.create(event=event, owner_user=actor, name="B 项目")
    first = Project.objects.create(event=event, owner_user=actor, name="A 项目")
    count_before = Project.objects.count()

    client.force_login(actor)
    response = client.get("/events/")
    body = response.content.decode()

    assert body.index("A 项目") < body.index("B 项目")
    assert reverse("projects:workspace", kwargs={"project_id": first.id}) in body
    assert reverse("projects:workspace", kwargs={"project_id": second.id}) in body
    assert Project.objects.count() == count_before


@pytest.mark.django_db
def test_landing_does_not_offer_workspace_link_for_unsupported_project_type(client):
    from accounts.models import User
    from competitions.models import EventMembership
    from projects.models import Project

    actor = User.objects.create_user("entry-frame")
    event = make_event(name="类型赛事", code="ENTRY-F")
    add_membership(user=actor, event=event, membership_type=EventMembership.Type.PARTICIPANT)
    Project.objects.create(
        event=event,
        owner_user=actor,
        name="未来刚架",
        analysis_type=Project.AnalysisType.FRAME_2D,
    )

    client.force_login(actor)
    response = client.get("/events/")

    assert "未来刚架" not in response.content.decode()
    assert "目前没有可进入的项目。" in response.content.decode()
