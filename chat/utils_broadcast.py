import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def broadcast_room_event(room_id: int, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("No channel layer configured; skip broadcast to room %s", room_id)
        return
    payload = {"type": "chat.message", **kwargs}
    async_to_sync(channel_layer.group_send)(f"chat_{room_id}", payload)
