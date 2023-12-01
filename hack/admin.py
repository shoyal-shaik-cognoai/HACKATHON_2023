from django.contrib import admin

from hack.models import CandidateProfile, JobData

# Register your models here.
admin.site.register(CandidateProfile)

admin.site.register(JobData)