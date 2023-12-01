import io
import sys
import json
# import boto3
import base64
from hack.models import CandidateProfile
import openai
import logging
import time
import azure.cognitiveservices.speech as speechsdk
from channels.generic.websocket import AsyncWebsocketConsumer
import librosa
import soundfile as sf
from asgiref.sync import sync_to_async


logger = logging.getLogger(__name__)

class ExoDevWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.use_azure = True
        self.recognised_transcript = ""
        self.stream_sid = None
        self.is_silent_packet_sent = False
        self.need_to_send_clear_packet = False
        self.sample_rate = 8000
        self.rate_of_frequency = 8000
        self.speech_interval = time.time()
        self.assistant_name = "Kajal"
        self.current_stage = ""
        self.scheduler = None
        self.job_role = "Software Engineer"
        self.chat_history_for_summarisation = []
        self.chat_history_for_summarisation.append({f"{self.assistant_name}": f"Hello, I am {self.assistant_name} HR from Exohire. As you applied for job in Exohire, we would like to congratulate you as your CV is shortlisted for current Screening Test. Is this right time to speak with you?"})
        self.common_prompt = """
            You are an HR interviewer you have talk call interview.
            Candidate will never ask a question.
            If user asks to repeat the question you have to repeat the question.
            Remeber after asking question never ask the for the answer twice.
        """
        self.system_prompt = self.common_prompt + """You have asked the user if they would want to continue for the interview

            If during conversation candidate says yes then you need to call proceed_with_interview function.
            If during conversation candidate says no  then you need to call ask_for_time_slot function.
        """
        self.functions = [
            {
                    "name": "proceed_with_interview",
                    "description": "Based on the ongoing conversation, if the candidate says yes, this function needs to be called.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
            },
            {
                    "name": "ask_for_time_slot",
                    "description": "Based on the ongoing conversation, if the candidate says no, this function needs to be called.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
            }]
        
        self.questions_dict = {"q1": "What is your name", "q2": "what is your job role?", "q3": "Why you want to join our company","q4": "why you leaving your previous company","q5": "How much salary you are expecting?"}
        self.stage_wise_questions = {
            "ask_for_time_slot": "I understand, can you please provide time slot that we can call?",
            "proceed_with_interview": "shall we proceed ahead to as I will ask few question you need to answer them as per you knowledge",
            "question_1": self.questions_dict['q1'],
            "question_2": self.questions_dict['q2'],
            "question_3": self.questions_dict['q3'],
            "question_4": self.questions_dict['q4'],
            "question_5": self.questions_dict['q5'],
            "close_interview": "Thank you for answering the question we will get back to you for next round",
            "interview_time_slot": "Thank you for providing time we will get back to you then.",
            "declining_offer": "Thank you for applying, ask you haven't provided any furture time slots we need to discontinue here",
        }
        self.question_1_prompt = self.common_prompt + f"""you have asked this question {self.questions_dict['q1']}

            If during conversation candidate provides the response just call question_2 function.
        """
        self.question_2_prompt = self.common_prompt+ f"""You have asked the next question which is  {self.questions_dict['q2']}
        
            If during conversation candidate provides the whole answer then you need to call question_3 function.
        """
        self.question_3_prompt = self.common_prompt + f"""You have asked the next question which is  {self.questions_dict['q3']}
        
            If during conversation candidate provides the whole answer then you need to call question_4 function.
        """
        self.question_4_prompt = self.common_prompt + f"""You have asked the next question which is  {self.questions_dict['q4']}
        
            If during conversation candidate provides the whole answer then you need to call question_5 function.
        """
        self.question_5_prompt = self.common_prompt + f"""You have asked the next question which is  {self.questions_dict['q5']}
        
            If during conversation candidate provides the whole answer then you need to call close_interview function.
        """
        
        self.ask_for_time_slot_functions = [{
                "name": "question_1",
                "description": "Based on the ongoing conversation, if the user provides the response for question 1, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer_1": {
                            "type": "string",
                            "description": "The response user provides",
                        }
                    },
                    "required": ["answer_1"],
                },
            },
            {
                "name": "declining_offer",
                "description": "Based on the ongoing conversation, if the user do not want to provide time slot, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                    }
            },
        ]
        self.ask_for_time_slot_prompt = self.common_prompt + """User have declined to take the interview you have asked for time slot 

            If during conversation customer provides time slot then you need to call interview_time_slot function.
            If during conversation customer provides do not want to provide time slot then you need to call declining_offer function.
        """

        self.proceed_with_interview_functions = [{
                "name": "question_1",
                "description": "Based on the ongoing conversation, if the user candidate says yes, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                    "name": "ask_for_time_slot",
                    "description": "Based on the ongoing conversation, if the user says no that they can not process with interview, this function needs to be called.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
            }
        ]
        self.proceed_with_interview_prompt = self.common_prompt + f"""You have asked user whether you should go ahead with the interview as you will ask few basic question
        
            If during conversation candidate says yes then you need to call question_1 function.
            If during conversation candidate says no then you need to call ask_for_time_slot function.
        """

        self.ask_for_time_slot_functions = [{
                "name": "interview_time_slot",
                "description": "Based on the ongoing conversation, if the user sprovides time slot, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "time_slot": {
                            "type": "string",
                            "description": "The time slot when user want to take interview",
                        }
                    },
                    "required": ["time_slot"],
                },
            },
            {
                "name": "declining_offer",
                "description": "Based on the ongoing conversation, if the user do not want to provide time slot, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                    }
            },
        ]

        self.question_1_functions = [
            {
                "name": "question_2",
                "description": "Based on the ongoing conversation, if the user provides the response for question 1, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer_1": {
                            "type": "string",
                            "description": "The response user provides",
                        }
                    },
                    "required": ["answer_1"],
                },
            },
        ]

        self.question_2_functions = [
            {
                "name": "question_3",
                "description": "Based on the ongoing conversation, if the user provides the response for question 2, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer_2": {
                            "type": "string",
                            "description": "The response user provides",
                        }
                    },
                    "required": ["answer_2"],
                },
            },
        ]

        self.question_3_functions = [
            {
                "name": "question_4",
                "description": "Based on the ongoing conversation, if the user provides the response for question 3, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer_3": {
                            "type": "string",
                            "description": "The response user provides",
                        }
                    },
                    "required": ["answer_3"],
                },
            },
        ]

        self.question_4_functions = [
            {
                "name": "question_5",
                "description": "Based on the ongoing conversation, if the user provides the response for question 4, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer_4": {
                            "type": "string",
                            "description": "The response user provides",
                        }
                    },
                    "required": ["answer_4"],
                },
            },
        ]

        self.question_5_functions = [
            {
                "name": "close_interview",
                "description": "Based on the ongoing conversation, if the user have provided all the reponses for the questions this function will wrap up the call, this function needs to be called.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                    }
            },
        ]

        self.stage_wise_prompts = {
            "ask_for_time_slot": self.ask_for_time_slot_prompt,
            "proceed_with_interview": self.proceed_with_interview_prompt,
            "question_1": self.question_1_prompt,
            "question_2": self.question_2_prompt,
            "question_3": self.question_3_prompt,
            "question_4": self.question_4_prompt,
            "question_5": self.question_5_prompt,
            "interview_time_slot": "",
            "close_interview": "",
            "end_call": "",
        }
        self.stage_wise_functions = {
            "ask_for_time_slot": self.ask_for_time_slot_functions,
            "proceed_with_interview": self.proceed_with_interview_functions,
            "question_1": self.question_1_functions,
            "question_2": self.question_2_functions,
            "question_3": self.question_3_functions,
            "question_4": self.question_4_functions,
            "question_5": self.question_5_functions,
            "interview_time_slot": [{}],
            "close_interview": [{}],
            "end_call": [{}],
        }
        self.chat_history = [{"role": "system", "content": self.system_prompt}]
        self.initial_response = False
        if self.use_azure:
            self.azure_api_key = "ac66d249a6884d67acc915866ffc28d5"
            self.azure_region = "swedencentral"
            self.speech_config = speechsdk.SpeechConfig(subscription=self.azure_api_key, region=self.azure_region)
            self.wave_format = speechsdk.audio.AudioStreamFormat(samples_per_second=self.sample_rate, bits_per_sample=16, channels=1)
            self.stream = speechsdk.audio.PushAudioInputStream(stream_format=self.wave_format)
            self.audio_config = speechsdk.audio.AudioConfig(stream=self.stream)
            self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=self.audio_config, auto_detect_source_language_config=speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-IN"]))
            self.speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, value='Continuous')
            self.speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceResponse_RecognitionLatencyMs, value='100')
            self.frame_duration = 200
            self.thread = None
            self.speech_recognizer.recognized.connect(self.get_recognised_transcribed_text)
            self.speech_recognizer.recognizing.connect(self.get_recognising_text)
            self.speech_recognizer.session_started.connect(lambda evt: logger.info("Socket connected on ExoDevWebSocketConsumer STARTED %s ", str(evt), extra={'AppName': 'hack'}))
            self.speech_recognizer.session_stopped.connect(lambda evt: logger.info("Socket connected on ExoDevWebSocketConsumer STOPED %s ", str(evt), extra={'AppName': 'hack'}))
            self.speech_recognizer.canceled.connect(lambda evt: logger.info("Socket connected on ExoDevWebSocketConsumer CANCLED %s ", str(evt), extra={'AppName': 'hack'}))
            self.speech_recognizer.start_continuous_recognition_async()

        logger.info("Socket connected on ExoDevWebSocketConsumer", extra={'AppName': 'hack'})

    async def disconnect(self, close_code):
        if self.use_azure:
            self.speech_recognizer.stop_continuous_recognition_async()
            self.stream.close()

        self.recognised_transcript = ""
        self.stream_sid = None
        await self.close()
        logger.info("Socket disconnected on ExoDevWebSocketConsumer", extra={'AppName': 'hack'})

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        event = text_data_json.get('event')
        if event == 'media':
            self.stream_sid = text_data_json.get('stream_sid', "")
            if not self.is_silent_packet_sent:
                await self.send(json.dumps({
                            'event': 'media',
                            'stream_sid': self.stream_sid,
                            'media': {
                                'payload': ""
                                }
                             }))
                self.is_silent_packet_sent = True
            await self.handle_media(text_data_json)
        elif event == "start":
                logger.info("Start event received on ExoWebSocketConsumer %s", str(text_data_json),
                            extra={'AppName': 'hack'})
                start_json = text_data_json.get('start', "")
                if start_json:
                    self.call_sid = start_json.get("call_sid", "")
                    self.account_sid = start_json.get("account_sid", "")
                    self.user_phone_number = start_json.get("from", "")
                    print(self.call_sid, self.account_sid, '91'+self.user_phone_number[-10:])

    async def handle_media(self, message_data):
        media_payload = message_data.get('media', {})
        if 'payload' in media_payload:
            audio_data_base64 = media_payload['payload']
            audio_data = base64.b64decode(audio_data_base64)
            if self.use_azure:
                await self.send_data_to_azure_stream(audio_data)
                
                if self.recognised_transcript.strip():
                    self.initial_response = True
                    print(self.recognised_transcript)
                    await self.get_openai_response()
                    
                    # await self.get_text_to_speech_data(self.recognised_transcript)
                    # self.recognised_transcript = ""
                # if not self.initial_response:
                #     self.speech_interval = time.time()

    async def send_data_to_azure_stream(self, audio_data):
        self.stream.write(audio_data)

    async def get_conversation_summary(self):
        try:
            self.chat_summary_stage_prompt = """You are provided with the conversation history which you had with the customer, you only need to generate a summary of it in {selected_language} so that the customer can get a gist of the entire conversation. The summary needs to be generated in first person point of view.
                Once you have given the summary of the conversation, ask the customer if it is correct.

                Chat Conversation:

            """ + self.chat_history_for_summarisation
            chat_completion_response = openai.ChatCompletion.create(
                model=self.model_used,
                deployment_id=self.deployment_id,
                messages=[{"role": "system", "content": self.chat_summary_stage_prompt}],
                temperature=0.2,
                n=1,
                presence_penalty=-2.0,
                stream=True
            )

            previous_streamed_text = ""
            complete_streamed_text = ""
            is_tts_called = False
            function_name = ""

            for chunk in chat_completion_response:
                try:
                    self.is_user_oncall = True
                    if chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("content"):
                        complete_streamed_text += chunk['choices'][0]['delta']["content"]
                        previous_streamed_text += chunk['choices'][0]['delta']["content"]

                        if chunk['choices'][0]['delta']["content"].strip() == ".":
                            logger.info("LLM function chunk %s", str(
                                chunk['choices'][0]['delta']["content"]), extra={'AppName': 'hack'})
                            logger.info("Old Query Text %s", str(
                                previous_streamed_text), extra={'AppName': 'hack'})
                            is_tts_called = True
                            await self.get_text_to_speech_data(previous_streamed_text)
                            previous_streamed_text = ""
                    elif chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("function_call") and chunk['choices'][0]['delta']["function_call"].get("name"):
                        function_name = chunk['choices'][0]['delta']["function_call"]["name"].strip()
                        break
                except:
                    pass
            print(complete_streamed_text)
            # if not self.is_intractive_bot:
            #     await self.send(json.dumps({
            #                     'event': 'mark',
            #                     'stream_sid': self.stream_sid,
            #                     }))
            
            # await self.get_text_to_speech_data(self.interested_call_end_message)
            # await self.send_stop_call_event(send_product_details=True)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in get_conversation_summary in ExoDevWebSocketConsumer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})

    async def get_qualification_score(self):
        prompt = """
            You will have full conversation between a interviewer and candidate in Source.
            You need to give a score for every question out of 10 
            You should return in the formate of {"q1": 7, "q2": 3, "q3": 9.2, "q4": 8, q5: "1"}

            Source:

        """ + json.dumps(self.chat_history_for_summarisation)

        messages = [{'role': 'system', 'content': prompt}]
        self.set_openai_env_variable()

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

    async def send_stop_call_event(self, send_product_details=False):
        print('send_stop_call_event')
        print({'event': 'stop', 'stream_sid': self.stream_sid, "stop": {
            "call_sid": self.call_sid,
            "account_sid": self.account_sid,
            "reason": "callended"
        }})
        await self.send(json.dumps({'event': 'stop', 'stream_sid': self.stream_sid, "stop": {
            "call_sid": self.call_sid,
            "account_sid": self.account_sid,
            "reason": "callended"
        }}))
        await self.close()
        logger.info("Stop event sent", extra={'AppName': 'hack'})


    @sync_to_async
    def save_transcript(self):
        print('save_transcript1')
        candidate_profile = CandidateProfile.objects.filter(phone_number=int('91'+self.user_phone_number[-10:])).first()
        if candidate_profile:
            candidate_profile.call_interview_transcript = json.dumps(self.chat_history_for_summarisation)
            candidate_profile.save(update_fields=['call_interview_transcript'])
        print('save_transcript2')

    def set_openai_env_variable(self):
        openai.api_key = "05a87e3db47149699916b25e2b6a664e"
        openai.api_type = "azure"
        openai.api_base = "https://swedencentral.api.cognitive.microsoft.com/"
        openai.api_version = "2023-07-01-preview"

    async def get_openai_response(self):
        try:
            self.is_user_oncall = True
            self.chat_history_for_summarisation.append({"Candidate": self.recognised_transcript})
            self.chat_history.append({'role': 'user', 'content': self.recognised_transcript})
            self.recognised_transcript = ""
            self.set_openai_env_variable()
            stream = True
            chat_completion_response = openai.ChatCompletion.create(
                deployment_id="hack-16k",
                model="gpt-3.5-turbo-16k",
                messages=self.chat_history,
                temperature=0,
                n=1,
                functions=self.functions,
                function_call="auto",
                stream=stream,
                presence_penalty=-2.0,
            )

            previous_streamed_text = ""
            complete_streamed_text = ""
            is_tts_called = False
            function_name = ""
            function_args = ""
            if stream:
                for chunk in chat_completion_response:
                    try:
                        self.is_user_oncall = True
                        if chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("content"):
                            complete_streamed_text += chunk['choices'][0]['delta']["content"]
                            previous_streamed_text += chunk['choices'][0]['delta']["content"]

                            if chunk['choices'][0]['delta']["content"].strip() == ".":
                                logger.info("LLM function chunk %s", str(
                                    chunk['choices'][0]['delta']["content"]), extra={'AppName': 'hack'})
                                is_tts_called = True
                                # await self.get_text_to_speech_data(previous_streamed_text)
                                previous_streamed_text = ""
                        elif chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("function_call"):
                            if chunk['choices'][0]['delta']["function_call"].get("name"):
                                function_name = chunk['choices'][0]['delta']["function_call"]["name"].strip()
                            if chunk['choices'][0]['delta']["function_call"].get("arguments"):
                                function_args += chunk['choices'][0]['delta']["function_call"].get("arguments")
                    except:
                        pass
                function_args = json.loads(function_args) if function_args else function_args
                print(complete_streamed_text)
                print(function_args)
                print(function_name)
            else:
                try:
                    complete_streamed_text = chat_completion_response.choices[0].message.get('content','')
                    function_name = chat_completion_response.choices[0].message.get('function_call', {}).get('name', '')
                    function_args = json.loads(chat_completion_response.choices[0].message.get('function_call', {}).get('arguments', str(dict())))
                except:
                    pass

            if complete_streamed_text:
                self.chat_history_for_summarisation.append({f"{self.assistant_name}": complete_streamed_text})

            if function_name and function_name != self.current_stage:
                self.current_stage = function_name
                self.chat_history_for_summarisation.append({f"{self.assistant_name}": self.stage_wise_questions[function_name]})
                await self.get_text_to_speech_data(self.stage_wise_questions[function_name])
                print('function_name', function_name in ["interview_time_slot", "close_interview", "end_call"])
                if function_name in ["interview_time_slot", "close_interview", "end_call"]:
                    await self.save_transcript()
                    await self.send_stop_call_event()
                self.chat_history.append({'role': 'system', 'content': self.stage_wise_prompts[function_name]}) 
                self.chat_history.append({'role': 'assistant', 'content': self.stage_wise_questions[function_name]})
                self.functions = self.stage_wise_functions[function_name]

            if is_tts_called and previous_streamed_text.strip():
                await self.get_text_to_speech_data(previous_streamed_text)
            if not is_tts_called:
                await self.get_text_to_speech_data(complete_streamed_text)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(e, str(exc_tb.tb_lineno))

    def get_recognised_transcribed_text(self, event: speechsdk.SessionEventArgs):
        logger.info("get_recognised_transcribed_text is called in ExoDevWebSocketConsumer", extra={'AppName': 'hack'})
        try:
            if event.result.text.strip():
                self.recognised_transcript = event.result.text
                self.speech_interval = time.time()
                logger.info("get_recognised_transcribed_text is called in ExoDevWebSocketConsumer %s", event.result.text, extra={'AppName': 'hack'})
        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in get_recognised_transcribed_text ExoDevWebSocketConsumer %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})

    def get_recognising_text(self, event: speechsdk.SessionEventArgs):
        logger.info("get_recognising_text is called in ExoDevWebSocketConsumer %s", str(event), extra={'AppName': 'hack'})
        try:
            if event.result.text.strip():
                self.need_to_send_clear_packet = True
                logger.info("get_recognising_text is called in ExoDevWebSocketConsumer %s", event.result.text, extra={'AppName': 'hack'})
        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in get_recognising_text ExoDevWebSocketConsumer %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})

    async def clear_sent_audio_chunk(self):
        await self.send(json.dumps({'event': 'clear', 'stream_sid': self.stream_sid}))
        logger.info("Clear audio packet sent", extra={'AppName': 'hack'})

    async def send_audio_chunk(self, audio_chunk):
        await self.send(json.dumps({
            'event': 'media',
            'stream_sid': self.stream_sid,
            'media': {
                'payload': audio_chunk
            }
        }))

    async def get_text_to_speech_data(self, text_to_speak):
        try:
            audio_stream = ''
            self.speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
            self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=None)

            result = speech_synthesizer.speak_text_async(text_to_speak).get()
            stream = speechsdk.AudioDataStream(result)
            stream.save_to_wav_file("file.wav")
            y, s = librosa.load("file.wav", sr=8000)
            bbf = io.BytesIO()
            
            sf.write(bbf, y, s, format='wav')

            audio_stream = base64.b64encode(bbf.getvalue()).decode('ascii')

            await self.send_audio_chunk(audio_stream)
        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(e, exc_tb.tb_lineno)
            logger.error("Error in get_text_to_speech_data ExoDevWebSocketConsumer %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})
