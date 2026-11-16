from django.urls import path
from . import views

urlpatterns = [
    path('<int:event_id>/accounts/preview/', views.provision_preview, name='provision_preview'),
    path('<int:event_id>/accounts/confirm/', views.provision_confirm, name='provision_confirm'),
    path('<int:event_id>/accounts/import/', views.provision_upload, name='provision_upload'),
    path('<int:event_id>/manage/', views.event_management, name='event_management'),
    path('<int:event_id>/participants/', views.participant_list, name='participant_list'),
    path('<int:event_id>/participants/new/', views.participant_new, name='participant_new'),
    path('<int:event_id>/participants/join/', views.participant_join, name='participant_join'),
    path('<int:event_id>/participants/<int:membership_id>/reactivate/preview/', views.participant_reactivate_preview, name='participant_reactivate_preview'),
    path('<int:event_id>/participants/<int:membership_id>/deactivate/preview/', views.participant_deactivate_preview, name='participant_deactivate_preview'),
    path('<int:event_id>/participants/confirm/', views.participant_confirm, name='participant_confirm'),
]
