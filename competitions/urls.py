from django.urls import path
from .views import provision_confirm,provision_preview

urlpatterns=[path('<int:event_id>/accounts/preview/',provision_preview,name='provision_preview'),path('<int:event_id>/accounts/confirm/',provision_confirm,name='provision_confirm')]
