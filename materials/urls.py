from django.urls import path

from . import views

app_name = "materials"

urlpatterns = [
    path("<int:project_id>/materials/", views.index, name="index"),
    path("<int:project_id>/materials/new/", views.material_create, name="material_create"),
    path("<int:project_id>/materials/<int:material_id>/edit/", views.material_edit, name="material_edit"),
    path("<int:project_id>/materials/<int:material_id>/delete/", views.material_delete, name="material_delete"),
    path("<int:project_id>/sections/new/", views.section_create, name="section_create"),
    path("<int:project_id>/sections/composite/new/", views.composite_section_create, name="composite_section_create"),
    path("<int:project_id>/sections/<int:section_id>/edit/", views.section_edit, name="section_edit"),
    path("<int:project_id>/sections/<int:section_id>/delete/", views.section_delete, name="section_delete"),
    path("<int:project_id>/strips/<int:strip_id>/material/", views.strip_material, name="strip_material"),
]
