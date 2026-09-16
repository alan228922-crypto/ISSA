from django.urls import path

from . import views


app_name = "learning"

urlpatterns = [
    path("<int:project_id>/predictions/", views.prediction_create, name="prediction_create"),
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
