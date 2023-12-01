from django.contrib import admin

from hack.models import CandidateProfile, JobData, CandidateJobStatus

# Register your models here.
admin.site.register(CandidateProfile)

admin.site.register(JobData)

admin.site.register(CandidateJobStatus)