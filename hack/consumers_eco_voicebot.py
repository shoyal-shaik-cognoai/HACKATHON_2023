import sys
import json
import boto3
import base64
import openai
import logging
import datetime
import replicate
import webrtcvad
from deepgram import Deepgram
import azure.cognitiveservices.speech as speechsdk
from channels.generic.websocket import AsyncWebsocketConsumer


logger = logging.getLogger(__name__)


DEEPGRAM_API_KEY = '7814e32632db3030800c4ecc8af67b73cf7a79c6'

PARAMS = {"model": "phonecall",
          "tier": "nova",
          "sample_rate": 8000,
          "encoding": "linear16"}

class ExoDevWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.use_azure = False
        self.deepgram_live = None
        self.recognised_transcript = ""
        self.stream_sid = None
        self.is_silent_packet_sent = False
        self.need_to_send_clear_packet = False
        self.sample_rate = 8000
        self.rate_of_frequency = 8000
        self.polly_client = boto3.Session(aws_access_key_id='AKIAWGA6T2KESS5PWYM3', aws_secret_access_key='zWMqRS+W4I6c2WXuh28Y1iorng471ukkFAfwJq7K', region_name='ap-south-1').client('polly')
        if self.use_azure:
            self.azure_api_key = "7c04d2047a4047ec8d3344fbb5abdb3f"
            self.azure_region = "eastus"
            self.speech_config = speechsdk.SpeechConfig(subscription=self.azure_api_key, region=self.azure_region)
            self.wave_format = speechsdk.audio.AudioStreamFormat(samples_per_second=self.sample_rate, bits_per_sample=16, channels=1)
            self.stream = speechsdk.audio.PushAudioInputStream(stream_format=self.wave_format)
            self.audio_config = speechsdk.audio.AudioConfig(stream=self.stream)
            self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=self.audio_config, auto_detect_source_language_config=speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-IN"]))
            self.speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, value='Continuous')
            self.speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceResponse_RecognitionLatencyMs, value='10')
            self.vad = webrtcvad.Vad(2)
            self.frame_duration = 200
            self.thread = None
            self.speech_recognizer.recognized.connect(self.get_recognised_transcribed_text)
            self.speech_recognizer.recognizing.connect(self.get_recognising_text)
            self.speech_recognizer.session_started.connect(lambda evt: logger.info("Socket connected on ExoDevWebSocketConsumer STARTED %s ", str(evt), extra={'AppName': 'EasyAssist'}))
            self.speech_recognizer.session_stopped.connect(lambda evt: logger.info("Socket connected on ExoDevWebSocketConsumer STOPED %s ", str(evt), extra={'AppName': 'EasyAssist'}))
            self.speech_recognizer.canceled.connect(lambda evt: logger.info("Socket connected on ExoDevWebSocketConsumer CANCLED %s ", str(evt), extra={'AppName': 'EasyAssist'}))
            self.speech_recognizer.start_continuous_recognition_async()
        else:
            self.deepgram_live = await self.initialize_deepgram()

        logger.info("Socket connected on ExoDevWebSocketConsumer", extra={'AppName': 'EasyAssist'})

    async def disconnect(self, close_code):
        if self.use_azure:
            self.speech_recognizer.stop_continuous_recognition_async()
            self.stream.close()
        else:
            self.deepgram_live.finish()

        self.recognised_transcript = ""
        self.stream_sid = None
        await self.close()
        logger.info("Socket disconnected on ExoDevWebSocketConsumer", extra={'AppName': 'EasyAssist'})

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        event = text_data_json.get('event', None)
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
            if not self.deepgram_live:
                self.deepgram_live = await self.initialize_deepgram()

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
            else:
                self.send_to_deepgram(audio_data)

    async def initialize_deepgram(self):
        try:
            deepgram = Deepgram(DEEPGRAM_API_KEY)
            deepgram_live = await deepgram.transcription.live(PARAMS)
            deepgram_live.registerHandler(deepgram_live.event.ERROR, self.handle_deepgram_error)
            deepgram_live.registerHandler(deepgram_live.event.CLOSE, self.handle_deepgram_close)
            deepgram_live.registerHandler(deepgram_live.event.TRANSCRIPT_RECEIVED, self.get_deepgram_recognised_text)
            return deepgram_live
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error ExoDevWebSocketConsumer in %s at handle_deepgram_error %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})
            return None

    async def send_data_to_azure_stream(self, audio_data):
        self.stream.write(audio_data)

    def send_to_deepgram(self, audio_data):
        self.deepgram_live.send(audio_data)

    async def handle_deepgram_error(self, error_data):
        logger.error("Error ExoDevWebSocketConsumer in %s at handle_deepgram_error", str(error_data), extra={'AppName': 'EasyAssist'})

    async def handle_deepgram_close(self, close_data):
        #self.deepgram_live = await self.initialize_deepgram()
        pass
        # logger.error("Error ExoDevWebSocketConsumer in %s at handle_deepgram_close", str(close_data), extra={'AppName': 'EasyAssist'})

    def get_recognised_transcribed_text(self, event: speechsdk.SessionEventArgs):
        logger.info("get_recognised_transcribed_text is called in ExoDevWebSocketConsumer", extra={'AppName': 'EasyAssist'})
        try:
            if event.result.text.strip():
                self.recognised_transcript = event.result.text
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
            response = self.polly_client.synthesize_speech(VoiceId='Kajal', OutputFormat='pcm', Text=text_to_speak, Engine='neural', SampleRate='8000', LanguageCode='en-IN')
            audio_stream = base64.b64encode(response['AudioStream'].read()).decode("ascii")
            for i in range(0, len(audio_stream), self.rate_of_frequency):
                logger.info("Get Azure TTS loop count inside while %s",str(i), extra={'AppName': 'EasyAssist'})
                await self.send_audio_chunk(audio_stream[i:i+self.rate_of_frequency])
        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in get_text_to_speech_data ExoDevWebSocketConsumer %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})

    async def get_deepgram_recognised_text(self, json_data):
        try:
            logger.info("Transcript recived on ExoDevWebSocketConsumer is %s", json_data['channel']['alternatives'][0]['transcript'], extra={'AppName': 'EasyAssist'})
            self.recognised_transcript += json_data['channel']['alternatives'][0]['transcript']
            if json_data['channel']['alternatives'][0]['transcript'].strip():
                await self.send(json.dumps({'event': 'clear', 'stream_sid': self.stream_sid}))
            if json_data["speech_final"] and self.recognised_transcript.strip():
                logger.info("Transcript function in side if %s", self.recognised_transcript, extra={'AppName': 'EasyAssist'})
                await self.get_text_to_speech_data(self.recognised_transcript)
                self.recognised_transcript = ""
        except KeyError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Error in print_transcript ExoDevWebSocketConsumer %s at %s", str(e), str(exc_tb.tb_lineno), extra={'AppName': 'EasyAssist'})