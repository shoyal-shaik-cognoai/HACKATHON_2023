import sys
import json
import logging
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sender_name = self.scope['url_route']['kwargs']['sender_name']
        # self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = 'chat_%s' % self.sender_name

        # # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'text_data': text_data,
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        text_data = event['text_data']

        # Send message to WebSocket
        await self.send(text_data=text_data)
