from django.urls import re_path
from . import views

urlpatterns = [
    # General ChatBot
    # re_path(r'^$', views.EasyChatHomePage),
    # re_path(r'^login/', views.Login),  # RenderLogin page
    re_path(r'^test/', views.TestPage),
    # re_path(r'^logout/', views.Logout, name="logout-api"),  # Logout
    # re_path(r'^set-session-time-limit/', views.SetSessionTimeLimit),
    # re_path(r'^authentication/', views.LoginSubmit),  # Authentication
]
