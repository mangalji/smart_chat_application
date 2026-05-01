import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from .models import ChatRoom, GroupMember, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close()
            return
        try:
            self.room_id = int(self.scope["url_route"]["kwargs"]["room_id"])
        except (KeyError, TypeError, ValueError):
            await self.close()
            return
        ok = await self._user_in_room(self.user.id, self.room_id)
        if not ok:
            await self.close()
            return
        self.group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def _user_in_room(self, user_id, room_id):
        return GroupMember.objects.filter(room_id=room_id, user_id=user_id).exists()

    @database_sync_to_async
    def _save_text_message(self, body):
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
        except ChatRoom.DoesNotExist:
            return None, None
        msg = Message.objects.create(room=room, sender=self.user, body=body.strip())
        return msg.id, msg.created_at.isoformat()

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        if data.get("type") != "chat_message":
            return
        body = (data.get("body") or "").strip()
        if not body:
            return
        msg_id, created_iso = await self._save_text_message(body)
        if msg_id is None:
            return
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "event": "message",
                "message_id": msg_id,
                "sender_id": self.user.id,
                "sender_email": self.user.email,
                "sender_name": self.user.get_full_name() or self.user.email,
                "body": body,
                "created_at": created_iso,
                "has_media": False,
                "media_url": None,
                "media_name": None,
            },
        )

    async def chat_message(self, event):
        out = {k: v for k, v in event.items() if k != "type"}
        await self.send(text_data=json.dumps(out))
