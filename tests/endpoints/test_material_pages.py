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
