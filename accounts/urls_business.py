from django.urls import path

from .views import event_landing


urlpatterns = [path("", event_landing)]
