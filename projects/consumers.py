import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

class ProjectConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.room_group_name = f'project_{self.project_id}'
        self.user = self.scope['user']

        # Reject anonymous users
        if self.user.is_anonymous:
            await self.close()
            return

        # Check if user is a member of the project (async DB query)
        is_member = await self.is_project_member()
        if not is_member:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket (e.g., from client)
    async def receive(self, text_data):
        data = json.loads(text_data)
        # We'll handle client messages later if needed
        pass

    # Receive message from room group (broadcast)
    async def project_update(self, event):
        # Send the update data to the WebSocket
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def is_project_member(self):
        from .models import Project
        try:
            project = Project.objects.get(pk=self.project_id)
            return self.user in project.members.all()
        except Project.DoesNotExist:
            return False