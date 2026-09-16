from django.urls import path

from . import views


app_name = 'projects'

urlpatterns = [
    path('<int:project_id>/model/save/', views.model_save, name='model_save'),
    path('<int:project_id>/model/check/', views.model_check, name='model_check'),
    path('<int:project_id>/analyze/', views.analyze, name='analyze'),
    path('<int:project_id>/analyses/<int:run_id>/data/', views.analysis_data, name='analysis_data'),
    path('<int:project_id>/analyses/<int:run_id>/comparison/', views.analysis_comparison, name='analysis_comparison'),
    path('<int:project_id>/analyses/<int:run_id>/explanation/', views.analysis_explanation, name='analysis_explanation'),
    path('<int:project_id>/sections/preview/', views.section_preview, name='section_preview'),
]
