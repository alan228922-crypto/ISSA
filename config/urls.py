"""项目路由将在 M2 按应用注册。"""
from django.urls import include, path

urlpatterns = [
    path("accounts/", include("accounts.urls")),
    path("events/", include("accounts.urls_business")),
    path("competitions/", include("competitions.urls")),
    path("projects/", include("projects.urls")),
    path("projects/", include("learning.urls")),
]
