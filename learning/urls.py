from django.urls import path

from . import views


app_name = "learning"

urlpatterns = [
    path("<int:project_id>/analyses/<int:run_id>/reasoning/", views.reasoning_detail, name="reasoning_detail"),
    path("<int:project_id>/analyses/<int:run_id>/reflection/", views.reflection_detail, name="reflection_detail"),
    path("<int:project_id>/analyses/<int:run_id>/reflection/complete/", views.reflection_complete, name="reflection_complete"),
    path("<int:project_id>/predictions/", views.prediction_create, name="prediction_create"),
    path("<int:project_id>/predictions/current/", views.prediction_current, name="prediction_current"),
    path(
        "<int:project_id>/predictions/<int:prediction_id>/complete/",
        views.prediction_complete,
        name="prediction_complete",
    ),
    path(
        "<int:project_id>/predictions/<int:prediction_id>/",
        views.prediction_detail,
        name="prediction_detail",
    ),
]
