import io
import sys
import json
# import boto3
import base64
import openai
import logging
import time
import azure.cognitiveservices.speech as speechsdk
from channels.generic.websocket import AsyncWebsocketConsumer
import librosa


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
        self.current_stage = ""
        self.chat_history_for_summarisation = "User: " + \
                f"Hello, I am Kajal HR from Exohire. As you applied for job in Exohire, we would like to congratulate you as your CV is shortlisted for current Screening Test. Is this right time to speak with you?"
        self.initial_response = False
        if self.use_azure:
            self.azure_api_key = "ac66d249a6884d67acc915866ffc28d5"
            self.azure_region = "swedencentral"
            self.speech_config = speechsdk.SpeechConfig(subscription=self.azure_api_key, region=self.azure_region)
            self.wave_format = speechsdk.audio.AudioStreamFormat(samples_per_second=self.sample_rate, bits_per_sample=16, channels=1)
            self.stream = speechsdk.audio.PushAudioInputStream(stream_format=self.wave_format)
            self.audio_config = speechsdk.audio.AudioConfig(stream=self.stream)
            self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=self.audio_config, auto_detect_source_language_config=speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-IN", "hi-IN"]))
            self.speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, value='Continuous')
            self.speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceResponse_RecognitionLatencyMs, value='10')
            self.frame_duration = 200
            self.thread = None
            self.speech_recognizer.recognized.connect(self.get_recognised_transcribed_text)
            self.speech_recognizer.recognizing.connect(self.get_recognising_text)
            self.speech_recognizer.session_started.connect(lambda evt: logger.info("Socket connected on ExoDevWebSocketConsumer STARTED %s ", str(evt), extra={'AppName': 'EasyAssist'}))
            self.speech_recognizer.session_stopped.connect(lambda evt: logger.info("Socket connected on ExoDevWebSocketConsumer STOPED %s ", str(evt), extra={'AppName': 'EasyAssist'}))
            self.speech_recognizer.canceled.connect(lambda evt: logger.info("Socket connected on ExoDevWebSocketConsumer CANCLED %s ", str(evt), extra={'AppName': 'EasyAssist'}))
            self.speech_recognizer.start_continuous_recognition_async()

        logger.info("Socket connected on ExoDevWebSocketConsumer", extra={'AppName': 'EasyAssist'})

    async def disconnect(self, close_code):
        if self.use_azure:
            self.speech_recognizer.stop_continuous_recognition_async()
            self.stream.close()

        self.recognised_transcript = ""
        self.stream_sid = None
        await self.close()
        logger.info("Socket disconnected on ExoDevWebSocketConsumer", extra={'AppName': 'EasyAssist'})

    async def receive(self, text_data):
        print(text_data)
        text_data_json = json.loads(text_data)
        event = text_data_json.get('event')
        print(event)
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

    async def handle_media(self, message_data):
        media_payload = message_data.get('media', {})
        if 'payload' in media_payload:
            audio_data_base64 = media_payload['payload']
            audio_data = base64.b64decode(audio_data_base64)
            if self.use_azure:
                await self.send_data_to_azure_stream(audio_data)
                if self.recognised_transcript.strip():
                    await self.get_text_to_speech_data(self.recognised_transcript)
                    self.recognised_transcript = ""

    async def send_data_to_azure_stream(self, audio_data):
        self.stream.write(audio_data)

    def set_openai_env_variable(self):
        openai.api_key = "0f5a99356d5045e485623b01cd73af53"
        openai.api_type = "azure"
        openai.api_base = "https://voice-bot-openai.openai.azure.com/"
        openai.api_version = "2023-07-01-preview"

    async def get_openai_response(self):
        try:
            self.is_user_oncall = True

            self.set_openai_env_variable()
            stream = False
            chat_completion_response = openai.ChatCompletion.create(
                deployment_id=self.deployment_id,
                model=self.model_used,
                messages=self.chat_history,
                temperature=0,
                n=1,
                functions=self.functions,
                function_call="auto",
                stream=stream,
                presence_penalty=-2.0,
                max_tokens=self.max_model_output_tokens
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
                                    chunk['choices'][0]['delta']["content"]), extra={'AppName': 'EasyAssist'})
                                is_tts_called = True
                                await self.get_text_to_speech_data(previous_streamed_text)
                                previous_streamed_text = ""
                        elif chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("function_call") and chunk['choices'][0]['delta']["function_call"].get("name"):
                            function_name = chunk['choices'][0]['delta']["function_call"]["name"].strip()
                            break
                        elif chunk['choices'] and chunk['choices'][0] and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get("function_call") and chunk['choices'][0]['delta']["function_call"].get("arguments"):
                            function_args += chunk['choices'][0]['delta']["function_call"]["arguments"].strip()
                            break
                    except:
                        pass
                function_args = json.loads(function_args) if function_args else function_args
            else:
                try:
                    complete_streamed_text = chat_completion_response.choices[0].message.get('content','')
                    function_name = chat_completion_response.choices[0].message.get('function_call', {}).get('name', '')
                    function_args = json.loads(chat_completion_response.choices[0].message.get('function_call', {}).get('arguments', str(dict())))
                except:
                    pass

            if function_name and function_name != self.current_stage:
                pass

            if is_tts_called and previous_streamed_text.strip():
                await self.get_text_to_speech_data(previous_streamed_text)
            if not is_tts_called:
                await self.get_text_to_speech_data(complete_streamed_text)

            self.chat_history_for_summarisation += f"{self.assistant_name}: " + \
                    complete_streamed_text

        except Exception as e:
            print(e)

    def get_recognised_transcribed_text(self, event: speechsdk.SessionEventArgs):
        logger.info("get_recognised_transcribed_text is called in ExoDevWebSocketConsumer", extra={'AppName': 'EasyAssist'})
        try:
            if event.result.text.strip():
                self.recognised_transcript = event.result.text
                self.speech_interval = time.time()
                logger.info("get_recognised_transcribed_text is called in ExoDevWebSocketConsumer %s", event.result.text, extra={'AppName': 'EasyAssist'})
        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in get_recognised_transcribed_text ExoDevWebSocketConsumer %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    def get_recognising_text(self, event: speechsdk.SessionEventArgs):
        logger.info("get_recognising_text is called in ExoDevWebSocketConsumer %s", str(event), extra={'AppName': 'EasyAssist'})
        try:
            if event.result.text.strip():
                self.need_to_send_clear_packet = True
                logger.info("get_recognising_text is called in ExoDevWebSocketConsumer %s", event.result.text, extra={'AppName': 'EasyAssist'})
        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in get_recognising_text ExoDevWebSocketConsumer %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

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

    async def get_text_to_speech_data(self, text_to_speak):
        try:
            audio_stream = ''
            self.speech_config.speech_synthesis_voice_name = "hi-IN-SwaraNeural"
            self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=None)

            result = speech_synthesizer.speak_text_async(text_to_speak).get()
            stream = speechsdk.AudioDataStream(result)
            stream.save_to_wav_file("file.wav")
            y, s = librosa.load("file.wav", sr=8000)
            # y_bytes = y.tobytes()
            bbf = io.BytesIO()
            import soundfile as sf
            sf.write(bbf, y, s, format='wav')

            audio_stream = base64.b64encode(bbf.getvalue()).decode('ascii')

            await self.send_audio_chunk(audio_stream)

            # for i in range(0, len(audio_stream), self.rate_of_frequency):
            #     logger.info("Get Azure TTS loop count inside while %s",str(i), extra={'AppName': 'EasyAssist'})
            #     await self.send_audio_chunk(audio_stream[i:i+self.rate_of_frequency])
        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in get_text_to_speech_data ExoDevWebSocketConsumer %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})
