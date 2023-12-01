from django.db import models

# Create your models here.
class CandidateProfile(models.Model):

    candidate_name = models.CharField(max_length=200)

    cv_content = models.TextField(
        null=True, blank=True, help_text="cv_content")

    phone_number = models.IntegerField()

    call_interview_transcript = models.TextField(
        null=True, blank=True, help_text="call_interview_transcript")

    file_path = models.TextField(null=True, blank=True)

    confidence_percentage = models.CharField(null=True, blank=True, max_length=10)

    questions_to_be_asked = models.TextField(
        null=True, blank=True, help_text="questions_to_be_asked")

    is_screening_done = models.BooleanField(default=False)

    def __str__(self):
        return self.candidate_name

    class Meta:
        verbose_name = 'CandidateProfile'
        verbose_name_plural = 'CandidateProfile'

class JobData(models.Model):

    job_title = models.CharField(max_length=200)

    job_description = models.TextField(null=True, blank=True, help_text="job_description")

    applicable_for = models.ManyToManyField('CandidateProfile', blank=True, help_text="CandidateProfile")

    job_status = models.CharField(max_length=200, default='pending')

    def __str__(self):
        return self.job_title

    class Meta:
        verbose_name = 'JobData'
        verbose_name_plural = 'JobData'


class CandidateJobStatus(models.Model):

    status = models.CharField(max_length=200, default="applied")

    candidate_profile = models.ForeignKey('CandidateProfile', null=True, blank=True, on_delete=models.SET_NULL)

    job = models.ForeignKey('JobData', null=True, blank=True, on_delete=models.SET_NULL)

    call_screening_score = models.IntegerField(null=True, blank=True, help_text="call_screening_score")

    def __str__(self):
        return str(self.status) + " - " + str(self.candidate_profile.candidate_name) + " - " + str(self.job.job_title)

    class Meta:
        verbose_name = 'CandidateJobStatus'
        verbose_name_plural = 'CandidateJobStatus'