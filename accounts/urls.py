from django.urls import path
from .views import AccountLoginView,AccountLogoutView,password_change

app_name='accounts'
urlpatterns=[path('login/',AccountLoginView.as_view(),name='login'),path('logout/',AccountLogoutView.as_view(),name='logout'),path('password-change/',password_change,name='password_change')]
