from django.urls import re_path
from . import consumers
from . import consumers_eco_voicebot

websocket_urlpatterns = [
    # re_path(r'^ws/chat/',
    #     consumers.ChatConsumer.as_asgi()),
    re_path(r'^ws/echo/$', consumers_eco_voicebot.ExoDevWebSocketConsumer.as_asgi()),

]