import sys
import json
import boto3
import base64
import openai
import logging
import requests
from deepgram import Deepgram
from asgiref.sync import async_to_sync, sync_to_async
from EasyChatApp.models import CallTransferStatus
from apscheduler.schedulers.background import BackgroundScheduler
from channels.generic.websocket import AsyncWebsocketConsumer
from EasyAssistApp.utils_voice_bot import count_num_tokens_from_message, find_minumun_history_message_count_to_remove
from EasyAssistApp.constants_voice_bot import DEEPGRAM_API_KEY, OPENAI_KEY, EXO_STREAM_SAMPLE_RATE, EXO_CHUNK_RATE, \
    EXO_CHUNK_ENCODING_TYPE, AWS_EXCESS_KEY_ID, AWS_EXCESS_KEY_SECRETE, AWS_REGION_NAME, EXO_SILENT_PACKET_VALUE

import asyncio

logger = logging.getLogger(__name__)

DEBUG_CONSTANT = "CALL_HOLD_FUNCTIONALITY"

extra = {'AppName': 'EasyAssist'}

bot_transfer = "voicebot-transfer-"

class ExoDevWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            await self.accept()
            self.use_tokyo_aoai_deployment = True
            if self.use_tokyo_aoai_deployment:
                self.deployment_id = "voice-bot-gpt-35-16k"
                self.model_used = "gpt-3.5-turbo-16k"
            else:
                self.deployment_id = "bajaj-finserv-markets"
                self.model_used = "gpt-3.5-turbo-16k"

            self.deepgram_live = None
            self.recognised_transcript = ""
            self.stream_sid = None
            self.is_silent_packet_sent = False
            self.is_user_oncall = False
            self.max_model_input_tokens = 13000
            self.max_model_output_tokens = 3000
            self.verification_attempt_left = 3
            self.rate_of_frequency = 3200
            self.is_intractive_bot = True
            self.sample_rate = EXO_STREAM_SAMPLE_RATE
            self.endpointing_time = 800
            self.waiting_time = self.endpointing_time/1000
            self.encoding_type = EXO_CHUNK_ENCODING_TYPE
            self.interim_results = "true"
            self.average_confidence_threshold_value_eng = 0.70
            self.transcribing_confidence_threshold_value_eng = 0.60
            self.average_confidence_threshold_value_hindi = 0.70
            self.transcribing_confidence_threshold_value_hindi = 0.60
            self.total_tokens_used = 0
            self.recognised_transcript_confidence_list = []
            self.call_hold_timer = None
            self.CALL_HOLD_TIMER_DURATION = 15 # in seconds
            self.CALL_HOLD_COMPLETION_RESPONSE_ENGLISH = "Hello, are you back?"
            self.CALL_HOLD_COMPLETION_RESPONSE_HINDI = "नमस्ते, क्या आप वापस आ गए?"
            self.CALL_HOLD_COMPLETION_RESPONSE_HINDI_LATIN = "Namaste, kya aap vapis aa gaye?"
            self.user_phone_number = ""
            self.noise_alert_eng_message = "Can you please repeat your query, I was not able to get that because of the high background noise."
            self.noise_alert_hin_message = "क्या आप कृपया अपना प्रश्न दोहरा सकते हैं, उच्च पृष्ठभूमि शोर के कारण मैं उसे प्राप्त नहीं कर सका।"
            self.polly_client = boto3.Session(
                aws_access_key_id=AWS_EXCESS_KEY_ID, aws_secret_access_key=AWS_EXCESS_KEY_SECRETE, region_name=AWS_REGION_NAME).client('polly')
            
            self.deepgram_final_params = {
                "model": "nova-general",
                "language": "hi-Latn",
                "interim_results": self.interim_results,
                "endpointing": self.endpointing_time,
                "sample_rate": self.sample_rate,
                "encoding": self.encoding_type
            }
            self.deepgram_live = await self.initialize_deepgram()
            self.assistant_name = "Kajal"
            self.silent_packet_value = EXO_SILENT_PACKET_VALUE

            self.is_deafult_language_changed = False

            self.average_confidence_threshold_value = self.average_confidence_threshold_value_eng

            self.transcribing_confidence_threshold_value = self.transcribing_confidence_threshold_value_eng

            self.system_prompt = f"""
                You are Kajal, an AI powered female assistant working in ExoBank. Your job is to respond to the customer's queries in a polite manner. You need to generate answers in the language in which the customer is talking with you. For example, if the user is speaking in hinglish, you need to generate answers in hinglish. 

                The customer has been asked their preferred language of conversation. If the customer selects english language for the conversation then you need to call the english_language_selected function and if the customer selects hindi language for the conversation then you need to call the hindi_language_selected function. Once the language is selected you need to ask the customer if they recently made a transaction of Rupees. 50,000 on their ExoBank Credit Card at ABC Shop on November 20th, 2023 or they have queries related to any other service?

                Once the language is selected you need to ask the customer if they have any queries regarding the recent transaction they have made of Rupees 50,000 or if they have queries related to any other service. 

                Based on the reply given by the customer, you need to perform the following steps one at a time:

                Step 1: If the customer is asking anything apart from the recent transaction that has been done, you need to call the handle_out_of_context function.

                Step 2: If the customer says that he is talking about the same transaction then you need to ask the customer what is the issue.

                Step 3: If the customer says that the transaction was an unauthorized transaction or they did not perform the transaction, you need to suggest the customer to block their credit card and raise a complaint regarding the same. You need to also tell them that you can block the credit card for them. Once you have informed the customer about the above things, you need to ask the customer if they want to get their credit card blocked.

                Step 4: If the customer agrees to block their credit card, you need to ask the customer for the last 4 digits of the credit card. 

                Step 5: Once the customer provides you with the last four digits of the credit card, call the verify_credit_card_details function.

                Remember your response should be in almost 40 words and you are conversing on a call with the customer.

                Always remember that if the customer wanted to talk to the agent then you need to call transfer_current_flow to transfer the ongoing conversation to an agent. If the customer denies to transfer the call to an agent then you need to say that you do not have an answer to the question which has been asked.

                Always remember that if the customer is asking anything apart from the recent transaction that has been done, you need to call the handle_out_of_context function.

            """

            self.rest_stage_functions = [
                # {
                #     "name": "pause_current_conversation",
                #     "description": "If the user asks to hold or pause the ongoing conversation, then this function needs to be called.",
                #     "parameters": {
                #         "type": "object",
                #         "properties": {},
                #     },
                # },
                {
                    "name": "verify_credit_card_details",
                    "description": "If the user provides the last 4 digit of credit card, then this function needs to be called to verify the credit card details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "last_four_digits": {
                                "type": "string",
                                "description": "The last four digits of the credit card entered by the user. For example - '3245'",
                            },
                        },
                        "required": ["last_four_digits"],
                    },
                },
                {
                    "name": "handle_out_of_context",
                    "description": "If the customer is asking anything apart from the recent transaction that has been done, then this function needs to be called.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
                {
                    "name": "hindi_language_selected",
                    "description": "If the customer selected Hindi for the conversation, then this function needs to be called.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
                {
                    "name": "english_language_selected",
                    "description": "If the customer selected English for the conversation, then this function needs to be called.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },

                {
                    "name": "transfer_current_flow",
                    "description": "If the customer wanted to speak to the agent, then this function needs to be called.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            ]

            self.functions = self.rest_stage_functions

            self.chat_history = [{"role": "system", "content": self.system_prompt},
                                 {"role": "assistant", "content": """Hello, I am Kajal from ExoBank. Can you tell me your preferred language for further conversation? I can speak in hindi or english."""}]

            self.call_transcript = [{"role": "system", "content": self.system_prompt},
                                 {"role": "assistant", "content": """Hello, I am Kajal from ExoBank. Can you tell me your preferred language for further conversation? I can speak in hindi or english."""}]
            
            self.total_tokens_used += count_num_tokens_from_message(
                self.chat_history[0], self.model_used) + count_num_tokens_from_message(self.chat_history[0], self.model_used)

            self.call_sid = None

            self.selected_bot_language = "English"

            self.hindi_predefined_questions = {
                'hindi_language_selected': "भाषा के रूप में हिंदी का चयन करने के लिए धन्यवाद। हमारे रिकॉर्ड के अनुसार, आपने 20 नवंबर, 2023 को एबीसी शॉप पर अपने एक्सोबैंक क्रेडिट कार्ड पर 50,000 रुपये का लेनदेन किया है। क्या यह कॉल उसी के संबंध में है या आपके पास किसी अन्य सेवा से संबंधित प्रश्न हैं?",
                'handle_out_of_context' : "क्या मैं आगे के समाधान के लिए कॉल को हमारे एजेंट को स्थानांतरित कर दूं क्योंकि पूछा गया प्रश्न मेरे दायरे से बाहर है",
                'digits_not_matched': "दिए गए अंतिम 4 अंक आपके क्रेडिट कार्ड से मेल नहीं खाते, कृपया सही अंक प्रदान करें। कृपया अंग्रेजी में अंक प्रदान करें। आपके पास {verification_attempt_left} प्रयास बचे हैं",
                'limit_exhausted': "आपने अधिकतम प्रयास समाप्त कर दिए हैं. कृपया कुछ देर बाद कॉल करें.",
                'digits_matched': "हमें '6 7 8 9' से समाप्त होने वाले क्रेडिट कार्ड को ब्लॉक करने का आपका अनुरोध प्राप्त हुआ है। इसके अलावा, हम शिकायत दर्ज करने में आपकी सहायता के लिए इस कॉल को ग्राहक सहायता कार्यकारी से जोड़ देंगे। कृपया तब तक प्रतीक्षा करें जब तक हम आपका कॉल स्थानांतरित नहीं कर देते।",
                'pause_current_conversation': "ठीक है ज़रूर, वापस आने पर कृपया मुझे बताएं.",
                'transfer_current_flow': "मैं इस कॉल को एक एजेंट को अग्रेषित कर रहा हूं ताकि वे आपकी मदद कर सकें।"
            }
                        
            self.english_predefined_questions = {
                'english_language_selected': "Thank you for selecting english as a language. As per our records, you have made a transaction of Rupees 50,000 on your ExoBank Credit Card, at ABC Shop, on, November 20th, 2023. Is this call regarding the same or do you have queries related to any other services?",
                'transfer_current_flow' : "I am forwarding this call to an agent so that they can help you out.",
                'digits_not_matched': "The provided last 4 digits does not match with your credit card, please provide correct digits. Please provide digits in English. You are left with {verification_attempt_left} attempts",
                'limit_exhausted': "You have exhausted the maximum attempts. Please call after sometime.",
                'digits_matched': "We have received your request to block the Credit Card ending with '6 7 8 9'. Further to this, we will connect this call to the customer support executive to help you with filing the complaint. Please wait while we transfer your call.",
                'pause_current_conversation': "Okay sure, please let me know once you are back.",
                'handle_out_of_context': "Shall I transfer the call to our agent for the further resolution as the asked question is out of my scope",
            }

            self.predefined_questions = self.english_predefined_questions
            
            
            self.account_sid = None

            self.scheduler = BackgroundScheduler()
            self.scheduler.add_job(self.start_keep_alive_timer, 'interval', seconds=8)
            self.scheduler.start()

            logger.info("Socket connected on ExoDevWebSocketConsumer",
                        extra={'AppName': 'EasyAssist'})

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in connect in ExoDevWebSocketConsumer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    def start_keep_alive_timer(self):
        self.deepgram_live.keep_alive()

    async def disconnect(self, close_code):
        try:
            self.deepgram_live.finish()
            self.recognised_transcript = ""
            self.stream_sid = None
            self.scheduler.shutdown()
            await self.close()
            logger.info("Socket disconnected on ExoDevWebSocketConsumer", extra={
                        'AppName': 'EasyAssist'})
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in disconnect in ExoDevWebSocketConsumer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            event = text_data_json.get('event', None)
            if event == 'media':
                self.stream_sid = text_data_json.get('stream_sid', "")
                if not self.is_silent_packet_sent:
                    await self.send(json.dumps({
                        'event': 'media',
                        'stream_sid': self.stream_sid,
                        'media': {
                                    'payload': self.silent_packet_value
                                    }
                    }))
                    self.is_silent_packet_sent = True
                if not self.deepgram_live:
                    self.deepgram_live = await self.initialize_deepgram()
                await self.handle_media(text_data_json)
            elif event == "mark":
                self.is_user_oncall = False
                logger.info("Mark event received on ExoWebSocketConsumer",
                            extra={'AppName': 'EasyAssist'})
            elif event == "start":
                logger.info("Start event received on ExoWebSocketConsumer %s", str(text_data_json),
                            extra={'AppName': 'EasyAssist'})
                start_json = text_data_json.get('start', "")
                if start_json:
                    self.call_sid = start_json.get("call_sid", "")
                    self.account_sid = start_json.get("account_sid", "")
                    self.user_phone_number = start_json.get("from", "")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in receive in ExoDevWebSocketConsumer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    def set_openai_env_variable(self):
        if self.use_tokyo_aoai_deployment:
            openai.api_key = "0f5a99356d5045e485623b01cd73af53"
            openai.api_type = "azure"
            openai.api_base = "https://voice-bot-openai.openai.azure.com/"
            openai.api_version = "2023-07-01-preview"
        else:
            openai.api_key = "93395151f1634e67bd1d3017437e033d"
            openai.api_type = "azure"
            openai.api_base = "https://exotel-cogno-openai.openai.azure.com/"
            openai.api_version = "2023-07-01-preview"

    async def handle_media(self, message_data):
        try:
            media_payload = message_data.get('media', {})
            if 'payload' in media_payload:
                self.send_to_deepgram(base64.b64decode(media_payload['payload']))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in handle_media in ExoDevWebSocketConsumer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    async def initialize_deepgram(self):
        try:
            deepgram = Deepgram(DEEPGRAM_API_KEY)
            deepgram_live = await deepgram.transcription.live(self.deepgram_final_params)
            deepgram_live.registerHandler(
                deepgram_live.event.ERROR, self.handle_deepgram_error)
            deepgram_live.registerHandler(
                deepgram_live.event.CLOSE, self.handle_deepgram_close)
            deepgram_live.registerHandler(
                deepgram_live.event.TRANSCRIPT_RECEIVED, self.get_deepgram_recognised_text)
            return deepgram_live
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error ExoDevWebSocketConsumer in %s at handle_deepgram_error %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})
            return None

    def send_to_deepgram(self, audio_data):
        try:
            self.deepgram_live.send(audio_data)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in send_to_deepgram in ExoDevWebSocketConsumer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    async def handle_deepgram_error(self, error_data):
        logger.error("Error ExoDevWebSocketConsumer in %s at handle_deepgram_error", str(
            error_data), extra={'AppName': 'EasyAssist'})

    async def handle_deepgram_close(self, close_data):
        self.deepgram_live = await self.initialize_deepgram()
        pass
        # logger.error("Error ExoDevWebSocketConsumer in %s at handle_deepgram_close", str(close_data), extra={'AppName': 'EasyAssist'})

    def async_call_later(self, seconds, callback):
        try:
            async def schedule():
                await asyncio.sleep(seconds)

                if asyncio.iscoroutinefunction(callback):
                    logger.error("%s in if of async_call_later", str(DEBUG_CONSTANT), extra=extra)
                    await callback()
                else:
                    logger.error("%s in else of async_call_later", str(DEBUG_CONSTANT), extra=extra)
                    callback()

            self.call_hold_timer = asyncio.ensure_future(schedule())
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in async_call_later %s at %s", str(
                e), str(exc_tb.tb_lineno), extra=extra)


    async def call_hold_timer_completion_callback(self):
        try:
            logger.error("%s - in call_hold_timer_completion_callback", str(DEBUG_CONSTANT), extra=extra)
            if self.selected_bot_language == "Hindi":
                self.chat_history.append({"role": "assistant", "content": self.CALL_HOLD_COMPLETION_RESPONSE_HINDI_LATIN})
                self.call_transcript.append({"role": "assistant", "content": self.CALL_HOLD_COMPLETION_RESPONSE_HINDI_LATIN})
                await self.get_text_to_speech_data(self.CALL_HOLD_COMPLETION_RESPONSE_HINDI)
            else:
                self.chat_history.append({"role": "assistant", "content": self.CALL_HOLD_COMPLETION_RESPONSE_ENGLISH})
                self.call_transcript.append({"role": "assistant", "content": self.CALL_HOLD_COMPLETION_RESPONSE_ENGLISH})
                await self.get_text_to_speech_data(self.CALL_HOLD_COMPLETION_RESPONSE_ENGLISH)
            self.abort_call_hold_timer()
            logger.error("%s - exited call_hold_timer_completion_callback", str(DEBUG_CONSTANT), extra=extra)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in call_hold_timer_completion_callback %s at %s", str(
                e), str(exc_tb.tb_lineno), extra=extra)

    def abort_call_hold_timer(self):
        try:
            if self.call_hold_timer:
                logger.error("%s - in abort_call_hold_timer", str(DEBUG_CONSTANT), extra=extra)
                self.call_hold_timer.cancel()
                self.call_hold_timer = None
                logger.error("%s - in abort_call_hold_timer execution completed", str(DEBUG_CONSTANT), extra=extra)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in abort_call_hold_timer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra=extra)

    def pause_current_conversation(self):
        try:
            logger.error("%s - in pause_current_conversation main function", str(DEBUG_CONSTANT), extra=extra)
            if not self.call_hold_timer:
                logger.error("%s - in pause_current_conversation before timer start", str(DEBUG_CONSTANT), extra=extra)
                self.async_call_later(self.CALL_HOLD_TIMER_DURATION, self.call_hold_timer_completion_callback)
                logger.error("%s - in pause_current_conversation after timer start", str(DEBUG_CONSTANT), extra=extra)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in pause_current_conversation %s at %s", str(
                e), str(exc_tb.tb_lineno), extra=extra)

    async def get_openai_response(self):
        try:
            self.is_user_oncall = True
            logger.info("get_openai_response is called",
                        extra={'AppName': 'EasyAssist'})
            logger.error("%s - get_openai_response chat history %s", str(DEBUG_CONSTANT), str(
                self.chat_history), extra={'AppName': 'EasyAssist'})
            
            if self.total_tokens_used >= self.max_model_input_tokens:
                self.chat_history = self.chat_history[find_minumun_history_message_count_to_remove(
                    self.chat_history, self.total_tokens_used, self.max_model_input_tokens):]

            self.set_openai_env_variable()
            
            chat_completion_response = openai.ChatCompletion.create(
                deployment_id=self.deployment_id,
                model=self.model_used,
                messages=self.chat_history,
                temperature=0,
                n=1,
                functions=self.functions,
                function_call="auto",
                stream=True,
                presence_penalty=-2.0,
                max_tokens=self.max_model_output_tokens
            )

            previous_streamed_text = ""
            complete_streamed_text = ""
            is_tts_called = False
            function_name = ""
            function_argument = ""

            for chunk in chat_completion_response:
                try:
                    self.is_user_oncall = True
                    if chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("content"):
                        complete_streamed_text += chunk['choices'][0]['delta']["content"]
                        previous_streamed_text += chunk['choices'][0]['delta']["content"]

                        if chunk['choices'][0]['delta']["content"].strip() == ".":
                            logger.info("LLM function chunk %s", str(
                                chunk['choices'][0]['delta']["content"]), extra={'AppName': 'EasyAssist'})
                            logger.error("%s - Old Query Text %s", str(DEBUG_CONSTANT), str(
                                previous_streamed_text), extra={'AppName': 'EasyAssist'})
                            is_tts_called = True
                            await self.get_text_to_speech_data(previous_streamed_text)
                            previous_streamed_text = ""
                    elif chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("function_call") and chunk['choices'][0]['delta']["function_call"].get("name"):
                        function_name = chunk['choices'][0]['delta']["function_call"]["name"].strip()
                        if function_name in ["pause_current_conversation", "handle_out_of_context", "hindi_language_selected", "transfer_current_flow", "english_language_selected"]:
                            break
                    elif chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("function_call") and chunk['choices'][0]['delta']["function_call"].get("arguments"):
                        function_argument += chunk['choices'][0]['delta']["function_call"]["arguments"].strip()
                except:
                    pass

            if function_name:    
                if function_name == "pause_current_conversation":
                    await self.get_text_to_speech_data(self.predefined_questions["pause_current_conversation"])
                    self.chat_history.append({"role": "assistant", "content": self.predefined_questions["pause_current_conversation"]})
                    self.call_transcript.append({"role": "assistant", "content": self.predefined_questions["pause_current_conversation"]})
                    self.pause_current_conversation()
                elif function_name == "verify_credit_card_details":
                    if function_argument:
                        function_argument = json.loads(function_argument)
                        if "last_four_digits" in function_argument and function_argument["last_four_digits"] == "6789":
                            self.chat_history.append(
                                {"role": "assistant", "content": self.predefined_questions["digits_matched"]})
                            self.call_transcript.append(
                                {"role": "assistant", "content": self.predefined_questions["digits_matched"]})
                            self.total_tokens_used += count_num_tokens_from_message(
                                self.chat_history[-1], self.model_used)
                            print("***********************************************************************************")
                            await self.set_cache()
                            await self.get_text_to_speech_data(self.predefined_questions["digits_matched"])
                            await self.send_stop_call_event()
                        else:
                            self.verification_attempt_left -= 1
                            if self.verification_attempt_left == 0:
                                self.chat_history.append(
                                    {"role": "assistant", "content": self.predefined_questions["limit_exhausted"]})
                                self.call_transcript.append(
                                    {"role": "assistant", "content": self.predefined_questions["limit_exhausted"]})
                                self.total_tokens_used += count_num_tokens_from_message(
                                    self.chat_history[-1], self.model_used)
                                await self.get_text_to_speech_data(self.predefined_questions["limit_exhausted"])
                                await self.send_stop_call_event(send_trancript=False)
                                return                            
                            else:
                                self.chat_history.append(
                                    {"role": "assistant", "content": self.predefined_questions["digits_not_matched"].format(verification_attempt_left=self.verification_attempt_left)})
                                self.call_transcript.append(
                                    {"role": "assistant", "content": self.predefined_questions["digits_not_matched"].format(verification_attempt_left=self.verification_attempt_left)})
                                self.total_tokens_used += count_num_tokens_from_message(
                                    self.chat_history[-1], self.model_used)
                                await self.get_text_to_speech_data(self.predefined_questions["digits_not_matched"].format(verification_attempt_left=self.verification_attempt_left))
                                return                            
                elif function_name == "handle_out_of_context":
                    self.chat_history.pop()
                    await self.get_text_to_speech_data(self.predefined_questions['handle_out_of_context'])
                    return
                elif function_name == "transfer_current_flow":
                    print("**********************************************************************************")
                    await self.set_cache()
                    await self.get_text_to_speech_data(self.predefined_questions['transfer_current_flow'])
                    self.chat_history.append(
                        {"role": "assistant", "content": self.predefined_questions["transfer_current_flow"]})
                    self.call_transcript.append(
                        {"role": "assistant", "content": self.predefined_questions["transfer_current_flow"]})
                    self.total_tokens_used += count_num_tokens_from_message(
                        self.chat_history[-1], self.model_used)
                    await self.send_stop_call_event()
                    return
                elif function_name == "hindi_language_selected":
                    self.selected_bot_language = "Hindi"
                    self.predefined_questions = self.hindi_predefined_questions
                    self.chat_history.append({"role": "assistant", "content": self.predefined_questions["hindi_language_selected"]})
                    self.call_transcript.append({"role": "assistant", "content": self.predefined_questions["hindi_language_selected"]})
                    await self.get_text_to_speech_data(self.predefined_questions["hindi_language_selected"])
                elif function_name == "english_language_selected":
                    self.chat_history.append({"role": "assistant", "content": self.predefined_questions["english_language_selected"]})
                    self.call_transcript.append({"role": "assistant", "content": self.predefined_questions["english_language_selected"]})
                    await self.get_text_to_speech_data(self.predefined_questions["english_language_selected"])

            if is_tts_called and previous_streamed_text.strip():
                logger.info("Old Query Text %s", str(
                    previous_streamed_text), extra={'AppName': 'EasyAssist'})
                await self.get_text_to_speech_data(previous_streamed_text)

            if not is_tts_called:
                await self.get_text_to_speech_data(complete_streamed_text)

            if not function_name:
                self.chat_history.append(
                    {"role": "assistant", "content": complete_streamed_text})
                self.call_transcript.append(
                    {"role": "assistant", "content": complete_streamed_text})
                self.total_tokens_used += count_num_tokens_from_message(
                    self.chat_history[-1], self.model_used)

            if not self.is_intractive_bot:
                await self.send(json.dumps({
                                'event': 'mark',
                                'stream_sid': self.stream_sid,
                                }))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in get_openai_response in ExoDevWebSocketConsumer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    async def clear_sent_audio_chunk(self):
        await self.send(json.dumps({'event': 'clear', 'stream_sid': self.stream_sid}))
        logger.info("Clear audio packet sent", extra={'AppName': 'EasyAssist'})

    async def send_audio_chunk(self, audio_chunk):
        await self.send(json.dumps({
            'event': 'media',
            'stream_sid': self.stream_sid,
            'media': {
                'payload': audio_chunk
            }
        }))

    async def send_stop_call_event(self, send_trancript=True, send_product_details=False):
        if send_product_details:
            await self.send_product_details_on_whatsapp()
        if send_trancript:
            await self.send_call_transcript()
        await self.send(json.dumps({'event': 'stop', 'stream_sid': self.stream_sid, "stop": {
            "call_sid": self.call_sid,
            "account_sid": self.account_sid,
            "reason": "callended"
        }}))
        await self.close()
        logger.info("Stop event sent", extra={'AppName': 'EasyAssist'})

    async def get_text_to_speech_data(self, text_to_speak):
        try:
            self.is_user_oncall = True
            response = self.polly_client.synthesize_speech(
                VoiceId='Kajal', OutputFormat='pcm', Text=text_to_speak, Engine='neural', SampleRate='8000', LanguageCode='en-IN')
            audio_stream = base64.b64encode(
                response['AudioStream'].read()).decode("ascii")
            for i in range(0, len(audio_stream), self.rate_of_frequency):
                logger.info("Get Azure TTS loop count inside while %s",
                            str(i), extra={'AppName': 'EasyAssist'})
                await self.send_audio_chunk(audio_stream[i:i+self.rate_of_frequency])
        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in get_text_to_speech_data ExoDevWebSocketConsumer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    async def get_deepgram_recognised_text(self, json_data):
        try:
            logger.info("Transcript recived on ExoDevWebSocketConsumer is %s", str(
                json_data), extra={'AppName': 'EasyAssist'})

            if self.is_intractive_bot:
                if json_data['channel']['alternatives'][0]['confidence'] >= self.transcribing_confidence_threshold_value \
                    and json_data['channel']['alternatives'][0]['transcript'].strip():
                    await self.clear_sent_audio_chunk()
            else:
                if self.is_user_oncall:
                    return

            if json_data["is_final"] and json_data['channel']['alternatives'][0]['transcript'] \
                and json_data['channel']['alternatives'][0]['confidence'] >= self.transcribing_confidence_threshold_value:
                self.abort_call_hold_timer()
                self.recognised_transcript += json_data['channel']['alternatives'][0]['transcript'].strip(
                ) + " "
                self.recognised_transcript_confidence_list.append(
                    json_data['channel']['alternatives'][0]['confidence'])

            if json_data["speech_final"] and self.recognised_transcript.strip():
                logger.info("Transcript function in side if %s",
                            self.recognised_transcript, extra={'AppName': 'EasyAssist'})
                if sum(self.recognised_transcript_confidence_list)/len(self.recognised_transcript_confidence_list) >= self.average_confidence_threshold_value:
                    self.chat_history.append(
                        {"role": "user", "content": self.recognised_transcript})
                    self.call_transcript.append(
                        {"role": "user", "content": self.recognised_transcript})
                    self.total_tokens_used += count_num_tokens_from_message(
                        self.chat_history[-1], self.model_used)
                    await self.get_openai_response()
                else:
                    if self.selected_bot_language == "Hindi":
                        await self.get_text_to_speech_data(self.noise_alert_hin_message)
                    else:
                        await self.get_text_to_speech_data(self.noise_alert_eng_message)
                self.recognised_transcript_confidence_list = []
                self.recognised_transcript = ""

            elif json_data["duration"] >= self.waiting_time and not json_data['channel']['alternatives'][0]['transcript'] and self.recognised_transcript.strip():
                logger.info("Transcript function in side if %s",
                            self.recognised_transcript, extra={'AppName': 'EasyAssist'})
                if sum(self.recognised_transcript_confidence_list)/len(self.recognised_transcript_confidence_list) >= self.average_confidence_threshold_value:
                    self.chat_history.append(
                        {"role": "user", "content": self.recognised_transcript})
                    self.call_transcript.append(
                        {"role": "user", "content": self.recognised_transcript})
                    self.total_tokens_used += count_num_tokens_from_message(
                        self.chat_history[-1], self.model_used)
                    await self.get_openai_response()
                else:
                    if self.selected_bot_language == "Hindi":
                        await self.get_text_to_speech_data(self.noise_alert_hin_message)
                    else:
                        await self.get_text_to_speech_data(self.noise_alert_eng_message)
                self.recognised_transcript_confidence_list = []
                self.recognised_transcript = ""

        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in print_transcript ExoDevWebSocketConsumer %s at %s", str(
                e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    async def send_product_details_on_whatsapp(self):
        try:
            headers = {
                'Content-Type': 'application/json'
            }

            payload = {
                "whatsapp": {
                    "messages": [
                        {
                            "from": "919920959347",
                            "to": self.user_phone_number,
                            "content": {
                                "type": "template",
                                "template": {
                                    "name": "bajaj_finserv_iphone_14_poc",
                                    "language": {
                                        "policy": "deterministic",
                                        "code": "en"
                                    },
                                    "components": []
                                }
                            }
                        }
                    ]
                }
            }

            exotel_api_endpoint = 'https://a6fba3157a13976b003265ec7fd225043d7c71dd51728769:1b6f739e3c71aebe79b62e2a71185daf690bb222ce42e897@api.exotel.com/v2/accounts/getcogno7/messages'

            response = requests.request("POST", exotel_api_endpoint, headers=headers, data=json.dumps(payload), timeout=20, verify=False)

            if response.status_code == 202:
                logger.info("send_product_details_on_whatsapp WhatsApp text message sent succesfully",
                            extra=extra)
            else:
                logger.error("send_product_details_on_whatsapp failed to send WhatsApp text message, status code received = %s", str(response.status_code),
                            extra=extra)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in send_product_details_on_whatsapp %s at %s", str(
                e), str(exc_tb.tb_lineno), extra=extra)

    async def send_call_transcript(self):
        try:
            url = 'https://demo.allincall.in/voice-bot-callback/'

            json_data = {
                'sid': self.call_sid,
                'user_phone_number': self.user_phone_number,
                'transcript': json.dumps({"transcript": self.call_transcript}) 
            }

            response = requests.post(url, json=json_data)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in send_call_transcript %s at %s", str(
                e), str(exc_tb.tb_lineno), extra=extra)

    @sync_to_async
    def set_cache(self):
        try:
            CallTransferStatus.objects.create(call_sid=self.call_sid)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in set_cache %s at %s", str(
                e), str(exc_tb.tb_lineno), extra=extra)