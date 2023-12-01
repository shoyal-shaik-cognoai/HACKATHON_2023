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


    def __str__(self):
        return self.candidate_name

    class Meta:
        verbose_name = 'CandidateProfile'
        verbose_name_plural = 'CandidateProfile'

class JobData(models.Model):

    job_title = models.CharField(max_length=200)

    job_description = models.TextField(null=True, blank=True, help_text="job_description")

    # user = models.ForeignKey(CandidateProfile, null=True,blank=True, on_delete=models.CASCADE)

    applicable_for = models.ManyToManyField('CandidateProfile', blank=True, help_text="CandidateProfile")

    def __str__(self):
        return self.job_title

    class Meta:
        verbose_name = 'JobData'
        verbose_name_plural = 'JobData'