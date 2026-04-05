from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_room_event(room_id: int, **kwargs):
    channel_layer = get_channel_layer()
    payload = {"type": "chat.message", **kwargs}
    async_to_sync(channel_layer.group_send)(f"chat_{room_id}", payload)
