from django.urls import path
from .creation_views import project_create

app_name = 'event_projects'
urlpatterns = [path('<int:event_id>/projects/create/', project_create, name='create')]
