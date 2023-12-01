import base64
import os
import sys
from django.shortcuts import render
import json
from hack.models import CandidateProfile, JobData, CandidateJobStatus
from rest_framework.views import APIView
from rest_framework.response import Response
import openai
import logging
import sys

from hack.views import logger

from exohack.settings import BASE_DIR
from hack.text_extraction import *

from scripts.job_description import DATA_SCIENTIST, SOFTWARE_ENGINEER

try:
    from django.contrib.auth import get_user_model

    User = get_user_model()

    if User.objects.all():
        Test_var = False
except:
    pass


def setup():
    try:
        analyze_general_documents(
            name="Maruthi", phone="918074928457", file_path="media/cv5.pdf")
        analyze_general_documents(
            name="Akash", phone="918074928457", file_path="media/cv4.pdf")
        analyze_general_documents(
            name="Aditya", phone="918074928457", file_path="media/cv3.pdf")
        analyze_general_documents(
            name="Rahul", phone="918074928457", file_path="media/cv2.pdf")
        analyze_general_documents(
            name="Jana", phone="918074928457", file_path="media/cv1.pdf")

        user = User.objects.create(
            username='admin', password='adminadmin', email="admin@exotel.com")

        JobData.objects.create(job_title="Data Scientist",
                               job_description=DATA_SCIENTIST)
        JobData.objects.create(job_title="Software Engineer",
                               job_description=SOFTWARE_ENGINEER)

        job_datas = JobData.objects.all()
        candidate_profiles = CandidateProfile.objects.all()

        for job_data in job_datas:
            for candidate_profile in candidate_profiles:
                CandidateJobStatus.objects.create(
                    candidate_profile=candidate_profile, job=job_data, status="applied")

    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("setup %s at %s",
                     str(err), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})


def reset():
    try:
        job_status = CandidateJobStatus.objects.all()
        for data in job_status:
            data.status = "applied"
            data.save()

        job_data = JobData.objects.all()
        for data in job_data:
            data.job_status = 'pending'
            data.save()

    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("reset %s at %s",
                     str(err), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})
