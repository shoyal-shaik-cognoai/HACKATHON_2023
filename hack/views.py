import base64
import os
import sys
from django.shortcuts import render
import json
from hack.models import CandidateProfile
from rest_framework.views import APIView
from rest_framework.response import Response
import openai
import logging
import sys

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

            short_list_query = data['short_list_query']

            openai.api_key = "93395151f1634e67bd1d3017437e033d"
            openai.api_type = "azure"
            openai.api_base = "https://exotel-cogno-openai.openai.azure.com/"
            openai.api_version = "2023-07-01-preview"
            model_used = "gpt-3.5-turbo-16k"
            deployment_id = "bajaj-finserv-markets"
            candidate_profile_objs = CandidateProfile.objects.all()
            candidates_phone_numbers_list = []
            for candidate_profile_obj in candidate_profile_objs:
                try:
                    chat_history = []
                    system_prompt = """You are HR at a Tech Company who is really strict in shortlist CVs.
                        You will be given a CV in Source, your job is to provide is that CV eligible base on user query.
                        You should look into all the aspects like skills are they related to the user query. 
                        Their past working experience are they related to the user query.
                        When asked on job role you need to very specific a techie can't be a sales and a soles guys can't be a techie.
                        Remember You need to provide will this person eligible based of user query just give yes or No?
                        If user query not present in the CV then the candidate is uneligible.
                        Remember You need to provide how confident are you on this just give here the percentage.
                        Give in this format dictionary E.g. {"Name":"candiadate name", "Eligible":true, "ResultConfidence":"70%" "Reason":"Person is sales person"
                        Source :
                    """ + candidate_profile_obj.cv_content
                    chat_history.append({'role': 'system', 'content': system_prompt})
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

                    if eligibility_dict.get('Eligible') and (int(eligibility_dict.get('ResultConfidence')[:-1]) > 50):
                        candidates_phone_numbers_list.append({'name': candidate_profile_obj.candidate_name, 'phone_number': candidate_profile_obj.phone_number, 'result_reason': eligibility_dict.get('Reason')})
                    elif not eligibility_dict.get('Eligible') and (int(eligibility_dict.get('ResultConfidence')[:-1]) < 30):
                        candidates_phone_numbers_list.append({'name': candidate_profile_obj.candidate_name, 'phone_number': candidate_profile_obj.phone_number, 'result_reason': eligibility_dict.get('Reason')})
                    
                    response['status'] = 200
                    response['selected_candidates'] = candidates_phone_numbers_list
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    print(e, exc_tb.tb_lineno)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(e, exc_tb.tb_lineno)
        return Response(data=response, status=response['status'])

CVShortlisting = CVShortlistingAPI.as_view()


def TestPage(request):
    try:

        logger.info("testing logs.", extra={'AppName': 'hack'})

        return render(request, 'hack/test.html', {
            'year': '2023'
        })

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("ECCTimeLine %s at %s",
                     str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})
        # return HttpResponse("500")
        return render(request, 'EasyChatApp/error_500.html')
