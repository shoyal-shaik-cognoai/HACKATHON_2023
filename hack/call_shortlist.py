import json
from hack.models import CandidateJobStatus, CandidateProfile
import openai

openai.api_key = "05a87e3db47149699916b25e2b6a664e"
openai.api_type = "azure"
openai.api_base = "https://swedencentral.api.cognitive.microsoft.com/"
openai.api_version = "2023-07-01-preview"

while True:
    candidate_obj = CandidateProfile.objects.filter(is_screening_done=False)
    print('candidate_obj', candidate_obj)
    for obj in candidate_obj:
        if not obj.call_interview_transcript:
            continue
        prompt = """
            You will have full conversation between a interviewer and candidate in Source.
            You need to give a score for every question out of 10.
            You should return in the formate of {"q1": 7, "q2": 3, "q3": 9.2, "q4": 8, q5: "1"}

            Source:

        """ + obj.call_interview_transcript

        messages = [{'role': 'system', 'content': prompt}]

        chat_completion_response = openai.ChatCompletion.create(
            deployment_id="hack-16k",
            model="gpt-3.5-turbo-16k",
            messages=messages,
            temperature=0.2,
            n=1,
            presence_penalty=-2.0,
        )

        chat_content = chat_completion_response.choices[0].message.content
        print('chat_content', chat_content)
        obj.is_screening_done = True
        obj.save(update_fields=["is_screening_done"])
        call_screening_score = sum(json.loads(chat_content).values())
        if call_screening_score > 20:
            can_job_sta_obj = CandidateJobStatus.objects.filter(candidate_profile=obj).first()
            can_job_sta_obj.status = "Qualified Call Screening"
        else:
            can_job_sta_obj = CandidateJobStatus.objects.filter(candidate_profile=obj).first()
            can_job_sta_obj.status = "Disqualified Call Screening"
        can_job_sta_obj.call_screening_score = call_screening_score
        can_job_sta_obj.save(update_fields=['status', 'call_screening_score'])