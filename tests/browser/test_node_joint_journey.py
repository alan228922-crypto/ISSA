import pytest

from tests.application.test_physical_draft import context


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_brand_new_project_opens_empty_v2_canvas_without_connection(context, workspace_page):
    from projects.models import Project

    owner, legacy, _, _ = context
    fresh = Project.objects.create(event=legacy.event, owner_user=owner, name="新桁架")
    page = workspace_page(user=owner, project=fresh)
    draft = page.evaluate("""() => JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft""")
    assert draft["schema_version"] == "physical-draft-v2"
    assert "connections" not in draft
    assert page.locator('[data-object-kind="Connection"]').count() == 0
    assert page.locator('[data-workspace-tool="NODE"]').is_visible()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_real_pointer_new_member_through_existing_node_authors_incidence(context, workspace_page):
    from modeling.services import save_physical_draft
    from projects.models import Project

    owner, legacy, material, section = context
    fresh = Project.objects.create(event=legacy.event, owner_user=owner, name="穿越节点")
    save_physical_draft(actor=owner, project=fresh, payload={
        "schema_version": "physical-draft-v2", "expected_draft_version": 0,
        "nodes": [{"client_key": key, "x_mm": x, "y_mm": 0.0, "label": ""} for key, x in [("a", -100.0), ("mid", 0.0), ("b", 100.0)]],
        "physical_members": [], "member_joint_incidences": [], "supports": [], "node_loads": [],
    })
    page = workspace_page(user=owner, project=fresh)
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-object-kind="GeometryNode"][data-client-key="a"]').click(force=True)
    target = page.locator('[data-object-kind="GeometryNode"][data-client-key="b"]').bounding_box()
    page.mouse.move(target["x"] + target["width"] / 2, target["y"] + target["height"] / 2)
    instruction = page.locator('[data-modeling-instruction]').text_content()
    assert "mid" in instruction and "1 个已有节点" in instruction
    page.locator('[data-object-kind="GeometryNode"][data-client-key="b"]').click(force=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    incidences = page.evaluate("""() => JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft.member_joint_incidences""")
    assert incidences == [{"member_client_key": "member-1", "node_client_key": "mid"}]


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_numeric_member_completion_previews_existing_node_before_second_enter(context, workspace_page):
    from modeling.services import save_physical_draft
    from projects.models import Project

    owner, legacy, _, _ = context
    fresh = Project.objects.create(event=legacy.event, owner_user=owner, name="数值穿越节点")
    save_physical_draft(actor=owner, project=fresh, payload={
        "schema_version": "physical-draft-v2", "expected_draft_version": 0,
        "nodes": [{"client_key": key, "x_mm": x, "y_mm": 0.0, "label": ""} for key, x in [("a", -100.0), ("mid", 0.0), ("b", 100.0)]],
        "physical_members": [], "member_joint_incidences": [], "supports": [], "node_loads": [],
    })
    page = workspace_page(user=owner, project=fresh)
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-object-kind="GeometryNode"][data-client-key="a"]').click(force=True)
    page.locator('.ux-precision summary').click()
    command = page.locator('[data-cad-command-input]')
    command.fill('100,0')
    command.press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 0
    assert 'mid' in page.locator('[data-modeling-instruction]').text_content()
    command.press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
