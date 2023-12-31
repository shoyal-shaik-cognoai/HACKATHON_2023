import base64
import os
import sys
from django.shortcuts import render
import json
from hack.models import CandidateProfile, JobData, CandidateJobStatus
from hack.utils import call_campaign
from rest_framework.views import APIView
from rest_framework.response import Response
import openai
import logging
import sys
from django.views.decorators.csrf import csrf_exempt


from exohack.settings import HACK_DOMAIN

logger = logging.getLogger(__name__)

# Create your views here.


class StartIndexingAPI(APIView):
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data["Request"]
            data = json.loads(data)

        except Exception as e:
            print(e)

StartIndexing = StartIndexingAPI.as_view()

class UploadCVsAPI(APIView):
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data["Request"]
            data = json.loads(data)
            base64_data = data["base64_file"]
            print(base64_data)
            file_path = "files/CV/"
            if not os.path.exists(file_path):
                os.makedirs(file_path)

            fh = open(file_path, "wb")
            fh.write(base64.b64decode(base64_data))
            fh.close()
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(e, exc_tb.tb_lineno)
        return Response(data=response, status=response['status'])

UploadCV = UploadCVsAPI.as_view()

class CVShortlistingAPI(APIView):
    def get(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.GET

            short_list_query = data.get('short_list_query', '')
            job_pk = data.get('job_pk', '')
            job_obj = None

            if job_pk:
                job_obj = JobData.objects.filter(pk=int(job_pk)).first()
                job_obj.job_status = 'resume_shortlist'
                job_obj.save()

            openai.api_key = "05a87e3db47149699916b25e2b6a664e"
            openai.api_type = "azure"
            openai.api_base = "https://gpt3-5-sc.openai.azure.com/"
            openai.api_version = "2023-07-01-preview"
            model_used = "gpt-35-turbo-16k"
            deployment_id = "hack-16k"
            # candidate_profile_objs = CandidateProfile.objects.all()
            candidate_profile_objs = job_obj.applicable_for.all()
            candidates_phone_numbers_list = []
            for candidate_profile_obj in candidate_profile_objs:
                try:
                    chat_history = []
                    # system_prompt = """You are HR at a Tech Company who is really strict in shortlist Resumes.
                    #     You will be given a Resumes in Source, your job is to provide is that Resumes eligible base on job post.
                    #     You should look into all the aspects like skills are they related to the job post. 
                    #     Their past working experience are they related to the job post.
                    #     When asked on job role you need to very specific a techie can't be a sales and a sales guys can't be a techie.
                    #     Remember You need to provide will this person eligible based of user query just give yes or No?
                    #     If job post skills not present in the Resumes then the candidate is not eligible.
                    #     Remember You need to provide how confident are you on this candidate just give here the percentage as ResultConfidence in range 0 to 100 percentage and all should ne unique it is a must.
                    #     NOTE: Give the result in this format python dictionary only nothing else this is a must.
                    #     Example format of response: {"Name":"candidates name", "Eligible":true, "ResultConfidence":"20%" "Reason":"Person is sales person".
                    #     keep the "Reason" inside the result dictionary short and concise within 50 words strictly.

                    #    Source:
                    # """ + candidate_profile_obj.cv_content
                    # chat_history.append({'role': 'system', 'content': system_prompt})
                    # if job_obj:
                    #     chat_history.append({'role': 'user', 'content': f"Job Description is : {job_obj.job_description} and Job Role is: "})
                    # else:
                    #     chat_history.append({'role': 'user', 'content': short_list_query})

                    system_prompt = """
                        Evaluate a tech candidate's eligibility based on specific job-related skills, experience, and role alignment. Respond with 'Yes' or 'No' and indicate confidence (ResultConfidence) from 0 to 100%.

                        Check for the presence of skills such as [List specific programming languages, tools, or technologies]. Ensure previous roles match the current tech job post.

                        Provide results:
                        {"Name": "Candidate's Name", "Eligible": true/false, "ResultConfidence": "X%", "Reason": "Brief reason for eligibility"}

                        Source:
                        """  + candidate_profile_obj.cv_content

                    chat_history.append({'role': 'system', 'content': system_prompt})

                    if job_obj:
                        chat_history.append({'role': 'user', 'content': f"Job Description: {job_obj.job_description} and Job Role: "})
                    else:
                        chat_history.append({'role': 'user', 'content': short_list_query})

                    chat_completion_response = openai.ChatCompletion.create(
                        deployment_id=deployment_id,
                        model=model_used,
                        messages=chat_history,
                        temperature=0,
                        n=1,
                        stream=True,
                        presence_penalty=-2.0
                    )

                    complete_streamed_text = ""

                    for chunk in chat_completion_response:
                        try:
                            if chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("content"):
                                complete_streamed_text += chunk['choices'][0]['delta']["content"]

                            # elif chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("function_call"):
                            #     if chunk['choices'][0]['delta']["function_call"].get("name"):
                            #         function_name = chunk['choices'][0]['delta']["function_call"]["name"].strip()
                            #     if chunk['choices'][0]['delta']["function_call"].get("arguments"):
                            #         argument += chunk['choices'][0]['delta']["function_call"].get("arguments")
                            #         function_to_call = function_name
                        except Exception as e:
                            print("Inside exception")
                            print(str(e))
                            pass
                    print(json.loads(complete_streamed_text))
                    eligibility_dict = json.loads(complete_streamed_text)

                    candidate_profile_obj.confidence_percentage = eligibility_dict.get('ResultConfidence')
                    candidate_profile_obj.save()

                    if eligibility_dict.get('Eligible') and (int(eligibility_dict.get('ResultConfidence')[:-1]) >= 60):
                        candidates_phone_numbers_list.append({'name': candidate_profile_obj.candidate_name, 'phone_number': candidate_profile_obj.phone_number, 'result_reason': eligibility_dict.get('Reason'), 'confidence': eligibility_dict.get('ResultConfidence'), 'cv_file_path': HACK_DOMAIN + candidate_profile_obj.file_path})
                        job_status = CandidateJobStatus.objects.filter(job=job_obj, candidate_profile=candidate_profile_obj).first()
                        job_status.status = 'cv_shortlisted'
                        job_status.save()
                    # elif not eligibility_dict.get('Eligible') and (int(eligibility_dict.get('ResultConfidence')[:-1]) < 30):
                    #     candidates_phone_numbers_list.append({'name': candidate_profile_obj.candidate_name, 'phone_number': candidate_profile_obj.phone_number, 'result_reason': eligibility_dict.get('Reason'), 'confidence': eligibility_dict.get('ResultConfidence'), 'cv_file_path': HACK_DOMAIN + candidate_profile_obj.file_path})
                    #     job_status = CandidateJobStatus.objects.filter(job=job_obj, candidate_profile=candidate_profile_obj).first()
                    #     job_status.status = 'cv_shortlisted'
                    #     job_status.save()
                    
                    response['status'] = 200
                    response['selected_candidates'] = candidates_phone_numbers_list
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    logger.error("CVShortlistingAPI 1 %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("CVShortlistingAPI 2 %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})
        return Response(data=response, status=response['status'])

CVShortlisting = CVShortlistingAPI.as_view()

@csrf_exempt
def HomePage(request):
    try:

        logger.info("testing logs.", extra={'AppName': 'hack'})

        return render(request, 'hack/transcript.html', {
            'year': '2023'
        })

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("ECCTimeLine %s at %s",
                     str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})
        # return HttpResponse("500")
        return render(request, 'EasyChatApp/error_500.html')


class GetCandidateDataAPI(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            req_data = request.data
            job_pk = req_data.get('job_id', None)
            
            job_obj = JobData.objects.filter(pk=int(job_pk)).first()
            candidate_profile_objs = CandidateJobStatus.objects.filter(job=job_obj, status="cv_shortlisted")

            req_data = []

            for candidate_profile_obj in candidate_profile_objs:

                candidate_profile_obj = candidate_profile_obj.candidate_profile
                curr_data = {
                    "name": candidate_profile_obj.candidate_name,
                    "phone_number": candidate_profile_obj.phone_number,
                    "cv_file_path": HACK_DOMAIN + candidate_profile_obj.file_path,
                    "confidence": candidate_profile_obj.confidence_percentage,
                }

                req_data.append(curr_data)

            response['status'] = 200
            response['response'] = 'success'
            response['data'] = req_data


        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GetCandidateDataAPI %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})

        return Response(data=response, status=response['status'])
GetCandidateData = GetCandidateDataAPI.as_view()

class GetJobDataAPI(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            req_data = request.data
            logger.info(f"GetJobDataAPI req_data : {req_data}", extra={'AppName': 'hack'})

            job_pk = req_data.get('job_pk', None)

            if job_pk:
                job_obj = JobData.objects.filter(pk=int(job_pk)).first()
                curr_data = {
                        "job_title": job_obj.job_title,
                        "job_description": job_obj.job_description,
                        "job_pk": job_obj.pk,
                        "status": job_obj.job_status
                    }
                response['data'] = curr_data
                
            else:
                job_objs = JobData.objects.all()
                req_data = []

                for job_obj in job_objs:
                    
                    curr_data = {
                        "job_title": job_obj.job_title,
                        "job_description": job_obj.job_description,
                        "job_pk": job_obj.pk,
                        "status": job_obj.job_status
                    }

                    req_data.append(curr_data)
                response['data'] = req_data

            response['status'] = 200
            response['response'] = 'success'

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("GetJobDataAPI %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})

        return Response(data=response, status=response['status'])
GetJobData = GetJobDataAPI.as_view()


class InitiateCallCampaignAPI(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            req_data = request.data
            job_profile_pk = req_data.get('job_profile_pk')
            job_data_obj = JobData.objects.filter(pk=job_profile_pk).first()
            print('job_data_obj', job_data_obj)
            qualified_objs = CandidateJobStatus.objects.filter(status='cv_shortlisted', job=job_data_obj)
            print('qualified_objs', qualified_objs)
            for objs in qualified_objs:
                candidate_profile = objs.candidate_profile
                job_description = job_data_obj.job_description
                job_title = job_data_obj.job_title
                system_prompt = """You are an HR professional conducting a telephonic interview for a Software Engineer position at a tech company. Your task is to craft five succinct interview questions, each requiring a short answer, directly aligned with the following job description. Please format your questions as shown below:
                        {
                        "q1": "Question 1 (short answer)",
                        "q2": "Question 2 (short answer)",
                        "q3": "Question 3 (short answer)",
                        "q4": "Question 4 (short answer)",
                        "q5": "Question 5 (short answer)"
                        }


                    Job Description:

                    """ + job_description + f"Please provide concise questions suitable for a telephonic interview that help gauge candidates' qualifications and suitability for the {job_title} role."
    
                openai.api_key = "05a87e3db47149699916b25e2b6a664e"
                openai.api_type = "azure"
                openai.api_base = "https://gpt3-5-sc.openai.azure.com/"
                openai.api_version = "2023-07-01-preview"
                model_used = "gpt-35-turbo-16k"
                deployment_id = "hack-16k"
                chat_history = [{'role': 'system', 'content': system_prompt}]
                chat_completion_response = openai.ChatCompletion.create(
                    deployment_id=deployment_id,
                    model=model_used,
                    messages=chat_history,
                    temperature=0,
                    n=1,
                    stream=True,
                    presence_penalty=-2.0
                )

                complete_streamed_text = ""

                for chunk in chat_completion_response:
                    try:
                        if chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("content"):
                            complete_streamed_text += chunk['choices'][0]['delta']["content"]
                    except Exception as e:
                        print("Inside exception")
                        print(str(e))
                        pass
                print(complete_streamed_text)
                candidate_profile.questions_to_be_asked = complete_streamed_text
                candidate_profile.save(update_fields=["questions_to_be_asked"])
                call_campaign(str(candidate_profile.phone_number))
                objs.status = "Screening Inprogress"
                objs.save(update_fields=['status'])
            response['status'] = 200
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(e, exc_tb.tb_lineno)
            logger.error("InitiateCallCampaignAPI %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})
        return Response(data=response, status=response['status'])

InitiateCallCampaign = InitiateCallCampaignAPI.as_view()

class VoiceScreeningResultsAPI(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            req_data = request.data
            job_id = req_data.get('job_id')
            job_obj = JobData.objects.filter(pk=job_id).first()
            print('job_obj', job_obj)
            candy_obj = CandidateJobStatus.objects.filter(status__in=['Qualified Call Screening', 'Disqualified Call Screening'], job=job_obj)
            print('candy_obj', candy_obj)
            ans = []
            for obj in candy_obj:
                candidate_name = obj.candidate_profile.candidate_name
                candidate_profile_pk = obj.candidate_profile.pk
                status = obj.status
                ans.append([candidate_name, candidate_profile_pk, status])
            response['ans_list'] = ans
            response['status'] = 200
        except Exception as e:
            response['error'] = e
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(e, exc_tb.tb_lineno)
            logger.error("GetJobDataAPI %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})
        return Response(data=response, status=response['status'])

VoiceScreeningResults = VoiceScreeningResultsAPI.as_view()


@csrf_exempt
def TranscriptGenerator(request):
    try:
        print('TranscriptGenerator')
        logger.info("testing logs.", extra={'AppName': 'hack'})
        data = request.GET
        print(data)

        return render(request, 'hack/transcript-generator.html', {
            'transcript': json.loads(CandidateProfile.objects.filter(pk=data.get('profile_pk')).first().call_interview_transcript)
        })

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("TranscriptGenerator %s at %s",
                     str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})

        return render(request, 'EasyChatApp/error_500.html')