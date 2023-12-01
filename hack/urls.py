from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^home/', views.HomePage),
    re_path(r'^/', views.HomePage),
    re_path(r'^get-candidate-data/', views.GetCandidateData),
    re_path(r'^get-job-data/', views.GetJobData),
    re_path(r'^initate-call-campaign/', views.InitiateCallCampaign)
]
