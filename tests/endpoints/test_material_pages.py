from decimal import Decimal

import pytest
from django.urls import reverse

from tests.application.test_physical_draft import context


@pytest.mark.django_db
def test_material_pages_require_login_and_owner_scope(context, client):
    from accounts.models import User
    from materials.models import Material, Section

    owner, project, material, section = context
    assert client.get(reverse("materials:index", kwargs={"project_id": project.id})).status_code == 302

    other = User.objects.create_user("material-page-other", password="pass")
    client.force_login(other)
    assert client.get(reverse("materials:index", kwargs={"project_id": project.id})).status_code == 404
    assert client.post(
        reverse("materials:material_edit", kwargs={"project_id": project.id, "material_id": material.id}),
        {"name": "越权", "E_MPa": "3000", "density_g_per_mm3": "0.0008", "source_type": "MEASURED"},
    ).status_code == 404
    assert Material.objects.get(pk=material.id).name == "竹材"
    assert Section.objects.get(pk=section.id).name == "矩形"


@pytest.mark.django_db
def test_owner_creates_and_edits_material_with_p0_units(context, client):
    from materials.models import Material

    owner, project, _, _ = context
    client.force_login(owner)
    create_url = reverse("materials:material_create", kwargs={"project_id": project.id})
    response = client.post(create_url, {
        "name": "试验竹材",
        "E_MPa": "2000",
        "density_g_per_mm3": "0.0007",
        "tensile_strength_MPa": "",
        "compressive_strength_MPa": "",
        "source_type": "MEASURED",
        "note": "学生实测",
    })
    material = Material.objects.get(name="试验竹材")
    assert response.status_code == 302
    assert material.owner_user == owner
    assert material.E_MPa == Decimal("2000")
    assert material.density_g_per_mm3 == Decimal("0.000700000")

    response = client.post(
        reverse("materials:material_edit", kwargs={"project_id": project.id, "material_id": material.id}),
        {
            "name": "修订竹材",
            "E_MPa": "2100",
            "density_g_per_mm3": "0.0008",
            "tensile_strength_MPa": "",
            "compressive_strength_MPa": "",
            "source_type": "MEASURED",
            "note": "复测",
        },
    )
    material.refresh_from_db()
    assert response.status_code == 302
    assert material.name == "修订竹材"
    assert material.E_MPa == Decimal("2100")


@pytest.mark.django_db
def test_owner_creates_and_edits_safe_rectangular_section(context, client):
    from materials.models import Section

    owner, project, _, _ = context
    client.force_login(owner)
    response = client.post(
        reverse("materials:section_create", kwargs={"project_id": project.id}),
        {"name": "1×6 条材截面", "width_mm": "1", "height_mm": "6", "density_g_per_mm3": "0.0007"},
    )
    section = Section.objects.get(name="1×6 条材截面")
    assert response.status_code == 302
    assert section.owner_user == owner
    assert section.section_type == "RECTANGLE"
    assert section.properties_json["A_mm2"] == pytest.approx(6.0)
    assert "components" not in response.wsgi_request.POST

    response = client.post(
        reverse("materials:section_edit", kwargs={"project_id": project.id, "section_id": section.id}),
        {"name": "2×6 条材截面", "width_mm": "2", "height_mm": "6", "density_g_per_mm3": "0.0007"},
    )
    section.refresh_from_db()
    assert response.status_code == 302
    assert section.name == "2×6 条材截面"
    assert section.properties_json["A_mm2"] == pytest.approx(12.0)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_name", "payload"),
    [
        ("material_create", {"name": "坏材料", "E_MPa": "0", "density_g_per_mm3": "-1", "source_type": "MEASURED"}),
        ("section_create", {"name": "坏截面", "width_mm": "0", "height_mm": "6", "density_g_per_mm3": "0.0007"}),
        ("material_create", {"name": "非有限材料", "E_MPa": "NaN", "density_g_per_mm3": "0.0007", "source_type": "MEASURED"}),
        ("section_create", {"name": "非有限截面", "width_mm": "Infinity", "height_mm": "6", "density_g_per_mm3": "0.0007"}),
    ],
)
def test_invalid_material_or_section_stays_on_form_without_writing(context, client, route_name, payload):
    from materials.models import Material, Section

    owner, project, _, _ = context
    client.force_login(owner)
    before = (Material.objects.count(), Section.objects.count())
    response = client.post(reverse(f"materials:{route_name}", kwargs={"project_id": project.id}), payload)
    assert response.status_code == 200
    assert (Material.objects.count(), Section.objects.count()) == before
    assert "请检查" in response.content.decode()


def _composite_payload(*, overlap=False, empty=False):
    rows = [] if empty else [
        ("60", "10", "0", "45"),
        ("10", "80", "0", "0" if not overlap else "40"),
    ]
    payload = {"name": "组合 H", "components-TOTAL_FORMS": str(len(rows)), "components-INITIAL_FORMS": "0", "components-MIN_NUM_FORMS": "0", "components-MAX_NUM_FORMS": "1000"}
    for index, (width, height, x, y) in enumerate(rows):
        prefix = f"components-{index}-"
        payload.update({prefix + "width_mm": width, prefix + "height_mm": height, prefix + "center_x_mm": x, prefix + "center_y_mm": y, prefix + "angle_deg": "0", prefix + "density_g_per_mm3": "0.0007"})
    return payload


@pytest.mark.django_db
def test_owner_creates_reopens_and_edits_composite_section(context, client):
    from materials.models import Section

    owner, project, _, _ = context
    client.force_login(owner)
    url = reverse("materials:composite_section_create", kwargs={"project_id": project.id})
    assert client.get(url).status_code == 200
    response = client.post(url, _composite_payload())
    assert response.status_code == 302
    section = Section.objects.get(name="组合 H")
    assert section.section_type == "COMPOSITE"
    assert len(section.definition_json["components"]) == 2
    assert section.properties_json["A_mm2"] == pytest.approx(1400)
    edit = reverse("materials:section_edit", kwargs={"project_id": project.id, "section_id": section.id})
    response = client.get(edit)
    assert response.status_code == 200
    assert b'components-0-width_mm' in response.content
    payload = _composite_payload()
    payload["name"] = "组合 H 修订"
    payload["components-INITIAL_FORMS"] = "2"
    payload["components-1-center_x_mm"] = "5"
    assert client.post(edit, payload).status_code == 302
    section.refresh_from_db()
    assert section.name == "组合 H 修订"
    assert section.definition_json["components"][1]["center_x_mm"] == 5


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["overlap", "empty"])
def test_invalid_composite_does_not_save(context, client, kind):
    from materials.models import Section

    owner, project, _, _ = context
    client.force_login(owner)
    before = Section.objects.count()
    response = client.post(reverse("materials:composite_section_create", kwargs={"project_id": project.id}), _composite_payload(overlap=kind == "overlap", empty=kind == "empty"))
    assert response.status_code == 200
    assert Section.objects.count() == before
    assert "重叠" in response.content.decode() if kind == "overlap" else "至少" in response.content.decode()


@pytest.mark.django_db
def test_composite_pages_are_owner_scoped(context, client):
    from accounts.models import User
    from materials.models import Section
    from materials.services import create_section

    owner, project, _, section = context
    other = User.objects.create_user("composite-other", password="pass")
    client.force_login(other)
    url = reverse("materials:composite_section_create", kwargs={"project_id": project.id})
    assert client.get(url).status_code == 404
    assert client.post(url, _composite_payload()).status_code == 404
    edit = reverse("materials:section_edit", kwargs={"project_id": project.id, "section_id": section.id})
    assert client.get(edit).status_code == 404
    composite = create_section(owner=owner, name="私有组合", definition={
        "schema_version": "section-definition-v1", "type": "composite", "components": [
            {"width_mm": 1, "height_mm": 2, "center_x_mm": 0, "center_y_mm": 0, "angle_deg": 0, "density_g_per_mm3": 0.0007},
        ],
    })
    composite_edit = reverse("materials:section_edit", kwargs={"project_id": project.id, "section_id": composite.id})
    assert client.get(composite_edit).status_code == 404
    assert client.post(composite_edit, _composite_payload()).status_code == 404
    assert Section.objects.get(pk=composite.id).name == "私有组合"


@pytest.mark.django_db
def test_composite_edit_rejects_deleting_all_components_and_preserves_saved_definition(context, client):
    from materials.models import Section

    owner, project, _, _ = context
    client.force_login(owner)
    client.post(reverse("materials:composite_section_create", kwargs={"project_id": project.id}), _composite_payload())
    section = Section.objects.get(name="组合 H")
    original = section.definition_json
    payload = _composite_payload()
    payload["components-INITIAL_FORMS"] = "2"
    payload["components-0-DELETE"] = "on"
    payload["components-1-DELETE"] = "on"
    response = client.post(reverse("materials:section_edit", kwargs={"project_id": project.id, "section_id": section.id}), payload)
    section.refresh_from_db()
    assert response.status_code == 200
    assert "至少" in response.content.decode()
    assert section.definition_json == original
