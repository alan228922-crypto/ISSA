from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from projects.models import Project

from .forms import MaterialForm, RectangleSectionForm
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


@login_required
def section_edit(request, project_id, section_id):
    project = _owned_project(request, project_id)
    section = get_object_or_404(Section, pk=section_id, owner_user=request.user, section_type="RECTANGLE")
    form = RectangleSectionForm(request.POST or None, initial=_section_initial(section))
    if request.method == "POST" and form.is_valid():
        try:
            update_section(actor=request.user, section=section, name=form.cleaned_data["name"], definition=form.definition())
        except SectionServiceError:
            form.add_error(None, "请检查截面尺寸与密度。")
        else:
            return redirect("materials:index", project_id=project.id)
    return render(request, "materials/section_form.html", {"project": project, "form": form, "editing": True})
