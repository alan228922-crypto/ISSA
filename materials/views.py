from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from projects.models import Project

from .forms import CompositeComponentFormSet, CompositeSectionForm, MaterialForm, RectangleSectionForm
from .models import Material, Section
from .services import SectionServiceError, create_section, update_section


def _owned_project(request, project_id):
    return get_object_or_404(Project, pk=project_id, owner_user=request.user)


def _section_initial(section):
    definition = section.definition_json
    return {
        "name": section.name,
        "width_mm": definition.get("width_mm"),
        "height_mm": definition.get("height_mm"),
        "density_g_per_mm3": definition.get("density_g_per_mm3"),
    }


@login_required
def index(request, project_id):
    project = _owned_project(request, project_id)
    return render(request, "materials/index.html", {
        "project": project,
        "materials": Material.objects.filter(owner_user=request.user).order_by("name", "id"),
        "sections": Section.objects.filter(owner_user=request.user).order_by("name", "id"),
    })


@login_required
def material_create(request, project_id):
    project = _owned_project(request, project_id)
    form = MaterialForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        material = form.save(commit=False)
        material.owner_user = request.user
        material.save()
        return redirect("materials:index", project_id=project.id)
    return render(request, "materials/material_form.html", {"project": project, "form": form, "editing": False})


@login_required
def material_edit(request, project_id, material_id):
    project = _owned_project(request, project_id)
    material = get_object_or_404(Material, pk=material_id, owner_user=request.user)
    form = MaterialForm(request.POST or None, instance=material)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("materials:index", project_id=project.id)
    return render(request, "materials/material_form.html", {"project": project, "form": form, "editing": True})


@login_required
def section_create(request, project_id):
    project = _owned_project(request, project_id)
    form = RectangleSectionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_section(owner=request.user, name=form.cleaned_data["name"], definition=form.definition())
        except SectionServiceError:
            form.add_error(None, "请检查截面尺寸与密度。")
        else:
            return redirect("materials:index", project_id=project.id)
    return render(request, "materials/section_form.html", {"project": project, "form": form, "editing": False})


def _composite_editor(request, project, section=None):
    initial = section.definition_json.get("components", []) if section else None
    form = CompositeSectionForm(request.POST or None, initial={"name": section.name} if section else None)
    formset = CompositeComponentFormSet(request.POST or None, initial=initial, prefix="components")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        components = [row.definition() for row in formset.forms if row.cleaned_data and not row.cleaned_data.get("DELETE")]
        if not components:
            form.add_error(None, "请至少保留一个矩形组件。")
        else:
            definition = {"schema_version": "section-definition-v1", "type": "composite", "components": components}
            try:
                if section:
                    update_section(actor=request.user, section=section, name=form.cleaned_data["name"], definition=definition)
                else:
                    create_section(owner=request.user, name=form.cleaned_data["name"], definition=definition)
            except SectionServiceError as exc:
                form.add_error(None, "矩形组件不能重叠，请调整位置或尺寸。" if str(exc) == "OVERLAP_UNSUPPORTED" else "请检查组件尺寸、位置与密度。")
            else:
                return redirect("materials:index", project_id=project.id)
    return render(request, "materials/composite_section_form.html", {
        "project": project, "form": form, "formset": formset, "editing": bool(section),
    })


@login_required
def composite_section_create(request, project_id):
    project = _owned_project(request, project_id)
    return _composite_editor(request, project)


@login_required
def section_edit(request, project_id, section_id):
    project = _owned_project(request, project_id)
    section = get_object_or_404(Section, pk=section_id, owner_user=request.user)
    if section.section_type == "COMPOSITE":
        return _composite_editor(request, project, section)
    if section.section_type != "RECTANGLE":
        raise Http404("不支持编辑此截面类型")
    form = RectangleSectionForm(request.POST or None, initial=_section_initial(section))
    if request.method == "POST" and form.is_valid():
        try:
            update_section(actor=request.user, section=section, name=form.cleaned_data["name"], definition=form.definition())
        except SectionServiceError:
            form.add_error(None, "请检查截面尺寸与密度。")
        else:
            return redirect("materials:index", project_id=project.id)
    return render(request, "materials/section_form.html", {"project": project, "form": form, "editing": True})
